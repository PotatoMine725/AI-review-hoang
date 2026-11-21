"""Đầu vào/đầu ra của CLI bàn giao theo từng đoạn (tách khỏi CLI để test không cần model).

Mỗi đoạn giữ liên kết: `segment_id` ↔ lời gốc (`voice_text`) ↔ văn bản sau chuẩn hoá (`normalized`)
↔ audio (`path`) ↔ thời lượng đo từ lần sinh thật (`duration_s`). Sửa lời hoặc bảng phát âm thì phải sinh lại
audio của đoạn đó; `stale_segments` chỉ ra các đoạn trong log cũ không còn khớp.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Segment:
    index: int  # đánh số từ 1; cũng là khoá trong tts-log.json
    segment_id: str
    text: str


def load_segments(path: Path) -> list[Segment]:
    """Đọc `{"segments": [{"text", "id"?}]}` hoặc `{"scenes": [{"voice_text", "id"?}]}`.

    `segment_id` lấy từ `segment_id` hoặc `id` (hoặc `scene_id` với scenes);
    thiếu thì dùng `s01`, `s02`... theo thứ tự.
    ID trùng nhau là lỗi (sẽ làm lẫn audio với nhau).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if "segments" in data:
        rows, text_key, id_keys = data["segments"], "text", ("segment_id", "id")
    elif "scenes" in data:
        rows, text_key, id_keys = data["scenes"], "voice_text", ("segment_id", "id", "scene_id")
    else:
        raise ValueError("Đầu vào cần khoá 'segments' (text) hoặc 'scenes' (voice_text)")
    out: list[Segment] = []
    for i, row in enumerate(rows, start=1):
        seg_id = next((str(row[k]) for k in id_keys if row.get(k) not in (None, "")), f"s{i:02d}")
        out.append(Segment(i, seg_id, row[text_key]))
    ids = [s.segment_id for s in out]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        raise ValueError(f"segment_id trùng nhau: {dup}")
    return out


def log_entry(
    seg: Segment, spoken: str, audio_name: str, duration_s: float, gen_s: float, *, voice: str
) -> dict[str, Any]:
    """Một dòng của tts-log.json (khoá "1", "2"... như log của #78), thêm `segment_id`, `voice`."""
    return {
        "segment_id": seg.segment_id,
        "voice_text": seg.text,
        "normalized": spoken,
        "path": audio_name,
        "duration_s": round(duration_s, 3),
        "gen_s": round(gen_s, 2),
        "voice": voice,
    }


def stale_segments(
    segments: list[Segment], log: Mapping[str, Any], spoken_of: Callable[[Segment], str]
) -> list[str]:
    """Các đoạn trong log cũ không còn khớp với lời/bảng phát âm hiện tại (cần sinh lại audio và timing).

    Khớp = cùng `segment_id`, cùng `voice_text` và cùng văn bản sau chuẩn hoá.
    Đoạn chưa có trong log cũng tính là stale.
    """
    stale: list[str] = []
    for seg in segments:
        old = log.get(str(seg.index))
        if (
            not isinstance(old, dict)
            or old.get("segment_id") != seg.segment_id
            or old.get("voice_text") != seg.text
            or old.get("normalized") != spoken_of(seg)
        ):
            stale.append(seg.segment_id)
    return stale
