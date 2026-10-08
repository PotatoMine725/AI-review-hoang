# Prompt: đặc tả M1 v0.3 theo ERD v1.3.1 (bản sửa sau #23, #38)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #23 (đồng bộ ERD ↔ M1), #38 (nghiệm thu tuần 1, hạn **14:30 08/10**) · **Branch:** `docs/m1-spec-v0-3` (tạo từ `origin/dev` mới nhất)
- **Chạy khi:** PR sửa ERD của @tranquangthong03 (4–6 điểm ở #38) đã merge vào `dev`. Kiểm tra bằng `git log origin/dev -- docs/specs/erd/`.

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản (xem `docs/README.md`).

## Đọc trước
- `CLAUDE.md`, `docs/README.md`
- Issue #23 (toàn bộ comment) và #38 (mục Backend, AI Dev). **Chỉ ghi những gì đã chốt.** Điểm chưa chốt ghi "chờ #23" hoặc "chờ #38", không tự quyết.
- `docs/specs/erd/erd.dbml` **bản mới nhất trên `origin/dev`**, `docs/specs/erd/data-dictionary.md`
- `docs/specs/m1-product-intelligence.md` (v0.2), `docs/specs/pkb/README.md`, `docs/specs/contracts/README.md`
- `docs/adr/0002-llm-provider.md` (Quyết định 4: embedding), `docs/logs/decision-log.md`, `docs/logs/qa-log.md` (#5, #12)
- `spikes/m1-crawl-extract/README.md` (mục Kết quả v0.2: Gamma bị WAF, lỗi `default_view`)

## Đã chốt (nguồn: #23, #38)
1. ERD v1.3.1 là nguồn chuẩn của data model. M1 bỏ vector RAG và 5 bảng riêng (`crawl_jobs`, `crawled_pages`, `product_assets`, `knowledge_chunks`, `product_inputs`).
2. `products.website_url` unique sau khi chuẩn hoá URL. Không unique theo domain.
3. PKB: `draft | in_review | approved | rejected`. **Chỉ merchant sở hữu product approve.** Admin chỉ reject bản `in_review` khi vi phạm chính sách, bắt buộc lý do; admin không sửa, không approve. Bản `approved` không sửa được; thu hồi làm ở mức product (`products.status` → `archived`) hoặc pause campaign.
4. Chi phí: cột `generation_jobs.tokens_in`, `tokens_out`, `cost_usd numeric(12,6)`, `cost_breakdown jsonb` theo `docs/specs/contracts/cost-breakdown.v1.schema.json`. Worker chỉ ghi `cost_breakdown`; DB tự tính 3 cột còn lại. `content_scripts` cũng có cost (theo ERD trên `dev`).
5. `result_manifest` (job crawl `completed`): `pkb_version`, `pages_used`, `model`. Job `failed`: `result_manifest = null`, lỗi ở cột `error`.
6. Video: admin QA (nội dung + kỹ thuật); merchant flag video sai (`merchant_flagged_at`, `merchant_flag_reason`). Không thuộc M1, chỉ ghi vào decision-log.
7. Pilot không đặt ngân sách tổng/product. NFR-02 của M1 (≤ $0.05/product, crawl + extract) giữ nguyên.

## Nhiệm vụ

### 1. `docs/specs/m1-product-intelligence.md` → v0.3
- **Data model và API:** thay 7 bảng bằng bảng ERD mà M1 dùng: `products`, `product_knowledge`, `generation_jobs` (`job_type = 'crawl'`). Markdown nguồn, screenshot, file upload nằm trong Storage; đường dẫn ghi trong `product_knowledge.sources` (theo `docs/specs/pkb/README.md`). Link `docs/specs/erd/`, không chép DBML.
- **1.1 Intake:** bỏ "kiểm tra trùng domain" → "`website_url` unique sau khi chuẩn hoá URL (ERD gate 2)".
- **1.2 Crawl:**
  - Bỏ qua trang không đổi bằng `content_hash` trong `sources` (NFR-04).
  - **Quy tắc robots.txt** (RFC 9309): 2xx = đọc luật; 4xx trừ 429 = không có robots, được crawl; 5xx, 429, timeout = coi như cấm toàn bộ.
  - **Bị WAF / challenge** (vd. header `cf-mitigated: challenge`): job `failed`, `error` bắt đầu bằng `waf_challenge`. Không đổi UA, không retry, không proxy. Merchant được hướng dẫn upload tài liệu (FR-10). Ví dụ thật: Gamma (spike v0.2).
- **1.3 / FR-06 / FR-13:** ảnh lưu Storage, metadata trong `sources` (`image_paths`). M3 đọc ảnh theo metadata này.
- **1.7 / FR-07:** trạng thái và quyền duyệt theo mục "Đã chốt" 3.
- **1.8 / FR-08:** bỏ khỏi MVP, FR-08 hạ xuống **Later**. M2, M4 dùng nguyên PKB approved (JSON) làm input. Bỏ endpoint `/knowledge/search` và AC tương ứng.
- **NFR-02 / NFR-07:** chi phí đọc từ cột `generation_jobs.cost_usd` (tổng do DB tính từ `cost_breakdown`). Sửa AC "đọc từ `crawl_jobs.cost_usd`".
- **Tech stack:** dòng Embedding và Phạm vi RAG ghi "hoãn sau MVP (qa-log #5)". Bỏ pgvector khỏi dòng DB của M1. Dòng chọn model: dẫn ADR-002 (đề xuất `gemini-3.5-flash-lite` batch, chờ team lead chốt 09/10 nếu chưa chốt).
- **Output:** JSON mẫu theo `docs/specs/pkb/` (có `schema_version`; bỏ `product_id`, `version`, `status` vì là cột bảng). Không chép lại toàn bộ schema, chỉ ví dụ ngắn + link.
- **Câu hỏi còn mở** (thêm/giữ):
  - `pricing.default_view` đang trộn tab chu kỳ (Monthly/Yearly) với tab đối tượng (Individual/Team). Đề xuất tách ở contract PKB v0.3. Chưa đổi schema trong PR này.
  - `evidence_in_source` của Dreamina giảm (0.92 → 0.81): đang điều tra ở branch `feat/m1-spike-elevenlabs`.
  - Sản phẩm chính sprint 1 thay Gamma: M1 đề xuất ElevenLabs, chờ QA chốt (#38).
  - Vùng giá (qa-log #9), Golden Facts (qa-log #11) giữ nguyên trạng thái.
- **Lịch sử phiên bản:** thêm dòng v0.3 (08/10/2026).

### 2. ADR-002
Quyết định 4 (embedding): thêm ghi chú "Hoãn: MVP không dùng vector RAG (ERD v1.3.1, qa-log #5, #23)". Không xoá nội dung cũ.

### 3. Logs
- `qa-log.md`: đóng #5 (không có vector RAG trong MVP, dùng nguyên PKB JSON; nguồn ERD v1.3.1, #23). #12: "không còn áp dụng trong MVP vì không có embedding".
- `decision-log.md`: thêm **dòng #17** (ngày 2026-10-08), tóm tắt 7 điểm ở mục "Đã chốt". Người quyết định: @VV6505 (data model), @khanhphi27 (luồng nghiệp vụ video), M1 owner @PotatoMine725 (phạm vi M1). Link #23, #38.

## Phạm vi
- Làm: `docs/specs/m1-product-intelligence.md`, `docs/adr/0002-llm-provider.md`, `docs/logs/qa-log.md`, `docs/logs/decision-log.md`.
- Không làm: `docs/specs/erd/**` (của @tranquangthong03), `srs.md` / `brd.md` (của BA), `docs/specs/pkb/**`, `docs/specs/contracts/**`, code.

## Acceptance criteria
- [ ] Đặc tả M1 không còn nhắc `crawl_jobs`, `crawled_pages`, `product_assets`, `knowledge_chunks`, `product_inputs`, pgvector như phần của MVP.
- [ ] Mọi bảng/cột nhắc trong đặc tả M1 có trong `erd.dbml` trên `origin/dev` (kiểm bằng grep, liệt kê trong body PR).
- [ ] Có quy tắc robots 4xx/5xx và WAF ở 1.2.
- [ ] qa-log #5 đóng, decision-log có dòng #17, ADR-002 có ghi chú hoãn.
- [ ] Điểm chưa chốt ghi "chờ #23/#38", không tự quyết.

## Ràng buộc
- Trình bày danh sách thay đổi trước khi sửa, chờ người dùng duyệt. Có hạn 14:30: giữ thay đổi gọn, không viết lại các mục không liên quan.
- Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(m1): đặc tả M1 v0.3 theo ERD v1.3.1, decision #17`), kèm file prompt này. Mở PR vào `dev`, body có `Closes #23`, `Refs #38`, `cc @tranquangthong03 @VV6505`.
- Trả về: link PR, danh sách mục đã đổi, điểm còn chờ.
