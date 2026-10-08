# Module 1 — Product Intelligence: Đặc tả kỹ thuật

Oct 5, 2026 · @Hoang Nguyen · **v0.3** (08/10/2026, issue #23, #38) · Lịch sử: xem cuối file

> **Nguồn chuẩn của data model:** ERD v1.3.1 ([`docs/specs/erd/`](erd/)). Đặc tả này chỉ nêu bảng và cột M1 dùng, không chép DBML. ERD đã gộp thay đổi của #23 (PR #49): `in_review`, 4 cột chi phí của `generation_jobs`. Ghi chú "chờ #50" nghĩa là điểm ERD còn để mở, chưa có quyết định.

## Tổng quan

Module 1 nhận URL (và form tùy chọn) của merchant, trả về **Product Knowledge Base (PKB)** đã chuẩn hóa, mọi fact đều có nguồn và được người duyệt. PKB là đầu vào duy nhất cho Module 2 (Content Strategy), Module 3 (screenshot cho video) và Module 4 (fact-check).

**Trong phạm vi MVP:** crawl tối đa 30 trang public/product; trích xuất structured có trích nguồn; chụp screenshot desktop + mobile làm bằng chứng; merchant review và approve theo version (qa-log #1). Không có vector RAG trong MVP: M2, M4 dùng nguyên PKB approved (JSON) làm input (qa-log #5, ERD v1.3.1, #23).

**Ngôn ngữ MVP (qa-log #3, #8, issue #15):** tiếng Anh cho site nguồn, PKB và video. Crawl ưu tiên và giới hạn ở trang tiếng Anh; bỏ qua trang bản dịch (`/fr/…`, `/ja-jp/…`).

**Ngoài phạm vi MVP:** tự đăng nhập để crawl sau login (nội dung sau login do merchant upload ảnh/PDF qua FR-10, qa-log #2), crawl sâu đối thủ (chỉ lưu tên + URL), re-crawl tự động theo lịch, đa ngôn ngữ (tiếng Việt và ngôn ngữ khác xét ở phase sau), Trend Engine.

## Kiến trúc & luồng xử lý

&#91;embedded content: Pipeline Module 1 · 8 sub-module, 1 job\]

Sau crawl, chụp ảnh (1.3) và trích xuất (1.4) chạy song song; chỉ PKB đã approve mới được cấp cho M2, M3, M4.

## Phân rã sub-module

Module 1 gồm 7 sub-module trong MVP, chạy tuần tự trong một job; 1.3 và 1.4 chạy song song sau khi crawl xong. 1.8 (Knowledge Indexing) bỏ khỏi MVP.

| Sub-module | Trách nhiệm | Input → Output |
| --- | --- | --- |
| 1.1 Intake | Validate URL/form; `website_url` phải unique sau khi chuẩn hoá URL (ERD gate 2, không unique theo domain); tạo `products` + `generation_jobs` (`job_type = 'crawl'`), đẩy vào queue | Form → `product_id`, `job_id` |
| 1.2 Discover & Crawl | Đọc `robots.txt` + `sitemap.xml`, chấm điểm link (pricing, features, docs, FAQ, changelog, compare), render JS, lưu markdown + `content_hash` (trang không đổi thì bỏ qua, NFR-04). Ghi vùng IP / locale lúc crawl (giá có thể theo vùng). Host phụ cùng domain gốc: xem FR-02. Quy tắc robots và WAF: xem [Quy tắc crawl](#quy-tắc-crawl) | URL → ≤ 30 trang markdown có `page_type` |
| 1.3 Asset Capture | Chụp full-page, viewport desktop 1440×900 và mobile 430×932 @3x, chụp theo element từng section tính năng; lấy logo (ưu tiên SVG, kèm wordmark), màu thương hiệu. Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai (`media_sample`, FR-13) | Trang → file ảnh trong Storage; metadata ở `product_knowledge.sources` (`image_paths`) |
| 1.4 Structured Extraction | LLM trích xuất theo JSON schema; mỗi fact kèm `source_id` + đoạn trích ngắn. **Mode mặc định `batch`:** gom top-k trang theo điểm (spike: k = 10) vào 1 lời gọi. Trang pricing gửi raw markdown, trang khác gửi fit markdown. Giá theo [Quy tắc trích xuất giá](#quy-tắc-trích-xuất-giá) | Markdown → fact |
| 1.5 Normalize & Merge | Gộp fact nhiều trang, khử trùng tính năng, chuẩn hóa giá (tiền tệ, chu kỳ) bằng code và ghi nguồn, áp thứ tự ưu tiên merchant > crawl > inferred, đánh dấu xung đột | Fact rời → PKB draft |
| 1.6 Enrichment | Suy ra audience, JTBD, use case, USP, đối thủ gợi ý; gắn nhãn `origin: inferred` | PKB draft → PKB draft đầy đủ |
| 1.7 Validation & Review | Validate schema, tính `completeness`, hiện xung đột; merchant sửa và gửi duyệt (`draft → in_review`), **chỉ merchant sở hữu product approve** → version mới (qa-log #1). Admin chỉ reject bản `in_review` khi vi phạm chính sách, bắt buộc lý do; admin không sửa, không approve. Đây là bổ sung cho decision-log #11 (đã chốt ở #23). Nơi lưu lý do reject và ý nghĩa `approved_by` / `approved_at` khi reject: chờ #50 | PKB draft → PKB approved vN |
| ~~1.8 Knowledge Indexing~~ | **Bỏ khỏi MVP** (FR-08 hạ xuống Later). Không có chunk, embedding, pgvector. M2, M4 dùng nguyên PKB approved (JSON). Nguồn: ERD v1.3.1, qa-log #5, #23 | — |

## Input

Chỉ 2 trường bắt buộc: **Website URL** và **Affiliate link**. Mọi trường khác tùy chọn; nếu merchant nhập thì giá trị đó ghi đè kết quả crawl.

| Trường | Bắt buộc | Nguồn nếu bỏ trống | Ghi chú |
| --- | --- | --- | --- |
| Website URL | Có | — | Host của URL giới hạn phạm vi crawl; host phụ cùng domain gốc theo FR-02 |
| Affiliate link / program URL | Có | — | Module 6 dùng làm đích redirect |
| Product name, description | Không | Crawl (title, meta, hero) |  |
| Pricing, free plan, trial, paid plans | Không | Crawl trang pricing | Sai giá là lỗi nghiêm trọng nhất |
| Main features, use cases | Không | Crawl features/docs |  |
| Target audience, USP | Không | 1.6 suy ra (inferred) | Cần merchant xác nhận |
| Competitors | Không | 1.6 gợi ý | Chỉ lưu tên + URL |
| Limitations | Không | Crawl FAQ/docs |  |
| Commission | Không | — | Hiển thị cho creator |
| Brand guidelines (logo, màu, tone) | Không | 1.3 trích từ trang |  |
| Forbidden / approved claims | Không | — | Module 4 dùng để chặn nội dung |
| Tài liệu upload (PDF, ảnh sau login) | Không | — | Thay cho crawl sau login. Merchant pilot sẽ cung cấp (qa-log #2) |

Nguồn cấu hình hệ thống: giới hạn 30 trang/job (tính cả trang host phụ), ≤ 5 trang host phụ, 1 request/giây/domain, danh sách `page_type` ưu tiên.

## Output

Output chính là một PKB JSON; mỗi fact mang `source_id` (crawl) hoặc `origin: merchant`, fact `inferred` phải được duyệt trước khi Module 2 dùng. Hợp đồng đầy đủ: [`docs/specs/pkb/`](pkb/README.md) (schema máy đọc được ở đó, không chép lại ở đây).

PKB nằm trong cột `product_knowledge.data`. `product_id`, `version`, `status`, `approved_by` là **cột của bảng**, không nằm trong JSON. JSON chỉ có `schema_version`. Danh sách trang nguồn nằm ở cột `product_knowledge.sources`.

Ví dụ rút gọn của `data`:

```json
{
  "schema_version": "0.2",
  "identity": {
    "name": { "value": "Claude", "origin": "crawled", "source_id": "src_01", "evidence": "…" },
    "website": "https://claude.com"
  },
  "pricing": {
    "region": "VN", "locale": "en-US", "default_view": "monthly", "other_views": ["yearly"],
    "plans": [{
      "name": "Pro", "currency": "USD", "list_price": 20, "promo_price": null,
      "price_unit": "month", "billing_cycle": "monthly",
      "price_text": "$20 / month billed monthly", "source_id": "src_02", "evidence": "…"
    }]
  },
  "features": [{ "id": "f1", "name": "Projects", "origin": "crawled", "source_id": "src_01", "evidence": "…", "screenshot_ids": [] }],
  "quality": { "completeness": 0.82, "conflicts": [] }
}
```

Ví dụ 1 phần tử của `sources`: `{ "id": "src_01", "url": "…", "page_type": "features", "variant": "fit", "fetched_at": "…", "content_hash": "…", "region": "VN", "locale": "en-US", "markdown_path": "…", "image_paths": ["…"] }`. Đường dẫn là Supabase Storage (private).

`identity.version` và `models[]` là fact như mọi fact khác (bắt buộc `source_id`): với product AI, phiên bản model (vd. "Seedance 2.5") là thông tin video hay dùng (`references/ref-videos-2026-10-06.md`).

### Quy tắc crawl

1. **robots.txt (RFC 9309).** Trả 2xx: đọc luật và tuân theo. Trả 4xx trừ 429: coi như không có robots, được crawl. Trả 5xx, 429 hoặc timeout: coi như cấm toàn bộ, không crawl.
2. **Bị WAF / challenge** (vd. header `cf-mitigated: challenge`): job `failed`, cột `generation_jobs.error` bắt đầu bằng `waf_challenge`, `result_manifest = null`. Không đổi User-Agent, không retry, không dùng proxy. Merchant được hướng dẫn upload tài liệu (FR-10). Ví dụ thật: Gamma (`spikes/m1-crawl-extract/README.md`, kết quả v0.2).
3. **Chuyển hướng tới trang đăng nhập (`login_redirect`).** Trang con chuyển hướng tới trang đăng nhập: bỏ qua trang đó, ghi lý do, crawl tiếp, không theo link từ trang đăng nhập. Trang chủ chuyển hướng tới đăng nhập: dừng product (job `failed`). Xem PR #39.
4. **Trang không đổi.** Bỏ qua trang có `content_hash` trùng với bản trong `product_knowledge.sources` (NFR-04).

### Quy tắc trích xuất giá

Rút ra từ spike #6 (`spikes/m1-crawl-extract/README.md`, mục "Đề xuất cho đặc tả v0.2"). Spike chỉ đạt 1/8 lần chạy đúng giá + tên plan; các lỗi đều thuộc những quy tắc dưới đây.

1. **Tách giá niêm yết và giá khuyến mãi.** `list_price` là giá thường; `promo_price` + `promo_terms` (vd. "tháng đầu") là giá khuyến mãi. Spike ghi giá tháng đầu của Dreamina vào trường `price` duy nhất.
2. **Model không tự tính giá.** Giá số phải là con số in trên trang; `price_text` chép nguyên văn. Quy đổi (năm → tháng, VND → USD) do code làm ở 1.5 và ghi nguồn. Spike: 3.1-flash-lite ghi 16.67 (= 200/12) thay vì $17 in trên trang.
3. **`price_unit` và `billing_cycle` bắt buộc, không nhận `unknown` cho plan lấy từ trang pricing.**
   - `price_unit`: giá tính cho đơn vị nào (`month`, `year`, `seat_month`, `seat_year`, `one_time`).
   - `billing_cycle`: cách trả (`monthly`, `quarterly`, `yearly`, `one_time`).
   - 1 plan có nhiều chu kỳ thì ghi nhiều dòng. Vd. Claude Pro: `17, month, yearly` và `20, month, monthly`.
4. **Tách plan khỏi giá theo đơn vị.** `plans` chỉ chứa gói đăng ký. Giá theo token, theo giây video, theo credit nằm trong `usage_prices` (tên, đơn vị, giá, tiền tệ).
5. **Ghi tab / chu kỳ mặc định của trang giá.** `default_view` là tab trang hiển thị lúc crawl; `other_views` là các tab chưa lấy (Dreamina có Yearly / Quarterly / Monthly / 1-month, crawl chỉ thấy Monthly). Reviewer dựa vào đây để biết giá đã đủ chưa.
6. **Giá theo vùng IP.** Ghi `region` (vùng của IP crawl) và `locale` ở `pricing` và từng `sources[]`; `currency` mỗi plan là tiền tệ in trên trang. Spike chạy từ IP Việt Nam nên Dreamina hiện giá VND. Không đổi vùng bằng proxy; đối chiếu giá (NFR-03) phải so cùng vùng. Chọn vùng giá cho MVP: chờ qa-log #9.
7. **Mode `batch` là mặc định** (1.4). Mode `per_page` (1 lời gọi / trang) sinh plan nhiễu ("Paid plans", giá API ghi thành plan) và không đạt NFR-01, NFR-02.

Output phụ và module sử dụng:

| Artifact | Lưu ở đâu | Ai dùng |
| --- | --- | --- |
| PKB approved (JSON) | `product_knowledge.data` | M2 (hook, script), M4 (fact-check), M8 (hiển thị) |
| Screenshot desktop/mobile/element, logo (ưu tiên SVG), `media_sample` | Supabase Storage; đường dẫn trong `product_knowledge.sources` (`image_paths`) | M3 (nền video, thẻ thương hiệu), M4 (bằng chứng) |
| Markdown trang nguồn, file merchant upload | Supabase Storage; đường dẫn trong `product_knowledge.sources` (`markdown_path`) | Debug, M4 |
| Báo cáo job (trạng thái, lỗi, chi phí token) | `generation_jobs` (`status`, `error`, `result_manifest`, cột chi phí) | Admin, tester |

## Requirements

Yêu cầu cốt lõi: không fact nào được vào PKB mà thiếu nguồn hoặc thiếu xác nhận của người duyệt.

### Functional

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| FR-01 | Tạo product chỉ với Website URL + affiliate link | Must |
| FR-02 | Tự chọn trang quan trọng (pricing, features, docs, FAQ, changelog), tối đa 30 trang, tôn trọng `robots.txt` của từng host. Crawl được host phụ cùng domain gốc (vd. `support.claude.com` cho `claude.com`): tối đa 5 trang, chỉ `page_type` faq / pricing, tính vào giới hạn 30. Bật theo từng product, không tự bật: domain gốc có thể là sản phẩm khác (`dreamina.capcut.com` → `capcut.com`) | Must |
| FR-03 | Render được trang SPA (JavaScript) | Must |
| FR-04 | Trích xuất theo JSON schema; mỗi fact có `source_id` + evidence; giá theo [Quy tắc trích xuất giá](#quy-tắc-trích-xuất-giá) | Must |
| FR-05 | Fact suy luận gắn `origin: inferred`, không được dùng khi chưa duyệt | Must |
| FR-06 | Chụp screenshot full-page, desktop 1440×900, mobile 430×932 @3x, element theo section tính năng; logo ưu tiên SVG. Ảnh lưu Storage, metadata trong `sources` (`image_paths`); M3 đọc ảnh theo metadata này | Must |
| FR-07 | Merchant xem, sửa, approve PKB; mỗi lần approve tạo version mới. Trạng thái: `draft \| in_review \| approved \| rejected`. **Chỉ merchant sở hữu product approve.** Admin chỉ reject bản `in_review` khi vi phạm chính sách, bắt buộc lý do; admin không sửa, không approve (bổ sung cho decision-log #11, đã chốt ở #23). Nơi lưu lý do reject và ý nghĩa `approved_by` / `approved_at` khi reject: chờ #50. Bản `approved` không sửa được; thu hồi làm ở mức product (`products.status` → `archived`) hoặc pause campaign (#23, #38) | Must |
| FR-08 | ~~Index PKB approved vào pgvector, API search~~ **Hoãn sau MVP** (qa-log #5, ERD v1.3.1, #23). M2, M4 dùng nguyên PKB approved (JSON) | Later |
| FR-09 | Phát hiện xung đột (form vs crawl, giá khác nhau giữa các trang) và hiện cho reviewer | Should |
| FR-10 | Upload PDF/ảnh cho phần sau login, đưa vào extraction | Should |
| FR-11 | Re-crawl thủ công + diff với version trước | Should |
| FR-12 | Hiển thị tiến trình job theo bước (queued → crawling → extracting → review) | Should |
| FR-13 | Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai làm bằng chứng (ảnh lưu Storage, metadata `kind: media_sample` trong `product_knowledge.sources`) | Could |

### Non-functional

| ID | Yêu cầu | Mục tiêu |
| --- | --- | --- |
| NFR-01 | Thời gian xử lý 1 product (30 trang) | ≤ 5 phút p95 |
| NFR-02 | Chi phí LLM mỗi product (crawl + extract) | ≤ $0.05, đọc từ `generation_jobs.cost_usd` (DB tính tổng từ `cost_breakdown`). Chỉ tính job có `cost_breakdown` khác `'{}'`: `'{}'` (mặc định) nghĩa là chưa ghi chi phí, khác chi phí = 0. Spike đo **~$0.01** ($0.008–0.014) với mode `batch` (10 trang, 1 lời gọi); mode `per_page` $0.065–0.110, không đạt. Mẫu 2 product, giá gói trả phí Standard; cần xác nhận trên golden set (qa-log #6) |
| NFR-03 | Độ chính xác giá + tên plan trước review | ≥ 95% trên golden set 10 product, so cùng vùng IP lúc crawl. Spike: 1/8 lần chạy đúng (trước khi có Quy tắc trích xuất giá) |
| NFR-04 | Retry | 3 lần, exponential backoff; job idempotent theo `content_hash` |
| NFR-05 | Lịch sự với site | ≤ 1 request/giây/domain, User-Agent định danh platform |
| NFR-06 | Bảo mật | File upload và tài liệu merchant chỉ merchant + admin đọc (Supabase RLS) |
| NFR-07 | Quan sát | Log từng bước, trace mọi lời gọi LLM. Token và chi phí ghi ở `generation_jobs` (`tokens_in`, `tokens_out`, `cost_usd`, `cost_breakdown`). Worker chỉ ghi `cost_breakdown` theo [contract](contracts/README.md); DB tự tính 3 cột còn lại. Worker ghi payload v1 đầy đủ khi job kết thúc (`completed` hoặc `failed`). `NOT NULL` / default của `tokens_in`, `tokens_out`, `cost_usd`: chờ #50. Pilot không đặt ngân sách tổng / product |
| NFR-08 | Thay provider | Đổi model LLM bằng config, không sửa code |

## Tech stack

Worker viết bằng Python vì hệ sinh thái crawl/LLM tốt nhất; frontend và DB theo stack chung của PRD (Next.js + Supabase).

| Thành phần | Chọn | Lý do / thay thế |
| --- | --- | --- |
| Worker runtime | Python 3.12 + FastAPI (internal API) | Thư viện crawl, LLM, Pydantic đầy đủ |
| Queue | Supabase Queues (pgmq) | Không thêm hạ tầng; thay thế: Redis + ARQ |
| Crawl (1.2) | [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0, chạy Playwright, xuất markdown cho LLM ([so sánh](https://crawlbase.com/blog/firecrawl-alternatives/)). Không chọn Firecrawl self-host vì AGPL-3.0 |
| Screenshot (1.3) | Playwright for Python | Kiểm soát viewport, device scale, element screenshot |
| Extraction (1.4) | Gemini Flash-Lite 3.x, structured output theo JSON schema, mode `batch`. Ứng viên: `gemini-3.1-flash-lite` ($0.25/$1.50) và `gemini-3.5-flash-lite` ($0.30/$2.50). **Chọn model: theo [ADR-0002](../adr/0002-llm-provider.md)** (đề xuất `gemini-3.5-flash-lite`, mode `batch`; chờ team lead chốt 09/10) | Gemini 2.5 Flash-Lite bỏ vì không mở cho dự án mới (issue #5, qa-log #6). Spike: 3.1 rẻ hơn ~30 %; 3.5 đúng hơn ở chi tiết giá (chép nguyên văn, điền `currency` từng plan). Đọc được ảnh |
| Merge + Enrichment (1.5–1.6) | Gemini Flash (model mạnh hơn 1 bậc). Tham khảo: `gemini-3.5-flash` ($1.50/$9.00). **Chờ ADR-002** | Ít lời gọi, cần suy luận tốt hơn |
| LLM adapter | Adapter mỏng của dự án, chọn provider/model bằng config (ADR-0005). Có dùng LiteLLM hay không: **chờ ADR-002** | **Rủi ro LiteLLM:** bản 1.82.7 và 1.82.8 trên PyPI bị cài mã độc (24/03/2026). Spike gọi thẳng `google-genai` (decision-log #9). `crawl4ai` 0.9.4 kéo gián tiếp `unclecode-litellm` (bản fork, đã ghim hash trong `uv.lock`). Phương án thay model: DeepSeek V4-Flash ($0.14/$0.28, [so sánh](https://www.spheron.network/blog/llm-api-pricing-comparison-gpt-claude-gemini-deepseek-2026/)) |
| Schema + validate | Pydantic v2 | Dùng chung schema cho LLM output và API |
| DB | Supabase Postgres | 1 nơi cho data, RLS |
| Storage | Supabase Storage | Screenshot, markdown nguồn |
| Embedding | **Hoãn sau MVP** (qa-log #5, ERD v1.3.1, #23) | MVP không dùng vector RAG. Ứng viên cũ: xem ADR-0002, Quyết định 4 |
| Phạm vi RAG | **Hoãn sau MVP** (qa-log #5) | M2, M4 dùng nguyên PKB approved (vài KB) làm context |
| LLM tracing | Langfuse (self-host hoặc cloud free tier) | Theo dõi prompt, token, chi phí |
| Review UI | Next.js + shadcn/ui + Supabase Realtime | Theo PRD; realtime để hiện tiến trình job |
| Test | pytest, golden set 10 product, Playwright E2E cho UI | Tester đo NFR-03 |

Giá Gemini tra lại ngày **07/10/2026** tại trang giá chính thức <https://ai.google.dev/gemini-api/docs/pricing>: gói trả phí, tier **Standard**, USD / 1M token, input text (input / output; output gồm thinking token). Khớp giá spike dùng ngày 06/10/2026 (`spikes/m1-crawl-extract/config.py`). 

"Mode `batch`" trong đặc tả này là gom nhiều trang vào 1 lời gọi, **không phải** tier Batch API của Gemini (rẻ hơn ~50 %, trả kết quả không đồng bộ). Mọi chi phí ở đây tính theo tier Standard. Giá DeepSeek tra ngày 05/10/2026 qua trang so sánh, chưa kiểm tra lại.

## Data model và API

M1 dùng 3 bảng của ERD v1.3.1 ([`docs/specs/erd/`](erd/erd.dbml), [data dictionary](erd/data-dictionary.md)). Không có bảng riêng cho crawl, trang, asset, chunk hay input.

| Bảng | Cột M1 dùng | Ghi chú |
| --- | --- | --- |
| `products` | `id`, `merchant_id`, `website_url`, `affiliate_url`, `name`, `merchant_input`, `current_knowledge_version`, `status` | `website_url` unique sau khi chuẩn hoá URL, không unique theo domain. Form merchant nhập nằm ở `merchant_input` |
| `product_knowledge` | `product_id`, `version`, `status`, `data`, `sources`, `approved_by`, `approved_at` | PK `(product_id, version)`. `data` = PKB JSON, `sources` = trang nguồn + đường dẫn Storage (theo [`docs/specs/pkb/`](pkb/README.md)). `status`: `draft \| in_review \| approved \| rejected` Lý do reject: chờ #50 |
| `generation_jobs` | `id`, `product_id`, `job_type`, `status`, `idempotency_key`, `input_snapshot`, `result_manifest`, `error`, `attempts`, `finished_at` | M1 dùng `job_type = 'crawl'`. Cột chi phí `tokens_in`, `tokens_out`, `cost_usd` `numeric(12,6)`, `cost_breakdown` `jsonb DEFAULT '{}'`. `'{}'` = chưa ghi chi phí, khác chi phí = 0; worker ghi payload v1 đầy đủ khi job `completed` hoặc `failed`. Nullability của `tokens_in`, `tokens_out`, `cost_usd`: chờ #50 |

`result_manifest`: job `completed` có `pkb_version`, `pages_used`, `model`. Job `failed`: `result_manifest = null`, lỗi ở cột `error` (mã ngắn đứng đầu, vd. `waf_challenge`). Markdown nguồn, screenshot, file upload nằm trong Supabase Storage (private), không có bảng riêng.

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| POST | `/products` | Body: website\_url, affiliate\_url, form? → product\_id, job\_id |
| GET | `/jobs/{id}` | Trạng thái, bước hiện tại, lỗi, chi phí |
| POST | `/products/{id}/uploads` | Upload PDF/ảnh bổ sung |
| POST | `/products/{id}/recrawl` | Tạo job mới, trả diff khi xong |
| GET | `/products/{id}/knowledge?version=` | Lấy PKB (mặc định bản approved mới nhất) |
| PATCH | `/products/{id}/knowledge` | Sửa bản draft (field-level) |
| POST | `/products/{id}/knowledge/approve` | Chỉ merchant sở hữu product. Khóa bản `in_review` thành `approved` |
| GET | `/products/{id}/assets?kind=` | Danh sách screenshot cho M3, đọc từ `sources[].image_paths` |

## Phân công, kế hoạch và acceptance criteria

AI-1 phụ trách toàn bộ phần AI của Module 1 (1.2–1.6; qa-log #4, issue #14); AI-2 làm Module 2 và 4 theo kế hoạch tuần 1. Ước tính 3 tuần ở v0.1 giả định 2 AI dev, **cần ước tính lại** cho 1 AI dev.

| Vai trò | Phụ trách |
| --- | --- |
| AI-1 | 1.2 Crawl, 1.3 Asset Capture, 1.4 Extraction, 1.5 Merge, 1.6 Enrichment, prompt + schema |
| Backend core | Bảng Supabase (theo ERD), queue, API `/products`, `/jobs`, RLS |
| Frontend | Form onboarding, màn hình review PKB (diff, xung đột, approve) |
| BA | Chốt schema PKB, danh sách `page_type`, form merchant, quy tắc forbidden claims |
| Tester | Golden set 10 product (đáp án nhập tay), test API, E2E review UI |

Kế hoạch:

1. Tuần 1 — Spike: script Python URL → markdown → PKB JSON cho 3 product mẫu; BA chốt schema; tester dựng golden set.
2. Tuần 2 — Worker + queue + bảng DB + screenshot; API `/products`, `/jobs`, `/knowledge`.
3. Tuần 3 — Màn hình review, versioning, đo NFR trên golden set.

Acceptance criteria (tester kiểm):

- [ ] Chỉ nhập URL + affiliate link → có PKB draft trong ≤ 5 phút cho ≥ 8/10 product golden set
- [ ] Giá và tên plan đúng ≥ 95% so với đáp án trước khi review
- [ ] 0 fact thiếu `source_id` mà không phải `origin: merchant`
- [ ] Mỗi tính năng chính có ≥ 1 screenshot; có ảnh mobile 1290×2796 cho trang chủ và pricing
- [ ] Approve tạo version mới; bản cũ vẫn đọc được qua `?version=`
- [ ] Site chặn bằng WAF → job `failed`, `error` bắt đầu bằng `waf_challenge`, không retry
- [ ] Re-crawl site không đổi → 0 trang xử lý lại, 0 token LLM
- [ ] Chi phí LLM trung bình ≤ $0.05/product (đọc từ `generation_jobs.cost_usd`, chỉ job có `cost_breakdown` khác `'{}'`)

Câu hỏi đã trả lời (BA, issue #15):

- Ai approve PKB? → Merchant (qa-log #1). Giữ FR-07.
- Merchant pilot có cung cấp ảnh/tài liệu phần sau login không? → Có, upload qua FR-10; crawler không tự đăng nhập (qa-log #2).
- Ngôn ngữ? → MVP dùng tiếng Anh cho site nguồn, PKB và video (qa-log #3, #8).

Câu hỏi còn mở:

- ~~Phạm vi RAG của 1.8~~ → đã đóng: không có vector RAG trong MVP (qa-log #5, ERD v1.3.1, #23).
- `pricing.default_view` đang trộn tab chu kỳ (Monthly / Yearly) với tab đối tượng (Individual / Team). Đề xuất tách ở contract PKB v0.3. Chưa đổi schema trong PR này.
- ~~`evidence_in_source` của Dreamina giảm (0.92 → 0.81)~~ → đã điều tra (PR #39): 4 fact lệch do LLM gán sai `source_id` (evidence nằm ở `src_01`, ghi `src_02`); `check_evidence` không lỗi. Đề xuất cho contract / pipeline sau: code tìm evidence trên mọi trang rồi tự sửa `source_id`.
- Sản phẩm chính sprint 1 thay Gamma (bị WAF): M1 đề xuất ElevenLabs, chờ QA chốt (#38).
- Vùng giá → qa-log #9. Golden Facts → qa-log #11. Cả hai giữ nguyên trạng thái.
- Nơi lưu lý do reject PKB, ý nghĩa `approved_by` / `approved_at` khi reject, nullability của `tokens_in` / `tokens_out` / `cost_usd` → chờ #50.
- NFR-02 trên golden set → chờ qa-log #6.
- Chọn model extraction / merge (3.1 hay 3.5 Flash-Lite), có dùng LiteLLM không → chờ ADR-002 (team lead chốt 09/10).

## Lịch sử phiên bản

| Phiên bản | Ngày | Người sửa | Thay đổi |
| --- | --- | --- | --- |
| v0.1 | 05/10/2026 | @Hoang Nguyen | Bản đầu |
| v0.2 | 07/10/2026 | @PotatoMine725 (issue #5) | Thay Gemini 2.5 Flash-Lite bằng ứng viên Flash-Lite 3.x, tra lại giá 07/10/2026 trên trang chính thức, chọn model chờ ADR-002. NFR-02 ghi số đo spike (~$0.01/product, mode `batch`), link qa-log #6. Embedding ứng viên `gemini-embedding-2` 768 chiều; phạm vi RAG chờ qa-log #5. Ghi rủi ro LiteLLM. AI-1 làm toàn bộ M1 (#14). Merchant approve PKB, nội dung sau login qua FR-10, MVP tiếng Anh (#15). Thêm Quy tắc trích xuất giá từ spike #6 (tách giá niêm yết / khuyến mãi, cấm model tự tính giá, `price_unit` + `billing_cycle` bắt buộc, `usage_prices`, `default_view`, vùng IP), mode `batch` mặc định, crawl host phụ cùng domain gốc (≤ 5 trang). Thêm `identity.version`, `models[]`, logo ưu tiên SVG, FR-13 `media_sample` (Could) từ video tham khảo |
| v0.3 | 08/10/2026 | @PotatoMine725 (issue #23, #38) | Theo ERD v1.3.1: bỏ 5 bảng riêng (`crawl_jobs`, `crawled_pages`, `product_assets`, `knowledge_chunks`, `product_inputs`), dùng `products`, `product_knowledge`, `generation_jobs`. Bỏ vector RAG: 1.8 ra khỏi MVP, FR-08 hạ xuống Later, bỏ `/knowledge/search`, hoãn embedding. `website_url` unique sau chuẩn hoá. Thêm Quy tắc crawl (robots RFC 9309, WAF `waf_challenge`). Trạng thái PKB `draft \| in_review \| approved \| rejected`, chỉ merchant approve, admin chỉ reject có lý do. Chi phí đọc từ `generation_jobs.cost_usd`. Output dẫn contract `docs/specs/pkb/`. Điểm ERD còn để mở ghi "chờ #50". Đồng bộ theo ERD đã merge (PR #49): `cost_breakdown` `'{}'` = chưa ghi chi phí, NFR-02 chỉ tính job đã ghi; admin chỉ reject (bổ sung decision-log #11) |
