# Prompt: đặc tả M1 v0.3.1 theo ERD v1.3.3 (đóng #50)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #50 · **Branch:** `docs/m1-spec-v0-3-1` (tạo từ `origin/dev` mới nhất, sau PR #51)
- **Liên quan:** ERD v1.3.3 (PR #51, decision-log #18, #19), đặc tả M1 v0.3 (PR #40)

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản (xem `docs/README.md`). PR nhỏ, chỉ đồng bộ tên cột và quy tắc đã chốt.

## Đọc trước
- `docs/specs/erd/erd.dbml` trên `origin/dev`: bảng `product_knowledge` (cột review, các ghi chú REVIEW METADATA, GAP đã RESOLVED, mục 20–21 SQL REQUIRED), `generation_jobs` (cost), `content_scripts` (cost).
- `docs/logs/decision-log.md` dòng #18, #19. Issue #50 (toàn bộ comment).
- `docs/specs/m1-product-intelligence.md` (v0.3), `docs/specs/pkb/README.md`.

## Đã chốt ở ERD v1.3.3
1. `product_knowledge.approved_by` / `approved_at` đổi tên thành **`reviewed_by` / `reviewed_at`**, ghi cho **cả approve lẫn reject**.
2. Thêm **`reviewer_role`** (`merchant | admin`) và **`review_note`** (text, ≤ 1000 ký tự). Không có `review_action` (trùng với `status`).
3. Quy tắc (SQL REQUIRED, PLANNED):
   - `approved` → `reviewed_by`, `reviewed_at` có giá trị, `reviewer_role = 'merchant'`.
   - `rejected` → `reviewed_by`, `reviewed_at` có giá trị, `reviewer_role IN ('merchant','admin')`, `review_note` bắt buộc, không rỗng.
   - `draft`, `in_review` → 4 cột review đều null.
4. `generation_jobs.tokens_in`, `tokens_out`, `cost_usd`: nullable, không default. `cost_breakdown = '{}'` → 3 cột null (chưa ghi chi phí). Payload v1 có tổng 0 → 3 cột = 0 (thật sự $0, vd. cache hết). Payload v1 thường → > 0.
5. `content_scripts` có cost riêng (thuộc M2), **không tính vào NFR-02 của M1**.

## Nhiệm vụ

### 1. `docs/specs/m1-product-intelligence.md` → v0.3.1
- Dòng nguồn chuẩn (đầu file): ERD **v1.3.3**, dẫn PR #51, decision #18, #19.
- **Data model** (bảng `product_knowledge`): thay `approved_by`, `approved_at` bằng `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note`.
- **1.7 / FR-07:** thêm quy tắc mục "Đã chốt" 3, viết ngắn. Lý do reject lưu ở `review_note`.
- **Output / mô tả cột bảng** (dòng "… là cột của bảng, không nằm trong JSON"): đổi `approved_by` → `reviewed_by` (và các cột review).
- **NFR-02 / NFR-07:** thêm quy tắc nullability ở mục "Đã chốt" 4. NFR-02 chỉ tính job có `cost_usd` khác null. Ghi 1 câu: cost của `content_scripts` là số đo của M2, không tính vào NFR-02.
- **Câu hỏi còn mở:** bỏ dòng "→ chờ #50" (đã giải quyết), thay bằng 1 dòng gạch ngang dẫn ERD v1.3.3.
- **Lịch sử phiên bản:** thêm dòng v0.3.1 (08/10/2026, issue #50).

### 2. `docs/specs/pkb/README.md`
- Dòng "Các trường sau là cột của bảng…": đổi `approved_by` → `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note`.

## Phạm vi
- Làm: 2 file trên.
- Không làm: `docs/specs/erd/**` (của @tranquangthong03), decision-log (đã có #18, #19), contract schema, code.

## Acceptance criteria
- [ ] `git grep -n "approved_by\|approved_at" -- docs/specs/m1-product-intelligence.md docs/specs/pkb/` chỉ còn trong dòng lịch sử phiên bản (nếu có).
- [ ] Không còn "chờ #50" trong spec.
- [ ] Mọi cột nhắc trong spec có trong `erd.dbml` trên `origin/dev` (liệt kê trong body PR).

## Ràng buộc
- Trình bày danh sách thay đổi trước khi sửa, chờ duyệt. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(m1): đặc tả M1 v0.3.1 theo ERD v1.3.3`), kèm file prompt này. Mở PR vào `dev`, body có `Closes #50`, `cc @tranquangthong03`.
- Trả về: link PR, kết quả grep.
