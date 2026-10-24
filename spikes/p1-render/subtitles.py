"""Phụ đề cháy vào hình: sinh file ASS (libass) từ timeline.

Không có timestamp theo từ (ADR-0004: TTS chỉ cho mốc theo câu), nên mỗi câu được cắt thành
cụm ngắn và chia thời gian theo số ký tự trong khoảng voice của câu đó.
"""

from __future__ import annotations

import math
import re

from presets import FRAME_SIZE, Preset, Ratio
from timeline import TimedScene, Timeline

# Vùng an toàn (px, theo hệ toạ độ ASS = kích thước khung): lề trái/phải. Lề dưới nằm ở preset.
SIDE_MARGIN: dict[str, int] = {"9:16": 90, "16:9": 240}
BASE_FONT_PX: dict[str, int] = {"9:16": 78, "16:9": 58}

_PUNCT_END = re.compile(r"[,.;:!?…]$")


def _ass_color(rgb: str, alpha: int = 0) -> str:
    """RRGGBB → &HAABBGGRR& (ASS dùng thứ tự BGR, alpha 0 = đặc)."""
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _ass_time(seconds: float) -> str:
    cs = round(seconds * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def chunk_caption(text: str, max_words: int) -> list[str]:
    """Cắt câu thành cụm ≤ max_words từ: ưu tiên ngắt ở dấu câu, rồi chia đều phần dài."""
    words = text.split()
    if not words:
        return []
    phrases: list[list[str]] = [[]]
    for word in words:
        phrases[-1].append(word)
        if _PUNCT_END.search(word):
            phrases.append([])
    phrases = [p for p in phrases if p]

    pieces: list[list[str]] = []
    for phrase in phrases:
        parts = math.ceil(len(phrase) / max_words)
        size = math.ceil(len(phrase) / parts)
        pieces.extend(phrase[i : i + size] for i in range(0, len(phrase), size))

    # Gộp cụm quá ngắn (1–2 từ) vào cụm kề nếu vẫn không vượt max_words.
    merged: list[list[str]] = []
    for piece in pieces:
        if (
            merged
            and (len(piece) <= 2 or len(merged[-1]) <= 2)
            and (len(merged[-1]) + len(piece) <= max_words)
        ):
            merged[-1].extend(piece)
        else:
            merged.append(list(piece))
    return [" ".join(p) for p in merged]


def split_times(chunks: list[str], t0: float, t1: float) -> list[tuple[float, float, str]]:
    """Chia [t0, t1] cho các cụm theo số ký tự; các cụm liền nhau, không hở."""
    total = sum(len(c) for c in chunks) or 1
    out: list[tuple[float, float, str]] = []
    cursor = t0
    for i, chunk in enumerate(chunks):
        end = t1 if i == len(chunks) - 1 else cursor + (t1 - t0) * len(chunk) / total
        out.append((cursor, end, chunk))
        cursor = end
    return out


def _window(ts: TimedScene, tail: float) -> tuple[float, float]:
    """Khoảng thời gian chữ hiện trong cảnh."""
    if ts.voice_s:
        return ts.voice_start_s, min(ts.end_s, ts.voice_start_s + ts.voice_s + tail / 2)
    return ts.voice_start_s, ts.end_s - tail


def build_ass(timeline: Timeline, preset: Preset, ratio: Ratio) -> str:
    width, height = FRAME_SIZE[ratio]
    base = BASE_FONT_PX[ratio]
    side = SIDE_MARGIN[ratio]
    size = round(base * preset.sub_size)
    card_size = round(base * preset.card_size)
    # Độ dày viền/bóng tính theo cỡ chữ, để giống nhau giữa hai tỉ lệ.
    outline = round(size * preset.sub_outline, 1)
    shadow = round(size * preset.sub_shadow, 1)
    bold = -1 if preset.bold else 0

    if preset.sub_box:
        border_style = 3  # hộp nền: OutlineColour là màu hộp, Outline là độ đệm
        outline_colour = _ass_color(preset.sub_box_color, preset.sub_box_alpha)
        box_pad = round(size * 0.28, 1)
        outline_field, shadow_field = box_pad, 0.0
    else:
        border_style = 1
        outline_colour = _ass_color(preset.sub_outline_color)
        outline_field, shadow_field = outline, shadow

    fmt = (
        "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    back = _ass_color("000000", 0x80)
    sub = (
        f"Style: Sub,{preset.font},{size},{_ass_color(preset.sub_color)},&H000000FF,"
        f"{outline_colour},{back},{bold},0,0,0,100,100,0,0,{border_style},{outline_field},"
        f"{shadow_field},2,{side},{side},{preset.sub_margin_v[ratio]},1"
    )
    card = (
        f"Style: Card,{preset.font},{card_size},{_ass_color(preset.card_color)},&H000000FF,"
        f"{_ass_color(preset.sub_outline_color)},{back},{bold},0,0,0,100,100,0,0,1,"
        f"{round(card_size * preset.sub_outline * 0.8, 1) if not preset.sub_box else 0},0,5,"
        f"{side},{side},0,1"
    )

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        f"Format: {fmt}",
        sub,
        card,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    fade = "{\\fad(90,90)}"
    pop = "{\\fscx88\\fscy88\\t(0,160,\\fscx100\\fscy100)}"
    tail = preset.tail_s
    for ts in timeline.scenes:
        style = "Card" if ts.scene.kind == "text_card" else "Sub"
        words = preset.max_words[ratio] + (2 if style == "Card" else 0)
        chunks = chunk_caption(_escape(ts.scene.caption), words)
        t0, t1 = _window(ts, tail)
        for start, end, chunk in split_times(chunks, t0, t1):
            tag = pop if preset.sub_pop else fade
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},{style},,0,0,0,,{tag}{chunk}"
            )
    return "\n".join(lines) + "\n"
