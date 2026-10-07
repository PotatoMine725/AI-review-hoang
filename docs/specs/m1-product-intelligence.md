# Module 1 — Product Intelligence: Đặc tả kỹ thuật

Oct 5, 2026 · @Hoang Nguyen · **v0.2** (07/10/2026, issue #5) · Lịch sử: xem cuối file

## Tổng quan

Module 1 nhận URL (và form tùy chọn) của merchant, trả về **Product Knowledge Base (PKB)** đã chuẩn hóa, mọi fact đều có nguồn và được người duyệt. PKB là đầu vào duy nhất cho Module 2 (Content Strategy), Module 3 (screenshot cho video) và Module 4 (fact-check).

**Trong phạm vi MVP:** crawl tối đa 30 trang public/product; trích xuất structured có trích nguồn; chụp screenshot desktop + mobile làm bằng chứng; merchant review và approve theo version (qa-log #1); index RAG.

**Ngôn ngữ MVP (qa-log #3, #8, issue #15):** tiếng Anh cho site nguồn, PKB và video. Crawl ưu tiên và giới hạn ở trang tiếng Anh; bỏ qua trang bản dịch (`/fr/…`, `/ja-jp/…`).

**Ngoài phạm vi MVP:** tự đăng nhập để crawl sau login (nội dung sau login do merchant upload ảnh/PDF qua FR-10, qa-log #2), crawl sâu đối thủ (chỉ lưu tên + URL), re-crawl tự động theo lịch, đa ngôn ngữ (tiếng Việt và ngôn ngữ khác xét ở phase sau), Trend Engine.

## Kiến trúc & luồng xử lý

&#91;embedded content: Pipeline Module 1 · 8 sub-module, 1 job\]

Sau crawl, chụp ảnh (1.3) và trích xuất (1.4) chạy song song; chỉ PKB đã approve mới được index và cấp cho M2, M3, M4.

## Phân rã sub-module

Module 1 gồm 8 sub-module chạy tuần tự trong một job; 1.3 và 1.4 chạy song song sau khi crawl xong.

| Sub-module | Trách nhiệm | Input → Output |
| --- | --- | --- |
| 1.1 Intake | Validate URL/form, kiểm tra trùng domain, tạo `product` + `crawl_job`, đẩy vào queue | Form → `product_id`, `job_id` |
| 1.2 Discover & Crawl | Đọc `robots.txt` + `sitemap.xml`, chấm điểm link (pricing, features, docs, FAQ, changelog, compare), render JS, lưu markdown + `content_hash`. Ghi vùng IP / locale lúc crawl (giá có thể theo vùng). Host phụ cùng domain gốc: xem FR-02 | URL → ≤ 30 trang markdown có `page_type` |
| 1.3 Asset Capture | Chụp full-page, viewport desktop 1440×900 và mobile 430×932 @3x, chụp theo element từng section tính năng; lấy logo (ưu tiên SVG, kèm wordmark), màu thương hiệu. Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai (`media_sample`, FR-13) | Trang → file ảnh trong Storage + metadata |
| 1.4 Structured Extraction | LLM trích xuất theo JSON schema; mỗi fact kèm `source_id` + đoạn trích ngắn. **Mode mặc định `batch`:** gom top-k trang theo điểm (spike: k = 10) vào 1 lời gọi. Trang pricing gửi raw markdown, trang khác gửi fit markdown. Giá theo [Quy tắc trích xuất giá](#quy-tắc-trích-xuất-giá) | Markdown → fact |
| 1.5 Normalize & Merge | Gộp fact nhiều trang, khử trùng tính năng, chuẩn hóa giá (tiền tệ, chu kỳ) bằng code và ghi nguồn, áp thứ tự ưu tiên merchant > crawl > inferred, đánh dấu xung đột | Fact rời → PKB draft |
| 1.6 Enrichment | Suy ra audience, JTBD, use case, USP, đối thủ gợi ý; gắn nhãn `origin: inferred` | PKB draft → PKB draft đầy đủ |
| 1.7 Validation & Review | Validate schema, tính `completeness`, hiện xung đột; merchant sửa và approve → tạo version mới (qa-log #1) | PKB draft → PKB approved vN |
| 1.8 Knowledge Indexing | Chia chunk PKB approved + markdown nguồn, embed, lưu pgvector; cung cấp API search cho M2/M4 (phạm vi: chờ qa-log #5) | PKB approved → chunks + vector |

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

Output chính là một PKB JSON có version; mỗi fact mang `source_id` (crawl) hoặc `origin: merchant`, fact `inferred` phải được duyệt trước khi Module 2 dùng.

```json
{
  "product_id": "uuid",
  "version": 3,
  "status": "draft | in_review | approved",
  "identity": {
    "name": "", "website": "", "category": "AI video generator", "tagline": "",
    "version": { "value": "2.5", "source_id": "src_01" },
    "models": [{ "name": "Seedance 2.5", "source_id": "src_01", "evidence": "" }]
  },
  "pricing": {
    "currency": "USD", "free_plan": true, "trial_days": 7,
    "region": "VN", "locale": "en-US",
    "default_view": "monthly", "other_views": ["yearly", "quarterly"],
    "plans": [{
      "name": "Pro", "currency": "USD",
      "list_price": 20, "promo_price": null, "promo_terms": "",
      "price_unit": "month", "billing_cycle": "monthly",
      "price_text": "$20 / month billed monthly",
      "limits": [""], "source_id": "src_02", "evidence": ""
    }],
    "usage_prices": [{ "name": "API input", "unit": "1M tokens", "price": 3, "currency": "USD", "source_id": "src_02" }]
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
  "sources": [{ "id": "src_01", "url": "", "page_type": "features", "fetched_at": "", "content_hash": "", "region": "VN", "locale": "en-US" }],
  "quality": { "completeness": 0.82, "conflicts": [{ "field": "pricing.plans[0].price", "values": [29, 25], "source_ids": ["src_02", "src_07"] }] }
}
```

`identity.version` và `models[]` là fact như mọi fact khác (bắt buộc `source_id`): với product AI, phiên bản model (vd. "Seedance 2.5") là thông tin video hay dùng (`references/ref-videos-2026-10-06.md`).

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
| PKB approved (JSON) | `product_knowledge` | M2 (hook, script), M4 (fact-check), M8 (hiển thị) |
| Screenshot desktop/mobile/element, logo (ưu tiên SVG), `media_sample` | Supabase Storage + `product_assets` | M3 (nền video, thẻ thương hiệu), M4 (bằng chứng) |
| Markdown trang nguồn | Storage + `crawled_pages` | 1.8, debug |
| Chunks + embedding | `knowledge_chunks` (pgvector) | M2, M4, Review Agent (phase sau) |
| Crawl report (trang lấy/bỏ, lỗi, chi phí token) | `crawl_jobs` | Admin, tester |

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
| FR-06 | Chụp screenshot full-page, desktop 1440×900, mobile 430×932 @3x, element theo section tính năng; logo ưu tiên SVG | Must |
| FR-07 | Merchant xem, sửa, approve PKB; mỗi lần approve tạo version mới (`draft → in_review → approved`). Admin không tham gia từng lần approve trong MVP (qa-log #1) | Must |
| FR-08 | Index PKB approved vào pgvector, có API search theo product (phạm vi: chờ qa-log #5) | Must |
| FR-09 | Phát hiện xung đột (form vs crawl, giá khác nhau giữa các trang) và hiện cho reviewer | Should |
| FR-10 | Upload PDF/ảnh cho phần sau login, đưa vào extraction | Should |
| FR-11 | Re-crawl thủ công + diff với version trước | Should |
| FR-12 | Hiển thị tiến trình job theo bước (queued → crawling → extracting → review) | Should |
| FR-13 | Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai làm bằng chứng (`product_assets.kind = media_sample`) | Could |

### Non-functional

| ID | Yêu cầu | Mục tiêu |
| --- | --- | --- |
| NFR-01 | Thời gian xử lý 1 product (30 trang) | ≤ 5 phút p95 |
| NFR-02 | Chi phí LLM mỗi product | ≤ $0.05. Spike đo **~$0.01** ($0.008–0.014) với mode `batch` (10 trang, 1 lời gọi); mode `per_page` $0.065–0.110, không đạt. Mẫu 2 product, giá gói trả phí Standard; cần xác nhận trên golden set (qa-log #6) |
| NFR-03 | Độ chính xác giá + tên plan trước review | ≥ 95% trên golden set 10 product, so cùng vùng IP lúc crawl. Spike: 1/8 lần chạy đúng (trước khi có Quy tắc trích xuất giá) |
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
| Extraction (1.4) | Gemini Flash-Lite 3.x, structured output theo JSON schema, mode `batch`. Ứng viên: `gemini-3.1-flash-lite` ($0.25/$1.50) và `gemini-3.5-flash-lite` ($0.30/$2.50). **Chọn model: chờ ADR-002** | Gemini 2.5 Flash-Lite bỏ vì không mở cho dự án mới (issue #5, qa-log #6). Spike: 3.1 rẻ hơn ~30 %; 3.5 đúng hơn ở chi tiết giá (chép nguyên văn, điền `currency` từng plan). Đọc được ảnh |
| Merge + Enrichment (1.5–1.6) | Gemini Flash (model mạnh hơn 1 bậc). Tham khảo: `gemini-3.5-flash` ($1.50/$9.00). **Chờ ADR-002** | Ít lời gọi, cần suy luận tốt hơn |
| LLM adapter | Adapter mỏng của dự án, chọn provider/model bằng config (ADR-0005). Có dùng LiteLLM hay không: **chờ ADR-002** | **Rủi ro LiteLLM:** bản 1.82.7 và 1.82.8 trên PyPI bị cài mã độc (24/03/2026). Spike gọi thẳng `google-genai` (decision-log #9). `crawl4ai` 0.9.4 kéo gián tiếp `unclecode-litellm` (bản fork, đã ghim hash trong `uv.lock`). Phương án thay model: DeepSeek V4-Flash ($0.14/$0.28, [so sánh](https://www.spheron.network/blog/llm-api-pricing-comparison-gpt-claude-gemini-deepseek-2026/)) |
| Schema + validate | Pydantic v2 | Dùng chung schema cho LLM output và API |
| DB + vector | Supabase Postgres + pgvector | 1 nơi cho data, RLS, vector |
| Storage | Supabase Storage | Screenshot, markdown nguồn |
| Embedding | Ứng viên `gemini-embedding-2`, `output_dimensionality = 768` (lên 1536 nếu chất lượng tìm kiếm thiếu). Gọi qua adapter LLM | $0.20 / 1M token text. Mặc định 3 072 chiều (Matryoshka, cắt được); Google khuyên 768 / 1536 / 3072. Index HNSW của pgvector với kiểu `vector` chỉ nhận ≤ 2 000 chiều, nên chọn ≤ 1536. Input tối đa 8 192 token / lần |
| Phạm vi RAG (1.8) | **Chờ qa-log #5.** Phương án A: full-text search của Postgres trước, M2 dùng nguyên PKB (vài KB) làm context. Phương án B: embedding + pgvector ngay | A rẻ và đơn giản cho MVP; B cần khi tìm trong markdown nguồn hoặc khi M4 fact-check theo câu |
| LLM tracing | Langfuse (self-host hoặc cloud free tier) | Theo dõi prompt, token, chi phí |
| Review UI | Next.js + shadcn/ui + Supabase Realtime | Theo PRD; realtime để hiện tiến trình job |
| Test | pytest, golden set 10 product, Playwright E2E cho UI | Tester đo NFR-03 |

Giá Gemini tra lại ngày **07/10/2026** tại trang giá chính thức <https://ai.google.dev/gemini-api/docs/pricing>: gói trả phí, tier **Standard**, USD / 1M token, input text (input / output; output gồm thinking token). Khớp giá spike dùng ngày 06/10/2026 (`spikes/m1-crawl-extract/config.py`). Số chiều embedding theo <https://ai.google.dev/gemini-api/docs/embeddings>; giới hạn index theo [README pgvector](https://github.com/pgvector/pgvector#hnsw).

"Mode `batch`" trong đặc tả này là gom nhiều trang vào 1 lời gọi, **không phải** tier Batch API của Gemini (rẻ hơn ~50 %, trả kết quả không đồng bộ). Mọi chi phí ở đây tính theo tier Standard. Giá DeepSeek tra ngày 05/10/2026 qua trang so sánh, chưa kiểm tra lại.

## Data model và API

7 bảng Supabase; PKB lưu nguyên JSON trong `product_knowledge.data` (jsonb) để đổi schema không cần migration.

| Bảng | Cột chính | Ghi chú |
| --- | --- | --- |
| `products` | id, merchant\_id, name, website\_url, affiliate\_link, current\_version, status | 1 domain = 1 product |
| `product_inputs` | product\_id, form (jsonb), uploaded\_files\[\], created\_at | Dữ liệu gốc merchant nhập |
| `crawl_jobs` | id, product\_id, status, step, pages\_found, pages\_used, error, tokens, cost\_usd, crawl\_region, locale, started\_at, finished\_at | 1 lần crawl/re-crawl = 1 job. `crawl_region` = vùng của IP crawl (giá có thể theo vùng) |
| `crawled_pages` | id, job\_id, url, page\_type, markdown\_path, content\_hash, fetched\_at, used (bool) | `content_hash` để bỏ qua trang không đổi |
| `product_assets` | id, product\_id, kind (full\_page, desktop, mobile, element, logo, media\_sample), storage\_path, source\_url, width, height, captured\_at | M3 lấy ảnh từ đây |
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

AI-1 phụ trách toàn bộ phần AI của Module 1 (1.2–1.6, 1.8; qa-log #4, issue #14); AI-2 làm Module 2 và 4 theo kế hoạch tuần 1. Ước tính 3 tuần ở v0.1 giả định 2 AI dev, **cần ước tính lại** cho 1 AI dev.

| Vai trò | Phụ trách |
| --- | --- |
| AI-1 | 1.2 Crawl, 1.3 Asset Capture, 1.4 Extraction, 1.5 Merge, 1.6 Enrichment, 1.8 Indexing, prompt + schema |
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

Câu hỏi đã trả lời (BA, issue #15):

- Ai approve PKB? → Merchant (qa-log #1). Giữ FR-07.
- Merchant pilot có cung cấp ảnh/tài liệu phần sau login không? → Có, upload qua FR-10; crawler không tự đăng nhập (qa-log #2).
- Ngôn ngữ? → MVP dùng tiếng Anh cho site nguồn, PKB và video (qa-log #3, #8).

Câu hỏi còn mở:

- Phạm vi RAG của 1.8: full-text search hay pgvector ngay? → chờ qa-log #5.
- NFR-02 trên golden set → chờ qa-log #6.
- Chọn model extraction / merge (3.1 hay 3.5 Flash-Lite), có dùng LiteLLM không → chờ ADR-002.

## Lịch sử phiên bản

| Phiên bản | Ngày | Người sửa | Thay đổi |
| --- | --- | --- | --- |
| v0.1 | 05/10/2026 | @Hoang Nguyen | Bản đầu |
| v0.2 | 07/10/2026 | @PotatoMine725 (issue #5) | Thay Gemini 2.5 Flash-Lite bằng ứng viên Flash-Lite 3.x, tra lại giá 07/10/2026 trên trang chính thức, chọn model chờ ADR-002. NFR-02 ghi số đo spike (~$0.01/product, mode `batch`), link qa-log #6. Embedding ứng viên `gemini-embedding-2` 768 chiều; phạm vi RAG chờ qa-log #5. Ghi rủi ro LiteLLM. AI-1 làm toàn bộ M1 (#14). Merchant approve PKB, nội dung sau login qua FR-10, MVP tiếng Anh (#15). Thêm Quy tắc trích xuất giá từ spike #6 (tách giá niêm yết / khuyến mãi, cấm model tự tính giá, `price_unit` + `billing_cycle` bắt buộc, `usage_prices`, `default_view`, vùng IP), mode `batch` mặc định, crawl host phụ cùng domain gốc (≤ 5 trang). Thêm `identity.version`, `models[]`, logo ưu tiên SVG, FR-13 `media_sample` (Could) từ video tham khảo |
