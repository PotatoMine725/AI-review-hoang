"""Gọi ffmpeg/ffprobe: đo thông số file, lấy khung hình. Không chứa logic dựng video."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class MediaError(RuntimeError):
    """Lỗi chạy ffmpeg/ffprobe hoặc file media hỏng."""


def tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MediaError(f"không tìm thấy {name} trong PATH (cài: winget install Gyan.FFmpeg)")
    return path


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Chạy lệnh, trả kết quả; lỗi thì ném MediaError kèm vài dòng cuối của stderr."""
    proc = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd, check=False,
    )  # fmt: skip
    if proc.returncode != 0:
        tail = " | ".join(proc.stderr.strip().splitlines()[-6:])
        raise MediaError(f"{Path(args[0]).stem} lỗi (mã {proc.returncode}): {tail}")
    return proc


def _probe(path: Path, *extra: str) -> dict:
    proc = run([tool("ffprobe"), "-v", "error", "-of", "json", *extra, str(path)])
    return json.loads(proc.stdout)


def probe_duration(path: Path) -> float:
    """Độ dài (giây) của file audio/video."""
    data = _probe(path, "-show_entries", "format=duration")
    try:
        return float(data["format"]["duration"])
    except (KeyError, ValueError) as exc:
        raise MediaError(f"không đọc được độ dài của {path}") from exc


def probe_image_size(path: Path) -> tuple[int, int]:
    """Kích thước thật (rộng, cao) của ảnh hoặc clip."""
    data = _probe(path, "-select_streams", "v:0", "-show_entries", "stream=width,height")
    streams = data.get("streams") or []
    if not streams:
        raise MediaError(f"{path} không có luồng hình")
    return int(streams[0]["width"]), int(streams[0]["height"])


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration_s: float
    video_codec: str
    audio_codec: str | None
    size_bytes: int


def probe_video(path: Path) -> VideoInfo:
    """Thông số MP4 sau khi dựng (để kiểm tra đầu ra)."""
    data = _probe(path, "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate"
                  ":format=duration,size")  # fmt: skip
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if video is None:
        raise MediaError(f"{path} không có luồng hình")
    num, _, den = str(video["r_frame_rate"]).partition("/")
    fps = float(num) / float(den or 1)
    return VideoInfo(
        width=int(video["width"]),
        height=int(video["height"]),
        fps=fps,
        duration_s=float(data["format"]["duration"]),
        video_codec=video["codec_name"],
        audio_codec=audio["codec_name"] if audio else None,
        size_bytes=int(data["format"]["size"]),
    )


def contact_sheet(video: Path, out: Path, times: list[float], width: int = 240) -> Path:
    """Ghép các khung hình tại `times` thành 1 ảnh ngang (để xem nhanh cả video)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    args = [tool("ffmpeg"), "-y", "-v", "error"]
    for t in times:
        args += ["-ss", f"{t:.2f}", "-i", str(video)]
    scaled = "".join(f"[{i}:v]scale={width}:-2[s{i}];" for i in range(len(times)))
    stack = "".join(f"[s{i}]" for i in range(len(times))) + f"hstack=inputs={len(times)}"
    run([*args, "-filter_complex", scaled + stack, "-frames:v", "1", str(out)])
    return out


def extract_frame(video: Path, out: Path, at_s: float, width: int = 360) -> Path:
    """Lấy 1 khung hình PNG nhỏ (rộng `width` px) tại giây `at_s`, để đưa vào README."""
    out.parent.mkdir(parents=True, exist_ok=True)
    run([
        tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{at_s:.2f}", "-i", str(video),
        "-frames:v", "1", "-vf", f"scale={width}:-2", str(out),
    ])  # fmt: skip
    return out
