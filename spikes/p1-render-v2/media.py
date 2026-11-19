"""Gọi ffmpeg/ffprobe: đo độ dài voice, cắt + tua clip cho từng cảnh, đọc thông số MP4."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from plan import Clip


class MediaError(RuntimeError):
    """Lỗi chạy ffmpeg/ffprobe hoặc file media hỏng."""


def tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MediaError(f"không tìm thấy {name} trong PATH (cài: winget install Gyan.FFmpeg)")
    return path


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd, check=False,
    )  # fmt: skip
    if proc.returncode != 0:
        tail = " | ".join(proc.stderr.strip().splitlines()[-6:])
        raise MediaError(f"{Path(args[0]).stem} lỗi (mã {proc.returncode}): {tail}")
    return proc


def probe_duration(path: Path) -> float:
    proc = run([tool("ffprobe"), "-v", "error", "-of", "json", "-show_entries",
                "format=duration", str(path)])  # fmt: skip
    return float(json.loads(proc.stdout)["format"]["duration"])


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration_s: float
    video_codec: str
    audio_codec: str | None
    pix_fmt: str


def probe_video(path: Path) -> VideoInfo:
    proc = run([tool("ffprobe"), "-v", "error", "-of", "json", "-show_entries",
                "stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt:format=duration",
                str(path)])  # fmt: skip
    data = json.loads(proc.stdout)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    num, den = v["avg_frame_rate"].split("/")
    return VideoInfo(
        width=v["width"], height=v["height"], fps=int(num) / int(den),
        duration_s=float(data["format"]["duration"]), video_codec=v["codec_name"],
        audio_codec=a["codec_name"] if a else None, pix_fmt=v["pix_fmt"],
    )  # fmt: skip


def prepare_clip(clip: Clip, scene_s: float, speed: float, root: Path, out_dir: Path,
                 fps: int) -> Path:  # fmt: skip
    """Cắt các đoạn, crop, nối, tua theo `speed`, đúng `scene_s` giây, 30 fps, keyframe mỗi 0,5 s
    (HyperFrames tua video theo khung; keyframe thưa gây đứng hình). Không tiếng.
    Kết quả cache theo tham số, dùng chung cho cả hai tỉ lệ."""
    _, _, cw, ch = clip.crop
    for p in clip.parts:
        if p.crop and abs(p.crop[2] / p.crop[3] - cw / ch) > 0.01:
            raise MediaError(f"đoạn {p.src}: crop {p.crop} khác tỉ lệ với crop chung {clip.crop}")
    key = json.dumps([clip.model_dump(), round(scene_s, 4), fps], sort_keys=True)
    out = out_dir / f"clip-{hashlib.sha256(key.encode()).hexdigest()[:12]}.mp4"
    if out.exists():
        return out
    out_dir.mkdir(parents=True, exist_ok=True)

    args = [tool("ffmpeg"), "-v", "error", "-y"]
    chains = []
    for i, part in enumerate(clip.parts):
        src = (root / part.src).resolve()
        if not src.exists():
            raise MediaError(f"thiếu clip {src} (chạy prepare_local.py)")
        args += ["-i", str(src)]
        x, y, w, h = part.crop or clip.crop
        chains.append(
            f"[{i}:v]trim=start={part.start_s}:end={part.end_s},setpts=PTS-STARTPTS,"
            f"crop={w}:{h}:{x}:{y},scale={cw}:{ch}:flags=lanczos,setsar=1,fps={fps}[p{i}]"
        )
    labels = "".join(f"[p{i}]" for i in range(len(clip.parts)))
    chains.append(
        f"{labels}concat=n={len(clip.parts)}:v=1:a=0,setpts=PTS/{speed:.6f},fps={fps},"
        f"tpad=stop_mode=clone:stop_duration=1[v]"
    )
    args += [
        "-filter_complex", ";".join(chains), "-map", "[v]", "-t", f"{scene_s:.4f}", "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-g", str(fps // 2),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]  # fmt: skip
    run(args)
    return out
