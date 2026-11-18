"""Dựng `input.json` (p1-ac-03-input.v1) cho lần chạy M2 đầu tiên với PDFCraft.

    cd services/worker
    uv run python ../../docs/report/m2-first-run-pdfcraft/build_input.py \
        D:/tmp/extract-pdfcraft-lang-p4 D:/tmp/crawl-pdfcraft-lang

Nguồn: PKB lang-p4 (#90, extract 21/10 trên crawl 21/10 `en,vi`) + fact bổ sung mô phỏng bước
người dùng xác nhận PKB. Chỉ thêm fact khi câu evidence của BA (`_refs/notebooklm/
pdfcraft-thong-tin-san-pham.md`) có NGUYÊN VĂN trong trang đã crawl (kiểm bằng `EvidenceIndex` của
M1, chuẩn hoá NFC + khoảng trắng như `_check_evidence`). Không có thì không thêm và in ra.
"""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from worker.m1.extract.evidence import EvidenceIndex
from worker.m1.pkb.validate import validate_pkb
from worker.m2.validate import validate_input

OUT = Path(__file__).resolve().parent / "input.json"
PRODUCT_ID = "3b7e9c1a-2f4d-4a8b-9c6e-1d2f3a4b5c6d"  # UUID giả lập cho PDFCraft (chưa có DB)
REVIEWER_ID = "00000000-0000-4000-8000-0000000000b1"  # người duyệt mô phỏng
REVIEWED_AT = "2026-10-29T08:30:00Z"

# Fact BA (bộ 9 fact) chưa có trong PKB lang-p4. (id BA, source_id, tên, mô tả, evidence nguyên văn)
SUPPLEMENT = [
    ("F2", "src_01", "Không đăng ký, không chi phí ẩn",
     "Dùng không cần đăng ký, không có chi phí ẩn.",
     "Không đăng ký, không giới hạn, không chi phí ẩn."),
    # F3 + F7 gần trùng ý (xử lý cục bộ): gộp thành 1 fact, giữ evidence F3 (tiếng Việt, ngắn,
    # nói thẳng "không rời khỏi thiết bị"). Quyền riêng tư là lời PDFCraft tự công bố (QA 29/10).
    ("F3+F7", "src_01", "Xử lý trong trình duyệt (PDFCraft tự công bố)",
     "PDFCraft công bố: mọi xử lý diễn ra trong trình duyệt, tệp không rời khỏi thiết bị.",
     "Mọi xử lý diễn ra trong trình duyệt. Tệp của bạn không bao giờ rời khỏi thiết bị."),
    ("F4", "src_02", "Đánh số trang",
     "Thêm số trang vào PDF, chỉnh được vị trí, định dạng và số bắt đầu.",
     "Add page numbers to PDF documents. Customize position, format, and starting number."),
    # F5: nguồn chỉ nói "chỉnh sửa được", không nói giữ nguyên định dạng (QA 29/10).
    ("F5", "src_02", "Chuyển PDF sang Word",
     "Chuyển PDF sang tài liệu Word (DOCX) chỉnh sửa được.",
     "Convert PDF to editable Word (DOCX) documents."),
    # F9: src_10 = https://pdfcraft.devtoolcafe.com/en/tools/merge-pdf (trang /en, không dùng /ro).
    ("F9", "src_10", "Cách ghép",
     "Bấm Merge để gộp tất cả tệp thành một PDF rồi tải về.",
     "Click the Merge button to automatically convert and combine all files into a single PDF, "
     "then download your result."),
]  # fmt: skip

ASSETS = [
    ("pdfcraft-pagenum", "Clip tự quay: mở Page Numbers, chọn vị trí, Apply, hiện số trang."),
    ("pdfcraft-word-export", "Clip tự quay: menu Save & Export → Export as Word (.docx)."),
    ("pdfcraft-word-result", "Clip tự quay: file Word sau khi xuất."),
    ("pdfcraft-merge", "Clip tự quay: Combine Files & Merge PDF, thêm tài liệu thứ hai, Append."),
]


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main(extract_dir: Path, crawl_dir: Path) -> int:
    pkb_path = extract_dir / "pkb.json"
    pkb = json.loads(pkb_path.read_text(encoding="utf-8"))
    src = pkb["data"]
    sources = {s["id"]: s for s in pkb["sources"]}
    texts = {
        sid: (crawl_dir / s["markdown_path"]).read_text(encoding="utf-8")
        for sid, s in sources.items()
    }  # noqa: E501
    index = EvidenceIndex(texts)

    # Giữ: fact đã có trong PKB, khớp bộ BA, không có warning/conflict.
    data: dict[str, Any] = {
        "schema_version": src["schema_version"],
        "identity": {
            "name": src["identity"]["name"],  # PDFCraft, evidence src_03, không warning
            "website": src["identity"]["website"],
            "tagline": src["identity"]["tagline"],  # F1
            "product_kind": src["identity"]["product_kind"],
        },
        # plans[0] (Free, price_unit month là giữ chỗ: free_only_placeholder_period) bị bỏ.
        "pricing": {"plans": [], "free_plan": src["pricing"]["free_plan"]},
        "features": [deepcopy(src["features"][0])],  # F6 Hợp nhất PDF
        "limitations": [deepcopy(src["limitations"][0])],  # F8 100 tệp / 500MB
        "quality": {"conflicts": []},  # conflict "features" (số công cụ) CHƯA giải quyết, xem _note
    }
    added, missing = [], []
    for ba_id, sid, name, desc, evidence in SUPPLEMENT:
        url = sources[sid]["url"]
        if "/ro/" in url:  # QA 29/10: không dùng trang /ro
            missing.append(f"{ba_id}(url {url})")
            continue
        if not index.found(sid, evidence):
            missing.append(ba_id)
            continue
        print(f"{ba_id}: evidence nguyên văn trong {sid} = {url}")
        data["features"].append({
            "origin": "crawled", "source_id": sid, "evidence": evidence,
            "id": f"f{len(data['features']) + 1}", "name": name, "description": desc,
            "screenshot_ids": [],
        })  # fmt: skip
        added.append(f"{ba_id}→features[{len(data['features']) - 1}]")
    data["features"][0]["id"] = "f1"

    used = {"src_01", "src_02", "src_03", "src_10"}
    kept_sources = [sources[s] for s in sorted(used)]
    validate_pkb(data, kept_sources)

    doc = {
        "_note": (
            "INPUT THỬ NGHIỆM, KHÔNG PHẢI PKB ĐÃ DUYỆT. "
            "approved_pkb.status = 'approved', reviewer và thời điểm duyệt là MÔ PHỎNG để chạy "
            "thử; chưa có BA, khách hàng hay merchant nào xác nhận PKB này. "
            "PKB lang-p4 + fact bổ sung mô phỏng bước xác nhận PKB, evidence nguyên văn. "
            f"Nguồn: {pkb_path.as_posix()} ({sha256(pkb_path)}), "
            f"crawl {crawl_dir.as_posix()}. "
            f"Người duyệt mô phỏng {REVIEWER_ID} lúc {REVIEWED_AT}: giữ name, tagline (F1), "
            "free_plan, features[0] (F6), limitations[0] (F8); bỏ identity.description, "
            "identity.category, pricing.plans[0], features[1..7], use_cases. "
            "CONFLICT CHƯA GIẢI QUYẾT: nguồn ghi 67 và 132+ công cụ, chưa thống nhất được một "
            "con số. Số công cụ CHƯA DÙNG, conflict 'features' vẫn mở; các fact có con số này bị "
            "loại khỏi input. 'quality.conflicts: []' chỉ vì đây là input test đã lọc, KHÔNG đại "
            "diện PKB chuẩn và KHÔNG có nghĩa conflict đã xử lý. "
            "Fact bổ sung (origin crawled vì v0.3 không cho owner ở features; F3+F7 gộp thành 1, "
            "giữ evidence F3; quyền riêng tư ghi là PDFCraft tự công bố): "
            f"{', '.join(added)}. "
            f"Không tìm thấy nguyên văn: {', '.join(missing) or 'không có'}. product_id giả lập."
        ),
        "schema_version": "p1-ac-03-input.v1-draft",
        "product_id": PRODUCT_ID,
        "knowledge_version": 1,
        "approved_pkb": {
            "status": "approved",
            "schema_version": data["schema_version"],
            "data": data,
            "sources": kept_sources,
        },
        "permitted_assets": [
            {
                "asset_id": aid,
                "product_id": PRODUCT_ID,
                "kind": "screen_recording",
                "source_id": None,
                "allowed_use": ["internal_demo"],
                "rights_basis": f"{desc} Nhóm tự quay giao diện PDFCraft cho demo nội bộ P1 (#52).",
            }
            for aid, desc in ASSETS
        ],  # fmt: skip
        "content_context": {
            "forbidden_claims": [
                "Số lượng công cụ (nguồn ghi 67 và 132+, chưa thống nhất, conflict đang để mở).",
                "Khẳng định tuyệt đối về bảo mật hay quyền riêng tư như sự thật đã kiểm chứng; "
                "chỉ nói theo cách PDFCraft tự công bố.",
                "Giá, đánh giá, số người dùng, so sánh với sản phẩm khác (nguồn không có).",
                "Chuyển PDF sang Word giữ nguyên định dạng (thử thực tế mất một số nền màu).",
            ]
        },
    }
    errors = validate_input({k: v for k, v in doc.items() if k != "_note"})
    if errors:
        print("\n".join(errors))
        return 1
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ghi {OUT}\nthêm: {added}\nthiếu: {missing}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
