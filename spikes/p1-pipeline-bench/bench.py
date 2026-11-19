"""Đo thời gian toàn luồng PDFCraft (P1-07). Chỉ đo, không sửa code sản phẩm.

    python bench.py env
    python bench.py crawl extract script
    python bench.py tts ffmpeg hf hf-par
    python bench.py report                      # gom results.json thành bảng trung vị

Orchestrator chỉ dùng stdlib. Từng bước gọi code của spike khác bằng subprocess với venv của
spike đó (xem `drivers/`), nên cần các worktree sau cùng tồn tại (đổi bằng biến môi trường):
    P1_TTS_VI (#73), P1_RENDER_V2 (#88), P1_RENDER (#77), P1_PDFCRAFT_CRAWL, P1_ENV_FILE.
Kết quả ghi vào `P1_BENCH_OUT` (mặc định D:\\tmp\\p1-pipeline-bench), ngoài git.
Mỗi phép đo chạy 2 lần, báo trung vị (2 mẫu: trung bình của hai giá trị). Máy phải rảnh.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
WORKTREES = HERE.parents[2]  # .../.claude/worktrees
REPO_WORKER = HERE.parents[1] / "services" / "worker"

TTS_VI = Path(os.environ.get("P1_TTS_VI", WORKTREES / "p1-tts-vi" / "spikes" / "p1-tts-vi"))
RENDER_V2 = Path(
    os.environ.get("P1_RENDER_V2", WORKTREES / "p1-render-v2" / "spikes" / "p1-render-v2")
)
RENDER_FF = Path(
    os.environ.get("P1_RENDER", WORKTREES / "spike-p1-render" / "spikes" / "p1-render")
)
CRAWL_DIR = Path(os.environ.get("P1_PDFCRAFT_CRAWL", r"D:\tmp\crawl-pdfcraft-lang"))
ENV_FILE = Path(
    os.environ.get("P1_ENV_FILE", WORKTREES.parents[1] / "services" / "worker" / ".env")
)
OUT = Path(os.environ.get("P1_BENCH_OUT", r"D:\tmp\p1-pipeline-bench"))
M2_INPUT = (
    WORKTREES / "m2-generate-script" / "docs" / "report" / "m2-first-run-pdfcraft" / "input.json"
)
HF_PLAN = "plans/pdfcraft-40-45s.json"
FF_PLAN = "local/plans/dien-anh-toi-gian.json"  # mốc 40–45 s của #77 (nội dung Acme Demo, KHÔNG phải PDFCraft)
RATIOS = ("16:9", "9:16")
RUNS = 2
RESULTS = OUT / "results.json"


def py(spike: Path) -> str:
    return str(spike / ".venv" / "Scripts" / "python.exe")


def save(step: str, data: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cur = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    cur[step] = data
    RESULTS.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{step}] đã ghi {RESULTS}")


def load() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}


def med(xs: list[float]) -> float:
    return round(statistics.median(xs), 2)


def sh(
    cmd: list[str], cwd: Path, timeout: int = 1800, env: dict | None = None
) -> tuple[float, str, int]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env={**os.environ, **(env or {})})  # fmt: skip
    return time.perf_counter() - t0, p.stdout + p.stderr, p.returncode


def last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError("không có dòng JSON: " + text[-600:])


def idle_check() -> dict:
    """Chụp tình trạng máy trước khi đo: tải CPU, RAM trống, VRAM đang dùng."""
    ps = ("$c=(Get-CimInstance Win32_Processor).LoadPercentage;"
          "$o=Get-CimInstance Win32_OperatingSystem;"
          "\"$c $([math]::Round($o.FreePhysicalMemory/1024))\"")  # fmt: skip
    _, o, _ = sh(["powershell", "-NoProfile", "-Command", ps], HERE, 60)
    cpu, free = (o.split() + ["?", "?"])[:2]
    _, g, _ = sh(
        ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader"], HERE, 30
    )
    return {
        "cpu_load_pct": cpu,
        "free_ram_mb": free,
        "gpu": g.strip(),
        "at": datetime.now().isoformat(timespec="seconds"),
    }


# --------------------------------------------------------------------------- các bước


def step_env() -> None:
    _, ff, _ = sh(["ffmpeg", "-version"], HERE, 30)
    _, node, _ = sh(["node", "-v"], HERE, 30)
    save("env", {"idle": idle_check(), "ffmpeg": ff.splitlines()[0], "node": node.strip(),
                 "paths": {"tts": str(TTS_VI), "render_v2": str(RENDER_V2), "render_ff": str(RENDER_FF)}})  # fmt: skip


def step_crawl() -> None:
    """Đọc crawl PDFCraft 21/10 (không crawl lại). Tách thời gian fetch và thời gian chờ lịch sự."""
    j = json.loads((CRAWL_DIR / "crawl.json").read_text(encoding="utf-8"))
    reqs = [r for r in j["requests"] if "t" in r]
    gaps = [b["t"] - a["t"] for a, b in zip(reqs, reqs[1:], strict=False)]
    pages = j["pages_used"]
    save("crawl", {
        "source": f"{CRAWL_DIR} (đọc output cũ, không chạy lại)", "started_at": j["started_at"],
        "crawl_seconds": j["crawl_seconds"], "pages_used": pages, "requests": len(reqs),
        "pages_found": j["pages_found"], "s_per_page": round(j["crawl_seconds"] / pages, 2),
        "s_per_request": round(j["crawl_seconds"] / len(reqs), 2),
        "gap_between_requests_median_s": med(gaps), "gap_max_s": round(max(gaps), 2),
        "min_observed_interval_s": j["min_observed_interval_s"],
    })  # fmt: skip


def llm_step(name: str, module: str, args: list[str], outdir: Path) -> None:
    """1 mẫu duy nhất (LLM free tier, độ trễ dao động). Ghi thêm số lần gọi để biết RPD đã dùng."""
    idle = idle_check()
    import_s, _, _ = sh(["uv", "run", "python", "-c", f"import {module}"], REPO_WORKER, 300)
    wall, out, rc = sh(["uv", "run", "python", "-m", module, *args, "--out", str(outdir), "--env", str(ENV_FILE)],
                       REPO_WORKER, 1800)  # fmt: skip
    m = re.search(r"llm_calls=(\d+)", out)
    cost = outdir / "cost_breakdown.json"
    items = json.loads(cost.read_text(encoding="utf-8")).get("items", []) if cost.exists() else []
    save(name, {
        "samples": 1, "note": "1 mẫu, độ trễ LLM dao động; wall gồm cả khởi động uv+import",
        "wall_s": round(wall, 1), "import_overhead_s": round(import_s, 1),
        "wall_minus_import_s": round(wall - import_s, 1), "returncode": rc,
        "llm_calls": int(m.group(1)) if m else len(items),
        "tokens_in": sum(i.get("tokens_in", 0) for i in items), "tokens_out": sum(i.get("tokens_out", 0) for i in items),
        "cost_usd": round(sum(i.get("cost_usd", 0) for i in items), 6), "model": items[0].get("model") if items else None,
        "attempts": [i.get("attempt") for i in items], "idle": idle,
        "stdout_tail": "\n".join(out.strip().splitlines()[-12:]),
    })  # fmt: skip


def step_extract() -> None:
    llm_step("extract", "worker.m1.extract", [str(CRAWL_DIR)], OUT / "extract")


def step_script() -> None:
    llm_step("script", "worker.m2.generate", [str(M2_INPUT)], OUT / "script")


def step_tts() -> None:
    runs: dict[str, list[dict]] = {}
    plan = RENDER_V2 / HF_PLAN
    for label, device, backend in (
        ("onnx-cpu", "cpu", "onnx"),
        ("pytorch-cuda", "cuda", "pytorch"),
    ):
        for i in range(RUNS):
            idle = idle_check()
            wall, out, rc = sh([py(TTS_VI / "vieneu"), str(HERE / "drivers" / "tts_driver.py"), "--tts-dir",
                                str(TTS_VI / "vieneu"), "--plan", str(plan), "--device", device,
                                "--backend", backend, "--work", str(OUT / "tts" / f"{label}-{i}")],
                               TTS_VI / "vieneu", 1800)  # fmt: skip
            if rc != 0:
                runs.setdefault(label, []).append({"error": out[-800:], "idle": idle})
                continue
            r = last_json(out)
            r["process_wall_s"] = round(wall, 1)
            r["idle"] = idle
            runs.setdefault(label, []).append(r)
            print(
                f"  {label} #{i}: load {r['load_s']}s gen {r['gen_total_s']}s RTF {r['rtf']} cache {r['cache_s']}s"
            )
    save("tts", runs)


def step_ffmpeg() -> None:
    res: list[dict] = []
    warm = OUT / "ff" / "warm.mp4"
    sh([py(RENDER_FF), str(HERE / "drivers" / "ff_driver.py"), "--spike", str(RENDER_FF), "--plan", FF_PLAN,
        "--ratio", "16:9", "--res", "1080", "--out", str(warm)], RENDER_FF, 600)  # fmt: skip
    for ratio in RATIOS:
        for resn in ("1080", "720"):
            for i in range(RUNS):
                out = OUT / "ff" / f"ff-{ratio.replace(':', 'x')}-{resn}-{i}.mp4"
                idle = idle_check()
                _, o, rc = sh([py(RENDER_FF), str(HERE / "drivers" / "ff_driver.py"), "--spike", str(RENDER_FF),
                               "--plan", FF_PLAN, "--ratio", ratio, "--res", resn, "--out", str(out)],
                              RENDER_FF, 900)  # fmt: skip
                r: dict[str, Any] = last_json(o) if rc == 0 else {"error": o[-600:]}
                r.update(idle=idle, run=i)
                res.append(r)
                print(f"  ffmpeg {ratio} {resn}p #{i}: {r.get('total_wall_s')} s")
    save("ffmpeg", res)


def hf_cmd(
    ratio: str, resn: str, tag: str, workers: str = "auto", quality: str = "looks"
) -> list[str]:
    return [py(RENDER_V2), str(HERE / "drivers" / "hf_driver.py"), "--spike", str(RENDER_V2), "--plan", HF_PLAN,
            "--ratio", ratio, "--res", resn, "--workers", workers, "--quality", quality,
            "--out", str(OUT / "hf"), "--tag", tag]  # fmt: skip


def step_hf() -> None:
    res: list[dict] = []
    for ratio in RATIOS:
        for resn, quality in (("1080", "looks"), ("720", "looks"), ("1080", "draft")):
            for i in range(RUNS):
                tag = f"{resn}{quality}-{i}"
                idle = idle_check()
                _, o, rc = sh(hf_cmd(ratio, resn, tag, quality=quality), RENDER_V2, 1500)
                r: dict[str, Any] = last_json(o) if rc == 0 else {"error": o[-800:]}
                r.update(idle=idle, run=i, variant=f"{resn}p-{quality}", ratio=ratio)
                res.append(r)
                print(f"  hf {ratio} {resn}p {quality} #{i}: {r.get('total_wall_s')} s")
                save("hf", res)


def step_hf_par() -> None:
    """Dựng 2 tỉ lệ cùng lúc ở 1080p: workers auto/auto và 3+3. So với tổng 2 lần chạy tuần tự."""
    res: list[dict] = []
    for workers in ("auto", "3"):
        for i in range(RUNS):
            idle = idle_check()
            t0 = time.perf_counter()
            with ThreadPoolExecutor(2) as ex:
                futs = [
                    ex.submit(sh, hf_cmd(r, "1080", f"par{workers}-{i}", workers), RENDER_V2, 2400)
                    for r in RATIOS
                ]
                outs = [f.result() for f in futs]
            wall = time.perf_counter() - t0
            parts = [last_json(o) if rc == 0 else {"error": o[-600:]} for _, o, rc in outs]
            res.append(
                {
                    "workers_each": workers,
                    "run": i,
                    "wall_both_s": round(wall, 1),
                    "parts": parts,
                    "idle": idle,
                }
            )
            print(f"  hf song song workers={workers} #{i}: {wall:.1f} s")
            save("hf_parallel", res)


def step_report() -> None:
    d = load()
    print(
        json.dumps(
            {k: v for k, v in d.items() if k in ("crawl", "extract", "script")},
            ensure_ascii=False,
            indent=1,
        )
    )

    def group(rows: list[dict], keys: tuple[str, ...], val: str) -> None:
        g: dict[tuple, list[float]] = {}
        for r in rows:
            if val in r:
                g.setdefault(tuple(r[k] for k in keys), []).append(r[val])
        for k, xs in sorted(g.items()):
            print(f"  {k}: median {med(xs)} (n={len(xs)}, {xs})")

    print("ffmpeg total_wall_s")
    group(d.get("ffmpeg", []), ("ratio", "res"), "total_wall_s")
    print("hf total_wall_s")
    group(d.get("hf", []), ("ratio", "variant"), "total_wall_s")
    print("tts gen_total_s")
    for label, rows in d.get("tts", {}).items():
        ok = [r for r in rows if "error" not in r]
        print(f"  {label}: load {med([r['load_s'] for r in ok])} gen {med([r['gen_total_s'] for r in ok])} "
              f"rtf {med([r['rtf'] for r in ok])} ram {med([r['peak_ram_mb'] for r in ok])} "
              f"vram {[r['peak_vram_mb'] for r in ok]} cache {med([r['cache_s'] for r in ok])}")  # fmt: skip
    for r in d.get("hf_parallel", []):
        print(f"  parallel workers={r['workers_each']} #{r['run']}: {r['wall_both_s']} s")


STEPS = {"env": step_env, "crawl": step_crawl, "extract": step_extract, "script": step_script, "tts": step_tts,
         "ffmpeg": step_ffmpeg, "hf": step_hf, "hf-par": step_hf_par, "report": step_report}  # fmt: skip

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    todo = sys.argv[1:] or ["report"]
    for s in todo:
        if s not in STEPS:
            raise SystemExit(f"bước lạ: {s}; có: {', '.join(STEPS)}")
        STEPS[s]()
