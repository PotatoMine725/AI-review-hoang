"""3 preset bố cục (quyết định 14/10, #67): cùng một engine, khác tham số.

Preset chỉ là dữ liệu: nhịp (đệm cuối cảnh, chuyển cảnh), chuyển động ảnh, màu thẻ chữ,
kiểu phụ đề và vài lớp phủ. Thêm preset = thêm 1 dòng vào PRESETS, không sửa engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Ratio = Literal["9:16", "16:9"]
RATIOS: tuple[Ratio, ...] = ("9:16", "16:9")
# Chỉ zoom (không pan): pan trượt ảnh ra ngoài khung nên cắt mất nội dung.
Motion = Literal["zoom_in", "zoom_out"]

# Kích thước đầu ra (rộng, cao). 30 fps, H.264 + AAC.
FRAME_SIZE: dict[Ratio, tuple[int, int]] = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
FPS = 30


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    description: str
    # --- Nhịp ---
    transition: str  # tên xfade của ffmpeg, hoặc "cut"
    transition_s: float  # ≤ 0.3 s (prompt); 0 nếu cắt
    tail_s: float  # đệm sau câu thoại cuối mỗi cảnh
    # --- Hình ---
    kb_zoom: float  # mức zoom Ken Burns tối đa (0.1 = 10%)
    motions: tuple[Motion, ...]
    card_bg: str  # màu thẻ chữ, "0xRRGGBB"
    card_gradient: tuple[str, str] | None = None  # nếu có: nền thẻ chuyển màu thay cho card_bg
    grade: str = ""  # filter chỉnh màu thêm vào toàn video (rỗng = không)
    bars_frac: float = 0.0  # dải đen trên/dưới (điện ảnh), theo tỉ lệ chiều cao
    vignette: bool = False
    border_px: int = 0  # viền khung quanh video (cổ điển)
    border_color: str = "0xF4ECD8"
    # --- Phụ đề (ASS) ---
    font: str = "Be Vietnam Pro"
    bold: bool = True
    sub_color: str = "FFFFFF"  # RRGGBB
    sub_outline_color: str = "000000"
    sub_outline: float = 0.07  # độ dày viền chữ, theo cỡ chữ
    sub_shadow: float = 0.0
    sub_box: bool = False  # nền hộp mờ sau chữ
    sub_box_color: str = "000000"
    sub_box_alpha: int = 0x60  # 0 = đặc, 0xFF = trong suốt
    sub_pop: bool = False  # chữ nảy nhẹ khi hiện
    sub_size: float = 1.0  # nhân với cỡ chữ cơ sở
    card_color: str = "FFFFFF"
    card_size: float = 1.35
    # khoảng cách từ mép dưới đến chân chữ (px, theo hệ toạ độ ASS của từng tỉ lệ)
    sub_margin_v: dict[str, int] = field(default_factory=lambda: {"9:16": 380, "16:9": 90})
    max_words: dict[str, int] = field(default_factory=lambda: {"9:16": 5, "16:9": 8})
    music_volume: float = 0.16


PRESETS: dict[str, Preset] = {
    p.id: p
    for p in (
        Preset(
            id="hoat-hinh-do-hoa",
            label="Hoạt hình đồ họa",
            description="Màu rực, thẻ chữ nền chuyển màu, chữ to nảy, chuyển cảnh trượt nhanh.",
            transition="slideleft",
            transition_s=0.25,
            tail_s=0.15,
            kb_zoom=0.12,
            motions=("zoom_in", "zoom_out", "zoom_in", "zoom_out"),
            card_bg="0x6D28D9",
            card_gradient=("0x6D28D9", "0xEC4899"),
            font="Be Vietnam Pro ExtraBold",
            bold=False,
            sub_color="FFFFFF",
            sub_outline_color="3B0764",
            sub_outline=0.12,
            sub_pop=True,
            card_color="FACC15",
            card_size=1.45,
        ),
        Preset(
            id="dien-anh-toi-gian",
            label="Điện ảnh tối giản",
            description="Dải đen trên/dưới, tối, vignette, zoom chậm, chữ mảnh nhỏ, mờ chuyển.",
            transition="fadeblack",
            transition_s=0.3,
            tail_s=0.2,
            kb_zoom=0.07,
            motions=("zoom_in", "zoom_in", "zoom_in", "zoom_in"),
            card_bg="0x0B0F14",
            grade="eq=contrast=1.06:saturation=0.9:brightness=-0.03",
            bars_frac=0.09,
            vignette=True,
            font="Be Vietnam Pro",
            bold=False,
            sub_color="F2F2F2",
            sub_outline_color="000000",
            sub_outline=0.04,
            sub_shadow=0.05,
            sub_size=0.82,
            card_color="F2F2F2",
            card_size=1.2,
            sub_margin_v={"9:16": 330, "16:9": 150},
            max_words={"9:16": 6, "16:9": 10},
            music_volume=0.14,
        ),
        Preset(
            id="co-dien",
            label="Cổ điển",
            description="Nền kem, viền khung ảnh, tông nâu ấm, chữ trên hộp mờ, mờ chồng.",
            transition="fade",
            transition_s=0.3,
            tail_s=0.2,
            kb_zoom=0.05,
            motions=("zoom_out", "zoom_in", "zoom_out", "zoom_in"),
            card_bg="0xF4ECD8",
            grade="eq=saturation=0.78:contrast=1.04,colorchannelmixer=rr=1.05:bb=0.92",
            border_px=28,
            border_color="0xF4ECD8",
            font="Be Vietnam Pro",
            bold=True,
            sub_color="FFF8E7",
            sub_outline_color="2B1B10",
            sub_outline=0.02,
            sub_box=True,
            sub_box_color="2B1B10",
            sub_box_alpha=0x40,
            card_color="3B2A1E",
            card_size=1.25,
            sub_margin_v={"9:16": 400, "16:9": 110},
        ),
    )
}


def get_preset(preset_id: str) -> Preset:
    try:
        return PRESETS[preset_id]
    except KeyError:
        raise KeyError(
            f"preset '{preset_id}' không có; chọn một trong: {', '.join(PRESETS)}"
        ) from None
