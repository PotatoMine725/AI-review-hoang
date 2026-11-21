"""PDF mẫu tối thiểu (không phụ thuộc thư viện) để quay demo, không dùng tài liệu thật."""

from __future__ import annotations

from pathlib import Path

Rgb = tuple[float, float, float]
BLUE: Rgb = (0.15, 0.39, 0.92)
GREEN: Rgb = (0.06, 0.6, 0.45)
ORANGE: Rgb = (0.93, 0.45, 0.1)


def _page_stream(label: str, n: int, pages: int, color: Rgb) -> bytes:
    """Trang dễ nhận ra trong video: dải màu đầu trang, tiêu đề lớn, số trang to, vài 'đoạn văn'
    là các thanh xám, để khi gộp hay đánh số trang người xem thấy ngay trang nào của file nào."""
    r, g, b = color
    bars = "".join(
        f"0.85 0.87 0.9 rg 72 {470 - i * 34} {380 - (i % 3) * 70} 14 re f\n" for i in range(8)
    )
    return (
        f"{r} {g} {b} rg 0 612 612 180 re f\n"
        f"BT 1 1 1 rg /F2 44 Tf 54 700 Td ({label}) Tj ET\n"
        f"BT 1 1 1 rg /F1 20 Tf 54 650 Td (Tai lieu mau de quay demo) Tj ET\n"
        f"{r} {g} {b} rg 54 520 220 64 re f\n"
        f"BT 1 1 1 rg /F2 30 Tf 70 540 Td (Trang {n} / {pages}) Tj ET\n"
        f"{bars}"
        f"{r} {g} {b} RG 4 w 54 120 504 0 re S\n"
        f"BT 0.3 0.3 0.35 rg /F1 14 Tf 54 96 Td ({label} - PDFCraft demo) Tj ET"
    ).encode("latin-1", "replace")


def make_pdf(path: Path, label: str, pages: int, color: Rgb = BLUE) -> None:
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Pages, điền sau
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    kids = []
    for n in range(1, pages + 1):
        page_id = len(objs) + 1
        kids.append(f"{page_id} 0 R")
        stream = _page_stream(label, n, pages, color)
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {page_id + 1} 0 R "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>".encode()
        )
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {pages} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


def make_samples(out: Path) -> list[Path]:
    """Hai file ghép (merge) và một file nhiều trang (đánh số trang)."""
    files = [
        (out / "mau-a.pdf", "Bao cao quy 1", 2, BLUE),
        (out / "mau-b.pdf", "Bao cao quy 2", 2, GREEN),
        (out / "mau-nhieu-trang.pdf", "Tai lieu dai", 5, ORANGE),
    ]
    for p, label, n, color in files:
        make_pdf(p, label, n, color)
    return [p for p, _, _, _ in files]
