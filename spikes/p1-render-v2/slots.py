"""Ô clip của layout và phép tính zoom vào `clip_focus`.

Với HyperFrames, trình duyệt tự đặt <video> vào ô [data-slot="clip"] (bo góc, đổ bóng bằng CSS),
nên không cần đo getBoundingClientRect rồi overlay bằng FFmpeg như đề xuất ban đầu (#80).
Python chỉ cần: (1) đọc layout để chắc ô clip tồn tại; (2) tính tham số zoom và thời điểm zoom,
truyền vào template dưới dạng biến CSS.

Zoom dùng toạ độ chuẩn hoá [0, 1] theo khung clip đã cắt, nên không phụ thuộc kích thước ô:
ô có aspect-ratio đúng bằng clip (--clip-aspect), transform-origin 0 0, và
    điểm p của clip → tx + s·p    (tx, s: --fx-tx, --fx-s)
Chọn s để vùng focus lấp ô (tối đa MAX_ZOOM), tx để tâm focus nằm giữa ô, kẹp để không lộ mép.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from plan import Clip, PlanError

MAX_ZOOM = 2.2
ZOOM_ANIM_S = 0.9  # khớp .zoom-focus trong base.css
# Clip được tua nhanh/chậm để khớp lời đọc; ngoài khoảng này thao tác trông giả.
MIN_SPEED, MAX_SPEED = 0.6, 2.0


class _SlotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.slots: list[str] = []
        self.layouts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "data-slot" and value:
                self.slots.append(value)
            if name == "data-layout" and value:
                self.layouts.append(value)


@dataclass(frozen=True)
class LayoutInfo:
    name: str
    slots: tuple[str, ...]


def read_layout(html: str) -> LayoutInfo:
    """Đọc tên layout (data-layout) và các ô (data-slot) trong file layout."""
    p = _SlotParser()
    p.feed(html)
    if len(p.layouts) != 1:
        raise PlanError(f"layout phải có đúng 1 phần tử data-layout, thấy {p.layouts}")
    if f'TPL.mount("{p.layouts[0]}")' not in html:
        raise PlanError(f'layout {p.layouts[0]} thiếu lời gọi TPL.mount("{p.layouts[0]}")')
    return LayoutInfo(p.layouts[0], tuple(p.slots))


def load_layouts(layout_dir: Path) -> dict[str, LayoutInfo]:
    infos = {}
    for f in sorted(layout_dir.glob("*.html")):
        info = read_layout(f.read_text(encoding="utf-8"))
        if info.name != f.stem:
            raise PlanError(f"{f.name}: data-layout='{info.name}' khác tên file")
        infos[info.name] = info
    return infos


@dataclass(frozen=True)
class Zoom:
    scale: float
    tx: float  # tỉ lệ theo chiều rộng ô (−0,5 = dịch trái nửa ô)
    ty: float

    def css(self) -> dict[str, str]:
        return {
            "--fx-s": f"{self.scale:.4f}",
            "--fx-tx": f"{self.tx * 100:.3f}%",
            "--fx-ty": f"{self.ty * 100:.3f}%",
        }


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def normalize_rect(
    rect: tuple[int, int, int, int], crop: tuple[int, int, int, int]
) -> tuple[float, float, float, float]:
    """Hình chữ nhật pixel nguồn → [0, 1] theo vùng cắt; phần nằm ngoài vùng cắt bị cắt bỏ."""
    x, y, w, h = rect
    cx, cy, cw, ch = crop
    x0 = _clamp((x - cx) / cw, 0, 1)
    y0 = _clamp((y - cy) / ch, 0, 1)
    x1 = _clamp((x + w - cx) / cw, 0, 1)
    y1 = _clamp((y + h - cy) / ch, 0, 1)
    if x1 <= x0 or y1 <= y0:
        raise PlanError(f"clip_focus {rect} nằm ngoài vùng cắt {crop}")
    return x0, y0, x1 - x0, y1 - y0


def zoom_for(rect01: tuple[float, float, float, float], max_zoom: float = MAX_ZOOM) -> Zoom:
    x, y, w, h = rect01
    s = max(1.0, min(max_zoom, 1 / w, 1 / h))
    tx = _clamp(0.5 - (x + w / 2) * s, 1 - s, 0)
    ty = _clamp(0.5 - (y + h / 2) * s, 1 - s, 0)
    return Zoom(round(s, 4), round(tx, 6), round(ty, 6))


def clip_speed(clip: Clip, scene_s: float) -> float:
    """Hệ số tua để tổng các đoạn clip vừa khít thời lượng cảnh."""
    src = sum(p.length_s for p in clip.parts)
    speed = src / scene_s
    if not MIN_SPEED <= speed <= MAX_SPEED:
        raise PlanError(
            f"clip dài {src:.2f} s cho cảnh {scene_s:.2f} s: tốc độ {speed:.2f} ngoài "
            f"{MIN_SPEED}–{MAX_SPEED}; chọn lại đoạn clip"
        )
    return speed


def focus_time(clip: Clip, scene_s: float) -> float:
    """Thời điểm (giây, tính từ đầu cảnh) bắt đầu zoom, theo mốc source_t của clip nguồn.
    Kẹp để zoom chạy xong trước khi hết cảnh."""
    assert clip.focus is not None
    f = clip.focus
    part = clip.parts[f.part]
    if not part.start_s <= f.source_t <= part.end_s:
        raise PlanError(f"clip_focus.source_t {f.source_t} ngoài đoạn {part.start_s}–{part.end_s}")
    before = sum(p.length_s for p in clip.parts[: f.part])
    t = (before + f.source_t - part.start_s) / clip_speed(clip, scene_s)
    return round(_clamp(t, 0.0, max(0.0, scene_s - ZOOM_ANIM_S - 0.1)), 3)


def clip_css(clip: Clip, scene_s: float) -> dict[str, str]:
    """Biến CSS cho layout feature_clip: tỉ lệ ô clip + zoom + thời điểm zoom."""
    _, _, cw, ch = clip.crop
    css = {"--clip-aspect": f"{cw} / {ch}", "--clip-ar": f"{cw / ch:.5f}"}
    if clip.focus:
        crop = clip.parts[clip.focus.part].crop or clip.crop
        css.update(zoom_for(normalize_rect(clip.focus.rect, crop)).css())
        css["--focus-at"] = f"{focus_time(clip, scene_s)}s"
    return css
