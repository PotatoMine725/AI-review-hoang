"""Kiểm MP4 cuối bằng ffprobe: tổng thời lượng so với mốc chung (#77 `config.py`).

Ngoài khoảng thì BÁO (trạng thái `too_short`/`too_long`), không kéo dài, không tua chậm, không cắt
câu. Mốc lấy từ `config.load_limits`, không chép số mốc vào đây.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from worker.produce.config import Limits, ProduceConfig
from worker.produce.runner import Runner, require_ok

# Dự kiến từ timeline và ffprobe lệch quá mức này (giây) là dấu hiệu hai bên tính khác nhau.
PREDICT_TOLERANCE_S = 0.1


@dataclass(frozen=True)
class ProbeInfo:
    duration_s: float
    width: int
    height: int


def probe(path: Path, cfg: ProduceConfig, runner: Runner) -> ProbeInfo:
    res = require_ok(
        runner(
            [
                cfg.ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            timeout_s=120,
        ),
        f"ffprobe {path.name}",
    )
    data = json.loads(res.stdout)
    video = next(s for s in data["streams"] if s.get("codec_type") == "video")
    return ProbeInfo(float(data["format"]["duration"]), int(video["width"]), int(video["height"]))


def check_duration(actual_s: float, limits: Limits) -> str:
    """'ok' | 'too_short' | 'too_long'."""
    if actual_s < limits.min_total_s:
        return "too_short"
    if actual_s > limits.max_total_s:
        return "too_long"
    return "ok"
