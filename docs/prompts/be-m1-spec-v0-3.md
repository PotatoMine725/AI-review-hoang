# Prompt: đặc tả M1 v0.3 theo ERD v1.3.1

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #23 (đồng bộ ERD ↔ M1) · **Branch:** `docs/m1-spec-v0-3` (tạo từ `dev` mới nhất)
- **Chạy khi:** @VV6505 đã duyệt ERD (buổi review T6 09/10) **và** PR `feat/m1-pkb-schema-v0-2` đã merge.

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản (xem `docs/README.md`).

## Đọc trước
- `CLAUDE.md`, `docs/README.md`
- Issue #23: toàn bộ comment, nhất là phần trả lời của @tranquangthong03 và @VV6505. **Chỉ ghi những gì đã được chốt trong issue.** Điểm chưa chốt thì ghi "chờ #23", không tự quyết.
- `docs/specs/erd/erd.dbml` (bản mới nhất trên `dev`), `docs/specs/erd/data-dictionary.md`
- `docs/specs/m1-product-intelligence.md` (v0.2), `docs/specs/pkb/README.md`
- `docs/adr/0002-llm-provider.md` (Quyết định 4: embedding), `docs/logs/decision-log.md`, `docs/logs/qa-log.md` (#5, #12)

## Nhiệm vụ

### 1. `docs/specs/m1-product-intelligence.md` → v0.3
- **Data model và API:** thay 7 bảng bằng các bảng của ERD mà M1 dùng: `products`, `product_knowledge`, `generation_jobs` (`job_type = 'crawl'`). Markdown nguồn, screenshot, file upload nằm trong Storage; đường dẫn ghi trong `product_knowledge.sources` (theo `docs/specs/pkb/README.md`). Link tới `docs/specs/erd/`, không chép lại DBML.
- **1.1 Intake:** bỏ "kiểm tra trùng domain". Thay bằng: `website_url` unique sau khi chuẩn hoá URL (ERD gate 2).
- **1.2:** bỏ qua trang không đổi bằng `content_hash` lưu trong `sources` (NFR-04), không cần bảng `crawled_pages`.
- **1.3 / FR-06 / FR-13:** ảnh lưu Storage, metadata trong `sources` (hoặc nơi mà #23 chốt). M3 đọc ảnh theo metadata này.
- **1.8 / FR-08:** bỏ khỏi MVP. FR-08 hạ xuống **Later**. M2, M4 dùng nguyên PKB approved (JSON) làm input (ERD: "Use approved JSON directly as AI input; no vector RAG in pilot"). Bỏ endpoint `/knowledge/search` và acceptance criterion tương ứng.
- **FR-07:** trạng thái PKB theo bản đã chốt ở #23 (đề xuất `draft|in_review|approved|rejected`). Người duyệt: merchant (decision-log #11).
- **NFR-02 / NFR-07:** chi phí đọc từ cột hoặc key `result_manifest` của `generation_jobs` theo bản đã chốt ở #23. Sửa acceptance criterion "đọc từ `crawl_jobs.cost_usd`".
- **Tech stack:** dòng Embedding và Phạm vi RAG ghi "hoãn sau MVP (qa-log #5)". Bỏ pgvector khỏi dòng DB của M1.
- **Output:** JSON mẫu thêm `schema_version`; bỏ `product_id`, `version`, `status` khỏi JSON (là cột bảng); link `docs/specs/pkb/`.
- **Lịch sử phiên bản:** thêm dòng v0.3.

### 2. ADR-002
Quyết định 4 (embedding): thêm ghi chú "Hoãn: MVP không dùng vector RAG (ERD v1.3.1, qa-log #5)". Không xoá nội dung cũ.

### 3. Logs
- `qa-log.md`: đóng #5 (câu trả lời: không có vector RAG trong MVP, dùng nguyên PKB JSON; nguồn: ERD v1.3.1, #23). #12: ghi "không còn áp dụng trong MVP vì không có embedding".
- `decision-log.md`: thêm 1 dòng: ERD v1.3.1 là nguồn chuẩn của data model; M1 bỏ vector RAG, bỏ bảng riêng của M1, URL unique không domain unique. Người quyết định: @VV6505. Link #23.

## Phạm vi
- Làm: 4 file trên.
- Không làm: sửa `docs/specs/erd/**` (thuộc @tranquangthong03), `srs.md` (thuộc BA), code.

## Acceptance criteria
- [ ] Đặc tả M1 không còn nhắc `crawl_jobs`, `crawled_pages`, `product_assets`, `knowledge_chunks`, `product_inputs`, pgvector như phần của MVP.
- [ ] Mọi bảng / cột nhắc tới trong đặc tả M1 có trong `erd.dbml` trên `dev`.
- [ ] Điểm chưa chốt ở #23 được ghi "chờ #23", không tự quyết.
- [ ] qa-log #5 đóng, decision-log có dòng mới, ADR-002 có ghi chú hoãn.

## Ràng buộc
- Trình bày danh sách thay đổi trước khi sửa, chờ người dùng duyệt.
- Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(m1): đặc tả M1 v0.3 theo ERD v1.3.1`), kèm file prompt này. Mở PR vào `dev`, body ghi `Refs #23`.
- Trả về: link PR, danh sách mục đã đổi, điểm còn "chờ #23".
