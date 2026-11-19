"""webm của Playwright → MP4 H.264 và đoạn `assets.json` cho khâu dựng."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from worker.demo.errors import DemoError
from worker.demo.recorder import ReplayResult
from worker.demo.schema import ActionScript, Wait, WaitFor
from worker.produce.assets import Asset, AssetFocus, AssetPart

FPS = 30


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise DemoError(f"không tìm thấy {name} trong PATH (cài FFmpeg, cần cả ffprobe)")
    return path


def to_mp4(webm: Path, mp4: Path) -> None:
    """VP8 của Playwright bitrate thấp, nên mã hoá lại ở CRF thấp để không mất thêm chi tiết."""
    mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _tool("ffmpeg"), "-y", "-loglevel", "error", "-i", str(webm),
        "-vf", f"fps={FPS}", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(mp4),
    ]  # fmt: skip
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise DemoError(f"ffmpeg lỗi: {r.stderr.strip()[-400:]}")


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )  # fmt: skip
    try:
        return float(r.stdout.strip())
    except ValueError as ex:
        raise DemoError(f"ffprobe không đọc được thời lượng của {path}") from ex


# Đoạn chờ (wait, wait_for, giữ cuối) dài hơn IDLE_MAX_S bị rút còn IDLE_HEAD_S đầu + IDLE_TAIL_S
# cuối: người xem thấy lúc bắt đầu chờ (vd. "Processing...") và lúc có kết quả, không phải ngồi
# xem màn hình đứng yên (chuyển đổi PDF→Word mất ~26 s).
IDLE_MAX_S = 1.2
IDLE_HEAD_S = 0.4
IDLE_TAIL_S = 0.8
END_HOLD_S = 1.8  # giữ khung kết quả cuối
MIN_SPAN_S = 0.1


def compact_spans(
    script: ActionScript, result: ReplayResult, duration_s: float
) -> list[tuple[float, float]]:
    """Các đoạn (giây trong video) giữ lại, theo mốc kết thúc từng bước (`step_times_s`).

    Bước thao tác (click, gõ, cuộn, upload...) giữ nguyên; bước chờ dài thì cắt giữa. Đoạn liền
    nhau được nối lại. Mốc tính theo đồng hồ replay nên lệch video vài chục ms (kẹp vào thời lượng
    thật). Thiếu `step_times_s` (kết quả cũ) thì giữ một đoạn từ lúc trang tải xong tới hết.
    """
    start = min(result.start_s, max(0.0, duration_s - 1.0))
    end = min(result.end_s, duration_s)
    times = result.step_times_s
    if len(times) != len(script.steps):
        return [(start, end)]
    raw: list[tuple[float, float]] = []

    def keep(a: float, b: float, idle: bool) -> None:
        a, b = max(a, start), min(b, end)
        if b - a < MIN_SPAN_S:
            return
        if idle and b - a > IDLE_MAX_S:
            raw.extend([(a, a + IDLE_HEAD_S), (b - IDLE_TAIL_S, b)])
        else:
            raw.append((a, b))

    prev = 0.0
    for step, t in zip(script.steps, times, strict=True):
        keep(prev, t, isinstance(step, (Wait, WaitFor)))
        prev = t
    last = times[-1] if times else start
    if end - last > 0:
        raw.append((max(last, start), min(end, max(last, start) + END_HOLD_S)))
    spans: list[tuple[float, float]] = []
    for a, b in sorted(raw):
        if spans and a - spans[-1][1] < 0.05:
            spans[-1] = (spans[-1][0], max(spans[-1][1], b))
        else:
            spans.append((a, b))
    return [(round(a, 2), round(b, 2)) for a, b in spans if b - a >= MIN_SPAN_S] or [(start, end)]


def build_asset(
    script: ActionScript, result: ReplayResult, duration_s: float, rel_path: str
) -> Asset:
    """Asset `kind=clip` đúng mô hình của `worker.produce.assets` (khâu dựng đọc được ngay).

    `parts` là các đoạn của `compact_spans` (đã bỏ phần chờ dài); `anchor="end"` để khâu dựng,
    khi clip vẫn dài hơn cảnh, giữ phần cuối có kết quả thao tác thay vì phần đầu.
    """
    spans = compact_spans(script, result, duration_s)
    focus = None
    if result.focus:
        t = result.focus.t_s
        for i, (a, b) in enumerate(spans):
            if a <= t <= b:
                focus = AssetFocus(part=i, source_t=round(t, 2), rect=result.focus.rect)
                break
    return Asset(
        kind="clip",
        path=rel_path,
        crop=script.crop,
        parts=[AssetPart(start_s=a, end_s=b) for a, b in spans],
        focus=focus,
        anchor="end",
        source=f"Playwright recordVideo ({script.generated_by or 'script tay'})",
    )
