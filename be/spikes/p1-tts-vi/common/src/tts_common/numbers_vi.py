"""Đọc số tiếng Việt thành chữ (không dùng thư viện ngoài)."""

from __future__ import annotations

_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
# Đơn vị của từng nhóm 3 chữ số, tính từ phải sang trái
_SCALES = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ"]
_MAX_DIGITS = 15  # dài hơn (quá 5 nhóm) thì đọc từng chữ số


def read_digits(digits: str) -> str:
    """Đọc từng chữ số: '0909' -> 'không chín không chín'."""
    return " ".join(_DIGITS[int(c)] for c in digits if c.isdigit())


def _read_group(n: int, *, full: bool) -> str:
    """Đọc một nhóm 0..999. `full`=True khi còn nhóm lớn hơn phía trước (đọc 'không trăm', 'lẻ')."""
    h, t, u = n // 100, (n // 10) % 10, n % 10
    parts: list[str] = []
    if h > 0 or full:
        parts += [_DIGITS[h], "trăm"]
    if t == 0:
        if u > 0:
            if h > 0 or full:
                parts.append("lẻ")
            parts.append(_DIGITS[u])
    elif t == 1:
        parts.append("mười")
        if u == 5:
            parts.append("lăm")
        elif u > 0:
            parts.append(_DIGITS[u])
    else:
        parts += [_DIGITS[t], "mươi"]
        if u == 1:
            parts.append("mốt")
        elif u == 4:
            parts.append("tư")
        elif u == 5:
            parts.append("lăm")
        elif u > 0:
            parts.append(_DIGITS[u])
    return " ".join(parts)


def read_int(digits: str) -> str:
    """Đọc số nguyên không dấu: '390000' -> 'ba trăm chín mươi nghìn'."""
    digits = digits.lstrip("0") or "0"
    if len(digits) > _MAX_DIGITS:
        return read_digits(digits)
    n = int(digits)
    if n == 0:
        return _DIGITS[0]
    groups: list[int] = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    out: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        has_higher = i < len(groups) - 1
        words = _read_group(g, full=has_higher)
        out.append(f"{words} {_SCALES[i]}".strip())
    return " ".join(out)


def read_decimal(int_part: str, frac_part: str) -> str:
    """'12', '5' -> 'mười hai phẩy năm'. Phần thập phân đọc từng chữ số."""
    return f"{read_int(int_part)} phẩy {read_digits(frac_part)}"
