"""PDF mẫu tối thiểu (không phụ thuộc thư viện) để quay demo, không dùng tài liệu thật."""

from __future__ import annotations

from pathlib import Path


def make_pdf(path: Path, label: str, pages: int) -> None:
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Pages, điền sau
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    kids = []
    for n in range(1, pages + 1):
        page_id = len(objs) + 1
        kids.append(f"{page_id} 0 R")
        stream = (
            f"BT /F1 36 Tf 72 700 Td ({label}) Tj ET\n"
            f"BT /F1 20 Tf 72 650 Td (Trang {n} / {pages}) Tj ET\n"
            "BT /F1 14 Tf 72 600 Td (Tai lieu mau de quay demo) Tj ET"
        ).encode("latin-1", "replace")
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {page_id + 1} 0 R "
            f"/Resources << /Font << /F1 3 0 R >> >> >>".encode()
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
        (out / "mau-a.pdf", "Bao cao quy 1", 2),
        (out / "mau-b.pdf", "Bao cao quy 2", 2),
        (out / "mau-nhieu-trang.pdf", "Tai lieu dai", 5),
    ]
    for p, label, n in files:
        make_pdf(p, label, n)
    return [p for p, _, _ in files]
