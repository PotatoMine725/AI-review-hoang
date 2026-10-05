# Module 1 — Product Intelligence: Đặc tả kỹ thuật

Oct 5, 2026 · @Hoang Nguyen

## Tổng quan

Module 1 nhận URL (và form tùy chọn) của merchant, trả về **Product Knowledge Base (PKB)** đã chuẩn hóa, mọi fact đều có nguồn và được người duyệt. PKB là đầu vào duy nhất cho Module 2 (Content Strategy), Module 3 (screenshot cho video) và Module 4 (fact-check).

**Trong phạm vi MVP:** crawl tối đa 30 trang public/product; trích xuất structured có trích nguồn; chụp screenshot desktop + mobile làm bằng chứng; merchant/admin review và approve theo version; index RAG.

**Ngoài phạm vi MVP:** tự đăng nhập để crawl sau login (thay bằng upload ảnh/PDF), crawl sâu đối thủ (chỉ lưu tên + URL), re-crawl tự động theo lịch, đa ngôn ngữ, Trend Engine.

## Kiến trúc & luồng xử lý

&#91;embedded content: Pipeline Module 1 · 8 sub-module, 1 job\]

Sau crawl, chụp ảnh (1.3) và trích xuất (1.4) chạy song song; chỉ PKB đã approve mới được index và cấp cho M2, M3, M4.

## Phân rã sub-module

Module 1 gồm 8 sub-module chạy tuần tự trong một job; 1.3 và 1.4 chạy song song sau khi crawl xong.

| Sub-module | Trách nhiệm | Input → Output |
| --- | --- | --- |
| 1.1 Intake | Validate URL/form, kiểm tra trùng domain, tạo `product` + `crawl_job`, đẩy vào queue | Form → `product_id`, `job_id` |
| 1.2 Discover & Crawl | Đọc `robots.txt` + `sitemap.xml`, chấm điểm link (pricing, features, docs, FAQ, changelog, compare), render JS, lưu markdown + `content_hash` | URL → ≤ 30 trang markdown có `page_type` |
| 1.3 Asset Capture | Chụp full-page, viewport desktop 1440×900 và mobile 430×932 @3x, chụp theo element từng section tính năng; lấy logo, màu thương hiệu | Trang → file ảnh trong Storage + metadata |
| 1.4 Structured Extraction | LLM trích xuất theo JSON schema riêng cho từng `page_type`; mỗi fact kèm `source_id` + đoạn trích ngắn | Markdown → fact theo trang |
| 1.5 Normalize & Merge | Gộp fact nhiều trang, khử trùng tính năng, chuẩn hóa giá (tiền tệ, chu kỳ), áp thứ tự ưu tiên merchant > crawl > inferred, đánh dấu xung đột | Fact rời → PKB draft |
| 1.6 Enrichment | Suy ra audience, JTBD, use case, USP, đối thủ gợi ý; gắn nhãn `origin: inferred` | PKB draft → PKB draft đầy đủ |
| 1.7 Validation & Review | Validate schema, tính `completeness`, hiện xung đột; merchant/admin sửa và approve → tạo version mới | PKB draft → PKB approved vN |
| 1.8 Knowledge Indexing | Chia chunk PKB approved + markdown nguồn, embed, lưu pgvector; cung cấp API search cho M2/M4 | PKB approved → chunks + vector |

## Input

Chỉ 2 trường bắt buộc: **Website URL** và **Affiliate link**. Mọi trường khác tùy chọn; nếu merchant nhập thì giá trị đó ghi đè kết quả crawl.

| Trường | Bắt buộc | Nguồn nếu bỏ trống | Ghi chú |
| --- | --- | --- | --- |
| Website URL | Có | — | Domain gốc, dùng để giới hạn crawl |
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
| Tài liệu upload (PDF, ảnh sau login) | Không | — | Thay cho crawl sau login |

Nguồn cấu hình hệ thống: giới hạn 30 trang/job, 1 request/giây/domain, danh sách `page_type` ưu tiên.

## Output

Output chính là một PKB JSON có version; mỗi fact mang `source_id` (crawl) hoặc `origin: merchant`, fact `inferred` phải được duyệt trước khi Module 2 dùng.

```json
{
  "product_id": "uuid",
  "version": 3,
  "status": "draft | in_review | approved",
  "identity": { "name": "", "website": "", "category": "AI video generator", "tagline": "" },
  "pricing": {
    "currency": "USD", "free_plan": true, "trial_days": 7,
    "plans": [{ "name": "Pro", "price": 29, "period": "month", "limits": [""], "source_id": "src_02" }]
  },
  "features": [{
    "id": "f1", "name": "", "description": "",
    "origin": "crawled", "source_id": "src_01", "evidence": "đoạn trích ≤ 200 ký tự",
    "screenshot_ids": ["ss_04"]
  }],
  "use_cases": [{ "title": "", "origin": "crawled", "source_id": "src_03" }],
  "audiences": [{ "segment": "Students", "jtbd": "Tạo slide trong 10 phút", "origin": "inferred" }],
  "usp": [{ "text": "", "origin": "merchant" }],
  "limitations": [{ "text": "", "origin": "crawled", "source_id": "src_05" }],
  "competitors": [{ "name": "", "url": "", "origin": "inferred" }],
  "brand": { "logo_asset_id": "ss_01", "colors": ["#000000"], "tone": "" },
  "compliance": { "forbidden_claims": [""], "approved_claims": [""] },
  "affiliate": { "link": "", "commission": "30% recurring" },
  "sources": [{ "id": "src_01", "url": "", "page_type": "features", "fetched_at": "", "content_hash": "" }],
  "quality": { "completeness": 0.82, "conflicts": [{ "field": "pricing.plans[0].price", "values": [29, 25], "source_ids": ["src_02", "src_07"] }] }
}
```

Output phụ và module sử dụng:

| Artifact | Lưu ở đâu | Ai dùng |
| --- | --- | --- |
| PKB approved (JSON) | `product_knowledge` | M2 (hook, script), M4 (fact-check), M8 (hiển thị) |
| Screenshot desktop/mobile/element, logo | Supabase Storage + `product_assets` | M3 (nền video), M4 (bằng chứng) |
| Markdown trang nguồn | Storage + `crawled_pages` | 1.8, debug |
| Chunks + embedding | `knowledge_chunks` (pgvector) | M2, M4, Review Agent (phase sau) |
| Crawl report (trang lấy/bỏ, lỗi, chi phí token) | `crawl_jobs` | Admin, tester |

## Requirements

Yêu cầu cốt lõi: không fact nào được vào PKB mà thiếu nguồn hoặc thiếu xác nhận của người duyệt.

### Functional

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| FR-01 | Tạo product chỉ với Website URL + affiliate link | Must |
| FR-02 | Tự chọn trang quan trọng (pricing, features, docs, FAQ, changelog), tối đa 30 trang, tôn trọng `robots.txt` | Must |
| FR-03 | Render được trang SPA (JavaScript) | Must |
| FR-04 | Trích xuất theo JSON schema; mỗi fact có `source_id` + evidence | Must |
| FR-05 | Fact suy luận gắn `origin: inferred`, không được dùng khi chưa duyệt | Must |
| FR-06 | Chụp screenshot full-page, desktop 1440×900, mobile 430×932 @3x, element theo section tính năng | Must |
| FR-07 | Merchant/admin xem, sửa, approve PKB; mỗi lần approve tạo version mới | Must |
| FR-08 | Index PKB approved vào pgvector, có API search theo product | Must |
| FR-09 | Phát hiện xung đột (form vs crawl, giá khác nhau giữa các trang) và hiện cho reviewer | Should |
| FR-10 | Upload PDF/ảnh cho phần sau login, đưa vào extraction | Should |
| FR-11 | Re-crawl thủ công + diff với version trước | Should |
| FR-12 | Hiển thị tiến trình job theo bước (queued → crawling → extracting → review) | Should |

### Non-functional

| ID | Yêu cầu | Mục tiêu |
| --- | --- | --- |
| NFR-01 | Thời gian xử lý 1 product (30 trang) | ≤ 5 phút p95 |
| NFR-02 | Chi phí LLM mỗi product | ≤ $0.05 |
| NFR-03 | Độ chính xác giá + tên plan trước review | ≥ 95% trên golden set 10 product |
| NFR-04 | Retry | 3 lần, exponential backoff; job idempotent theo `content_hash` |
| NFR-05 | Lịch sự với site | ≤ 1 request/giây/domain, User-Agent định danh platform |
| NFR-06 | Bảo mật | File upload và tài liệu merchant chỉ merchant + admin đọc (Supabase RLS) |
| NFR-07 | Quan sát | Log từng bước, trace mọi lời gọi LLM kèm token và chi phí |
| NFR-08 | Thay provider | Đổi model LLM/embedding bằng config, không sửa code |

## Tech stack

Worker viết bằng Python vì hệ sinh thái crawl/LLM tốt nhất; frontend và DB theo stack chung của PRD (Next.js + Supabase).

| Thành phần | Chọn | Lý do / thay thế |
| --- | --- | --- |
| Worker runtime | Python 3.12 + FastAPI (internal API) | Thư viện crawl, LLM, Pydantic đầy đủ |
| Queue | Supabase Queues (pgmq) | Không thêm hạ tầng; thay thế: Redis + ARQ |
| Crawl (1.2) | [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0, chạy Playwright, xuất markdown cho LLM ([so sánh](https://crawlbase.com/blog/firecrawl-alternatives/)). Không chọn Firecrawl self-host vì AGPL-3.0 |
| Screenshot (1.3) | Playwright for Python | Kiểm soát viewport, device scale, element screenshot |
| Extraction (1.4) | Gemini 2.5 Flash-Lite, structured output theo JSON schema | Giá $0.10/$0.40 mỗi 1M token ([pricing](https://benchlm.ai/google/api-pricing)); đọc được ảnh |
| Merge + Enrichment (1.5–1.6) | Gemini Flash (model mạnh hơn 1 bậc) | Ít lời gọi, cần suy luận tốt hơn |
| LLM adapter | LiteLLM | Đổi sang DeepSeek V4-Flash ($0.14/$0.28, [so sánh](https://www.spheron.network/blog/llm-api-pricing-comparison-gpt-claude-gemini-deepseek-2026/)) bằng config |
| Schema + validate | Pydantic v2 | Dùng chung schema cho LLM output và API |
| DB + vector | Supabase Postgres + pgvector | 1 nơi cho data, RLS, vector |
| Storage | Supabase Storage | Screenshot, markdown nguồn |
| Embedding | Model embedding của Gemini (qua LiteLLM) | Chốt model khi làm spike |
| LLM tracing | Langfuse (self-host hoặc cloud free tier) | Theo dõi prompt, token, chi phí |
| Review UI | Next.js + shadcn/ui + Supabase Realtime | Theo PRD; realtime để hiện tiến trình job |
| Test | pytest, golden set 10 product, Playwright E2E cho UI | Tester đo NFR-03 |

Giá tham khảo tra cứu ngày 05/10/2026, cần kiểm tra lại trước khi chốt.

## Data model và API

7 bảng Supabase; PKB lưu nguyên JSON trong `product_knowledge.data` (jsonb) để đổi schema không cần migration.

| Bảng | Cột chính | Ghi chú |
| --- | --- | --- |
| `products` | id, merchant\_id, name, website\_url, affiliate\_link, current\_version, status | 1 domain = 1 product |
| `product_inputs` | product\_id, form (jsonb), uploaded\_files\[\], created\_at | Dữ liệu gốc merchant nhập |
| `crawl_jobs` | id, product\_id, status, step, pages\_found, pages\_used, error, tokens, cost\_usd, started\_at, finished\_at | 1 lần crawl/re-crawl = 1 job |
| `crawled_pages` | id, job\_id, url, page\_type, markdown\_path, content\_hash, fetched\_at, used (bool) | `content_hash` để bỏ qua trang không đổi |
| `product_assets` | id, product\_id, kind (full\_page, desktop, mobile, element, logo), storage\_path, source\_url, width, height, captured\_at | M3 lấy ảnh từ đây |
| `product_knowledge` | product\_id, version, status, data (jsonb), completeness, approved\_by, approved\_at | Unique (product\_id, version) |
| `knowledge_chunks` | id, product\_id, version, chunk\_type, content, source\_id, embedding (vector) | Index HNSW trên embedding |

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| POST | `/products` | Body: website\_url, affiliate\_link, form? → product\_id, job\_id |
| GET | `/jobs/{id}` | Trạng thái, bước hiện tại, lỗi, chi phí |
| POST | `/products/{id}/uploads` | Upload PDF/ảnh bổ sung |
| POST | `/products/{id}/recrawl` | Tạo job mới, trả diff khi xong |
| GET | `/products/{id}/knowledge?version=` | Lấy PKB (mặc định bản approved mới nhất) |
| PATCH | `/products/{id}/knowledge` | Sửa bản draft (field-level) |
| POST | `/products/{id}/knowledge/approve` | Khóa draft thành version mới, kích hoạt 1.8 |
| GET | `/products/{id}/assets?kind=` | Danh sách screenshot cho M3 |
| POST | `/knowledge/search` | Body: product\_id, query, k → chunks + source (cho M2, M4) |

## Phân công, kế hoạch và acceptance criteria

Module 1 cần khoảng 3 tuần với 2 AI dev làm chính; con số này là giả định, cần chỉnh theo lịch thực tế của team.

| Vai trò | Phụ trách |
| --- | --- |
| AI dev 1 | 1.2 Crawl, 1.3 Asset Capture, 1.8 Indexing |
| AI dev 2 | 1.4 Extraction, 1.5 Merge, 1.6 Enrichment, prompt + schema |
| Backend core | Bảng Supabase, queue, API `/products`, `/jobs`, RLS |
| Frontend | Form onboarding, màn hình review PKB (diff, xung đột, approve) |
| BA | Chốt schema PKB, danh sách `page_type`, form merchant, quy tắc forbidden claims |
| Tester | Golden set 10 product (đáp án nhập tay), test API, E2E review UI |

Kế hoạch:

1. Tuần 1 — Spike: script Python URL → markdown → PKB JSON cho 3 product mẫu; BA chốt schema; tester dựng golden set.
2. Tuần 2 — Worker + queue + bảng DB + screenshot; API `/products`, `/jobs`, `/knowledge`.
3. Tuần 3 — Màn hình review, versioning, indexing + `/knowledge/search`; đo NFR trên golden set.

Acceptance criteria (tester kiểm):

- [ ] Chỉ nhập URL + affiliate link → có PKB draft trong ≤ 5 phút cho ≥ 8/10 product golden set
- [ ] Giá và tên plan đúng ≥ 95% so với đáp án trước khi review
- [ ] 0 fact thiếu `source_id` mà không phải `origin: merchant`
- [ ] Mỗi tính năng chính có ≥ 1 screenshot; có ảnh mobile 1290×2796 cho trang chủ và pricing
- [ ] Approve tạo version mới; bản cũ vẫn đọc được qua `?version=`
- [ ] Re-crawl site không đổi → 0 trang xử lý lại, 0 token LLM
- [ ] `/knowledge/search` trả chunk đúng product, có `source_id`
- [ ] Chi phí LLM trung bình ≤ $0.05/product (đọc từ `crawl_jobs.cost_usd`)

Câu hỏi mở:

- Ai approve PKB: merchant, admin, hay cả hai?
- Merchant pilot có cung cấp ảnh/tài liệu phần sau login không?
- Site của merchant có ngôn ngữ nào ngoài tiếng Anh?
