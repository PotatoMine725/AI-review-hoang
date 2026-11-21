"""Phụ đề ASS đốt vào hình bằng FFmpeg (cách làm của #77).

VieNeu chỉ cho độ dài theo từng câu (không có mốc từng chữ, ADR-0004). Tiêu chí #80: không đủ
timing thì phụ đề theo cụm khớp lời đọc, không tạo timing giả. Vì vậy mỗi câu thoại (đã được viết
ngắn, sinh giọng riêng) là MỘT phụ đề, hiện đúng khoảng voice đo thật của câu đó, ngắt tối đa
MAX_LINES dòng. Không chia cụm 2–4 chữ theo số ký tự như bản #77 (đó là timing đoán).
Kiểu benchmark NotebookLM: hộp nền, chữ lớn, vị trí cố định trong vùng an toàn phía dưới
(template chừa vùng này, xem base.css --safe-bottom).
"""

from __future__ import annotations

from plan import PlanError, Ratio, RenderPlan
from timeline import Timeline

FRAME_SIZE: dict[str, tuple[int, int]] = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
FONT_PX: dict[str, int] = {"9:16": 74, "16:9": 58}
MARGIN_V: dict[str, int] = {"9:16": 280, "16:9": 78}  # từ mép dưới lên đáy hộp phụ đề
SIDE_MARGIN: dict[str, int] = {"9:16": 90, "16:9": 140}
# Số ký tự tối đa mỗi dòng, ước theo cỡ chữ và lề (Be Vietnam Pro ExtraBold ≈ 0,55 em/ký tự).
# 16:9 để 1 dòng: phụ đề 2 dòng che chip callout ở chân ô clip.
LINE_CHARS: dict[str, int] = {"9:16": 24, "16:9": 50}
MAX_LINES = 2


# --- chép từ spikes/p1-render/subtitles.py (#77), không import chéo spike ---
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


# --- hết phần chép ---


def wrap_caption(text: str, max_chars: int) -> list[str]:
    """Ngắt câu thành ít dòng nhất (mỗi dòng ≤ max_chars), các dòng dài gần bằng nhau.
    Không bao giờ cắt giữa một từ; từ dài hơn max_chars đứng riêng một dòng."""
    words = text.split()
    if not words:
        return []
    for n in range(1, len(words) + 1):
        target = len(text) / n
        lines: list[list[str]] = [[]]
        for w in words:
            cur = " ".join(lines[-1] + [w])
            # sang dòng mới khi vượt max_chars, hoặc đã đủ độ dài trung bình và còn dòng trống
            if lines[-1] and (len(cur) > max_chars or (len(" ".join(lines[-1])) >= target
                                                     and len(lines) < n)):  # fmt: skip
                lines.append([w])
            else:
                lines[-1].append(w)
        out = [" ".join(line) for line in lines]
        if len(out) <= n and all(len(x) <= max_chars or " " not in x for x in out):
            return out
    return words


def build_ass(plan: RenderPlan, tl: Timeline, ratio: Ratio) -> str:
    width, height = FRAME_SIZE[ratio]
    size = FONT_PX[ratio]
    side = SIDE_MARGIN[ratio]
    box_pad = round(size * 0.3, 1)
    fmt = (
        "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    # BorderStyle 3 = hộp nền; OutlineColour là màu hộp (nền tối của preset, hơi trong).
    style = (
        f"Style: Sub,Be Vietnam Pro ExtraBold,{size},{_ass_color('F4F1EA')},&H000000FF,"
        f"{_ass_color('080B14', 0x30)},{_ass_color('000000', 0x80)},-1,0,0,0,100,100,0,0,3,"
        f"{box_pad},0,2,{side},{side},{MARGIN_V[ratio]},1"
    )
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        f"Format: {fmt}",
        style,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    pop = "{\\fscx90\\fscy90\\t(0,140,\\fscx100\\fscy100)}"
    captions = {g.segment_id: g.caption for s in plan.scenes for g in s.narration_segments}
    for seg in tl.segments:
        rows = wrap_caption(_escape(captions[seg.segment_id]), LINE_CHARS[ratio])
        if len(rows) > MAX_LINES:
            raise PlanError(
                f"{seg.segment_id}: phụ đề {len(rows)} dòng ở {ratio}, cần câu ngắn hơn"
            )
        text = r"\N".join(rows)  # \N = xuống dòng trong ASS
        lines.append(
            f"Dialogue: 0,{_ass_time(seg.start_s)},{_ass_time(seg.end_s)},Sub,,0,0,0,,{pop}{text}"
        )
    return "\n".join(lines) + "\n"
