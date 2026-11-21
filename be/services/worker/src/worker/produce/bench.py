"""Đo thời gian từng khâu của `produce` theo nhiều cấu hình, trên máy render thật.

    uv run python -m worker.produce.bench <script.json> --input <input.json> \\
        --assets <assets.json> --out <thư mục> [--configs seq3,par4,par6,par8] [--repeat 2] \\
        [--mode preview|final] [--ratios 16:9,9:16] [--cache cold|warm]

Mỗi (cấu hình × lượt) chạy `produce` một lần, ghi `bench.json` và `bench.md` (bảng so sánh). Lỗi
của một lượt (kể cả lỗi bất định) được ghi lại và không dừng cả ma trận. `--cache cold` (mặc định)
dùng thư mục cache TTS/cảnh mới cho mỗi lượt nên số đo gồm cả nạp model và dựng lại mọi cảnh;
`warm` dùng chung một cache cho cả ma trận (đo hiệu quả cache). Nếu có `nvidia-smi`, mỗi lượt đo
thêm mức dùng GPU/encoder/VRAM/nhiệt độ đỉnh (không bật NVENC, chỉ quan sát).

Cấu hình có sẵn: `seq3` (tuần tự, 3 worker mỗi tỉ lệ), `par<N>` (song song N tiến trình,
cache cảnh tắt trong chế độ cold). Hậu tố nối bằng `+`: `cuda` (TTS PyTorch CUDA), `nolock`
(HYPERFRAMES_RENDER_LOCK=off, bỏ hàng đợi render cùng tài khoản), `fast`
(`--experimental-fast-capture`), `gpu` (`--browser-gpu`), vd. `par6+nolock+fast`.
Phiên bản HyperFrames được ghi vào `bench.json`/`bench.md` (`--hf-version` để ghi tay).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from worker.produce.config import ProduceConfig
from worker.produce.pipeline import ProduceResult, produce
from worker.produce.render import available_ram_mb

GPU_QUERY = "utilization.gpu,utilization.encoder,memory.used,temperature.gpu,power.draw"
GPU_KEYS = ("gpu_util_pct", "enc_util_pct", "vram_mb", "temp_c", "power_w")
Produce = Callable[..., ProduceResult]


SUFFIXES = ("cuda", "nolock", "fast", "gpu")
HF_FLAGS = {"fast": "--experimental-fast-capture", "gpu": "--browser-gpu"}


def parse_config(name: str, base: ProduceConfig, *, warm: bool) -> ProduceConfig:
    """`seq3`, `par6`, `par6+cuda`, `par4+nolock+fast` → ProduceConfig. Tên lạ thì ValueError."""
    core, *extras = name.split("+")
    bad = [x for x in extras if x not in SUFFIXES]
    if bad:
        raise ValueError(f"hậu tố cấu hình không hợp lệ: {bad[0]!r} (có {', '.join(SUFFIXES)})")
    over: dict[str, Any] = {"tts_device": "cuda" if "cuda" in extras else base.tts_device}
    flags = [HF_FLAGS[x] for x in extras if x in HF_FLAGS]
    if flags:
        over["hf_args"] = " ".join([base.hf_args, *flags]).strip()
    if "nolock" in extras:
        over["hf_env"] = ",".join(filter(None, [base.hf_env, "HYPERFRAMES_RENDER_LOCK=off"]))
    if m := re.fullmatch(r"seq(\d+)", core):
        over |= {"render_mode": "sequential", "workers": m.group(1)}
    elif m := re.fullmatch(r"par(\d+)", core):
        over |= {"render_mode": "parallel", "render_jobs": int(m.group(1))}
    else:
        raise ValueError(f"cấu hình không hợp lệ: {name!r} (dạng seq3, par6, par6+cuda)")
    over["render_cache"] = warm and over["render_mode"] == "parallel"
    return base.model_copy(update=over)


def hyperframes_version(cfg: ProduceConfig) -> str | None:
    """Phiên bản HyperFrames của spike (`npx hyperframes --version`); không đọc được thì None."""
    npx = shutil.which("npx")
    if not npx:
        return None
    try:
        out = subprocess.run(
            [npx, "--no-install", "hyperframes", "--version"],
            cwd=cfg.render_v2,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out.splitlines()[-1] if out else None


class GpuSampler:
    """Lấy mẫu `nvidia-smi` mỗi `interval_s` giây trong lúc một lượt chạy. Không có thì rỗng."""

    def __init__(self, interval_s: float = 2.0) -> None:
        self._interval = interval_s
        self._rows: list[list[float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.available = shutil.which("nvidia-smi") is not None

    def _sample(self) -> list[float] | None:
        try:
            out = subprocess.run(
                ["nvidia-smi", f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.splitlines()[0]
            return [float(v) for v in out.split(",")]
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            return None  # bỏ mẫu lỗi (một số trường báo [N/A])

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            if (row := self._sample()) is not None:
                self._rows.append(row)

    def __enter__(self) -> GpuSampler:
        if self.available:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def peaks(self) -> dict[str, float | int | None]:
        if not self._rows:
            return {"samples": 0, **{k: None for k in GPU_KEYS}}
        cols = list(zip(*self._rows, strict=True))
        return {
            "samples": len(self._rows),
            **{k: max(c) for k, c in zip(GPU_KEYS, cols, strict=True)},
        }


def summarize(res: ProduceResult | None, wall_s: float, error: str | None) -> dict[str, Any]:
    """Phần đáng so sánh của một lượt từ `render_report.json`."""
    if res is None:
        return {"ok": False, "wall_s": round(wall_s, 1), "error": error}
    rep = res.report
    outs = rep.get("outputs", [])
    err = rep.get("error")
    return {
        "ok": res.ok,
        "status": rep["status"],
        "wall_s": round(wall_s, 1),
        "timings_s": rep.get("timings_s"),
        "actual_s": rep.get("actual_s"),
        "hf_peak_ram_mb": max((o.get("hf_peak_ram_mb") or 0 for o in outs), default=0) or None,
        "render": [o.get("render") for o in outs],
        "outputs_ok": [o.get("ok") for o in outs],
        "error": error or (f"{err.get('code')}: {err.get('message')}" if err else None),
        "warnings": len(rep.get("warnings", [])),
    }


def run_matrix(
    script: Path,
    input_path: Path,
    assets: Path,
    out_dir: Path,
    configs: list[str],
    *,
    repeat: int,
    mode: str,
    ratios: tuple[str, ...],
    warm: bool,
    base: ProduceConfig | None = None,
    produce_fn: Produce = produce,
    gpu_interval_s: float = 2.0,
) -> list[dict[str, Any]]:
    base = base or ProduceConfig.from_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    shared_cache = Path(tempfile.mkdtemp(prefix="bench-cache-")) if warm else None
    runs: list[dict[str, Any]] = []
    for name in configs:
        cfg0 = parse_config(name, base, warm=warm)
        for i in range(1, repeat + 1):
            cache = shared_cache or Path(tempfile.mkdtemp(prefix="bench-cache-"))
            cfg = cfg0.model_copy(update={"cache_dir": cache})
            run_out = out_dir / f"{name}-{i}"
            ram_before = available_ram_mb()
            res: ProduceResult | None = None
            error: str | None = None
            t0 = time.perf_counter()
            with GpuSampler(gpu_interval_s) as gpu:
                try:
                    res = produce_fn(
                        script, input_path, assets, run_out, mode=mode, ratios=ratios, cfg=cfg
                    )
                except Exception as e:  # noqa: BLE001 - lỗi lạ cũng là dữ liệu của phép đo
                    error = f"{type(e).__name__}: {e}"
            row = summarize(res, time.perf_counter() - t0, error)
            runs.append(
                {
                    "config": name,
                    "run": i,
                    "ram_free_before_mb": ram_before,
                    "gpu": gpu.peaks() if gpu.available else None,
                    **row,
                }
            )
            print(f"[{name} #{i}] ok={row['ok']} wall={row['wall_s']} s {row['error'] or ''}")
            if not warm and not shared_cache:
                shutil.rmtree(cache, ignore_errors=True)
    if shared_cache:
        shutil.rmtree(shared_cache, ignore_errors=True)
    return runs


def _med(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def markdown(runs: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    lines = [
        "# Đo `produce` theo cấu hình",
        "",
        f"Chế độ `{meta['mode']}`, tỉ lệ {', '.join(meta['ratios'])}, cache `{meta['cache']}`, "
        f"{meta['repeat']} lượt mỗi cấu hình, HyperFrames {meta.get('hyperframes') or '?'}. "
        "Số là trung vị các lượt thành công (giây).",
        "",
        "| Cấu hình | Lượt OK | TTS | Render | Tổng | RAM HF MB | GPU % | Enc % | VRAM MB |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name in dict.fromkeys(r["config"] for r in runs):
        mine = [r for r in runs if r["config"] == name]
        ok = [r for r in mine if r["ok"]]

        def pick(key: str, ok: list[dict[str, Any]] = ok) -> float | None:
            return _med([r["timings_s"][key] for r in ok if (r.get("timings_s") or {}).get(key)])

        def gpu(key: str, mine: list[dict[str, Any]] = mine) -> Any:
            vals = [r["gpu"][key] for r in mine if r.get("gpu") and r["gpu"].get(key) is not None]
            return max(vals) if vals else "-"

        ram = max((r["hf_peak_ram_mb"] or 0 for r in ok), default=0) or "-"
        total = pick("total_s") or _med([r["wall_s"] for r in ok]) or "-"
        lines.append(
            f"| {name} | {len(ok)}/{len(mine)} | {pick('tts_s') or '-'} | "
            f"{pick('render_s') or '-'} | {total} "
            f"| {ram} | {gpu('gpu_util_pct')} | {gpu('enc_util_pct')} | {gpu('vram_mb')} |"
        )
    failed = [r for r in runs if not r["ok"] or r.get("error")]
    if failed:
        lines += ["", "## Lượt lỗi hoặc có cảnh báo lỗi", ""]
        lines += [f"- `{r['config']}` #{r['run']}: {r['error']}" for r in failed]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m worker.produce.bench", description=__doc__)
    ap.add_argument("script", type=Path)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--assets", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--configs", default="seq3,par4,par6,par8")
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--mode", choices=("preview", "final"), default="preview")
    ap.add_argument("--ratios", default="16:9,9:16")
    ap.add_argument("--cache", choices=("cold", "warm"), default="cold")
    ap.add_argument("--hf-version", default="", help="ghi tay phiên bản HyperFrames (vd. 0.9.69)")
    args = ap.parse_args(argv)
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    ratios = tuple(r.strip() for r in args.ratios.split(",") if r.strip())
    try:
        for c in configs:
            parse_config(c, ProduceConfig(), warm=False)
    except ValueError as e:
        ap.error(str(e))
    if args.repeat < 1:
        ap.error("--repeat phải ≥ 1")
    runs = run_matrix(
        args.script,
        args.input,
        args.assets,
        args.out,
        configs,
        repeat=args.repeat,
        mode=args.mode,
        ratios=ratios,
        warm=args.cache == "warm",
    )
    meta = {
        "mode": args.mode,
        "ratios": list(ratios),
        "cache": args.cache,
        "repeat": args.repeat,
        "hyperframes": args.hf_version or hyperframes_version(ProduceConfig.from_env()),
    }
    (args.out / "bench.json").write_text(
        json.dumps({"meta": meta, "runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.out / "bench.md").write_text(markdown(runs, meta), encoding="utf-8")
    print(f"\nGhi {args.out / 'bench.md'} và bench.json")
    return 0 if any(r["ok"] for r in runs) else 2


if __name__ == "__main__":
    sys.exit(main())
