# Prompt: P1-04 — đưa extract vào worker (website + link shop) theo PKB v0.3

- **Repo / cwd:** `AI-review-BE`
- **Người làm:** Hoàng (M1). Lead đã giao ở #67: P1-04, tuần **19–25/10**.
- **Chia 2 PR**, mỗi PR một branch, làm lần lượt:
  - **A** `feat/m1-extract-worker`: adapter Gemini (retry/429, fixture, cost), PKB models/validate, extract cho `software` ra PKB v0.3, CLI, ngôn ngữ `en,vi`.
  - **B** `feat/m1-shop-item`: link shop, gồm `classify_input_url`, crawl mode `shop_item`, trích dữ liệu có cấu trúc (JSON-LD, microdata, OpenGraph) ra PKB `physical`.
- **Base branch:** `origin/docs/p1-pkb-v0-3-shop` (#68, cần schema v0.3) nếu #68 chưa merge; merge xong thì rebase lên `origin/dev`. Ghi rõ phụ thuộc #68 trong PR.
- **Cập nhật phạm vi 21/10:** sửa `normalize_page_url` và SSRF đã chuyển sang PR #89 (`feat/m1-page-url-query`, của Định). Xem mục "Ngoài phạm vi PR A" bên dưới.

---

Bạn là coding agent của repo `AI-review-BE`, chạy trên máy Windows. Làm việc bằng tiếng Việt. Người dùng là AI dev nền C#/.NET, mới với Python: giải thích ngắn, comment code tiếng Việt ngắn. **Trình bày cấu trúc module, interface và thư viện mới trước khi code, rồi chờ duyệt.**

## Đọc trước
- `CLAUDE.md`
- `docs/adr/0001-crawl-tool.md`, `docs/adr/0002-llm-provider.md`. ADR-0002 có phụ lục quota free tier và quy tắc 429/RPD (#70).
- `docs/adr/0005-repo-structure-and-extensibility.md`
- `docs/specs/m1-product-intelligence.md` (v0.4.0, trên branch #68) và `docs/specs/pkb/README.md` + `pkb-*.v0.3.schema.json`
- Code hiện có:
  - `services/worker/src/worker/m1/`: `url.py`, `crawl/*`, `models.py`, `config.py` (#63)
  - `spikes/m1-crawl-extract/extract.py`, `schema_v03.py`, `validate_contracts.py`
  - `spikes/m1-crawl-extract/probe_shop.py` (#68)
  - `spikes/p1-demo-pdfcraft/extract_facts.py` (#78): cách đọc output crawl của worker
- Issue #61: comment của lead ngày 13/10 và 18/10 (normalize URL, SSRF, retry/quota). Comment của AI ngày 14/10.
- `docs/specs/contracts/cost-breakdown.v1.schema.json` và issue #74. Usage ghi theo v1; chưa có trường `usage_*`.
- PR #83 (contract M2): M2 đọc PKB đã xác nhận qua `field_path`.

## PR A — `feat/m1-extract-worker`

Thứ tự làm: adapter LLM → extract → CLI → ngôn ngữ.

### Ngoài phạm vi PR A (đã chuyển sang #89)
- **Không làm lại:** sửa `normalize_page_url` (giữ query, bỏ tracking), `ssrf.py`, thay urllib bằng httpx, browser guard (Playwright route).
- Nếu PR A cần các phần đó để chạy thật: rebase branch lên `feat/m1-page-url-query` (sau khi đã có base `docs/p1-pkb-v0-3-shop`) và ghi rõ trong PR "chồng lên #68 và #89".
- Các điểm sửa SSRF (redirect qua route, `UnsafeUrlError` chưa bắt, IPv4-mapped, test) nằm trong review #89. Chờ Định trả lời ai làm. **Không tự sửa trên branch của Định.**

### Quyết định đã duyệt (giữ nguyên)
- `tzdata` để tính giờ reset RPD.
- Lần gọi lỗi ghi cost `0` / `$0`, `cost_status=estimated`.
- Fact có evidence không khớp: giữ fact và thêm warning.
- Fact mâu thuẫn ghi vào `conflicts`.
- Fixture 429 là dữ liệu synthetic.

### Việc cần làm

1. **Adapter Gemini** (`worker/m1/llm/`):
   - Gọi `google-genai` trực tiếp, structured output, model lấy từ config (`gemini-3.5-flash-lite`).
   - **Phân loại lỗi:**
     - 429 do vượt RPM: retry có backoff 5 → 10 → 20 → 40 → 60 s.
     - 429 do hết RPD: **không retry ngay**. Trả lỗi `llm_quota_daily` (`retryable=True`) kèm `retry_after` = thời điểm reset (0h giờ Thái Bình Dương) để hàng đợi BE đưa job về chờ.
     - 500/503: retry có backoff.
     - Lỗi khác: không retry.
     - Phân biệt RPM với RPD dựa vào nội dung lỗi trả về. Ghi rõ cách nhận diện và lưu 1 ví dụ response thật làm fixture nếu có.
   - Mỗi lần gọi, kể cả lần lỗi, ghi 1 item `cost_breakdown` v1 (`category=llm`, `call_id`, `attempt`, `cost_status`). Free tier: ghi giá niêm yết với `cost_status` theo quy ước hiện hành, không tự đổi contract.
   - Chế độ `LLM_PROVIDER=fixture` để CI và test đọc response đã lưu, không gọi mạng (ADR-0002).
2. **Extract `software`** (`worker/m1/extract/`):
   - Port logic spike: chọn top-k trang, trang pricing dùng raw markdown, trang khác dùng fit markdown, gom thành 1 lời gọi.
   - Kết quả: PKB **v0.3** (`identity.product_kind="software"`), mỗi fact có `source_id` + `evidence`, kiểm evidence có trong nguồn, merge và repair như spike.
   - Interface: `extract_product(crawl_result, page_store, llm) -> ExtractResult(data, sources, cost_breakdown, warnings)`.
   - Fact mâu thuẫn (vd số lượng công cụ khác nhau giữa 2 trang) ghi vào `conflicts`, không chọn bừa.
   - Validate bằng schema v0.3 trước khi trả.
3. **CLI:** `uv run python -m worker.m1.extract <crawl_dir> --out <dir>`. Chạy thật trên PDFCraft (`D:\tmp\crawl-pdfcraft`) và ElevenLabs. So với fact đã kiểm của demo #78 và Golden Facts T12b. Ghi kết quả vào PR, không commit output nặng.
4. **Ngôn ngữ trang:** hiện crawler bỏ trang không phải tiếng Anh (`not_english`). P1 làm video tiếng Việt, nên cho cấu hình danh sách ngôn ngữ bằng `M1_CRAWL_LANGUAGES`, mặc định `en,vi`. Giữ quy tắc chống trùng giữa các bản dịch của cùng một trang. Cập nhật `.env.example`.
   - Thay mã `not_english` bằng 2 mã đã duyệt, **không giữ alias**:
     - `language_not_allowed`: trang có ngôn ngữ ngoài `M1_CRAWL_LANGUAGES`.
     - `translation_duplicate`: bản dịch trùng với trang đã lấy ở ngôn ngữ ưu tiên hơn.
   - Cập nhật bảng mã trong `docs/specs/m1-product-intelligence.md`. BE có đọc mã này, nên PR phải cc `@tranquangthong03 @tua0201n`.

## PR B — `feat/m1-shop-item` (sau khi A đã mở PR)

1. `classify_input_url(url, html) -> software | physical`:
   - Dấu hiệu: JSON-LD `Product` có `Offer`, path `/products/`, host sàn đã biết.
   - Trả kèm lý do. Người dùng sửa được ở bước xác nhận.
2. Crawl mode `shop_item`: trang sản phẩm + tối đa 4 trang cùng host (chính sách, vận chuyển, thông số). Giữ đủ robots, WAF, SSRF như mode thường.
3. Trích dữ liệu có cấu trúc **bằng code**, không dùng LLM:
   - JSON-LD, microdata, OpenGraph → `offers[]`, `variants[]`, `media.images[]`;
   - chuẩn hoá giá theo các dạng đã gặp ở khảo sát #68;
   - evidence là chuỗi giá trị gốc; `extracted_via` ghi rõ nguồn trích.
   
   LLM chỉ dùng cho lợi ích, use-case, đối tượng. Không suy giá hoặc ảnh cho biến thể chưa kiểm (#68).
4. Test bằng fixture HTML **dữ liệu giả** (giống ví dụ của #68). Không commit HTML thật của sàn hay shop.
5. Chưa có URL shop demo nào được duyệt (BA #67). Chỉ chạy tay trên trang được phép; nếu chưa có thì ghi "chưa chạy trên nguồn thật".

## Phạm vi
- **Làm:** `services/worker/**` (code, test, README), `docs/specs/m1-product-intelligence.md` (mục extract, lỗi quota, ngôn ngữ; dòng lịch sử phiên bản), file prompt này. SSRF và `normalize_page_url` thuộc #89.
- **Không làm:** DB/migration, API FastAPI, hàng đợi, Storage (thuộc BE, #61), M2 (#83), renderer.
- **Thư viện:** `google-genai` (ADR-0002), `httpx` (đã có). Parse HTML bằng thư viện Crawl4AI đã kéo theo. Cần thêm gì thì hỏi trước.
- **Không commit:** `.env`, output crawl hoặc PKB thật cỡ lớn, HTML của bên thứ ba.

## Tiêu chí hoàn thành
**PR A:**
- [ ] `extract_product` trả PKB v0.3 hợp lệ schema cho PDFCraft và ElevenLabs (chạy tay).
- [ ] Test không cần mạng (fixture LLM) phủ các ca:
  - retry RPM; RPD → `llm_quota_daily` kèm `retry_after`; 500/503;
  - item `cost_breakdown` cho mỗi lần gọi;
  - evidence không có trong nguồn bị loại hoặc cảnh báo;
  - conflict.
- [ ] `M1_CRAWL_LANGUAGES` (mặc định `en,vi`), `language_not_allowed` và `translation_duplicate` có test; không còn `not_english`; bảng mã trong spec đã cập nhật.
- [ ] ruff, ruff format, pyright, pytest xanh trong CI worker.

**PR B:**
- [ ] `classify_input_url` và trích dữ liệu có cấu trúc có test bằng fixture giả.
- [ ] PKB `physical` hợp lệ v0.3.

## Khi xong
- Mỗi PR commit kèm file prompt này, mở vào `dev`, body có:
  - `Refs #67, #61` (A thêm `#68`, `#70`, `#89`);
  - kết quả chạy tay;
  - giới hạn còn lại.
- `cc @VV6505 @tranquangthong03 @tua0201n`. Interface `extract_product` và mã lỗi dùng cho job BE.
- Trả về: link PR, kết quả test, so sánh với fact đã kiểm.
