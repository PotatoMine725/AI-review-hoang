"""Dựng cả ma trận 3 preset × 2 tỉ lệ, kiểm tra ffprobe, đo thời gian/RAM, chụp khung hình.

    uv run python run_matrix.py --set fixture --runs 1          # asset mẫu, chạy ở bất kỳ máy nào
    uv run python prepare_real.py && uv run python run_matrix.py --set real
    uv run python run_matrix.py --set real --encoders cpu,nvenc,qsv --runs 3   # đo (mất vài phút)

Giao thức đo: lần chạy đầu tiên của cả phiên là khởi động (fontconfig dựng cache) và bị bỏ;
mỗi cấu hình chạy `--runs` lần, báo trung vị. RAM = `maxrss` mà `ffmpeg -benchmark` báo.
Ghi `results/measurements-<set>-<min>-<max>s.json` và `.md`; khung hình vào
`frames/<min>-<max>s/` (commit được, nhỏ). Hậu tố là mốc thời lượng đang áp dụng
(`config.py`, mặc định `40-45s`), nên kết quả của mốc khác (vd. `measurements-real.*` của mốc cũ
15–25 s) không bị ghi đè.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from config import ConfigError, load_limits
from graph import Encoder
from media import MediaError, extract_frame
from presets import PRESETS, RATIOS, Ratio
from render_plan import PlanError, load_plan
from renderer import RENDER_TIMEOUT_S, ROOT, RenderResult, render
from timeline import Timeline, build_timeline

OUT = ROOT / "output"
RESULTS = ROOT / "results"  # số đo (commit được, nhỏ)
PLAN_DIRS = {"fixture": ROOT / "plans", "real": ROOT / "local" / "plans"}
# Cảnh (từ 0) lấy khung hình cho README: real = cảnh 5, ảnh AI thật, câu "Nắp khóa kín, không rò
# nước…" (không có tên thương hiệu); fixture = cảnh 9, câu thử dấu "Tiết kiệm 390.000đ — dùng thử
# miễn phí ngay hôm nay!".
FRAME_SCENE = {"real": 4, "fixture": 8}


def limits_label() -> str:
    """Hậu tố theo mốc thời lượng đang áp dụng, vd. `40-45s`."""
    lim = load_limits()
    return f"{lim.min_total_s:g}-{lim.max_total_s:g}s"


def frames_dir() -> Path:
    return ROOT / "frames" / limits_label()  # khung của mốc cũ 15–25 s nằm thẳng trong frames/


def machine_info() -> dict[str, str]:
    info = {"os": platform.platform(), "python": platform.python_version()}
    cmd = (
        "$c=Get-CimInstance Win32_Processor|Select -First 1;"
        "$m=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1);"
        "$g=(Get-CimInstance Win32_VideoController|%{$_.Name}) -join '; ';"
        '"$($c.Name)|$($c.NumberOfCores)|$($c.NumberOfLogicalProcessors)|$m|$g"'
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout.strip()  # fmt: skip
        cpu, cores, threads, ram, gpu = out.split("|")
        info |= {"cpu": cpu, "cores": cores, "threads": threads, "ram_gb": ram, "gpu": gpu}
    except (OSError, subprocess.SubprocessError, ValueError):
        info["cpu"] = platform.processor()
    ffmpeg = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
    info["ffmpeg"] = (ffmpeg.stdout.splitlines() or ["?"])[0]
    return info


def run_one(plan_path: Path, ratio: Ratio, encoder: Encoder, tag: str) -> RenderResult:
    plan = load_plan(plan_path)
    out = OUT / f"{tag}-{plan_path.stem}-{ratio.replace(':', 'x')}-{encoder}.mp4"
    return render(plan, ratio, out, encoder=encoder)


def save_frame(tag: str, preset_id: str, ratio: Ratio, video: Path, tl: Timeline) -> None:
    """Chụp 1 khung nhỏ cho README. 9:16 rộng 270 px, 16:9 rộng 480 px (đủ đọc dấu tiếng Việt)."""
    ts = tl.scenes[FRAME_SCENE[tag]]
    # real: giữa câu; fixture: đầu câu, để thấy "Tiết kiệm 390.000đ — dùng"
    at = ts.voice_start_s + (0.25 if tag == "fixture" else ts.voice_s * 0.5)
    name = f"{tag}-{preset_id}-{ratio.replace(':', 'x')}.png"
    extract_frame(video, frames_dir() / name, at, width=270 if ratio == "9:16" else 480)


def frames_only(tag: str, encoder: Encoder) -> int:
    """Chụp lại khung hình từ MP4 đã dựng trong output/, không dựng lại."""
    for preset_id, preset in PRESETS.items():
        plan = load_plan(PLAN_DIRS[tag] / f"{preset_id}.json")
        tl = build_timeline(plan, preset)
        for ratio in RATIOS:
            video = OUT / f"{tag}-{preset_id}-{ratio.replace(':', 'x')}-{encoder}.mp4"
            save_frame(tag, preset_id, ratio, video, tl)
            print("frame", video.name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--frames-only", action="store_true", help="chỉ chụp lại khung hình")
    parser.add_argument("--set", choices=["fixture", "real"], default="real")
    parser.add_argument("--runs", type=int, default=3, help="số lần đo mỗi cấu hình")
    parser.add_argument("--encoders", default="cpu,nvenc", help="cpu,nvenc,qsv")
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument(
        "--only", metavar="PRESET,RATIO,ENCODER",
        help="chỉ đo lại một cấu hình (vd. co-dien,16:9,nvenc) và gộp vào results/ hiện có",
    )  # fmt: skip
    args = parser.parse_args()
    encoders = cast(list[Encoder], args.encoders.split(","))
    if args.frames_only:
        return frames_only(args.set, encoders[0])
    plan_dir = PLAN_DIRS[args.set]
    tag = args.set
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    warmed = args.no_warmup
    only = tuple(args.only.split(",")) if args.only else None
    if only and (len(only) != 3 or only[0] not in PRESETS or only[1] not in RATIOS):
        parser.error("--only cần dạng PRESET,RATIO,ENCODER (vd. co-dien,16:9,nvenc)")

    try:
        for preset_id in PRESETS:
            plan_path = plan_dir / f"{preset_id}.json"
            for ratio in RATIOS:
                for encoder in encoders:
                    if only and (preset_id, ratio, encoder) != only:
                        continue
                    if not warmed:
                        run_one(plan_path, ratio, "cpu", tag)  # khởi động, bỏ kết quả
                        warmed = True
                    results: list[RenderResult] = []
                    try:
                        for _ in range(args.runs):
                            results.append(run_one(plan_path, ratio, encoder, tag))
                    except MediaError as exc:
                        failures.append(f"{preset_id} {ratio} {encoder}: {exc}")
                        print(f"FAIL {preset_id} {ratio} {encoder}: {exc}", file=sys.stderr)
                        continue
                    last = results[-1]
                    walls = [r.ffmpeg_wall_s for r in results]
                    rss = [r.max_rss_mb for r in results if r.max_rss_mb]
                    cpus = [r.cpu_s for r in results if r.cpu_s]
                    rows.append({
                        "preset": preset_id, "ratio": ratio, "encoder": encoder,
                        "wall_s_median": round(statistics.median(walls), 2),
                        "wall_s_all": [round(w, 2) for w in walls],
                        "cpu_s_median": round(statistics.median(cpus), 1) if cpus else None,
                        "max_rss_mb": round(max(rss), 0) if rss else None,
                        "duration_s": round(last.info.duration_s, 2),
                        "size_mb": round(last.info.size_bytes / 1e6, 2),
                        "resolution": f"{last.info.width}x{last.info.height}",
                        "fps": round(last.info.fps, 2),
                        "codec": f"{last.info.video_codec}/{last.info.audio_codec}",
                        "file": last.path.name,
                    })  # fmt: skip
                    print(
                        f"OK {preset_id:18} {ratio} {encoder:5} "
                        f"{rows[-1]['wall_s_median']:6.1f}s  {rows[-1]['size_mb']}MB"
                    )
                    if encoder == encoders[0]:
                        save_frame(tag, preset_id, ratio, last.path, last.timeline)
    except (PlanError, MediaError, ConfigError, OSError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2

    RESULTS.mkdir(exist_ok=True)
    stem = f"measurements-{tag}-{limits_label()}"
    if only:  # gộp vào kết quả cũ: thay đúng dòng vừa đo, giữ nguyên các dòng khác
        old = json.loads((RESULTS / f"{stem}.json").read_text(encoding="utf-8"))
        key = lambda r: (r["preset"], r["ratio"], r["encoder"])  # noqa: E731
        fresh = {key(r): r for r in rows}
        rows = [fresh.pop(key(r), r) for r in old["rows"]] + list(fresh.values())
        order = {p: i for i, p in enumerate(PRESETS)}
        rows.sort(key=lambda r: (order[r["preset"]], RATIOS.index(r["ratio"]), r["encoder"]))
    lim = load_limits()
    payload = {
        "machine": machine_info(),
        "limits_s": {"min": lim.min_total_s, "max": lim.max_total_s},
        "scenes": len(load_plan(plan_dir / f"{next(iter(PRESETS))}.json").scenes),
        "render_timeout_s": RENDER_TIMEOUT_S,
        "runs": args.runs,
        "rows": rows,
        "failures": failures,
    }
    (RESULTS / f"{stem}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "| Preset | Tỉ lệ | Encoder | Dựng (s, trung vị) | CPU-s | RAM đỉnh (MB) "
        "| Dài (s) | MB | Phân giải |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['preset']} | {r['ratio']} | {r['encoder']} | {r['wall_s_median']} "
            f"| {r['cpu_s_median']} | {(r['max_rss_mb'] or 0):.0f} | {r['duration_s']} "
            f"| {r['size_mb']} | {r['resolution']} |"
        )
    (RESULTS / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    for f in failures:
        print("THẤT BẠI:", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
