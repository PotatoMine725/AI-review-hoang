"""render(plan, ratio, out_path): chạy ffmpeg và kiểm tra MP4 đầu ra."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from config import RenderLimits, load_limits
from graph import Encoder, build_command
from media import MediaError, VideoInfo, probe_video, tool
from presets import FPS, FRAME_SIZE, Ratio, get_preset
from render_plan import RenderPlan
from subtitles import build_ass
from timeline import Timeline, build_timeline

ROOT = Path(__file__).resolve().parent
FONTS_DIR = ROOT / "fonts"
WORK_ROOT = ROOT / ".work"  # cùng ổ đĩa với fonts/ để dùng được đường dẫn tương đối
# Quá ngưỡng này là treo (ffmpeg không tự thoát sau lỗi NVENC). Dựng bình thường: xem số đo
# mốc 40–45 s trong README (CPU, máy tác giả); ngưỡng này chưa phải tiêu chí hiệu năng đã chốt.
RENDER_TIMEOUT_S = 300
# Sai lệch cho phép giữa thời lượng ffprobe đọc và timeline / mốc min–max (làm tròn khung AAC,
# container). Lớn hơn mức này là lỗi dựng thật.
DURATION_TOLERANCE_S = 0.15


@dataclass(frozen=True)
class RenderResult:
    path: Path
    ratio: Ratio
    preset: str
    encoder: Encoder
    ffmpeg_wall_s: float  # thời gian chạy ffmpeg (đồng hồ treo tường)
    cpu_s: float | None  # utime + stime do ffmpeg -benchmark báo
    max_rss_mb: float | None  # RAM đỉnh của tiến trình ffmpeg (-benchmark: maxrss)
    info: VideoInfo
    timeline: Timeline


def _bench(stderr: str) -> tuple[float | None, float | None]:
    """Đọc dòng `bench: utime=... stime=... rtime=...` và `bench: maxrss=... KiB` của ffmpeg."""
    cpu = rss = None
    m = re.search(r"bench: utime=([\d.]+)s stime=([\d.]+)s", stderr)
    if m:
        cpu = float(m.group(1)) + float(m.group(2))
    m = re.search(r"bench: maxrss=(\d+)KiB", stderr)
    if m:
        rss = int(m.group(1)) / 1024
    return cpu, rss


def check_output(
    info: VideoInfo, ratio: Ratio, tl: Timeline, limits: RenderLimits | None = None
) -> None:
    """MP4 phải đúng độ phân giải, 30 fps, H.264 + AAC, thời lượng sát timeline và nằm trong
    [min, max] của `limits`. Thời lượng là số ffprobe đo trên file cuối, nên đã tính cả khoảng
    nghỉ đầu/cuối cảnh và phần chuyển cảnh chồng nhau."""
    limits = limits or load_limits()
    w, h = FRAME_SIZE[ratio]
    problems = []
    if (info.width, info.height) != (w, h):
        problems.append(f"kích thước {info.width}x{info.height}, cần {w}x{h}")
    if abs(info.fps - FPS) > 0.01:
        problems.append(f"fps {info.fps:.2f}, cần {FPS}")
    if info.video_codec != "h264" or info.audio_codec != "aac":
        problems.append(f"codec {info.video_codec}/{info.audio_codec}, cần h264/aac")
    if abs(info.duration_s - tl.total_s) > DURATION_TOLERANCE_S:
        problems.append(f"dài {info.duration_s:.2f} s, timeline {tl.total_s:.2f} s")
    if not (
        limits.min_total_s - DURATION_TOLERANCE_S
        <= info.duration_s
        <= limits.max_total_s + DURATION_TOLERANCE_S
    ):
        problems.append(
            f"dài {info.duration_s:.2f} s, ngoài khoảng cho phép "
            f"{limits.min_total_s:g}–{limits.max_total_s:g} s"
        )
    if problems:
        raise MediaError("MP4 đầu ra không đạt: " + "; ".join(problems))


def render(
    plan: RenderPlan,
    ratio: Ratio,
    out_path: Path,
    encoder: Encoder = "cpu",
    verbose: bool = False,
    keep_work: bool = False,
) -> RenderResult:
    """Dựng `plan` thành MP4 theo `ratio`. Lỗi plan (độ dài ngoài khoảng của `config`, mặc định
    40–45 s...) ném PlanError trước khi chạy ffmpeg; ffmpeg lỗi hoặc MP4 sai thông số ném
    MediaError. Mốc đọc MỘT lần ở đây và dùng cho cả kiểm plan lẫn kiểm MP4 cuối."""
    limits = load_limits()
    preset = get_preset(plan.preset)
    tl = build_timeline(plan, preset, limits=limits)
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    WORK_ROOT.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="r-", dir=WORK_ROOT))
    try:
        (work / "subs.ass").write_text(build_ass(tl, preset, ratio), encoding="utf-8")
        fonts_rel = Path(os.path.relpath(FONTS_DIR, work)).as_posix()
        cmd = build_command(
            plan, tl, preset, ratio, out_path, encoder,
            fonts_dir=fonts_rel, log_level="verbose" if verbose else "info",
        )  # fmt: skip
        (work / cmd.filter_name).write_text(cmd.filter_script, encoding="utf-8")
        cmd.args[0] = tool("ffmpeg")

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd.args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=work, check=False, timeout=RENDER_TIMEOUT_S,
            )  # fmt: skip
        except subprocess.TimeoutExpired:
            raise MediaError(
                f"ffmpeg ({encoder}) không xong sau {RENDER_TIMEOUT_S} s, đã dừng "
                "(đã gặp NVENC treo sau lỗi mã hoá; xem README)"
            ) from None
        wall = time.perf_counter() - start
        if verbose:
            (out_path.with_suffix(".log")).write_text(proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            tail = " | ".join(proc.stderr.strip().splitlines()[-8:])
            raise MediaError(f"ffmpeg lỗi (mã {proc.returncode}): {tail}")
        cpu, rss = _bench(proc.stderr)
    finally:
        if not keep_work:
            shutil.rmtree(work, ignore_errors=True)

    info = probe_video(out_path)
    check_output(info, ratio, tl, limits)
    return RenderResult(
        path=out_path, ratio=ratio, preset=preset.id, encoder=encoder,
        ffmpeg_wall_s=wall, cpu_s=cpu, max_rss_mb=rss, info=info, timeline=tl,
    )  # fmt: skip
