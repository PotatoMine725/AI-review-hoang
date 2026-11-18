# Module 1 — Product Intelligence: Đặc tả kỹ thuật

Oct 5, 2026 · @Hoang Nguyen · **v0.4.5** (02/11/2026, issue #67) · Lịch sử: xem cuối file

> **Nguồn chuẩn của data model:** ERD v1.3.3 ([`docs/specs/erd/`](erd/)). Đặc tả này chỉ nêu bảng và cột M1 dùng, không chép DBML. ERD đã gộp thay đổi của #23 (PR #49): `in_review`, 4 cột chi phí của `generation_jobs`; và PR #51 (decision-log #18, #19): cột review `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note`, quy tắc nullability của chi phí.

> **P1 (v0.4.0, 13/10/2026):** M1 nhận thêm **link sản phẩm vật lý trên shop** (xem [Sản phẩm vật lý (P1)](#sản-phẩm-vật-lý-p1)). P1 bỏ merchant, campaign, creator, tracking, attribution, affiliate; **1 chủ sở hữu (owner) xác nhận PKB** ở bước 2 của workspace. Trong đặc tả này, "merchant" ở các mục chưa sửa nghĩa là owner. ERD v1.3.3, data dictionary và tên cột DB (`merchant_id`, `affiliate_url`, `reviewer_role = 'merchant'`) **chưa đổi** (PR này không sửa ERD / migration); phần BE cần làm nằm ở [Danh sách thay đổi cho BE](#danh-sách-thay-đổi-cho-be). PKB JSON dùng `owner` ngay từ contract v0.3.

## Tổng quan

Module 1 nhận URL website / công cụ AI **hoặc link sản phẩm trên shop** (và form tùy chọn) của owner, trả về **Product Knowledge Base (PKB)** đã chuẩn hóa, mọi fact đều có nguồn và được người duyệt. PKB là đầu vào duy nhất cho Module 2 (Content Strategy), Module 3 (screenshot / ảnh sản phẩm cho video) và Module 4 (fact-check).

**Trong phạm vi MVP:** crawl tối đa 30 trang public/product; trích xuất structured có trích nguồn; chụp screenshot desktop + mobile làm bằng chứng; owner (trước P1 gọi là merchant) review và approve theo version (qa-log #1). Không có vector RAG trong MVP: M2, M4 dùng nguyên PKB approved (JSON) làm input (qa-log #5, ERD v1.3.1, #23). **Từ P1:** sản phẩm vật lý (`product_kind = physical`) crawl theo mode `shop_item` (1 trang sản phẩm + tối đa 4 trang cùng host), giá / biến thể / ảnh bóc bằng code từ dữ liệu có cấu trúc.

**Ngôn ngữ MVP (qa-log #3, #8, issue #15):** tiếng Anh cho site nguồn, PKB và video. Crawl ưu tiên và giới hạn ở trang tiếng Anh; bỏ qua trang bản dịch (`/fr/…`, `/ja-jp/…`).
**P1 (v0.4.1, P1-04):** video tiếng Việt, nên crawl nhận các ngôn ngữ trong `M1_CRAWL_LANGUAGES` (mặc định `en,vi`, theo thứ tự ưu tiên). Cùng 1 trang có nhiều bản dịch thì chỉ giữ bản ngôn ngữ đứng trước. Xem [Mã lỗi crawl](#mã-lỗi-crawl).

**Ngoài phạm vi MVP:** tự đăng nhập để crawl sau login (nội dung sau login do merchant upload ảnh/PDF qua FR-10, qa-log #2), crawl sâu đối thủ (chỉ lưu tên + URL), re-crawl tự động theo lịch, đa ngôn ngữ (tiếng Việt và ngôn ngữ khác xét ở phase sau), Trend Engine. **Ngoài phạm vi P1:** Shopee và TikTok Shop (chưa kiểm chứng, hoãn tới sau luồng P1 chính), crawl nhiều sản phẩm / cả cửa hàng, theo dõi giá theo thời gian, affiliate / tracking / campaign.

## Kiến trúc & luồng xử lý

&#91;embedded content: Pipeline Module 1 · 8 sub-module, 1 job\]

Sau crawl, chụp ảnh (1.3) và trích xuất (1.4) chạy song song; chỉ PKB đã approve mới được cấp cho M2, M3, M4.

## Phân rã sub-module

Module 1 gồm 7 sub-module trong MVP, chạy tuần tự trong một job; 1.3 và 1.4 chạy song song sau khi crawl xong. 1.8 (Knowledge Indexing) bỏ khỏi MVP.

| Sub-module | Trách nhiệm | Input → Output |
| --- | --- | --- |
| 1.1 Intake | Validate URL/form; `website_url` phải unique sau khi chuẩn hoá URL (ERD gate 2, không unique theo domain); tạo `products` + `generation_jobs` (`job_type = 'crawl'`), đẩy vào queue | Form → `product_id`, `job_id` |
| 1.2 Discover & Crawl | Đọc `robots.txt` + `sitemap.xml`, chấm điểm link (pricing, features, docs, FAQ, changelog, compare), render JS, lưu markdown + `content_hash` (trang không đổi thì bỏ qua, NFR-04). Ghi vùng IP / locale lúc crawl (giá có thể theo vùng). Host phụ cùng domain gốc: xem FR-02. Quy tắc robots và WAF: xem [Quy tắc crawl](#quy-tắc-crawl). **Sản phẩm vật lý:** mode `shop_item`, xem [Crawl mode `shop_item`](#crawl-mode-shop_item) | URL → ≤ 30 trang markdown có `page_type` (`shop_item`: ≤ 5 trang) |
| 1.3 Asset Capture | Chụp full-page, viewport desktop 1440×900 và mobile 430×932 @3x, chụp theo element từng section tính năng; lấy logo (ưu tiên SVG, kèm wordmark), màu thương hiệu. Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai (`media_sample`, FR-13) | Trang → file ảnh trong Storage; metadata ở `product_knowledge.sources` (`image_paths`) |
| 1.4 Structured Extraction | LLM trích xuất theo JSON schema; mỗi fact kèm `source_id` + đoạn trích ngắn. **Mode mặc định `batch`:** gom top-k trang theo điểm (spike: k = 10) vào 1 lời gọi. Trang pricing gửi raw markdown, trang khác gửi fit markdown. Giá theo [Quy tắc trích xuất giá](#quy-tắc-trích-xuất-giá). **Sản phẩm vật lý:** giá, biến thể, ảnh, thông số bóc bằng code từ dữ liệu có cấu trúc, LLM chỉ làm lợi ích / use case / đối tượng / điểm khác biệt, xem [Trích xuất cho `physical`](#trích-xuất-cho-physical) | Markdown → fact |
| 1.5 Normalize & Merge | Gộp fact nhiều trang, khử trùng tính năng, chuẩn hóa giá (tiền tệ, chu kỳ) bằng code và ghi nguồn, áp thứ tự ưu tiên owner > crawl > inferred (trước P1: merchant), đánh dấu xung đột | Fact rời → PKB draft |
| 1.6 Enrichment | Suy ra audience, JTBD, use case, USP, đối thủ gợi ý; gắn nhãn `origin: inferred` | PKB draft → PKB draft đầy đủ |
| 1.7 Validation & Review | Validate schema, tính `completeness`, hiện xung đột; merchant sửa và gửi duyệt (`draft → in_review`), **chỉ merchant sở hữu product approve** → version mới (qa-log #1). Admin chỉ reject bản `in_review` khi vi phạm chính sách, bắt buộc lý do; admin không sửa, không approve. Đây là bổ sung cho decision-log #11 (đã chốt ở #23). Reject: `review_note` bắt buộc; quy tắc 4 cột review xem FR-07 | PKB draft → PKB approved vN |
| ~~1.8 Knowledge Indexing~~ | **Bỏ khỏi MVP** (FR-08 hạ xuống Later). Không có chunk, embedding, pgvector. M2, M4 dùng nguyên PKB approved (JSON). Nguồn: ERD v1.3.1, qa-log #5, #23 | — |

## Input

**Từ P1 chỉ 1 trường bắt buộc: URL** (website / công cụ AI, hoặc link sản phẩm trên shop). Mọi trường khác tùy chọn; nếu owner nhập thì giá trị đó ghi đè kết quả crawl. Affiliate link không còn là input (deprecated). Trước P1 có 2 trường bắt buộc: Website URL và Affiliate link.

| Trường | Bắt buộc | Nguồn nếu bỏ trống | Ghi chú |
| --- | --- | --- | --- |
| URL (website hoặc link sản phẩm shop) | Có | — | Host của URL giới hạn phạm vi crawl; host phụ cùng domain gốc theo FR-02 (chỉ `software`). Loại sản phẩm: `classify_input_url`, owner sửa được ở bước 2 |
| ~~Affiliate link / program URL~~ | ~~Có~~ **Deprecated (P1)** | — | ~~Module 6 dùng làm đích redirect~~. P1 bỏ affiliate / tracking. Không còn bắt buộc, không còn là input |
| Product name, description | Không | Crawl (title, meta, hero) |  |
| Pricing, free plan, trial, paid plans | Không | Crawl trang pricing | Sai giá là lỗi nghiêm trọng nhất |
| Main features, use cases | Không | Crawl features/docs |  |
| Target audience, USP | Không | 1.6 suy ra (inferred) | Cần merchant xác nhận |
| Competitors | Không | 1.6 gợi ý | Chỉ lưu tên + URL |
| Limitations | Không | Crawl FAQ/docs |  |
| ~~Commission~~ | **Deprecated (P1)** | — | ~~Hiển thị cho creator~~. P1 bỏ creator và affiliate |
| Brand guidelines (logo, màu, tone) | Không | 1.3 trích từ trang |  |
| Forbidden / approved claims | Không | — | Module 4 dùng để chặn nội dung |
| Tài liệu upload (PDF, ảnh sau login) | Không | — | Thay cho crawl sau login. Merchant pilot sẽ cung cấp (qa-log #2) |

Nguồn cấu hình hệ thống: giới hạn 30 trang/job (tính cả trang host phụ), ≤ 5 trang host phụ, 1 request/giây/domain, danh sách `page_type` ưu tiên.

## Output

Output chính là một PKB JSON; mỗi fact mang `source_id` (crawl) hoặc `origin: owner` (trước P1: `merchant`, đã đổi tên), fact `inferred` phải được duyệt trước khi Module 2 dùng. Hợp đồng đầy đủ: [`docs/specs/pkb/`](pkb/README.md) (schema máy đọc được ở đó, không chép lại ở đây). **Contract hiện hành là PKB v0.3** (superset của v0.2: thêm `identity.product_kind`, `offers[]`, `variants[]`, `specs[]`, `media.images[]`; `affiliate` deprecated; `merchant` → `owner`).

PKB nằm trong cột `product_knowledge.data`. `product_id`, `version`, `status`, `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note` là **cột của bảng**, không nằm trong JSON. JSON chỉ có `schema_version`. Danh sách trang nguồn nằm ở cột `product_knowledge.sources`.

Ví dụ rút gọn của `data`:

```json
{
  "schema_version": "0.3",
  "identity": {
    "product_kind": "software",
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

Ví dụ rút gọn trên là `software`. Ví dụ `physical` (có `offers[]`, `variants[]`, `media.images[]`) nằm trong README PKB và [`docs/specs/pkb/examples/`](pkb/examples/).

Ví dụ 1 phần tử của `sources`: `{ "id": "src_01", "url": "…", "page_type": "features", "variant": "fit", "fetched_at": "…", "content_hash": "…", "region": "VN", "locale": "en-US", "markdown_path": "…", "image_paths": ["…"] }`. Từ v0.3 thêm `structured_path` tuỳ chọn (bản chụp JSON-LD / meta của trang). Đường dẫn là Supabase Storage (private).

`identity.version` và `models[]` là fact như mọi fact khác (bắt buộc `source_id`): với product AI, phiên bản model (vd. "Seedance 2.5") là thông tin video hay dùng (`references/ref-videos-2026-10-06.md`).

### Quy tắc crawl

1. **robots.txt (RFC 9309).** Trả 2xx: đọc luật và tuân theo. Trả 4xx trừ 429: coi như không có robots, được crawl. Trả 5xx, 429 hoặc timeout: coi như cấm toàn bộ, không crawl.
2. **Trang chủ hoặc robots.txt bị WAF / challenge** (vd. header `cf-mitigated: challenge`, HTTP 403 hoặc 429 ở trang chủ): job `failed`, cột `generation_jobs.error` bắt đầu bằng `waf_challenge`, `result_manifest = null`. Không đổi User-Agent, không retry, không dùng proxy. Merchant được hướng dẫn upload tài liệu (FR-10). Ví dụ thật: Gamma (`spikes/m1-crawl-extract/README.md`, kết quả v0.2).
3. **Chuyển hướng tới trang đăng nhập (`login_redirect`).** Trang con chuyển hướng tới trang đăng nhập: bỏ qua trang đó, ghi lý do, crawl tiếp, không theo link từ trang đăng nhập. Trang chủ chuyển hướng tới đăng nhập: dừng product (job `failed`). Xem PR #39.
4. **Trang không đổi.** Bỏ qua trang có `content_hash` trùng với bản trong `product_knowledge.sources` (NFR-04). Trang vẫn nằm trong danh sách trang của kết quả (đánh dấu `unchanged`, không ghi lại markdown) để PKB giữ nguồn.
5. **Bị chặn ở trang con** (`http_403`, `http_429`, trang challenge): dừng crawl host đó ngay, không gửi thêm request tới host đó (bị chặn ở host gốc thì dừng toàn bộ crawl; ở host phụ thì host gốc chạy tiếp). Không đổi UA, không proxy.
   - Đã có trang chủ và ít nhất 1 trang khác dùng được: job vẫn `completed`, kết quả có `partial = true` và `warning = "blocked_mid_crawl:<lý do>"`. Trang bị chặn và các trang chưa crawl của host đó ghi lý do bỏ qua `blocked`.
   - Chỉ có trang chủ: job `failed` với `waf_challenge`.

### Mã lỗi crawl

Lỗi cấp **job**: job `failed`, `generation_jobs.error` là chuỗi bắt đầu bằng mã. Module crawl chỉ báo `retryable`; retry tối đa 3 lần với exponential backoff (AC của #42) là việc của hàng đợi.

| Mã | Khi nào | `retryable` |
| --- | --- | --- |
| `invalid_url` | URL sai dạng, scheme khác http(s), có `user:pass@`; hoặc trang chủ trả 404 / 410 (detail `http_404` / `http_410`) | không |
| `waf_challenge` | Trang chủ hoặc robots.txt bị WAF / challenge, hoặc bị chặn ở trang con khi mới có trang chủ | không (không đổi UA, không proxy) |
| `robots_disallow` | robots.txt cấm trang chủ | không |
| `robots_unavailable` | robots.txt trả 5xx, 429 hoặc timeout: coi như cấm toàn bộ (RFC 9309) | có |
| `login_redirect` | Trang chủ chuyển sang trang đăng nhập (hoặc trả 401) | không |
| `home_unreachable` | DNS lỗi, kết nối lỗi, timeout hoặc 503 ở trang chủ, trình duyệt crawl lỗi | có |
| `no_content` | Trang chủ render được nhưng dưới 200 ký tự, hoặc không lấy được trang chủ | không |
| `no_product_data` | **Mới (P1, đề xuất).** Chỉ mode `shop_item`: trang sản phẩm render được nhưng không bóc được tên sản phẩm hoặc offer nào (không JSON-LD, microdata, `og:price`, JSON nhúng). Không tạo PKB; owner nhập tay hoặc upload (FR-10) | không |

Trong mode `shop_item`, "trang chủ" ở các mã trên là **trang sản phẩm** của URL nhập (không tải trang chủ của shop).

Lý do bỏ qua cấp **trang** (job vẫn chạy tiếp). Tên theo code; cột spike là tên trong `spikes/m1-crawl-extract/crawl.py`:

| Lý do | Tên trong spike | Ghi chú |
| --- | --- | --- |
| `robots_disallowed` | `robots_disallow` | robots.txt của host đó cấm trang, hoặc không tải được robots.txt của host phụ |
| `login_redirect` | `blocked: login_redirect` | không theo link từ trang đăng nhập |
| `over_limit` | `over_limit` | vượt 30 trang, 5 trang host phụ hoặc hạn mức `page_type` |
| `duplicate` | `duplicate_of` | trùng `raw_hash` với trang đã lấy |
| `language_not_allowed` | (mới, v0.4.1) | tiền tố ngôn ngữ ở path (`/fr/`, `/ja-jp/`) không có trong `M1_CRAWL_LANGUAGES`. `detail` là mã ngôn ngữ. Chưa dò ngôn ngữ nội dung |
| `translation_duplicate` | `locale_duplicate` | bản dịch của 1 trang đã giữ ở ngôn ngữ ưu tiên hơn (cùng path sau khi bỏ tiền tố, vd. `/vi/pricing` và `/pricing`). `detail` là URL bản được giữ. Path không có tiền tố coi là `en`; nếu `en` không có trong danh sách thì xếp cuối nhưng không bị bỏ. Bản đã crawl không bị thay |
| `non_html` | `asset` | ảnh, PDF, CSS, JSON... |
| `fetch_error` | `not_found`, `crawl_failed`, `blocked: http_401/503` | |
| `unchanged` | (mới) | `content_hash` không đổi; trang vẫn có trong danh sách trang |
| `blocked` | (mới) | bị chặn giữa chừng (quy tắc 5) hoặc chưa crawl vì đã dừng |
| `out_of_scope`, `excluded_path`, `low_score`, `redirect_out_of_scope` | giữ nguyên | host ngoài phạm vi, đường dẫn bị loại, điểm 0, chuyển hướng ra ngoài phạm vi |

Mã `not_english` (v0.3.2) đã bỏ, **không giữ alias**: BE đọc `skipped_counts` cần đổi sang 2 mã trên.

### Extract 1.4 trong worker (P1-04)

Interface cho job BE: `extract_product(crawl_result, page_store, llm) -> ExtractResult(data, sources, cost_breakdown, warnings)` (`services/worker/src/worker/m1/extract/`). Chạy tay: `uv run python -m worker.m1.extract <crawl_dir> --out <dir>`. Hiện chỉ cho `software`; `physical` làm ở PR B (P1-04).

- **Chọn trang:** 10 trang điểm cao nhất của crawl, trang `pricing` gửi raw markdown, trang khác gửi fit. Gom vào **1 lời gọi** structured output. Trang `unchanged` không có markdown trong lần crawl này thì bỏ, ghi warning.
- **Kết quả:** PKB v0.3, `identity.product_kind = "software"`, validate bằng model v0.3 và kiểm mọi `source_id` có trong `sources`.
- **Evidence:** fact trỏ tới trang không gửi thì bị loại. Evidence không có nguyên văn trong trang nguồn thì **giữ fact và thêm warning**. So khớp sau khi chuẩn hoá NFC, chữ thường và bỏ markdown. Prompt yêu cầu evidence chứa chính giá trị: `identity.name` có tên sản phẩm; mỗi plan có cả tên plan và giá. Schema gửi LLM đặt `value` của `identity.name` trước `evidence`, vì LLM sinh JSON theo thứ tự khoá. Chạy thật 21/10: khi evidence đứng trước, PDFCraft 4/4 lần lấy câu đầu trang không có tên; khi đổi thứ tự thì 2/2 lần có tên. Code kiểm lại bằng warning `value_not_in_evidence`. Prompt có thêm: "evidence là MỘT đoạn liền, chép nguyên văn, không ghép, không sửa chữ" (LLM vẫn có lúc ghép 2 dòng hoặc viết lại câu: giữ fact + `evidence_not_found`).
- **Tên sản phẩm do code tìm lại:** evidence của `identity.name` không chứa tên (so theo từ sau chuẩn hoá) thì code tìm tên trong og:site_name, `<title>`, rồi các dòng h1 của các trang đã crawl: trang đã gửi LLM trước (theo điểm), rồi trang còn lại. Thấy thì thay `evidence` + `source_id` (không đổi `value`), `extracted_via` là `og` / `dom` (h1 là chữ markdown: không ghi). Trang chưa gửi được thêm vào `sources`. Không thấy thì giữ `value_not_in_evidence:identity.name`. Crawl ghi `title` và `site_name` vào header của file markdown (`<!-- … | title: … | site_name: … -->`, đã bỏ `|`, `-->`, xuống dòng) và vào `PageRecord`, nên evidence vẫn kiểm được trên chính `markdown_path` (chưa có `structured_path`). Hash trang không tính header. Chạy lại trên 6 output ElevenLabs 21/10 (crawl cũ, chưa có title): 6/6 lấy h1 "ElevenLabs Mobile App" (src_12).
- **Sản phẩm chỉ miễn phí, không có bảng giá:** PKB v0.3 không có trường kiểu `pricing.model`; `free_plan` chỉ nghĩa là "có gói miễn phí". Nên ghi 1 plan `name` "Free", `list_price` 0, `price_unit` month, `billing_cycle` monthly (2 giá trị này do model bắt buộc khi có giá, không phải chữ in trên trang; **chỉ là giá trị giữ chỗ để đáp ứng cấu trúc model, KHÔNG phải cam kết chu kỳ thanh toán**. Plan không có trường ghi chú và không đổi schema v0.3, nên code thêm warning `free_only_placeholder_period:pricing.plans[0]` để FE / M2 không đọc nhầm), `price_text` / `evidence` là câu khẳng định miễn phí (vd. "Hoàn toàn Miễn phí"), và `free_plan` true. Ngoại lệ của `value_not_in_evidence`: đúng 1 plan, giá 0, evidence có chữ miễn phí thì không kiểm tên plan. Ví dụ: `docs/specs/pkb/examples/valid-v03-software-free-only.json`.
- **Mâu thuẫn:** LLM ghi các giá trị khác nhau của cùng 1 thông tin (vd. số công cụ giữa 2 trang). Code tìm thêm giá khác nhau của cùng plan + chu kỳ + đơn vị. Cả hai vào `quality.conflicts` (`field`, `values`, `source_ids`), không chọn giá trị nào.
- **Chi phí:** mỗi lần gọi, kể cả lần lỗi, ghi 1 item `cost_breakdown` v1 (`category=llm`, `step=extract`, `call_id`, `attempt`). Lần thành công: token từ usage, giá niêm yết, `cost_status=exact` (free tier vẫn ghi giá niêm yết, theo #74). Lần lỗi: token và `cost_usd` là 0, `cost_status=estimated`.

Mã lỗi của extract. Job `failed`, `generation_jobs.error` bắt đầu bằng mã. Lỗi luôn kèm `cost_breakdown` của các lần đã gọi.

| Mã | Khi nào | `retryable` |
| --- | --- | --- |
| `llm_quota_daily` | 429 do hết quota ngày (RPD). Worker **không retry**; trả `retry_after` = 0h giờ Thái Bình Dương kế tiếp (UTC; 14h giờ Việt Nam khi Mỹ dùng giờ mùa hè, 15h khi dùng giờ chuẩn). Hàng đợi đưa job về chờ, không đánh `failed` hẳn | có, sau `retry_after` |
| `llm_rate_limited` | 429 do vượt RPM, worker đã retry hết lịch 5 → 10 → 20 → 40 → 60 s | có |
| `llm_unavailable` | 500 / 503 hoặc lỗi mạng, đã retry hết cùng lịch | có |
| `llm_request_failed` | Lỗi khác của provider (400, 401, 403, 404...) | không |
| `llm_invalid_output` | Response không dùng được: bị cắt vì hết `max_output_tokens` (`finish_reason=MAX_TOKENS`) hoặc `finish_reason` khác `STOP` (vd. `SAFETY`), không phải JSON, sai schema, hoặc `identity.name` trỏ tới trang lạ. Không retry: gọi lại cùng prompt thường bị cắt lần nữa | không |
| `extract_no_pages` | Crawl `failed` hoặc không còn trang nào đọc được | không |
| `pkb_invalid` | PKB ghép xong không hợp lệ v0.3 (lỗi code) | không |

Nhận diện 429 RPM / RPD theo nội dung lỗi Gemini (`error.details[]`):
1. Có `google.rpc.QuotaFailure` với `violations[].quotaId` / `quotaMetric` chứa `PerDay` → RPD.
2. Không thì chứa `PerMinute` → RPM.
3. Không có `QuotaFailure`: `message` chứa "per day" / "daily" → RPD, còn lại → RPM.
RPM có `RetryInfo.retryDelay` lớn hơn bước backoff thì chờ theo gợi ý đó (tối đa 60 s). **Chưa có response 429 thật** (#70: 0 lần 429), fixture test là dữ liệu synthetic theo dạng lỗi trong tài liệu Google.

**Thời gian xấu nhất của 1 lần extract** (BE đặt timeout job / lease hàng đợi lớn hơn số này): `LLM_TIMEOUT_S × (1 + số bước của LLM_RETRY_DELAYS_S) + tổng thời gian chờ`. Mặc định: 180 s × 6 lần + (5 + 10 + 20 + 40 + 60) s = **1215 s (~20 phút)**. Nếu mọi lần là 429 RPM kèm `RetryInfo` ≥ 60 s thì mỗi lần chờ 60 s: 1080 + 300 = **1380 s (~23 phút)**. 429 RPD và lỗi không retry kết thúc sau 1 lần gọi (≤ 180 s). Đổi `LLM_TIMEOUT_S` / `LLM_RETRY_DELAYS_S` thì tính lại.

Warning (job vẫn `completed`, dạng `mã:chi tiết`): `evidence_not_found:<đường dẫn>`, `value_not_in_evidence:<đường dẫn>` (evidence có trong nguồn nhưng không chứa giá trị; chỉ kiểm `identity.name`, tên plan, `list_price` / `promo_price` của plan và `price` của `usage_prices`; so chữ theo từ sau chuẩn hoá (`ElevenLabsClient` không chứa `ElevenLabs`), so số sau khi đọc `1,000` / `1.000` / `9,99`; giá 0 khớp chữ "free" / "miễn phí"; free-only không kiểm tên plan; tên sản phẩm được code tìm lại trước khi cảnh báo. Không bắt được giá bị đảo khi cả 2 số có trong evidence, ca đó do `promo_above_list` bắt), `unknown_source_id:<đường dẫn>:<id>`, `evidence_truncated:<số>`, `conflict:<field>`, `free_only_placeholder_period:pricing.plans[0]` (ca free-only ở trên: `month` / `monthly` chỉ là giữ chỗ), `conflict_field_unresolved:<field>` (`field` do LLM ghi không trỏ tới trường nào trong PKB), `promo_above_list:pricing.plans[i]` (giá khuyến mãi cao hơn giá niêm yết, thường do LLM đảo 2 trường; không tự đảo), `promo_split:pricing.plans[i]` (code tách giá: evidence có đúng 2 giá cùng tiền và đơn vị, liền nhau như `$9$18` hoặc có "% off" / "giảm" thì giá lớn là `list_price`, giá nhỏ là `promo_price`, kèm `promo_terms` nếu evidence có; đã ghi đè giá LLM), `promo_unparsed:pricing.plans[i]` (có dấu hiệu khuyến mãi nhưng không chắc, giữ nguyên giá LLM), `promo_missing:pricing.plans[i]` (nguồn của plan có ≥ 2 giá mà PKB chỉ ghi 1 và có giá chưa plan nào ghi), `conflict_too_broad:<field>` (conflict của LLM ở mức cả mảng, không thu hẹp được về 1 fact), `section_not_covered:<heading>` (trang chủ / about có section đáng kể mà không fact nào có evidence nằm trong đó; xem dưới), `self_reported_metric:usp[i]` / `self_reported_metric:use_cases[i]` (fact có số liệu như `5.06M+`, `+35%`, `5x`, `12 hours`; là số website tự công bố, chưa kiểm), `metric_label_mismatch:usp[i]` / `metric_label_mismatch:use_cases[i]` (số trong `text` / `title` không đứng liền trước nhãn của nó trong evidence, vd. `33,973+ AI content views` trong khi nguồn ghi `AI content views 33,973+ / new followers`), `page_not_stored:<src>`, `page_read_failed:<src>:<lỗi>`, `page_empty:<src>`, `llm_retried:<số lần>:wait_<giây>s`.

**Lưu và hiển thị warning.** Warning của một lần extract (`evidence_not_found`, `value_not_in_evidence`, `promo_above_list`, `conflict`, `conflict_field_unresolved`, `conflict_too_broad`, `promo_split`, `promo_unparsed`, `promo_missing`, `section_not_covered`, `self_reported_metric`, `metric_label_mismatch`, `evidence_context_missing`, `free_only_placeholder_period`, ...) phải được lưu cùng PKB draft của job (cùng `quality.conflicts`) và hiện ở bước xác nhận PKB. Fact còn conflict hoặc có warning về căn cứ (evidence không khớp, giá trị không nằm trong evidence, giá khuyến mãi cao hơn giá niêm yết) **không tự coi là đã xác nhận**: người dùng / QA xem và xác nhận hoặc sửa rồi mới đưa sang M2. Schema hợp lệ hoặc evidence có trong nguồn chưa đủ để coi claim là đúng về ý nghĩa. PR A chỉ trả warning trong `ExtractResult`; việc lưu và hiển thị làm ở đầu việc BE (queue / API / Storage) và FE tương ứng.

**Phủ nội dung trang và nhóm trích (v0.4.4, #67).** Schema gửi LLM (`PKBExtract`) có thêm `audiences[]` (`segment`, `jtbd` nếu trang nói rõ) và `usp[]` (`text`); **PKB v0.3 không đổi** (hai nhóm này đã có trong v0.3). Prompt hướng dẫn: lộ trình / giải pháp theo phòng ban → `use_cases[]` (`title` = phòng ban + tiêu đề, evidence là đoạn nguyên văn có kết quả kèm số); bảng việc làm, thử thách, chương trình đối tác → `features[]`; nhóm đối tượng → `audiences[]`; số liệu thành tích do website công bố → `usp[]`, `text` bắt đầu "Theo <tên sản phẩm> công bố:"; số liệu thị trường / ngành không nói về sản phẩm **không ghi vào PKB** (chưa có trường phù hợp, đề xuất `proof` / `market_stat` cho v0.3.x); bộ đếm chỉ toàn số 0 (`0+`, `0,00M+`) là giữ chỗ của hiệu ứng đếm số, bỏ qua. Mỗi số liệu thành tích là 1 mục `usp` riêng (1 số + nhãn đứng ngay sau nó, giữ chữ của nhãn). Code kiểm bằng `metric_label_mismatch` (ca `usp[0]` AISoEasy 30/10 ghép lệch một nấc), nhưng chỉ bắt được số đứng liền trước một nhãn khác có trong evidence; mục tách rời khỏi ngữ cảnh (`+720 in H1`) code không bắt được bằng nhãn; phần mất tên nền tảng / khối do bước nối ngữ cảnh khối nguồn (bên dưới) xử lý, phần còn lại QA / người dùng đối chiếu ở bước xác nhận.

`section_not_covered:<heading>`: code tách markdown đã gửi LLM theo heading (`#`…`######`; phần trước heading đầu tiên có heading `(đầu trang)`); section đáng kể là section có ≥ 15 từ dưới heading (`coverage.MIN_WORDS`). Section được coi là phủ khi có fact cùng `source_id` mà evidence (chuẩn hoá như khi kiểm evidence) nằm trong section, tính lần xuất hiện đầu của evidence trong trang; evidence vắt qua ranh giới phải lấn vào section kia ≥ 20 ký tự (`coverage.MIN_OVERLAP`). Chỉ kiểm trang `page_type` nằm trong `ExtractSettings.coverage_page_types` (mặc định `("other",)`: trang chủ, about), vì trang features / docs / faq / pricing có hàng chục section lặp dạng mà PKB chỉ lấy vài mục (đo offline: PDFCraft 1 so với 37, ElevenLabs 8 so với 122 nếu kiểm mọi trang). Section bị bỏ có chủ ý (số liệu thị trường) vẫn có warning; người xác nhận đọc theo ngữ cảnh. `<heading>` cắt ở 80 ký tự, có thể chứa dấu `:`, và warning không ghi `source_id`: bên nhận không nên tách warning theo `:` để lấy heading. `self_reported_metric` chỉ áp cho `usp[]` và `use_cases[]`; `features[]` có số như "90+ tools" thuộc mô tả sản phẩm nên không gắn cờ. Số có dấu `+` đứng trước (`+720 in H1`) cũng tính là số liệu.

**Ngữ cảnh khối nguồn (v0.4.5, #67).** Với `usp[]`, `use_cases[]`, `audiences[]`, nếu evidence không chứa heading của khối nguồn thì code (sau bước sửa plan, trước khi kiểm evidence) nối heading gần nhất phía trên vào evidence: evidence mới là đoạn liền từ dòng heading tới hết evidence cũ, cắt thẳng từ markdown nên vẫn nguyên văn. Điều kiện: ≤ 200 ký tự và ≤ 4 dòng (`context.MAX_LINES`; xa hơn thường là dòng thống kê chung của cả trang, không phải của khối). Không đủ điều kiện thì giữ evidence cũ và thêm warning `evidence_context_missing:<path>`. Khi evidence chính là dòng heading, code nối thêm dòng nhãn ngay trên nếu dòng đó ngắn (≤ 6 từ, không chữ số, không phải câu, danh sách, trích dẫn hay heading). `usp[]` thêm tên khối vào `text` (`2.58M+ Views (TikTok)`) nếu `text` chưa có và heading ≤ 4 từ (`context.NAME_MAX_WORDS`). Không gọi LLM. Giới hạn đã biết: khối lộ trình theo phòng ban (tên phòng ban, tiêu đề, kết quả cách nhau quá 200 ký tự) không nối được; muốn đạt cần nhiều evidence span hoặc nới giới hạn evidence, thuộc contract PKB. `features[]` chỉ nhận `origin: crawled` ở model hiện tại, nên bước xác nhận chưa thêm tay được feature (xem mục đề xuất schema bên dưới).

### Đề xuất cho phiên bản schema sau

Chưa áp dụng cho PKB v0.3 (contract v0.3 thuộc #68). Quyết định 02/11 (#67, #90): **không mở `origin: owner` cho `features[]` ở v0.3**; feature mà LLM bỏ sót thì để ngoài PKB cho video P1, không ghi `crawled` giả. Ca AISoEasy, evidence nguyên văn đã có sẵn nếu sau này schema cho phép:
- `### Challenges & rewards\nJoin real-world challenges, climb leaderboards, and earn rewards.`
- `### Become an AI Partner\nSend us your details and the AI So Easy team will reach out to discuss a distribution partnership.`

Các đề xuất khác đã nêu ở trên, cùng chờ phiên bản schema sau: nhóm `proof` / `market_stat` cho số liệu thị trường; nhiều evidence span (hoặc nới giới hạn 200 ký tự) để `use_cases[]` chứa đủ phòng ban + tiêu đề + kết quả.

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

## Sản phẩm vật lý (P1)

Nguồn: yêu cầu P1 của lead (v1.1, 13/10/2026), issue #67, khảo sát [`docs/report/p1-shop-url-survey.md`](../report/p1-shop-url-survey.md). Mục này **chỉ là đặc tả**; code extract cho `physical` trong `services/worker` làm ở PR sau.

### Phạm vi và quyết định

- Input là URL website / công cụ AI (như trước) **hoặc link sản phẩm trên shop**. Người dùng xác nhận thông tin sản phẩm ở bước 2 ("Xác nhận sản phẩm") trước khi cấu hình video. 1 chủ sở hữu xác nhận; không còn merchant, campaign, creator, tracking, affiliate.
- **URL demo.** Website / công cụ AI = `https://elevenlabs.io` (đã chốt; lead đồng ý). Sản phẩm vật lý: **Lock&Lock Riga Tumbler 897ml là ứng viên, chưa chốt** (`https://www.locknlock.vn/vi-vn/binh-giu-nhiet-locknlock-riga-tumbler-phien-ban-viet-nam-897ml/B80015105.html`). Website bán hàng chính hãng **được tính là link shop** (không bắt buộc là sàn); điều kiện còn thiếu là **quyền sử dụng dữ liệu và asset**. Robots cho phép và HTTP 200 chỉ chứng minh truy cập được về kỹ thuật; [điều khoản của site](https://www.locknlock.vn/vi-vn/account-register) còn hạn chế khai thác dữ liệu và sao chép / lưu nội dung (BA, #67). Cần xác nhận quyền, hoặc thay bằng URL khác. Trong lúc chờ, đừng dùng URL này làm nguồn crawl hay ảnh; dữ liệu khảo sát chỉ là bằng chứng trong báo cáo.
- **Ví dụ / fixture dùng chung là dữ liệu giả** (thương hiệu giả, `example.com`), gồm ca `out_of_stock`. Không cần tìm sản phẩm Tiki còn hàng. Nếu Lock&Lock được dùng: demo **một biến thể đã đối chiếu đủ** giá, thông tin, ảnh (xem quy tắc 4 và 5 ở mục Trích xuất).
- **Shopee và TikTok Shop: chưa kiểm chứng, hoãn tới sau luồng P1 chính.** Không kết luận hỗ trợ hay bị chặn. Khi mở lại cần URL sản phẩm thật, điều kiện sử dụng phù hợp, vẫn tuân thủ robots / WAF (không vượt chặn).
- Giữ nguyên [Quy tắc crawl](#quy-tắc-crawl): robots RFC 9309, `waf_challenge`, `login_redirect`, bị chặn thì dừng. Không stealth, không đổi User-Agent, không proxy, không gọi API nội bộ của sàn.
- Số đo (7 trang sản phẩm, 1 mẫu mỗi nền tảng nên chỉ là xu hướng): robots cho phép và không WAF ở 7/7; JSON-LD `Product` 6/7; giá đọc được từ JSON-LD 5/7; giá có trong HTML tĩnh 7/7; GET tĩnh cho cùng dữ liệu cấu trúc như render JS 7/7; biến thể có trong JSON-LD 0/7; ảnh tải được 7/7.

### Hợp đồng dữ liệu

Contract là [PKB v0.3](pkb/README.md), không chép lại ở đây. Tóm tắt:

| Mục | Quy tắc |
|---|---|
| `identity.product_kind` | `software` \| `physical`. Bắt buộc ở v0.3. PKB v0.2 = `software` |
| `physical` | Bắt buộc `offers[]` (≥ 1). `pricing.plans` không bắt buộc. `variants[]`, `specs[]`, `media.images[]` tuỳ chọn |
| `software` | Như v0.2: bắt buộc `pricing`; không có `offers` / `variants` / `specs` |
| `offers[]` | `price_text`, `amount`, `currency` (ISO 4217 lấy từ trang, không mặc định VND, không quy đổi), `original_amount`, `availability`, `seller`, `platform`, `variant_ref` |
| `variants[]` | `id`, `name`, `attributes[]`, `sku`, `selected`. **Không chứa giá**; giá ở `offers[]` liên kết bằng `variant_ref` |
| `media.images[]` | `url`, `storage_path`, `alt`, `role` (`hero` \| `gallery`), `variant_ref`, `generic` |
| Mục có nguồn | `origin` = `crawled` (bắt buộc `source_id` + `evidence`) hoặc `owner` |
| Owner nhập / sửa | **Mọi** mục `origin: owner` bắt buộc `edited_by` (UUID) + `edited_at` (ISO 8601 UTC); cấm với `crawled`. Owner sửa `identity.name`, `description`, `category`, `brand_name`, `sku`, `gtin` ở bản nháp: giữ giá trị đã crawl ở `previous` (1 giá trị, luôn là giá trị crawl, không đổi khi sửa lại). `origin: owner` = chưa kiểm chứng, không có cờ `verified` |
| Evidence của dữ liệu có cấu trúc | `evidence` = chuỗi giá trị gốc nguyên văn (vd. `"price":"520000"`), `source_id` = trang chứa chuỗi đó |
| `affiliate`, `origin: merchant` | Deprecated; cấm trong dữ liệu 0.3. `merchant` → `owner` |

### Phân loại input: `classify_input_url`

Đề xuất heuristic (chưa code). Trả `product_kind` + `confidence`; không chắc thì mặc định `software` (hành vi cũ). Owner sửa được ở bước 2; sửa loại thì tạo job crawl mới.

| Bước | Tín hiệu | Kết luận |
|---|---|---|
| 1. Chỉ dựa trên URL (chưa tốn request) | Host thuộc danh sách sàn đã biết (`tiki.vn`, `lazada.vn`, `shopee.vn`, `tiktok.com/shop`…), hoặc path khớp mẫu: `/products/<handle>` (Shopify, Haravan), `/product/`, `/san-pham/`, đuôi `-p<số>.html` (Tiki), `-i<số>.html` (Lazada) | `physical`, `confidence = medium` |
| 2. Sau khi render trang đầu (đã có HTML) | JSON-LD có `Product` / `ProductGroup` kèm `Offer` / `AggregateOffer`; hoặc `og:type = product`; hoặc có `product:price:*` / `og:price:*` | `physical`, `confidence = high` |
| 3. Loại trừ | JSON-LD `SoftwareApplication` / `WebApplication`, hoặc URL là gốc domain (`/`) mà không có Offer | `software` |
| 4. Không khớp | | `software`, `confidence = low`, hỏi owner ở bước 2 |

Rủi ro: trang pricing của SaaS đôi khi có JSON-LD `Product`; bước 3 và việc owner sửa ở bước 2 xử lý. Tham số `product_kind` ở API cho phép ép loại ngay từ đầu.

### Crawl mode `shop_item`

Dùng khi `product_kind = physical`. Khác mode mặc định (`site`, ≤ 30 trang):

| Mục | `shop_item` (đề xuất) |
|---|---|
| Điểm bắt đầu | Chính URL sản phẩm đã chuẩn hoá (`normalize_product_url`). Không tải trang chủ, không đọc sitemap |
| Trang cùng host | Tối đa **4** trang, chọn từ link nội bộ của trang sản phẩm theo từ khoá path: chính sách đổi trả / vận chuyển / bảo hành (`policies`, `chinh-sach`, `doi-tra`, `van-chuyen`, `bao-hanh`), thông số / hướng dẫn size (`thong-so`, `size`), `faq`. `page_type`: `policy`, `specs`, `faq` |
| Tổng trang | **≤ 5** (1 sản phẩm + ≤ 4). Không host phụ |
| Request | `robots.txt` của host, 5 trang tối đa, ≥ 1 giây giữa 2 request cùng host. Ảnh tải sau, mỗi ảnh kiểm robots của host ảnh |
| HTML | Dùng HTML của **chính lần render** Crawl4AI (`FetchResult.html`, không thêm request). Khảo sát: GET tĩnh cho cùng dữ liệu cấu trúc như render ở 7/7 trang, nên render chỉ là phương án an toàn cho trang cần JS |
| Lưu | Markdown như cũ; thêm `structured.json` mỗi trang (JSON-LD, meta `og:*` / `product:*`, microdata Product, JSON nhúng của nền tảng đã lọc) → `sources[].structured_path`. **Không lưu HTML thô** |
| Bị chặn / lỗi | Giữ nguyên quy tắc 1–5. Thêm mã `no_product_data` khi không bóc được tên hoặc offer nào |
| Chi phí | 1 lời gọi LLM nhỏ (lợi ích / use case / đối tượng / điểm khác biệt). Chưa đo; ước tính thấp hơn `site` vì ≤ 5 trang. Đo khi worker có |

Giới hạn là đề xuất, chỉnh theo số đo thật khi làm worker.

### Trích xuất cho `physical`

**Nguyên tắc: dữ liệu có cấu trúc trước, bằng code, không LLM.** LLM (`gemini-3.5-flash-lite`, giữ ADR-0002) chỉ dùng cho phần cần đọc hiểu và vẫn bắt buộc evidence.

| Trường | Thứ tự nguồn (dừng khi có) | Ai làm |
|---|---|---|
| `identity.name` | JSON-LD `name` → `og:title` (bỏ hậu tố sàn như "\| Lazada Việt Nam") → `<h1>` | code |
| `identity.brand_name`, `sku`, `gtin` | JSON-LD `brand.name`, `sku` / `mpn`, `gtin*` → microdata → JSON nhúng (`vendor`) | code |
| `offers[]` | JSON-LD `Offer` / `AggregateOffer` (kể cả `offers[].priceSpecification[].price`) → microdata → `product:price:*` / `og:price:*` → JSON nhúng của nền tảng (Haravan `meta`, Lazada `__moduleData__`) → DOM | code |
| `variants[]` | JSON-LD `hasVariant` (hiếm) → JSON nhúng → DOM (swatch / `<select>`) | code |
| `specs[]` | JSON-LD `additionalProperty`, `model` → microdata → bảng thông số trong DOM. Không có thì để trống | code |
| `media.images[]` | JSON-LD `image` → gallery DOM (`img[itemprop=image]`) → microdata → `og:image` | code |
| `features[]` (lợi ích), `use_cases[]`, `audiences[]`, `usp[]` (điểm khác biệt) | Markdown trang sản phẩm + trang chính sách / thông số | LLM |

Quy tắc:

1. **LLM không sinh hay sửa** `offers`, `variants`, `specs`, `media`, `sku`, `gtin`, `brand_name`, giá. Schema gửi cho LLM không có các trường đó.
2. Mỗi mục LLM kèm `evidence` ≤ 200 ký tự trích nguyên văn markdown. Có câu trích trực tiếp: `origin: crawled`; suy ra: `inferred` (phải duyệt trước khi M2 dùng, FR-05).
3. **Chuẩn hoá giá bằng code.** Định dạng đã gặp: `"520000"`, `26.25` (USD), `"690,000₫"`, `"7.800.000"`, `"210.000 ₫"`, `69000000.0` (Haravan, ×100).
   - Bỏ ký hiệu tiền và khoảng trắng; với VND (không có phần thập phân) thì `.` và `,` là dấu nghìn; với USD thì `.` là dấu thập phân.
   - `currency` lấy từ `priceCurrency` / `og:price:currency` / `product:price:currency`. Chỉ suy từ ký hiệu khi không nhập nhằng (`₫` → `VND`; `$` thì không). Thiếu `currency` thì `amount = null`, giữ chuỗi gốc ở `price_text`, owner nhập.
   - ÷100 chỉ áp cho giá lấy từ JSON nhúng của Haravan (nhận dạng bằng `HaravanAnalytics` / `hstatic.net`) và ghi `extracted_via: embedded`. Ưu tiên `og:price` / JSON-LD nếu có.
   - `AggregateOffer` có `lowPrice` ≠ `highPrice`: `amount = null`, khoảng giá ở `price_text`.
   - Không quy đổi tiền tệ.
4. **Biến thể, giá và ảnh gắn đúng `variant_ref`.** Giá JSON-LD chỉ của biến thể đang chọn (`selected`).
   - Mỗi `offers[]` và mỗi `media.images[]` của sản phẩm nhiều biến thể phải mang `variant_ref` của đúng biến thể mà giá / ảnh đó thuộc về.
   - **Không suy ra** giá hoặc ảnh cho biến thể chưa kiểm: không sao chép giá của biến thể này sang biến thể khác, không dùng ảnh của màu khác thay thế, không coi giá của biến thể đang chọn là giá chung. Biến thể chưa có giá thì **không có offer** cho nó; chưa có ảnh thì không có ảnh cho nó.
   - Demo: chỉ cần một biến thể đã đối chiếu đủ giá, thông tin và ảnh. Biến thể còn lại bổ sung sau khi đối chiếu.
5. **Ảnh:** lọc gallery theo mã sản phẩm / `variant_ref` (trên trang khảo sát, ảnh số 3 thuộc màu khác: không gắn vào biến thể đang chọn). `og:image` không chứa mã sản phẩm trong khi gallery có ảnh khác thì đánh `generic: true` (banner site), không tải và không dùng làm cảnh video. Tối đa 8 ảnh (đề xuất). 1 ảnh `hero`. Việc **được phép lưu và dùng** ảnh là điều kiện riêng, xem mục "Ảnh sản phẩm: quyền sử dụng".
6. **Kiểm sau trích xuất (code):** chuỗi `evidence` của mục có cấu trúc phải tìm thấy nguyên văn trong `structured.json` hoặc HTML của trang `source_id`. Không thấy thì bỏ mục đó và ghi cảnh báo, không giữ giá trị không có bằng chứng.
7. Làm sạch mô tả: `description` trong JSON-LD có thể là HTML kèm `iframe` (gặp ở trang khảo sát); bỏ thẻ trước khi đưa vào LLM.

### Ảnh sản phẩm: quyền sử dụng

Quy tắc của #52 (BA, #67), áp dụng cho ảnh sản phẩm **và screenshot** (kể cả screenshot trang public của website):

- Ảnh và mô tả trên trang shop thuộc người bán hoặc thương hiệu. **Chỉ lưu và dùng ảnh / screenshot (M3, video) khi có quyền sử dụng.** Dùng nội bộ và ghi nguồn **không thay thế** điều kiện này.
- Chưa có quyền thì **báo thiếu asset** (không tải, không đưa vào `assets`) và lấy nguồn được phép: ảnh do merchant / chủ sản phẩm cung cấp kèm xác nhận quyền (#53), asset có license, media kit hoặc press kit chính thức, hoặc xin đồng ý của chủ ảnh.
- Cách ly kỹ thuật khi đã có quyền: lưu ở Storage private; giữ `media.images[].url` và `sources[].url` làm nguồn; không bật bucket công khai; chỉ tải ảnh khi robots của host ảnh cho phép. Đây là biện pháp phụ, không phải điều kiện thay quyền.
- Trong lúc chờ xác nhận, fixture và spike dùng asset tự tạo hoặc dữ liệu giả có ghi rõ.
- PKB chỉ lưu evidence ≤ 200 ký tự, không lưu nguyên văn mô tả dài của shop.

### Danh sách thay đổi cho BE

PR này **không sửa ERD, migration, API hay worker**. Mục dưới là việc BE tự làm ở PR riêng. Khi làm, theo quy tắc repo: đổi schema DB thì thêm migration, đổi API thì cập nhật `docs/specs/api-contract.md`, thay đổi ảnh hưởng web thì tạo issue bên `AI-review-FE`.

| # | Hạng mục | Thay đổi đề xuất | Ghi chú |
|---|---|---|---|
| 1 | DB `products` | Thêm `product_kind` (`software` \| `physical`, mặc định `software`) làm bản sao để lọc / hiển thị; nguồn chuẩn vẫn là `product_knowledge.data.identity.product_kind` | Cần migration + cập nhật ERD / data dictionary |
| 2 | DB `products.affiliate_url` | Bỏ NOT NULL (hoặc xoá). Dữ liệu cũ giữ | P1 bỏ affiliate |
| 3 | DB `products.website_url` | Dùng cho cả link sản phẩm shop. Chuẩn hoá bằng `normalize_product_url`; tham số không phải theo dõi được giữ (vd. `?variant=`) nên 2 biến thể là 2 product | Quyết định có chấp nhận hay bỏ tham số biến thể |
| 4 | DB: chủ sở hữu Product | **Không đổi tên cột / role trong PR này** (`merchant_id`, `reviewer_role`). **Yêu cầu:** Product thuộc về tài khoản đăng nhập thường, không bắt buộc đăng ký Merchant. Giữ `merchant_id` trỏ tới `merchants` và chỉ đổi tên hiển thị thành "owner" **không đáp ứng** yêu cầu này. BE đề xuất: (a) quan hệ sở hữu Product với tài khoản đăng nhập; (b) ánh xạ metadata review (`reviewer_role`, người sửa / thời điểm); (c) cách giữ tương thích dữ liệu cũ. BA–AI–FE cùng review trước khi cập nhật ERD / migration. Các bảng hồ sơ merchant hiện có giữ cho phạm vi cũ | Lead (#67). Việc của BE; ERD / migration làm ở PR riêng sau khi thống nhất |
| 5 | DB `product_knowledge` | Không đổi cột. `data` chứa PKB `schema_version` `0.2` hoặc `0.3`. Có thể thêm chỉ mục trên `data->'identity'->>'product_kind'` | Code đọc phải kiểm `schema_version` |
| 6 | DB `generation_jobs` | `input_snapshot` thêm `product_kind`, `crawl_mode` (`site` \| `shop_item`); `result_manifest` (job `completed`) thêm `product_kind`, `crawl_mode` | README PKB, mục `result_manifest` |
| 7 | Storage | Bucket private cho ảnh sản phẩm và `structured.json`: `products/<product_id>/v<version>/…` | RLS như NFR-06 |
| 8 | API `POST /products` | Body: `website_url` (URL hoặc link sản phẩm), bỏ `affiliate_url`, thêm `product_kind?` (ép loại). Response thêm `product_kind` | Cập nhật `api-contract.md` |
| 9 | API `PATCH /products/{id}` | Cho owner đổi `product_kind` ở bước 2 → tạo job crawl mới | |
| 10 | API `GET /products/{id}/knowledge` | Trả `schema_version`; PKB 0.2 đọc được, chuyển lên 0.3 khi mở sửa (`merchant` → `owner`, bỏ `affiliate`) | |
| 11 | API `PATCH /products/{id}/knowledge` | Sửa theo trường cho `identity.*` (`name`, `description`, `category`, `brand_name`, `sku`, `gtin`), `offers[i].amount` / `currency`, thêm / xoá ảnh (upload → Storage), chọn biến thể. Mọi giá trị sửa ghi `origin: owner`. **Server** ghi `edited_by` (từ phiên đăng nhập) và `edited_at`, bỏ giá trị client gửi; lần sửa đầu của fact `crawled` đặt `previous` = giá trị crawl, các lần sau giữ nguyên `previous`. Chỉ sửa bản `draft` | README PKB, mục "Mục do owner nhập hoặc sửa" |
| 11a | DB / API: lịch sử sửa | Lưu lịch sử sửa đầy đủ (ai, lúc nào, giá trị cũ → mới); PKB chỉ giữ `previous`. Bản `approved` không sửa trực tiếp: sửa thì tạo bản nháp / version mới | Cần migration nếu chưa có bảng lịch sử. BE đề xuất |
| 11b | Dữ liệu v0.2 cũ | `origin: merchant` không có `edited_by` / `edited_at`. Khi chuyển lên 0.3 BE điền (đề xuất: user id chủ sản phẩm, thời điểm lưu bản v0.2) | **Chờ BE xác nhận** |
| 12 | API `POST …/knowledge/approve` | Kiểm thêm điều kiện duyệt của `physical` (README PKB): ≥ 1 offer có `amount` + `currency`, ≥ 1 ảnh không `generic`, mọi `source_id` / `variant_ref` hợp lệ | |
| 13 | API `GET /products/{id}/assets` | Thêm ảnh sản phẩm từ `media.images[].storage_path` | M3 dùng |
| 14 | Worker | `classify_input_url`; mode `shop_item`; parser dữ liệu có cấu trúc (chỉ `json` + parser HTML đã có, không thêm thư viện); lưu `structured.json`; mã lỗi `no_product_data`; tải ảnh có kiểm robots; prompt extract cho `physical` | PR "T3 làm lại theo v0.3" |
| 15 | Worker | Chuyển model Pydantic v0.3 từ `spikes/m1-crawl-extract/schema_v03.py` vào `services/worker` làm nguồn contract; giữ test sinh lại schema trùng file đã commit | |
| 16 | FE (issue bên `AI-review-FE`) | Form 1 trường URL; bước 2 hiển thị / sửa `offers`, `variants`, ảnh và loại sản phẩm; bỏ ô affiliate / commission | |
| 17 | QA | Golden Facts cho sản phẩm vật lý cạnh `docs/qa/T12*`, chỉ sau khi URL sản phẩm vật lý được xác nhận quyền sử dụng (ứng viên: Lock&Lock). Fixture dùng chung: dữ liệu giả ở `pkb/examples/`, gồm ca `out_of_stock` | |

### Câu hỏi mở (P1)

- Quyền dùng dữ liệu và asset của Lock&Lock: ai xác nhận, hoặc thay URL sản phẩm vật lý khác (AI–BA, trước mốc 18/10).
- Dữ liệu v0.2 cũ có `origin: merchant`: BE điền `edited_by` / `edited_at` thế nào khi chuyển lên 0.3 (mục 11b ở bảng trên).
- Ai được sửa, lịch sử sửa lưu ở đâu (mục 11a): phụ thuộc quan hệ sở hữu Product (mục 4); BE đề xuất, BA–AI–FE review.
- Quan hệ sở hữu Product với tài khoản đăng nhập thường và cách giữ tương thích dữ liệu cũ (BE đề xuất, mục 4 ở bảng trên).
- Shopee / TikTok Shop: hoãn tới sau luồng P1 chính; khi mở lại cần URL sản phẩm thật và điều kiện sử dụng phù hợp.

## Requirements

Yêu cầu cốt lõi: không fact nào được vào PKB mà thiếu nguồn hoặc thiếu xác nhận của người duyệt.

### Functional

| ID | Yêu cầu | Ưu tiên |
| --- | --- | --- |
| FR-01 | Tạo product chỉ với 1 URL (website / công cụ AI, hoặc link sản phẩm trên shop). ~~Website URL + affiliate link~~ (affiliate link deprecated từ P1) | Must |
| FR-02 | Tự chọn trang quan trọng (pricing, features, docs, FAQ, changelog), tối đa 30 trang, tôn trọng `robots.txt` của từng host. Crawl được host phụ cùng domain gốc (vd. `support.claude.com` cho `claude.com`): tối đa 5 trang, chỉ `page_type` faq / pricing, tính vào giới hạn 30. Bật theo từng product, không tự bật: domain gốc có thể là sản phẩm khác (`dreamina.capcut.com` → `capcut.com`) | Must |
| FR-03 | Render được trang SPA (JavaScript) | Must |
| FR-04 | Trích xuất theo JSON schema; mỗi fact có `source_id` + evidence; giá theo [Quy tắc trích xuất giá](#quy-tắc-trích-xuất-giá) | Must |
| FR-05 | Fact suy luận gắn `origin: inferred`, không được dùng khi chưa duyệt | Must |
| FR-06 | Chụp screenshot full-page, desktop 1440×900, mobile 430×932 @3x, element theo section tính năng; logo ưu tiên SVG. Ảnh lưu Storage, metadata trong `sources` (`image_paths`); M3 đọc ảnh theo metadata này | Must |
| FR-07 | Merchant xem, sửa, approve PKB; mỗi lần approve tạo version mới. Trạng thái: `draft \| in_review \| approved \| rejected`. **Chỉ merchant sở hữu product approve.** Admin chỉ reject bản `in_review` khi vi phạm chính sách, bắt buộc lý do; admin không sửa, không approve (bổ sung cho decision-log #11, đã chốt ở #23). Cả approve và reject đều ghi `reviewed_by`, `reviewed_at`. Approve: `reviewer_role = 'merchant'`. Reject: `reviewer_role` là `merchant` hoặc `admin`, `review_note` bắt buộc, không rỗng, tối đa 1000 ký tự (lý do reject lưu ở đây). `draft`, `in_review`: 4 cột review đều null (ERD v1.3.3, decision-log #18, #19). Bản `approved` không sửa được; thu hồi làm ở mức product (`products.status` → `archived`) hoặc pause campaign (#23, #38) | Must |
| FR-08 | ~~Index PKB approved vào pgvector, API search~~ **Hoãn sau MVP** (qa-log #5, ERD v1.3.1, #23). M2, M4 dùng nguyên PKB approved (JSON) | Later |
| FR-09 | Phát hiện xung đột (form vs crawl, giá khác nhau giữa các trang) và hiện cho reviewer | Should |
| FR-10 | Upload PDF/ảnh cho phần sau login, đưa vào extraction | Should |
| FR-11 | Re-crawl thủ công + diff với version trước | Should |
| FR-12 | Hiển thị tiến trình job theo bước (queued → crawling → extracting → review) | Should |
| FR-13 | Product tạo ảnh/video: lấy kết quả mẫu từ gallery/showcase công khai làm bằng chứng (ảnh lưu Storage, metadata `kind: media_sample` trong `product_knowledge.sources`) | Could |
| FR-14 | Phân loại input `software` \| `physical` bằng `classify_input_url`; owner sửa được ở bước 2 ([Phân loại input](#phân-loại-input-classify_input_url)) | Must (P1) |
| FR-15 | Crawl mode `shop_item` cho `physical`: 1 trang sản phẩm + ≤ 4 trang cùng host, giữ quy tắc robots / WAF ([Crawl mode `shop_item`](#crawl-mode-shop_item)) | Must (P1) |
| FR-16 | Trích `offers`, `variants`, `specs`, `media.images`, `brand_name`, `sku` bằng code từ dữ liệu có cấu trúc; evidence là chuỗi giá trị gốc ([Trích xuất cho `physical`](#trích-xuất-cho-physical)) | Must (P1) |
| FR-17 | Owner nhập / sửa giá, ảnh, biến thể của `physical` ở bước 2 (`origin: owner`); không duyệt được khi chưa có offer có giá | Must (P1) |

### Non-functional

| ID | Yêu cầu | Mục tiêu |
| --- | --- | --- |
| NFR-01 | Thời gian xử lý 1 product (30 trang) | ≤ 5 phút p95 |
| NFR-02 | Chi phí LLM mỗi product (crawl + extract) | ≤ $0.05, đọc từ `generation_jobs.cost_usd` (DB tính tổng từ `cost_breakdown`). Chỉ tính job có `cost_usd` khác null: `cost_breakdown = '{}'` (mặc định) → `cost_usd` null, nghĩa là chưa ghi chi phí, khác chi phí = 0. Cost của `content_scripts` là số đo của M2, không tính vào NFR-02. Spike đo **~$0.01** ($0.008–0.014) với mode `batch` (10 trang, 1 lời gọi); mode `per_page` $0.065–0.110, không đạt. Mẫu 2 product, giá gói trả phí Standard; cần xác nhận trên golden set (qa-log #6) |
| NFR-03 | Độ chính xác giá + tên plan trước review | ≥ 95% trên golden set 10 product, so cùng vùng IP lúc crawl. Spike: 1/8 lần chạy đúng (trước khi có Quy tắc trích xuất giá) |
| NFR-04 | Retry | 3 lần, exponential backoff; job idempotent theo `content_hash` |
| NFR-05 | Lịch sự với site | ≤ 1 request/giây/domain, User-Agent định danh platform |
| NFR-06 | Bảo mật | File upload và tài liệu merchant chỉ merchant + admin đọc (Supabase RLS) |
| NFR-07 | Quan sát | Log từng bước, trace mọi lời gọi LLM. Token và chi phí ghi ở `generation_jobs` (`tokens_in`, `tokens_out`, `cost_usd`, `cost_breakdown`). Worker chỉ ghi `cost_breakdown` theo [contract](contracts/README.md); DB tự tính 3 cột còn lại. Worker ghi payload v1 đầy đủ khi job kết thúc (`completed` hoặc `failed`). `tokens_in`, `tokens_out`, `cost_usd` nullable, không default: `cost_breakdown = '{}'` → 3 cột null (chưa ghi chi phí); payload v1 tổng 0 → 3 cột = 0 (thật sự $0); payload v1 thường → > 0. Pilot không đặt ngân sách tổng / product |
| NFR-08 | Thay provider | Đổi model LLM bằng config, không sửa code |

## Tech stack

FastAPI là API nghiệp vụ cho Product/PKB/job; API và worker xử lý nền chạy thành hai tiến trình riêng trong cấu trúc `services/worker/` hiện có. Worker viết bằng Python vì hệ sinh thái crawl/LLM phù hợp; frontend và DB theo stack chung của PRD (Next.js + Supabase). FE gửi yêu cầu và đọc trạng thái qua FastAPI; API tạo job rồi trả ID, không chờ crawl/LLM hoàn tất trong HTTP request. CRUD hồ sơ merchant/creator đã có tiếp tục gọi Supabase dưới RLS và column privileges. Chi tiết interface, phiên đăng nhập và trạng thái triển khai xem [API contract](api-contract.md).

| Thành phần | Chọn | Lý do / thay thế |
| --- | --- | --- |
| API và worker runtime | Python 3.12 + FastAPI cho API nghiệp vụ; API và worker chạy thành hai tiến trình riêng | API xác minh JWT, quyền sở hữu và vai trò; tạo job rồi trả ID. Worker xử lý nền |
| Queue | Đề xuất worker poll bảng `generation_jobs`, nhận job nguyên tử bằng `FOR UPDATE SKIP LOCKED`; chưa thêm Redis/Celery/pgmq | BE hoàn thiện ADR queue: claim job, retry, lease và phục hồi khi worker dừng; chưa triển khai queue |
| Crawl (1.2) | [Crawl4AI](https://github.com/unclecode/crawl4ai) như thư viện Python trong worker, qua adapter. **Đã chốt 08/10/2026 theo [ADR-0001](../adr/0001-crawl-tool.md)** | Apache-2.0 + điều khoản ghi công theo ADR-0001; ghim phiên bản/lock, không chạy Docker server của Crawl4AI, không stealth/proxy. Pricing dùng raw markdown, trang khác dùng fit |
| Screenshot (1.3) | Playwright for Python | Kiểm soát viewport, device scale, element screenshot |
| Extraction (1.4) | **`gemini-3.5-flash-lite`**, structured output JSON schema, mode `batch` (top-k trang trong 1 lời gọi). **Đã chốt 08/10/2026 theo [ADR-0002](../adr/0002-llm-provider.md)** | Tái sử dụng spike/prompt v0.2; QA kiểm giá, evidence và độ đầy đủ trên golden set. Chỉ chạy trong quota miễn phí đã xác minh |
| Merge + Enrichment (1.5–1.6) | Merge/chuẩn hóa ưu tiên code; phần LLM mặc định **`gemini-3.5-flash-lite`**, theo ADR-0002 | Chưa có số đo riêng cho 1.6. Không tự nâng model; fact inferred không dùng khi chưa được duyệt |
| LLM adapter | **`google-genai` trực tiếp qua adapter mỏng**, không dùng LiteLLM làm lớp gọi LLM; model qua config, ghim dependency/hash trong `uv.lock`. **Đã chốt theo ADR-0002** | Đổi model cùng provider bằng config; đổi provider cần adapter khác. `unclecode-litellm` do Crawl4AI kéo gián tiếp vẫn phải theo dõi theo ADR-0001 |
| Schema + validate | Pydantic v2 | Dùng chung schema cho LLM output và API |
| DB | Supabase Postgres | 1 nơi cho data, RLS |
| Storage | Supabase Storage | Screenshot, markdown nguồn |
| Embedding | **Hoãn sau MVP** (qa-log #5, ERD v1.3.1, #23) | MVP không dùng vector RAG. Ứng viên cũ: xem ADR-0002, Quyết định 4 |
| Phạm vi RAG | **Hoãn sau MVP** (qa-log #5) | M2, M4 dùng nguyên PKB approved (vài KB) làm context |
| LLM tracing | Langfuse (self-host hoặc cloud free tier) | Theo dõi prompt, token, chi phí |
| Review UI | Next.js + shadcn/ui; Sprint 1 poll `GET /jobs/{id}` qua FastAPI | FE dùng Supabase Auth để lấy phiên/access token; không đọc trực tiếp bảng job. Realtime là mở rộng sau nếu cần |
| Test | pytest, golden set 10 product, Playwright E2E cho UI | Tester đo NFR-03 |

Giá Gemini tra lại ngày **07/10/2026** tại trang giá chính thức <https://ai.google.dev/gemini-api/docs/pricing>: gói trả phí, tier **Standard**, USD / 1M token, input text (input / output; output gồm thinking token). Khớp giá spike dùng ngày 06/10/2026 (`spikes/m1-crawl-extract/config.py`).

"Mode `batch`" trong đặc tả này là gom nhiều trang vào 1 lời gọi, **không phải** tier Batch API của Gemini. Chi phí spike quy đổi theo tier Standard, không phải hóa đơn. Giai đoạn internship không có ngân sách tiền mặt: xác minh quota/model miễn phí và điều khoản dữ liệu trước khi chạy thật; hết quota thì báo lỗi và dừng, không tự bật billing hoặc fallback trả phí. CI/test thường xuyên dùng fixture; kết quả fixture không thay thế nghiệm thu crawl/LLM thật.

## Data model và API

M1 dùng 3 bảng của ERD v1.3.3 ([`docs/specs/erd/`](erd/erd.dbml), [data dictionary](erd/data-dictionary.md)). Không có bảng riêng cho crawl, trang, asset, chunk hay input.

| Bảng | Cột M1 dùng | Ghi chú |
| --- | --- | --- |
| `products` | `id`, `merchant_id`, `website_url`, ~~`affiliate_url`~~ (deprecated, P1), `name`, `merchant_input`, `current_knowledge_version`, `status` | `website_url` unique sau khi chuẩn hoá URL, không unique theo domain; từ P1 cũng chứa link sản phẩm shop. Form merchant (owner) nhập nằm ở `merchant_input`. Cột theo ERD v1.3.3, chưa đổi tên; thay đổi đề xuất: [Danh sách thay đổi cho BE](#danh-sách-thay-đổi-cho-be) |
| `product_knowledge` | `product_id`, `version`, `status`, `data`, `sources`, `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note` | PK `(product_id, version)`. `data` = PKB JSON, `sources` = trang nguồn + đường dẫn Storage (theo [`docs/specs/pkb/`](pkb/README.md)). `status`: `draft \| in_review \| approved \| rejected` Lý do reject ở `review_note` (≤ 1000 ký tự). Quy tắc 4 cột review theo `status`: xem FR-07 |
| `generation_jobs` | `id`, `product_id`, `job_type`, `status`, `idempotency_key`, `input_snapshot`, `result_manifest`, `error`, `attempts`, `finished_at` | M1 dùng `job_type = 'crawl'`. Cột chi phí `tokens_in`, `tokens_out`, `cost_usd` `numeric(12,6)`, `cost_breakdown` `jsonb DEFAULT '{}'`. `'{}'` = chưa ghi chi phí, khác chi phí = 0; worker ghi payload v1 đầy đủ khi job `completed` hoặc `failed`. `tokens_in`, `tokens_out`, `cost_usd` nullable, không default |

`result_manifest`: job `completed` có `pkb_version`, `pages_used`, `model`. Job `failed`: `result_manifest = null`, lỗi ở cột `error` (mã ngắn đứng đầu, vd. `waf_challenge`). Markdown nguồn, screenshot, file upload nằm trong Supabase Storage (private), không có bảng riêng.

Các endpoint dưới đây là **PLANNED**, chưa phải API đã triển khai. Mã crawl có trong worker không đồng nghĩa đã có endpoint hoặc queue chạy được. Interface dùng chung FE–BE–AI được quản lý tại [API contract](api-contract.md); BE bổ sung request/response, quyền, dependency và trạng thái triển khai trong cùng PR khi xây endpoint.

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| POST | `/products` | Body: website\_url (URL website hoặc link sản phẩm shop), ~~affiliate\_url~~ (deprecated), product\_kind?, form? → product\_id, job\_id, product\_kind |
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

- [ ] Chỉ nhập URL (~~+ affiliate link~~, deprecated từ P1) → có PKB draft trong ≤ 5 phút cho ≥ 8/10 product golden set
- [ ] (P1) URL sản phẩm vật lý đã được xác nhận quyền sử dụng → PKB `physical` hợp lệ schema v0.3 với `offers[0]` có `amount` + `currency` khớp con số in trên trang, `variant_ref` đúng biến thể đã đối chiếu; ≥ 1 ảnh không `generic` và được phép dùng; 0 lời gọi LLM cho giá, biến thể, ảnh
- [ ] (P1) Trang không có giá chuẩn (kiểu Lazada) → offer `amount = null`, không duyệt được cho tới khi owner nhập giá
- [ ] Giá và tên plan đúng ≥ 95% so với đáp án trước khi review
- [ ] 0 fact thiếu `source_id` mà không phải `origin: owner` (trước P1: `merchant`)
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
- `pricing.default_view` đang trộn tab chu kỳ (Monthly / Yearly) với tab đối tượng (Individual / Team). Đề xuất tách ở contract PKB v0.3 nhưng v0.3 (P1) chỉ thêm `physical`, chưa tách; vẫn mở cho phiên bản sau.
- ~~`evidence_in_source` của Dreamina giảm (0.92 → 0.81)~~ → đã điều tra (PR #39): 4 fact lệch do LLM gán sai `source_id` (evidence nằm ở `src_01`, ghi `src_02`); `check_evidence` không lỗi. Đề xuất cho contract / pipeline sau: code tìm evidence trên mọi trang rồi tự sửa `source_id`.
- Sản phẩm chính sprint 1 thay Gamma (bị WAF): M1 đề xuất ElevenLabs, chờ QA chốt (#38).
- Vùng giá → qa-log #9. Golden Facts → qa-log #11. Cả hai giữ nguyên trạng thái.
- ~~Nơi lưu lý do reject PKB, ý nghĩa cột review khi reject, nullability của `tokens_in` / `tokens_out` / `cost_usd`~~ → đã chốt ở ERD v1.3.3 (decision-log #18, #19, issue #50).
- NFR-02 trên golden set → chờ qa-log #6.
- Chọn crawl/LLM → **đã chốt 08/10/2026 theo ADR-0001/0002**: Crawl4AI; `gemini-3.5-flash-lite`; SDK `google-genai` qua adapter, không dùng LiteLLM làm lớp gọi LLM. Quota miễn phí, tích hợp worker và nghiệm thu golden set vẫn cần kiểm chứng khi triển khai.

## Lịch sử phiên bản

| Phiên bản | Ngày | Người sửa | Thay đổi |
| --- | --- | --- | --- |
| v0.1 | 05/10/2026 | @Hoang Nguyen | Bản đầu |
| v0.2 | 07/10/2026 | @PotatoMine725 (issue #5) | Thay Gemini 2.5 Flash-Lite bằng ứng viên Flash-Lite 3.x, tra lại giá 07/10/2026 trên trang chính thức, chọn model chờ ADR-002. NFR-02 ghi số đo spike (~$0.01/product, mode `batch`), link qa-log #6. Embedding ứng viên `gemini-embedding-2` 768 chiều; phạm vi RAG chờ qa-log #5. Ghi rủi ro LiteLLM. AI-1 làm toàn bộ M1 (#14). Merchant approve PKB, nội dung sau login qua FR-10, MVP tiếng Anh (#15). Thêm Quy tắc trích xuất giá từ spike #6 (tách giá niêm yết / khuyến mãi, cấm model tự tính giá, `price_unit` + `billing_cycle` bắt buộc, `usage_prices`, `default_view`, vùng IP), mode `batch` mặc định, crawl host phụ cùng domain gốc (≤ 5 trang). Thêm `identity.version`, `models[]`, logo ưu tiên SVG, FR-13 `media_sample` (Could) từ video tham khảo |
| v0.3 | 08/10/2026 | @PotatoMine725 (issue #23, #38) | Theo ERD v1.3.1: bỏ 5 bảng riêng (`crawl_jobs`, `crawled_pages`, `product_assets`, `knowledge_chunks`, `product_inputs`), dùng `products`, `product_knowledge`, `generation_jobs`. Bỏ vector RAG: 1.8 ra khỏi MVP, FR-08 hạ xuống Later, bỏ `/knowledge/search`, hoãn embedding. `website_url` unique sau chuẩn hoá. Thêm Quy tắc crawl (robots RFC 9309, WAF `waf_challenge`). Trạng thái PKB `draft \| in_review \| approved \| rejected`, chỉ merchant approve, admin chỉ reject có lý do. Chi phí đọc từ `generation_jobs.cost_usd`. Output dẫn contract `docs/specs/pkb/`. Điểm ERD còn để mở ghi "chờ #50". Đồng bộ theo ERD đã merge (PR #49): `cost_breakdown` `'{}'` = chưa ghi chi phí, NFR-02 chỉ tính job đã ghi; admin chỉ reject (bổ sung decision-log #11) |
| v0.3.1 | 08/10/2026 | @PotatoMine725 (issue #50) | Theo ERD v1.3.3 (PR #51, decision-log #18, #19): `approved_by` / `approved_at` đổi thành `reviewed_by` / `reviewed_at` (ghi cho cả approve và reject), thêm `reviewer_role`, `review_note` (lý do reject), quy tắc theo `status`. `tokens_in`, `tokens_out`, `cost_usd` nullable, không default; NFR-02 chỉ tính job có `cost_usd` khác null; cost của `content_scripts` không tính vào NFR-02. Bỏ các dòng "chờ #50" |
| v0.3.2 | 12/10/2026 | @PotatoMine725 (issue #41, #42, #59) | Đưa crawl từ spike vào `services/worker`. Thêm mục "Mã lỗi crawl" (mã lỗi job + `retryable`, lý do bỏ qua trang, đối chiếu tên với spike). Quy tắc crawl: robots 401/403 coi như không có robots (RFC 9309, spike trước đây coi là cấm), trang không đổi vẫn nằm trong danh sách trang, thêm quy tắc 5 (bị chặn giữa chừng ở trang con: dừng host đó, `completed` + `partial` nếu đủ trang). Quy tắc chuẩn hoá `website_url`: `http` đổi `https`, giữ `www.` và path, bỏ tham số theo dõi, sắp query theo tên, IDN sang punycode |
| v0.3.3 | 12/10/2026 | @VV6505 (issue #59, #61) | Đồng bộ ADR-001/002: Crawl4AI, `gemini-3.5-flash-lite`, `google-genai` qua adapter, hoãn embedding. FastAPI là API nghiệp vụ; API và worker chạy riêng, FE polling trạng thái qua API. Queue polling `generation_jobs` là đề xuất chờ ADR của BE. Ghi rõ endpoint M1 là PLANNED; không đổi schema, migration hoặc application code |
| v0.4.0 | 13/10/2026 | @PotatoMine725 (issue #67) | Đổi scope theo P1: thêm sản phẩm vật lý từ link shop. Mục mới "Sản phẩm vật lý (P1)": phạm vi và URL demo (ElevenLabs chốt; Lock&Lock chỉ là ứng viên chờ xác nhận quyền dùng dữ liệu / asset), `classify_input_url`, crawl mode `shop_item`, quy tắc trích xuất `physical` (dữ liệu có cấu trúc bằng code, LLM chỉ cho lợi ích / use case / đối tượng / điểm khác biệt), quy tắc quyền sử dụng ảnh / screenshot (#52: chỉ lưu và dùng khi có quyền; dùng nội bộ và ghi nguồn không đủ), quy tắc biến thể (không suy giá / ảnh cho biến thể chưa kiểm), owner nhập / sửa `identity.*` (`edited_by`, `edited_at`, `previous`; 14/10/2026), danh sách thay đổi cho BE (chủ sở hữu Product là tài khoản đăng nhập thường, chưa đổi tên cột DB). Output dẫn PKB v0.3 (superset v0.2: `product_kind`, `offers`, `variants`, `specs`, `media.images`, `sources[].structured_path`). Deprecated: affiliate link và commission (Input, FR-01, `POST /products`, `products.affiliate_url`), `affiliate` trong PKB; `origin: merchant` đổi thành `owner`. Thêm mã lỗi `no_product_data` (đề xuất), FR-14 đến FR-17, 2 acceptance criteria P1. Shopee và TikTok Shop ghi là chưa kiểm chứng, hoãn tới sau luồng P1 chính (không kết luận hỗ trợ hay bị chặn). Không đổi ERD, migration, API hay application code |
| v0.4.1 | 21/10/2026 | @PotatoMine725 (issue #67, #61, P1-04 PR A) | Mục mới "Extract 1.4 trong worker": interface `extract_product`, cách chọn trang, evidence (không khớp: giữ fact + warning), `quality.conflicts`, `cost_breakdown` mỗi lần gọi, mã lỗi `llm_quota_daily` (kèm `retry_after`), `llm_rate_limited`, `llm_unavailable`, `llm_request_failed`, `llm_invalid_output`, `extract_no_pages`, `pkb_invalid`, cách nhận diện 429 RPM / RPD, danh sách warning. Ngôn ngữ trang: `M1_CRAWL_LANGUAGES` (mặc định `en,vi`); mã `not_english` thay bằng `language_not_allowed` và `translation_duplicate`, không giữ alias. Bổ sung (review #90): warning `value_not_in_evidence`, thời gian xấu nhất của 1 lần extract, `MAX_TOKENS` thuộc `llm_invalid_output`, `value` trước `evidence` ở `identity.name`, code tìm lại tên sản phẩm (og:site_name / `<title>` / h1; crawl ghi `title`, `site_name`), luật free-only |
| v0.4.2 | 26/10/2026 | @PotatoMine725 (issue #67, P1-04 PR A) | Theo review #90: free-only ghi rõ `month` / `monthly` chỉ là giữ chỗ, không phải chu kỳ thanh toán, kèm warning `free_only_placeholder_period`; ghi cách lưu và hiển thị warning / conflict ở bước xác nhận PKB, fact còn conflict hoặc thiếu căn cứ không tự coi là đã xác nhận. Không đổi schema v0.3. |
| v0.4.4 | 30/10/2026 | @PotatoMine725 (issue #67) | Theo ca AISoEasy 30/10 (nhiều khối trang chủ không vào PKB): schema gửi LLM thêm `audiences[]`, `usp[]` (PKB v0.3 không đổi); prompt trích lộ trình theo phòng ban, jobs / thử thách / đối tác, đối tượng, số liệu traction (`usp`, "Theo … công bố:"), bỏ số liệu thị trường và bộ đếm số 0; warning mới `section_not_covered:<heading>` (độ phủ section của trang `other`), `self_reported_metric:<path>` và `metric_label_mismatch:<path>`. |
| v0.4.5 | 02/11/2026 | @PotatoMine725 (issue #67, P1-04 PR A) | Theo góp ý QA PKB AISoEasy: nối heading / nhãn khối nguồn vào evidence của `usp`, `use_cases`, `audiences` bằng code, warning mới `evidence_context_missing:<path>`; số có dấu `+` tính là số liệu tự công bố; prompt thêm ví dụ Challenge, audience nhân viên theo phòng ban, nhãn đầy đủ của số dùng chung nhãn. |
| v0.4.3 | 30/10/2026 | @PotatoMine725 (issue #67, #83, P1-04 PR A) | Theo ca AISoEasy: trang không phải pricing mà bản raw có giá ký hiệu tiền mà fit không có thì gửi raw; code tách giá niêm yết / khuyến mãi (`promo_split`, `promo_unparsed`, `promo_missing`), lấy tên plan từ heading phía trên khối giá; `quality.conflicts[].field` bỏ hậu tố `.value` / `.evidence` / `.source_id`, field cả mảng thu hẹp về 1 fact hoặc kèm `conflict_too_broad` (thống nhất ở #83). Không đổi schema v0.3. |
