"""normalize_vi: chuẩn hoá văn bản tiếng Việt trước khi đưa vào TTS (theo quy tắc, không dùng LLM).

Thứ tự xử lý (quan trọng, xem từng bước):
  1. bảng phát âm (tên tiếng Anh, viết tắt)
  2. số điện thoại, ngày, giờ
  3. khoảng "15-25" -> "15 đến 25"
  4. số + đơn vị / tiền / % (một lượt regex)
  5. viết tắt toàn chữ hoa còn lại -> đọc từng chữ cái
  6. dọn ký hiệu (`&` -> "en", mọi provider), khoảng trắng

Bảng phát âm tách theo provider (xem `pronunciations.py`); dùng `normalizer_for("vieneu")` thay vì mặc định.

Quy ước số: dấu chấm ngăn nhóm 3 chữ số (390.000), dấu phẩy là thập phân (1,2). "3.5" (nhóm không đủ 3 số)
được hiểu là thập phân. Số kiểu Anh "1,200,000" KHÔNG hỗ trợ.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping

from .numbers_vi import read_decimal, read_digits, read_int
from .pronunciations import DEFAULT_PRONUNCIATIONS, LETTER_NAMES, pronunciations_for

# đơn vị sau số -> cách đọc
_UNITS: dict[str, str] = {
    "ml": "mi li lít", "mL": "mi li lít", "ML": "mi li lít",
    "l": "lít", "L": "lít",
    "g": "gam", "kg": "ki lô gam", "mg": "mi li gam",
    "mm": "mi li mét", "cm": "xen ti mét", "m": "mét", "km": "ki lô mét",
    "m2": "mét vuông", "m²": "mét vuông",
    "gb": "gi ga bai", "GB": "gi ga bai", "mb": "mê ga bai", "MB": "mê ga bai",
    "tb": "tê ra bai", "TB": "tê ra bai",
    "w": "oát", "W": "oát", "kw": "ki lô oát", "kW": "ki lô oát",
    "mah": "mi li am pe giờ", "mAh": "mi li am pe giờ",
    "°C": "độ xê", "°c": "độ xê",
    "k": "nghìn",  # 390k = ba trăm chín mươi nghìn
    "tr": "triệu",
}  # fmt: skip
_MULTI_LETTER_SPACE_OK = {
    "tr",
    "ml",
    "mL",
    "ML",
    "kg",
    "mg",
    "mm",
    "cm",
    "km",
    "gb",
    "GB",
    "mb",
    "MB",
    "tb",
    "TB",
}
_CURRENCY: dict[str, str] = {
    "đ": "đồng", "₫": "đồng", "vnđ": "đồng", "vnd": "đồng", "VNĐ": "đồng", "VND": "đồng", "Đ": "đồng",
    "usd": "đô la Mỹ", "USD": "đô la Mỹ",
}  # fmt: skip

_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"
_LETTER = r"[^\W\d_]"  # chữ cái unicode (kể cả chữ có dấu)
_UNIT_KEYS = sorted([*_UNITS, *_CURRENCY, "%"], key=len, reverse=True)
_UNIT_ALT = "|".join(re.escape(k) for k in _UNIT_KEYS)
# số, rồi (tuỳ chọn) đơn vị; đơn vị không được dính vào chữ cái đứng sau
_NUM_UNIT_RE = re.compile(rf"(?<![\w.,])(?P<num>{_NUM})(?:(?P<sp>\s?)(?P<unit>{_UNIT_ALT}))?(?!{_LETTER})")
_SCALE_CURRENCY_RE = re.compile(rf"\b(nghìn|ngàn|triệu|tỷ|tỉ)\s?(đ|₫|vnđ|vnd|VNĐ|VND)(?!{_LETTER})")
_DOLLAR_RE = re.compile(rf"\$\s?(?P<num>{_NUM})(?!\d)")
# Dấu . và , cuối câu KHÔNG được chặn khớp ("ngày 31/10/2026."); chỉ chặn khi sau nó còn chữ số
_PHONE_RE = re.compile(r"(?<![\w.,])(0\d{2,3}[ .]?\d{3}[ .]?\d{3,4})(?!\w|[.,]\d)")
_DATE_RE = re.compile(r"(?<![\w/.-])(\d{1,2})([/-])(\d{1,2})(?:[/-](\d{4}))?(?![\w/-]|[.,]\d)")
_MONTH_YEAR_RE = re.compile(r"(?<![\w/.-])(\d{1,2})/(\d{4})(?![\w/-]|[.,]\d)")
_TIME_RE = re.compile(r"(?<![\w.,])(\d{1,2})(?:[hH]|:)(\d{2})?(?![\w])")
_FRACTION_RE = re.compile(r"(?<![\w/.-])(\d{1,2})/(\d{1,2})(?![\w/-]|[.,]\d)")
_RANGE_RE = re.compile(r"(?<=\d)\s?[-–]\s?(?=\d)")
_ACRONYM_RE = re.compile(r"(?<![\w.])[A-Z]{2,4}(?!\w|\.\w)")


def _spoken_number(token: str) -> str:
    """Đọc 1 token số theo quy ước Việt: '390.000', '1,2', '3.5', '2026'."""
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", token):
        int_part, _, frac = token.partition(",")
        return read_decimal(int_part.replace(".", ""), frac) if frac else read_int(int_part.replace(".", ""))
    sep = "," if "," in token else "." if "." in token else ""
    if sep:
        int_part, frac = token.split(sep, 1)
        return read_decimal(int_part, frac)
    return read_int(token)


def _apply_pronunciations(text: str, table: Mapping[str, str]) -> str:
    # khoá dài trước để "Lock&Lock" ăn trước "Lock"; khoá toàn chữ hoa (AI) so khớp phân biệt hoa thường
    for key in sorted(table, key=len, reverse=True):
        flags = 0 if (key.isupper() and len(key) <= 4) else re.IGNORECASE
        pattern = rf"(?<![\w&]){re.escape(key)}(?![\w&])"
        text = re.sub(pattern, lambda _m, v=table[key]: v, text, flags=flags)
    return text


def _phone(m: re.Match[str]) -> str:
    return read_digits(re.sub(r"\D", "", m.group(1)))


def _preceded_by(text: str, pos: int, word: str) -> bool:
    return text[:pos].rstrip().lower().endswith(word)


def _date(m: re.Match[str]) -> str:
    d, mo, y = int(m.group(1)), int(m.group(3)), m.group(4)
    after_ngay = _preceded_by(m.string, m.start(), "ngày")
    # "5-10 phút", "1/2 ly" không phải ngày: dạng 2 phần chỉ nhận khi đứng sau chữ "ngày"
    if not (1 <= d <= 31 and 1 <= mo <= 12) or (y is None and not after_ngay):
        return m.group(0)
    prefix = "" if after_ngay else "ngày "
    out = f"{prefix}{read_int(str(d))} tháng {read_int(str(mo))}"
    return f"{out} năm {read_int(y)}" if y else out


def _month_year(m: re.Match[str]) -> str:
    mo = int(m.group(1))
    if not 1 <= mo <= 12:
        return m.group(0)
    prefix = "" if _preceded_by(m.string, m.start(), "tháng") else "tháng "
    return f"{prefix}{read_int(str(mo))} năm {read_int(m.group(2))}"


def _time(m: re.Match[str]) -> str:
    hour, minute = int(m.group(1)), m.group(2)
    if hour > 24:
        return m.group(0)
    out = f"{read_int(str(hour))} giờ"
    if minute and int(minute) > 0:
        out += (" lẻ " + read_int(minute)) if minute.startswith("0") else f" {read_int(minute)}"
    return out


def _num_unit(m: re.Match[str]) -> str:
    spoken = _spoken_number(m.group("num"))
    unit = m.group("unit")
    if unit is None:
        return spoken
    # đơn vị 1 chữ cái (l, g, m, k, w) phải dính liền số; "5 g" để nguyên, không đoán
    if m.group("sp") and unit in _UNITS and unit not in _MULTI_LETTER_SPACE_OK:
        return f"{spoken} {unit}"
    if unit == "%":
        return f"{spoken} phần trăm"
    if unit in _CURRENCY:
        return f"{spoken} {_CURRENCY[unit]}"
    return f"{spoken} {_UNITS[unit]}"


def _acronym(m: re.Match[str]) -> str:
    return " ".join(LETTER_NAMES[c] for c in m.group(0))


def normalize_vi(
    text: str,
    pronunciations: Mapping[str, str] | None = DEFAULT_PRONUNCIATIONS,
    *,
    spell_acronyms: bool = True,
) -> str:
    """Chuẩn hoá `text` để TTS đọc đúng số, tiền, %, đơn vị, tên tiếng Anh.

    `pronunciations=None` bỏ qua bảng phát âm (để so sánh provider đọc tên tiếng Anh tự nhiên hay không).
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ")
    if pronunciations:
        text = _apply_pronunciations(text, pronunciations)
    text = _PHONE_RE.sub(_phone, text)
    text = _DATE_RE.sub(_date, text)
    text = _MONTH_YEAR_RE.sub(_month_year, text)
    text = _FRACTION_RE.sub(lambda m: f"{read_int(m.group(1))} phần {read_int(m.group(2))}", text)
    text = _TIME_RE.sub(_time, text)
    text = _DOLLAR_RE.sub(lambda m: f"{_spoken_number(m.group('num'))} đô la", text)
    text = _RANGE_RE.sub(" đến ", text)
    text = _NUM_UNIT_RE.sub(_num_unit, text)
    text = _SCALE_CURRENCY_RE.sub(lambda m: f"{m.group(1)} đồng", text)  # "1,2 triệu đ"
    if spell_acronyms:
        text = _ACRONYM_RE.sub(_acronym, text)
    text = text.replace("&", " en ")  # QA 21/10: "Lock&Lock" -> "Lock en Lock" 5/5; "và" bị 3/5
    text = re.sub(r"[*_#`~]+", "", text)  # ký hiệu markdown
    return re.sub(r"\s+", " ", text).strip()


def normalizer_for(provider: str) -> Callable[[str], str]:
    """`normalize_vi` với bảng phát âm của `provider` (`piper` / `vieneu`)."""
    table = pronunciations_for(provider)
    return lambda text: normalize_vi(text, table)
