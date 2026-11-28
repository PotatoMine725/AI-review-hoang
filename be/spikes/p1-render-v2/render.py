"""CLI: plan JSON → MP4 9:16 và 16:9.

    uv run python render.py plans/pdfcraft-pagenum-word.json
    uv run python render.py plans/pdfcraft-pagenum-word.json --ratio 9:16 --workers 3 --tag run2

Các bước cho mỗi tỉ lệ:
  1. compose.py dựng project HyperFrames (.work/…): template + dữ liệu cảnh + clip đã cắt.
  2. HyperFrames CLI (node, ghim trong package.json) chụp từng khung bằng Chrome headless
     → video.mp4
     (chỉ hình, không tiếng).
  3. FFmpeg: đốt phụ đề ASS + đặt voice VieNeu đúng mốc (adelay), chuẩn hoá loudness → MP4 cuối.
Số đo (thời gian từng bước, RAM đỉnh) ghi vào results/measurements.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from compose import ROOT, compose, load_template
from limits import load_limits
from measure import PeakRam
from media import MediaError, VideoInfo, probe_duration, probe_video, run, tool
from plan import PlanError, Ratio, RenderPlan, load_plan
from slots import clip_speed, focus_time
from subtitles import FRAME_SIZE, build_ass
from timeline import Timeline, build_timeline

DEFAULT_OUT = Path(r"D:\Code\AI-Content-Review\demo-out\v2")
HF_BIN = ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
RESULTS = ROOT / "results" / "measurements.json"
FRAMES_DIR = ROOT / "frames"
RATIO_TAG = {"9:16": "9x16", "16:9": "16x9"}
HF_TIMEOUT_S = 900

ENCODE_ARGS = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-profile:v", "high",
    "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
    "-colorspace", "bt709", "-color_range", "tv",
]  # fmt: skip


@dataclass
class RatioResult:
    ratio: str
    output: str
    total_s: float
    hf_wall_s: float  # HyperFrames: dựng + chụp khung + encode video trung gian
    hf_phases: dict[str, float]  # số liệu HyperFrames tự báo (capture, encode, setup…)
    hf_peak_ram_mb: int | None  # node + mọi tiến trình Chrome
    hf_mode: str
    ffmpeg_wall_s: float  # phụ đề + audio + encode cuối
    ffmpeg_max_rss_mb: float | None
    compose_s: float
    total_wall_s: float
    workers: str
    browser_gpu: str


def voice_durations(plan: RenderPlan) -> dict[str, float]:
    out = {}
    for scene in plan.scenes:
        for seg in scene.narration_segments:
            wav = ROOT / seg.voice
            if not wav.exists():
                raise MediaError(f"thiếu voice {wav} (chạy prepare_local.py)")
            out[seg.segment_id] = round(probe_duration(wav), 3)
    return out


def _hf_summary(log: str) -> tuple[dict[str, float], str]:
    phases: dict[str, float] = {}
    mode = ""
    for line in log.splitlines():
        if " capture · " in line and "compile" in line:
            mode = " · ".join(line.strip().split(" · ")[:2])
            # "capture 2m 44.5s · encode (during capture) 2m 44.3s · ..."
            for part in line.strip().split(" · "):
                m = re.fullmatch(r"([a-z][a-z ()]*?) (?:(\d+)m )?([\d.]+)s", part)
                if m:
                    key = m.group(1).replace(" (during capture)", "_overlap")
                    phases[key] = round(int(m.group(2) or 0) * 60 + float(m.group(3)), 1)
    m = re.search(r"rendered in (?:(\d+)m )?([\d.]+)s", log)
    if m:
        phases["rendered_in"] = int(m.group(1) or 0) * 60 + float(m.group(2))
    return phases, mode


def run_hyperframes(work: Path, out: Path, fps: int, workers: str, browser_gpu: str
                    ) -> tuple[float, dict[str, float], str, int | None]:  # fmt: skip
    args = ["node", str(HF_BIN), "render", str(work), "-o", str(out), "--fps", str(fps),
            "-q", "looks", "--workers", workers]  # fmt: skip
    if browser_gpu == "off":
        args.append("--no-browser-gpu")
    elif browser_gpu == "on":
        args.append("--browser-gpu")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "NO_COLOR": "1"}
    t0 = time.perf_counter()
    with PeakRam() as ram:
        proc = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=ROOT, env=env, check=False, timeout=HF_TIMEOUT_S,
        )  # fmt: skip
    wall = time.perf_counter() - t0
    log = proc.stdout + proc.stderr
    (work / "hyperframes.log").write_text(log, encoding="utf-8")
    if proc.returncode != 0 or not out.exists():
        tail = " | ".join(log.strip().splitlines()[-8:])
        raise MediaError(f"hyperframes lỗi (mã {proc.returncode}): {tail}")
    phases, mode = _hf_summary(log)
    return wall, phases, mode, ram.peak_mb


POP_SRC = "aevalsrc=0.7*sin(2*PI*(380+2600*t)*t)*exp(-28*t):d=0.16:s=48000"


def write_pop(path: Path) -> None:
    """Tiếng "pop" ngắn tự tổng hợp (không vướng bản quyền), dùng làm hiệu ứng đầu câu."""
    run([tool("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", POP_SRC, "-ac", "2",
         str(path)])  # fmt: skip


@dataclass(frozen=True)
class AudioMix:
    filters: list[str]  # filter_complex, ra nhãn [aout]
    sfx: bool  # có input pop.wav (ngay sau các voice)
    music: Path | None  # có input nhạc (sau pop nếu có)
    pops_s: list[float]


def audio_mix(plan: RenderPlan, tl: Timeline, tpl: dict) -> AudioMix:
    """Đồ thị audio: voice đặt đúng mốc (+ pop đầu mỗi câu trừ câu đầu, + nhạc nền nhỏ dần khi có
    giọng). Input: 0 = hình, 1..n = voice theo thứ tự câu, rồi pop.wav, rồi nhạc. Hàm thuần."""
    audio = plan.audio
    sfx = (audio.sfx if audio and audio.sfx else tpl.get("sfx")) or "none"
    music = None
    if audio and audio.music:
        music = Path(audio.music)
        music = music if music.is_absolute() else (ROOT / music).resolve()
    n = len(tl.segments)
    f: list[str] = []
    labels = ""
    for i, seg in enumerate(tl.segments, start=1):
        ms = round(seg.start_s * 1000)
        f.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
        labels += f"[a{i}]"
    f.append(f"{labels}amix=inputs={n}:normalize=0:duration=longest[voice]")
    parts = ["[voice]"]
    nxt = n + 1
    pops: list[float] = []
    if sfx == "pop":
        pops = [round(max(0.0, g.start_s - 0.05), 3) for g in tl.segments[1:]]
        if pops:
            db = audio.sfx_db if audio else -10.0
            split = "".join(f"[p{k}]" for k in range(len(pops)))
            f.append(f"[{nxt}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"asplit={len(pops)}{split}")  # fmt: skip
            outs = ""
            for k, t in enumerate(pops):
                ms = round(t * 1000)
                f.append(f"[p{k}]adelay={ms}|{ms}[q{k}]")
                outs += f"[q{k}]"
            f.append(f"{outs}amix=inputs={len(pops)}:normalize=0,volume={db}dB[sfx]")
            parts.append("[sfx]")
            nxt += 1
    if music is not None:
        db = audio.music_db if audio else -22.0
        total = tl.total_s
        f[f.index(f"{labels}amix=inputs={n}:normalize=0:duration=longest[voice]")] = (
            f"{labels}amix=inputs={n}:normalize=0:duration=longest,asplit=2[voice][vkey]"
        )
        f.append(
            f"[{nxt}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={db}dB,"
            f"atrim=0:{total:.3f},afade=t=in:d=0.6,afade=t=out:st={max(0.0, total - 1.5):.3f}:d=1.5"
            "[mus]"
        )
        # Nhạc tự nhỏ đi khi có giọng (ducking), lên lại ở khoảng nghỉ.
        f.append("[mus][vkey]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[duck]")
        parts.append("[duck]")
    f.append(
        f"{''.join(parts)}amix=inputs={len(parts)}:normalize=0:duration=first,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad[aout]"
    )
    return AudioMix(f, sfx == "pop" and bool(pops), music, pops)


def finalize(plan: RenderPlan, tl: Timeline, ratio: Ratio, work: Path, video: Path, out: Path
             ) -> tuple[float, float | None]:  # fmt: skip
    """Đốt phụ đề + trộn voice đúng mốc → MP4 cuối. Trả (thời gian, RAM đỉnh ffmpeg)."""
    (work / "subs.ass").write_text(build_ass(plan, tl, ratio), encoding="utf-8")
    args = [tool("ffmpeg"), "-y", "-v", "error", "-i", str(video)]
    voices = {g.segment_id: g.voice for s in plan.scenes for g in s.narration_segments}
    for seg in tl.segments:
        args += ["-i", str((ROOT / voices[seg.segment_id]).resolve())]
    mix = audio_mix(plan, tl, load_template(plan.template))
    if mix.sfx:
        write_pop(work / "pop.wav")
        args += ["-i", "pop.wav"]
    if mix.music:
        args += ["-stream_loop", "-1", "-i", str(mix.music)]
    filters = list(mix.filters)
    # Đường dẫn tương đối (chạy trong work/) để tránh lỗi escape ổ đĩa "D:" trong filter.
    filters.append("[0:v]subtitles=subs.ass:fontsdir=template/fonts[vout]")
    args += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
        *ENCODE_ARGS, "-r", str(plan.fps), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{tl.total_s:.4f}", str(out),
    ]  # fmt: skip
    t0 = time.perf_counter()
    with PeakRam() as ram:  # -benchmark không in maxrss khi -v error, nên đo cây tiến trình
        run(args, cwd=work)
    wall = time.perf_counter() - t0
    return wall, ram.peak_mb


def check_output(info: VideoInfo, ratio: Ratio, tl: Timeline) -> None:
    w, h = FRAME_SIZE[ratio]
    problems = []
    if (info.width, info.height) != (w, h):
        problems.append(f"kích thước {info.width}x{info.height}, cần {w}x{h}")
    if abs(info.fps - tl.fps) > 0.01:
        problems.append(f"fps {info.fps:.2f}, cần {tl.fps}")
    if info.video_codec != "h264" or info.audio_codec != "aac" or info.pix_fmt != "yuv420p":
        problems.append(f"codec {info.video_codec}/{info.audio_codec}/{info.pix_fmt}")
    if abs(info.duration_s - tl.total_s) > 0.1:
        problems.append(f"dài {info.duration_s:.2f} s, timeline {tl.total_s:.2f} s")
    limits = load_limits()  # cùng mốc với bước kiểm plan (config #77)
    if not limits.min_total_s <= info.duration_s <= limits.max_total_s:
        problems.append(
            f"dài {info.duration_s:.2f} s ngoài {limits.min_total_s:g}–{limits.max_total_s:g} s"
        )
    if problems:
        raise MediaError("MP4 đầu ra không đạt: " + "; ".join(problems))


def export_frames(plan: RenderPlan, tl: Timeline, ratio: Ratio, video: Path) -> list[Path]:
    """1 khung nhỏ cho mỗi cảnh (0,25 s trước khi hết cảnh: mọi lớp đã hiện, zoom đã xong)."""
    FRAMES_DIR.mkdir(exist_ok=True)
    width = 360 if ratio == "9:16" else 640
    paths = []
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        t = ts.start_s + ts.duration_s - 0.25
        path = FRAMES_DIR / f"{scene.scene_id}-{scene.layout}-{RATIO_TAG[ratio]}.png"
        run([tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
             "-frames:v", "1", "-vf", f"scale={width}:-2:flags=lanczos", str(path)])  # fmt: skip
        paths.append(path)
    return paths


def render_ratio(plan: RenderPlan, plan_path: Path, tl: Timeline, ratio: Ratio, out_dir: Path,
                 workers: str, browser_gpu: str, tag: str, keep_work: bool, frames: bool
                 ) -> RatioResult:  # fmt: skip
    t_all = time.perf_counter()
    work = ROOT / ".work" / f"{plan_path.stem}-{RATIO_TAG[ratio]}"
    t0 = time.perf_counter()
    compose(plan, tl, ratio, work, ROOT / ".work" / "clips")
    compose_s = time.perf_counter() - t0

    video = work / "video.mp4"
    hf_wall, phases, mode, peak = run_hyperframes(work, video, plan.fps, workers, browser_gpu)

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"-{tag}" if tag else ""
    out = out_dir / f"{plan_path.stem}-{RATIO_TAG[ratio]}{suffix}.mp4"
    ff_wall, ff_rss = finalize(plan, tl, ratio, work, video, out)
    check_output(probe_video(out), ratio, tl)
    if frames:
        export_frames(plan, tl, ratio, out)
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return RatioResult(
        ratio=ratio, output=str(out), total_s=round(tl.total_s, 3), hf_wall_s=round(hf_wall, 1),
        hf_phases=phases, hf_peak_ram_mb=peak, hf_mode=mode, ffmpeg_wall_s=round(ff_wall, 1),
        ffmpeg_max_rss_mb=round(ff_rss) if ff_rss else None, compose_s=round(compose_s, 1),
        total_wall_s=round(time.perf_counter() - t_all, 1), workers=workers,
        browser_gpu=browser_gpu,
    )  # fmt: skip


def dry_run(plan: RenderPlan, tl: Timeline) -> None:
    """In timeline từng cảnh + tốc độ tua clip, không dựng hình (vài giây thay vì vài phút)."""
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        extra = ""
        if scene.clip:
            extra = f", clip x{clip_speed(scene.clip, ts.duration_s):.2f}"
            if scene.clip.focus:
                extra += f", zoom lúc {focus_time(scene.clip, ts.duration_s):.2f} s"
        end = ts.start_s + ts.duration_s
        print(f"  {scene.scene_id} {scene.layout:<12} {ts.start_s:6.2f}–{end:6.2f} s"
              f" ({ts.duration_s:5.2f} s, {len(scene.narration_segments)} câu{extra})")  # fmt: skip


def append_results(entry: dict) -> None:
    RESULTS.parent.mkdir(exist_ok=True)
    data = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
    data.append(entry)
    RESULTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--ratio", action="append", choices=["9:16", "16:9"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workers", default="auto", help="số worker Chrome của HyperFrames")
    ap.add_argument("--browser-gpu", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--tag", default="", help="hậu tố tên file (vd run2, để so hash)")
    ap.add_argument("--keep-work", action="store_true", help="giữ .work/ để mở bằng preview")
    ap.add_argument("--frames", action="store_true", help="xuất khung hình cho README")
    ap.add_argument("--no-record", action="store_true", help="không ghi results/")
    ap.add_argument("--dry-run", action="store_true", help="chỉ kiểm plan + timeline, không dựng")
    args = ap.parse_args()

    plan = load_plan(args.plan)
    durations = voice_durations(plan)
    tl = build_timeline(plan, durations)
    print(f"{plan.product}: {len(plan.scenes)} cảnh, {tl.total_s:.2f} s, "
          f"nghỉ lớn nhất giữa câu {tl.max_gap_s():.2f} s")  # fmt: skip
    if args.dry_run:
        try:
            dry_run(plan, tl)
        except PlanError as e:
            raise SystemExit(f"plan lỗi: {e}") from None
        return
    for ratio in cast(list[Ratio], args.ratio or plan.ratios):
        res = render_ratio(plan, args.plan, tl, ratio, args.out, args.workers, args.browser_gpu,
                           args.tag, args.keep_work, args.frames)  # fmt: skip
        print(
            f"[{ratio}] {res.output}\n"
            f"  HyperFrames {res.hf_wall_s}s ({res.hf_mode}; {res.hf_phases}), "
            f"RAM đỉnh {res.hf_peak_ram_mb} MB\n"
            f"  FFmpeg {res.ffmpeg_wall_s}s (RAM {res.ffmpeg_max_rss_mb} MB), "
            f"tổng {res.total_wall_s}s"
        )
        if not args.no_record:
            append_results({"at": datetime.now().isoformat(timespec="seconds"),
                            "plan": args.plan.name, "tag": args.tag, **asdict(res)})  # fmt: skip


if __name__ == "__main__":
    main()
