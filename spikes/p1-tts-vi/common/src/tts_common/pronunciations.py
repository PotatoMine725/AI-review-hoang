"""Bảng phát âm: tên tiếng Anh / viết tắt -> cách đọc bằng chữ Việt, TÁCH THEO PROVIDER.

Đã nghe kiểm một phần (QA 21/10, bộ nghe v2, 65 clip), chưa nghe hết. Kết quả: Piper cần phiên âm,
còn VieNeu đọc tên tiếng Anh để nguyên tự nhiên hơn
(ElevenLabs để nguyên 4-5/5, phiên âm "I lép ven Láp" 2/5).
- `PRONUNCIATIONS_BY_PROVIDER["piper"]`: bảng gốc, giữ nguyên.
- `PRONUNCIATIONS_BY_PROVIDER["vieneu"]`: bảng gốc bỏ `ElevenLabs` và `Lock&Lock`. Các mục khác
  (Starter, Pro...) CHƯA đổi vì QA chưa nghe bản để nguyên; không suy rộng từ ElevenLabs sang tên khác.
- `&` -> "en" không nằm trong bảng mà ở bước chuẩn hoá ký hiệu của `normalize_vi` (dùng cho mọi provider).
Mở rộng: thêm dòng vào bảng của provider, hoặc truyền dict riêng / file JSON
(`load_pronunciations(path, provider)`).
Khoá so khớp không phân biệt hoa thường, theo từ nguyên vẹn (không nằm giữa chữ khác).
"""

from __future__ import annotations

import json
from pathlib import Path

PIPER_PRONUNCIATIONS: dict[str, str] = {
    # Thương hiệu / sản phẩm đã gặp trong khảo sát M1
    "ElevenLabs": "I lép ven Láp",
    "Lock&Lock": "Lốc en Lốc",
    "Claude": "Clốt",
    "Gemini": "Giê mi nai",
    "Gamma": "Ga ma",
    "Dreamina": "Đrim mi na",
    "TikTok": "Tích Tóc",
    "YouTube": "Diu Túp",
    "Facebook": "Phây búc",
    "Shopee": "Sốp pi",
    "Lazada": "La da đa",
    "Tiki": "Ti ki",
    "Google": "Gu gồ",
    # Từ hay gặp trong tên gói / kịch bản
    "AI": "ây ai",
    "Pro": "Prô",
    "Plus": "Plát",
    "Free": "Phri",
    "Max": "Mách",
    "Premium": "Pri mi âm",
    "Standard": "Stan đớt",
    "Starter": "Sờ ta tơ",
    "Creator": "Cri ây tơ",
    "App": "Ép",
    "Online": "On lai",
    "Video": "Vi đi ô",
    "Review": "Ri viu",
    "Sale": "Seo",
    "Freeship": "Phri síp",
    "Hot": "Hót",
    "Deal": "Đin",
    # Viết tắt địa danh
    "TP.HCM": "Thành phố Hồ Chí Minh",
    "TPHCM": "Thành phố Hồ Chí Minh",
}

# VieNeu đọc tên tiếng Anh để nguyên tốt hơn bản phiên âm (QA 21/10): bỏ ElevenLabs;
# Lock&Lock đã có quy tắc `&` -> "en".
_VIENEU_DROPPED = frozenset({"ElevenLabs", "Lock&Lock"})
VIENEU_PRONUNCIATIONS: dict[str, str] = {
    k: v for k, v in PIPER_PRONUNCIATIONS.items() if k not in _VIENEU_DROPPED
}

PRONUNCIATIONS_BY_PROVIDER: dict[str, dict[str, str]] = {
    "piper": PIPER_PRONUNCIATIONS,
    "vieneu": VIENEU_PRONUNCIATIONS,
}

# Tên cũ, giữ để mã đã có không vỡ (vd. demo #78 gọi load_pronunciations(path)); bằng bảng Piper.
# KHÔNG dùng cho VieNeu.
DEFAULT_PRONUNCIATIONS: dict[str, str] = PIPER_PRONUNCIATIONS

# Tên chữ cái tiếng Anh, dùng để đọc viết tắt toàn chữ hoa chưa có trong bảng (CTA -> xi ti ây)
LETTER_NAMES: dict[str, str] = {
    "A": "ây", "B": "bi", "C": "xi", "D": "đi", "E": "i", "F": "ép", "G": "giê", "H": "hết",
    "I": "ai", "J": "giây", "K": "kây", "L": "eo", "M": "em", "N": "en", "O": "âu", "P": "pi",
    "Q": "kiu", "R": "a", "S": "ét", "T": "ti", "U": "diu", "V": "vi", "W": "đắp bồ liu",
    "X": "ét", "Y": "quai", "Z": "dét",
}  # fmt: skip


def pronunciations_for(provider: str) -> dict[str, str]:
    """Bảng phát âm của provider (`piper` / `vieneu`); provider lạ thì báo lỗi, không đoán."""
    try:
        return PRONUNCIATIONS_BY_PROVIDER[provider]
    except KeyError:
        known = sorted(PRONUNCIATIONS_BY_PROVIDER)
        raise KeyError(f"chưa có bảng phát âm cho provider {provider!r}: {known}") from None


def load_pronunciations(path: str | Path, provider: str = "piper") -> dict[str, str]:
    """Đọc bảng phát âm bổ sung từ file JSON {"Tên": "cách đọc"}; gộp đè lên bảng của `provider`.

    Mặc định `piper` (= bảng cũ) để mã đã có không đổi hành vi; VieNeu phải truyền `provider="vieneu"`.
    """
    extra = json.loads(Path(path).read_text(encoding="utf-8"))
    return {**pronunciations_for(provider), **extra}
