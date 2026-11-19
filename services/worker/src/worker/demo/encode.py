"""webm của Playwright → MP4 H.264 và đoạn `assets.json` cho khâu dựng."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from worker.demo.errors import DemoError
from worker.demo.recorder import ReplayResult
from worker.demo.schema import ActionScript
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


def build_asset(
    script: ActionScript, result: ReplayResult, duration_s: float, rel_path: str
) -> Asset:
    """Asset `kind=clip` đúng mô hình của `worker.produce.assets` (khâu dựng đọc được ngay).

    Đoạn lấy từ lúc trang tải xong tới hết thao tác; mốc tính theo đồng hồ replay nên lệch
    video vài chục ms (đã kẹp vào thời lượng thật).
    """
    start = min(result.start_s, max(0.0, duration_s - 1.0))
    end = min(result.end_s, duration_s)
    focus = None
    if result.focus:
        t = min(max(result.focus.t_s, start), end)
        focus = AssetFocus(part=0, source_t=round(t, 2), rect=result.focus.rect)
    return Asset(
        kind="clip",
        path=rel_path,
        crop=script.crop,
        parts=[AssetPart(start_s=round(start, 2), end_s=round(end, 2))],
        focus=focus,
        source=f"Playwright recordVideo ({script.generated_by or 'script tay'})",
    )
