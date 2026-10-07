# Spike M1: Crawl → Markdown → JSON

- **Issue:** #6 · **Spec:** `docs/specs/m1-spike-crawl-extract.md` (v1.1) · **Plan:** `docs/plan/m1-spike-crawl-extract.md`
- **Trạng thái:** Xong bước 1 (`crawl.py`, SP-01, SP-02) và bước 2 (`schema.py`, `extract.py`, `run.py`, SP-03…SP-07). Chạy ngày 06/10/2026.

Đây là code spike, chạy độc lập. Không import từ `services/worker` và không chạy trong CI.

> **Lưu ý phụ thuộc (cho ADR-001):** `crawl4ai` 0.9.4 bắt buộc kéo theo `unclecode-litellm` 1.81.13 (bản fork LiteLLM) vào `uv.lock`. Quy tắc "không dùng LiteLLM" áp cho **code**: spike không import nó, mọi lời gọi Gemini đi qua `google-genai` trong `extract.py`. Dependency gián tiếp này **được chấp nhận** vì đã ghim phiên bản và hash trong `uv.lock`; coordinator đã kiểm tra wheel ("pre-compromise fork", không có file `.pth`, hash khớp).
> Điểm trừ của Crawl4AI cho ADR-001: gói nặng ~18 MB, 1 người duy trì, chiếm tên module `litellm` (đụng nếu sau này cài LiteLLM thật).
> Khi lên production: kiểm tra Crawl4AI có bản cài không kéo LiteLLM, và quét dependency trong CI.

## Cách chạy

```bash
cd spikes/m1-crawl-extract
uv sync
uv run crawl4ai-setup          # lần đầu: cài Chromium cho Playwright
uv run python crawl.py         # bước 1: crawl mọi product trong products.json (hoặc: crawl.py claude)
cp .env.example .env           # rồi điền GEMINI_API_KEY
uv run python run.py --dry-run # bước 2: chọn trang, đếm token (count_tokens), in ước tính chi phí; không gọi generate
uv run python run.py           # bước 2: ước tính rồi chạy 2 product × 2 model × 2 mode, ghi pkb + metrics.csv
```

`run.py` luôn in ước tính trước lần gọi đầu và dừng nếu chi phí xấu nhất > `BUDGET_USD` (đặt $0.20 cho lần chạy v0.2, trong `config.py`; lần chạy v0.1 dùng $2).
Lần chạy v0.2: `uv run python run.py --models gemini-3.5-flash-lite --modes batch`. Product không crawl được (0 trang) bị bỏ qua.
`uv run python export_schema.py` xuất JSON Schema của PKB v0.2 ra `docs/specs/pkb/`.
Thêm `--no-cache` để gọi lại LLM dù nội dung không đổi; `--models` / `--modes` để chạy 1 phần.

Output nằm trong `output/<slug>/`:
- `crawl.json` (commit): danh sách trang lấy và bỏ kèm lý do, log từng request, kết quả robots.txt, `content_hash`.
  Để file gọn, trang bị bỏ vì robots, bị chặn, trùng hoặc redirect được ghi đủ; `over_limit` chỉ ghi 50 trang điểm cao nhất; lý do khác chỉ đếm trong `skipped_counts`.
- `pages/<source_id>-<page_type>-<slug>.md` (không commit): markdown đã lọc (`fit_markdown`). File `.raw.md` là markdown chưa lọc.
- `pkb.<model>.json` (commit): PKB v0.2 của mode `batch`, gồm `data` (cột `product_knowledge.data`), `sources` (cột `product_knowledge.sources`) và `meta` (số đo của spike).
- `llm_cache/` (không commit): kết quả từng lời gọi LLM, khoá theo `content_hash` (SP-07).
- `output/metrics.csv` (commit): 1 dòng / product × model × mode của lần chạy v0.2 (có cột `schema_version`).
- `output/v0.1/` (commit): kết quả v0.1 (`metrics.csv`, `pkb.*.json` cả 2 mode), giữ để so sánh. Schema v0.1 nằm trong git history.

## Demo

`demo.py` đọc PKB v0.2 (`output/*/pkb.*.json`, `metrics.csv`; không đọc được PKB v0.1 trong `output/v0.1/`) và sinh 1 trang HTML tĩnh `output/demo.html` để trình bày. Không gọi LLM, không crawl, không cần mạng, chỉ dùng thư viện chuẩn.

```bash
uv run python demo.py                               # PKB mode batch của gemini-3.5-flash-lite
uv run python demo.py --model gemini-3.1-flash-lite # đổi model
```

Mở `output/demo.html` bằng trình duyệt. File này bị gitignore. Trang có: luồng + tổng chi phí, PKB từng product (kèm evidence và link nguồn), bảng `metrics.csv` (hàng `batch` nổi bật), bài học về giá lấy từ mục "Đề xuất cho đặc tả v0.2".
PKB không ghi cờ "evidence khớp nguồn" theo từng fact, nên trang chỉ hiện tỉ lệ `evidence_in_source` của cả PKB.

## Crawl lịch sự (NFR-05)

| Quy tắc | Cách làm | Bằng chứng trong `crawl.json` |
|---|---|---|
| Tôn trọng `robots.txt` | Tự tải `robots.txt` của **từng host** bằng UA của dự án và parse theo RFC 9309 (`parse_robots`). Hỗ trợ wildcard `*`/`$`; rule khớp dài nhất thắng. Chọn nhóm `User-agent` của dự án, nếu không có thì dùng nhóm `*`. Lỗi 401/403/429/5xx → không crawl host đó. Không dùng `urllib.robotparser` vì nó không hỗ trợ wildcard và lấy rule khớp đầu tiên | `robots.<host>` (`group`, `rules`, `crawl_delay`), `pages[].robots_allowed` + `robots_rule`, `skipped[].reason = robots_disallow` |
| ≤ 1 request/giây/host | Mọi request (robots, sitemap, trang) chạy tuần tự qua 1 `Throttle`, cách nhau ≥ max(1.0 s, `Crawl-delay`). Không dùng `arun_many` (mặc định chạy song song 5 luồng). `max_retries=0`, nên không có request ẩn đi vòng qua throttle | `requests[]`, `min_observed_interval_s` |
| ≤ 30 trang | `MAX_PAGES = 30` tính cả trang lỗi, trùng hoặc bị chặn, và cả trang của host phụ | `pages_used`, `requests[kind=page]` |
| UA định danh | `AIReviewContentFactory-Spike/0.1 (+https://github.com/PotatoMine725/AI-review-BE; M1 research spike)` | `user_agent` |
| Chỉ trong domain gốc | Host của URL product. Product có `"allow_subdomains": true` (chỉ Claude) nhận thêm `*.claude.com`, tối đa 5 trang (`MAX_EXTRA_HOST_PAGES`), chỉ trang loại faq / pricing (`EXTRA_HOST_TYPES`). Dreamina không bật, vì domain gốc của `dreamina.capcut.com` là `capcut.com` (sản phẩm khác) | `allowed_hosts`, `limits`, `skipped_counts.out_of_scope` |
| Không vượt chặn | Không bật `magic`, `simulate_user`, `override_navigator`, `enable_stealth`, không đổi UA ngẫu nhiên, không proxy. Gặp 403/429, trang thử thách Cloudflare hoặc bị chuyển tới trang login → dừng product đó | `blocked` |

Đã kiểm tra giá trị mặc định của crawl4ai 0.9.4 (đọc bằng `inspect.signature`): `BrowserConfig.enable_stealth=False`, `user_agent_mode=''`, `proxy_config=None`;
`CrawlerRunConfig.magic=False`, `simulate_user=False`, `override_navigator=False`, `max_retries=0`, `fallback_fetch_function=None`, `proxy_rotation_strategy=None`.
`crawl4ai-setup` có cài Patchright (bản Playwright chống phát hiện), nhưng chỉ được dùng khi bật `enable_stealth`. Spike không bật.

"Request" ở đây là 1 lần mở trang (navigation) hoặc 1 lần tải robots/sitemap. Tài nguyên con do trình duyệt tự tải (JS, ảnh) không được tính.
Spike tắt cache của Crawl4AI (`CacheMode.BYPASS`) để thời gian crawl và log request là số thật.

## Cách chọn trang (SP-01)

1. Đọc `robots.txt` → lấy sitemap (nếu không có thì thử `/sitemap.xml`). Sitemap index: đọc tối đa 5 sitemap con, ưu tiên sitemap không phải blog/news.
2. Crawl trang chủ trước tiên để kiểm tra bot có bị chặn không. Link nội bộ của mỗi trang đã crawl được thêm vào frontier mà không tốn thêm request.
3. Gán `page_type` (pricing, features, docs, faq, changelog, compare, other) bằng regex trên path và anchor text ngắn (≤ 4 từ). Trang ở host phụ như `support.*` được tính là faq. Điểm bị trừ theo độ sâu path và khi slug dài hơn 3 từ (thường là bài viết SEO).
4. Bỏ qua: link ngoài domain, file tĩnh, bản dịch (`/fr/…`, `/ja-jp/…`), trang login/legal/careers/blog/marketplace.
5. Chọn trang điểm cao nhất theo hạn mức từng loại (pricing 4, features 10, docs 6, faq 4, compare 3, changelog 2). Còn slot thì lấp theo điểm.

## Kết quả bước 1 (06/10/2026)

| Product | robots.txt | Trang tìm thấy | Trang lấy | Trang bị bỏ (lý do chính) | Khoảng cách request nhỏ nhất | Thời gian crawl |
|---|---|---|---|---|---|---|
| Claude | `claude.com`: nhóm `*` `Allow: /`. `support.claude.com`: chặn `/not-authorized`, `/not-found`. `platform.claude.com`: chặn `/api/` | 3 770 | 29 (25 `claude.com`, 2 `support`, 2 `platform`) | excluded_path 1 818, locale 1 284, over_limit 566 | 1.016 s | 198 s |
| Dreamina | 200; không có nhóm `*` hay nhóm cho UA dự án → được phép | 5 139 | 27 | over_limit 3 139, low_score 1 934, not_found 1 | 1.000 s | 165 s |

Không host nào đặt `Crawl-delay`. Cả 56 trang đã lấy đều có `robots_allowed: true`. Mỗi product mở đúng 30 trang (tính cả trang trùng / 404).
robots.txt của Dreamina chỉ chặn nhóm Baidu, 360, Sogou (`Disallow: /`); nhóm Googlebot… và nhóm bot AI (GPTBot, ClaudeBot…) đều `Allow: /`.

Số trang lấy theo `page_type`:

| Product | other (home) | pricing | features | docs | faq | compare | changelog |
|---|---|---|---|---|---|---|---|
| Claude | 1 | 4 | 14 | 6 | 3 | 1 | 0 |
| Dreamina | 1 | 4 | 12 | 6 | 1 | 3 | 0 |

Không product nào bị chặn bot hay bắt đăng nhập. Không trang nào bị chặn theo vùng, nhưng giá của Dreamina hiển thị theo vùng (xem nhận xét 3). Chi tiết từng trang có trong `output/<slug>/crawl.json`.

### Nhận xét

1. **Render SPA được.** Trang chủ Dreamina (SPA) ra 76 K ký tự raw markdown, có giá và tên model. Cấu hình: `wait_until="domcontentloaded"`, chờ thêm 3 giây, `scan_full_page=True`. Không dùng `networkidle` vì hay bị treo ở SPA.
2. **`fit_markdown` làm mất dữ liệu giá.** `PruningContentFilterLXML` bỏ các thẻ giá vì chúng ít chữ. Ở `claude.com/pricing`, bản raw có đủ thẻ Free ($0), Pro ($17/tháng khi trả năm, $20 khi trả tháng), Max (từ $100) và bảng giá API ($/MTok). Bản fit chỉ còn giá Enterprise.
   → Bước 2 gửi **raw** markdown cho trang pricing, **fit** cho trang khác.
3. **Giá Dreamina theo vùng IP.** Máy chạy ở Việt Nam nên trang pricing hiện VND (`VND10000 = 107 credits`), không phải USD. Spike chấp nhận và ghi `currency = VND`; đây là **giá theo vùng IP (VN)**, không phải giá USD người dùng ở Mỹ/EU thấy. Không đổi vùng bằng proxy. Khi đối chiếu tay (AC-04) phải so cùng vùng. Pipeline thật cần ghi vùng / tiền tệ lúc crawl.
4. **FAQ và changelog.** FAQ của Claude nằm ở `support.claude.com`: bật `allow_subdomains` lấy được trang chủ help center và 1 bài viết. Lần chạy đầu không giới hạn loại trang thì 4/5 slot host phụ bị `academy`, `code`, `platform.claude.com` (docs) chiếm, nên giờ host phụ chỉ nhận trang faq / pricing. Cả 2 site đều không có trang changelog trên host gốc.
5. **Trang SEO lọt bộ chấm điểm.** Dreamina có hàng nghìn trang `/resource/…`, `/tools/…`, `/create/…` sinh ra cho SEO. Chấm điểm bằng regex trên URL vẫn để lọt: `/tools/sora-2`, `/tools/veo-3`, `/tools/age-ai` (features, trang về model của hãng khác), `/resource/grok-vs-chatgpt`, `/create/childhood-vs-now` (compare), `/resource/chatgpt-image-generator-for-saas-pricing-page-graphics` (pricing).
   Khoảng 8/27 trang Dreamina là nhiễu loại này (thêm `/resource/short-form-advertisement-guide`, `/resource/tips-tutorials`); 2 trong số đó lọt vào top 10 gửi LLM (`/tools/age-ai`, `/tools/sora-2`). Cách cải thiện: phạt path `/resource/`, `/create/`; hoặc thêm 1 bước LLM rẻ phân loại tiêu đề trang trước khi crawl.
6. **Thời gian crawl so với NFR-01 (≤ 5 phút / product 30 trang, p95).** Claude 198 s, Dreamina 165 s: đạt, nhưng chỉ còn dư khoảng 100 s cho bước trích xuất. Thời gian chủ yếu là render: trung bình 6.4 s/trang (Claude) và 5.1 s/trang (Dreamina), trong đó 3 s là chờ cố định cho SPA, cộng throttle 1 request/giây.
   Đo trên 1 máy, 1 lần chạy, nên chưa phải p95. Cách giảm: crawl song song nhiều host (mỗi host vẫn ≤ 1 request/giây), chỉ chờ 3 s với trang SPA, dùng HTTP thường cho trang tĩnh.
7. **2 trường hợp báo nhầm "bị chặn" đã sửa.**
   - Trang `/tools/video` của Dreamina trả HTTP 404 nhưng bị Crawl4AI 0.9.4 gắn nhãn "Blocked by anti-bot protection" vì ít chữ. Spike kiểm tra 404/410 trước nên giờ ghi đúng là `not_found`.
   - Trang `claude.com/hard-questions` bị bộ dò của spike báo chặn vì chữ `captcha` nằm trong CSS của form HubSpot. Giờ spike chỉ dò marker Cloudflare (`cf-chl`, `challenge-platform`) trong HTML và câu thông báo chặn trong nội dung hiển thị, và chỉ khi trang ngắn (< 3 000 ký tự).
8. **`content_hash` ổn định khi tải lại.** Raw markdown chứa token đổi theo mỗi lần tải (`claude.ai/redirect/claude_com.v1.<uuid>/…`) và ảnh lazy-load đổi vị trí. Hash bỏ ảnh và URL đích của link trước khi băm, lưu cả `raw_hash` và `fit_hash`.
   Đã tải lại `claude.com/pricing`, trang pricing và trang chủ Dreamina: cả 2 hash đều không đổi. Bước 2 dùng hash này cho cache (SP-07).

## Bước 2: trích xuất PKB (SP-03…SP-07)

- **Schema** (`schema.py`): `identity` (kèm `version`, `models[]`), `pricing` (`plans`, `free_plan`, `trial_days`, `currency`), `features`, `use_cases`, `limitations`, `sources`.
  Mọi fact có `origin: "crawled"`, `source_id`, `evidence` ≤ 200 ký tự. LLM chỉ điền phần `PKBExtract`; `sources` và `meta` do code điền.
- **Adapter** (`extract.py`): mọi lời gọi Gemini qua `call_gemini` (structured output: `response_mime_type="application/json"`, `response_json_schema`), `count_tokens` để ước tính. Token lấy từ `usage_metadata`: input = `prompt_token_count`, output = `candidates_token_count + thoughts_token_count` (thinking token tính giá output).
- **Cấu hình** (`config.py`): model, bảng giá (tra 06/10/2026), số trang, ngân sách.
- **Input cho LLM:** trang pricing dùng raw, trang khác dùng fit. Trước khi gửi, bỏ ảnh và URL của link, giữ chữ (raw `claude.com/pricing` giảm từ 39 K xuống 25 K ký tự).
- **Mode (SP-06):** `per_page` = 1 lời gọi / trang cho **mọi trang đã crawl** (29 Claude, 27 Dreamina), rồi gộp (bỏ trùng theo tên); `batch` = gom **10 trang điểm cao nhất** vào 1 lời gọi. Chặn trên output: 4 096 token/lời gọi (`per_page`), 16 384 (`batch`), gồm cả thinking token.
  Kết quả bị cắt (`finish_reason` khác `STOP`) hoặc sai schema được ghi vào `_errors` và cột `truncated` / `schema_errors`, và không được cache.
- **Chi phí:** `cost_usd` tính theo giá gói trả phí trong `config.py`. Nếu key thuộc gói miễn phí thì số tiền thật bị tính là $0; số trong bảng là chi phí khi lên gói trả phí.
- **Kiểm tra evidence:** ngoài validate Pydantic, `run.py` kiểm tra evidence có xuất hiện nguyên văn trong trang nguồn (cột `evidence_in_source`).
- **SP-07:** cache theo (model, phiên bản prompt + schema, `content_hash` các trang). Chạy lại khi nội dung không đổi → 0 lời gọi LLM.

- **Sửa evidence quá dài:** Gemini không luôn tuân `maxLength` trong JSON schema: 10 / ~1 050 fact có evidence > 200 ký tự (đều ở mode `per_page`).
  `repair_evidence` cắt về ≤ 200 ký tự tại ranh giới từ (vẫn là trích nguyên văn); số fact bị cắt ở cột `evidence_truncated`. `schema_valid` là kết quả validate **sau** bước này.

## Kết quả bước 2 (06/10/2026)

Ước tính trước lần gọi đầu (`run.py --dry-run`, đếm bằng `count_tokens`): dự kiến $0.47, chặn trên $1.16 (ngân sách $2). Smoke test 1 lời gọi: schema được chấp nhận, `finish_reason=STOP`.

`output/metrics.csv` (giá gói trả phí; chi phí theo product = 1 dòng):

| Product | Model | Mode | Lời gọi | Trang gửi | Token vào | Token ra | Chi phí | Thời gian LLM | Schema | Plan | Fact | Evidence khớp nguồn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude | 3.1-flash-lite | batch | 1 | 10 | 22 354 | 2 863 | **$0.0099** | 7.1 s | ✔ | 9 | 40 | 100 % |
| Claude | 3.5-flash-lite | batch | 1 | 10 | 22 354 | 2 706 | **$0.0135** | 6.7 s | ✔ | 9 | 34 | 100 % |
| Claude | 3.1-flash-lite | per_page | 29 | 29 | 69 855 | 33 321 | $0.0674 | 107.8 s | ✔ (1 evidence cắt) | 22 | 308 | 98.7 % |
| Claude | 3.5-flash-lite | per_page | 29 | 29 | 69 855 | 27 363 | $0.0894 | 101.6 s | ✔ (2 cắt) | 13 | 221 | 98.6 % |
| Dreamina | 3.1-flash-lite | batch | 1 | 10 | 22 589 | 1 901 | **$0.0085** | 5.7 s | ✔ | 4 | 23 | 95.7 % |
| Dreamina | 3.5-flash-lite | batch | 1 | 10 | 22 589 | 2 442 | **$0.0129** | 6.4 s | ✔ | 4 | 26 | 92.3 % |
| Dreamina | 3.1-flash-lite | per_page | 27 | 27 | 70 970 | 31 637 | $0.0652 | 108.1 s | ✔ (2 cắt) | 13 | 275 | 97.8 % |
| Dreamina | 3.5-flash-lite | per_page | 27 | 27 | 70 970 | 35 372 | $0.1097 | 122.6 s | ✔ (2 cắt) | 11 | 248 | 98.8 % |

- Cả 2 model trả `thoughts_token_count = 0` với cấu hình mặc định (không thinking), `finish_reason=STOP` ở mọi lời gọi, 0 lời gọi bị cắt.
- **SP-07:** chạy lại `run.py` khi nội dung không đổi → 116/116 lời gọi lấy từ cache, chi phí API $0 (cột `cache_hits`).
- **Tổng chi phí API thật của spike: ≈ $0.40** (lần chạy đủ $0.376 + 2 smoke $0.003 + gọi lại 7 trang lỗi evidence trước khi có bước sửa $0.025). Đạt AC-06 (≤ $2).
  Số tiền tính theo giá gói trả phí; nếu key thuộc gói miễn phí thì số tiền thật bị trừ là $0.

### Đối chiếu giá và plan (AC-04)

Coordinator đọc 2 trang giá (06/10/2026, IP Việt Nam) và đối chiếu, người dùng đã duyệt. Kết quả ở cột `price_plan_correct` và `price_plan_note` của `metrics.csv`:

| Product | Model | Mode | Đúng? | Ghi chú |
|---|---|---|---|---|
| Claude | 3.1-flash-lite | batch | ✘ | Pro trả năm = 16.67 (tự tính), trang ghi $17 |
| Claude | 3.5-flash-lite | batch | ✔ | Đúng giá. Pro trả năm ghi `billing_period = year` nhưng 17 là giá/tháng, nên period mơ hồ |
| Claude | 3.1-flash-lite | per_page | ✘ | Lẫn giá API theo token vào plans, dòng rác (Paid plans, Personal) |
| Claude | 3.5-flash-lite | per_page | ✘ | Lẫn mục không phải plan (Paid plans, Team không giá, K-12) |
| Dreamina | 3.1-flash-lite | batch | ✘ | Advanced, Ultra lấy giá tháng đầu khuyến mãi thay vì giá niêm yết (4.145.379; 13.557.213) |
| Dreamina | 3.5-flash-lite | batch | ✘ | Như trên |
| Dreamina | 3.1-flash-lite | per_page | ✘ | Lẫn giá Seedance/giây, giá US $1.50, gán 4.145.379 cho Standard |
| Dreamina | 3.5-flash-lite | per_page | ✘ | Lẫn giá Seedance/giây và USD, plan trùng lặp |

**Chỉ 1/8 đạt** (Claude, 3.5-flash-lite, batch). Mode `batch` tốt hơn hẳn `per_page`: lỗi của batch là 1 con số (tự tính, hoặc chọn giá khuyến mãi), còn per_page lẫn cả mục không phải plan. Lỗi Dreamina ở batch nằm ở schema (chỉ 1 trường `price`), không ở model, xem đề xuất 1.

Chi tiết từng dòng so với markdown đã crawl:

| Product | Trên trang (06/10/2026) | 3.1-flash-lite batch | 3.5-flash-lite batch |
|---|---|---|---|
| Claude | Free 0 $; Pro 17 $/tháng trả năm (200 $ trả trước) hoặc 20 $ trả tháng; Max từ 100 $; Team Standard 20 $ / 25 $, Premium 100 $ / 125 $ mỗi seat; Enterprise US$20/seat/tháng trả năm | 9/9 dòng, nhưng Pro trả năm ghi `price = 16.67` (tự tính 200/12) thay vì 17; `currency` từng plan để trống | 9/9 dòng, giá đúng, có `currency = USD` từng plan, giữ ghi chú "200 $ billed up front" |
| Dreamina (VND, giá theo vùng IP VN) | Basic VND390000/tháng; Standard VND939000/tháng; Advanced VND 2,487,227 tháng đầu rồi VND 4,145,379/tháng; Ultra VND 8,134,328 tháng đầu rồi VND 13,557,213/tháng | 4/4 plan, `price` của Advanced/Ultra là giá tháng đầu (giá thường chỉ có trong `price_text`); `currency` từng plan trống | Giống 3.1 nhưng có `currency = VND` từng plan |

Lưu ý:
- Trang giá Dreamina **không có thẻ plan Free**; cả 2 model ghi `free_plan = true` từ trang chủ ("Dreamina provides free daily credits…"), tức là có dùng miễn phí bằng credit hằng ngày, không phải 1 plan.
- Trang giá Dreamina có tab Yearly / Quarterly / Monthly / 1-month; crawl chỉ thấy tab mặc định (giá tháng). Muốn lấy đủ phải bấm tab (`js_code` của Crawl4AI), spike không làm.
- **Mode `per_page` nhiễu hơn nhiều:** trang không phải pricing sinh plan giả ("Paid plans", "Team" không giá), giá API theo token / giá theo giây bị ghi thành plan dù prompt dặn bỏ, và trang chủ Dreamina sinh plan sai tên ("Standard" với giá của Advanced). Gộp bằng luật đơn giản không lọc hết.
- 3 evidence ở Dreamina batch không khớp nguyên văn trang được gán (có thể gán sai `source_id` hoặc ghép 2 câu).

## Trả lời 3 câu hỏi của spike

**1. Crawl4AI có lấy đủ trang quan trọng và render được SPA không?** Phần lớn có.
Render SPA được (Dreamina trang chủ 76 K ký tự, đủ giá và model). Lấy được pricing (4 trang mỗi product), features, docs; FAQ của Claude cần mở sang `support.claude.com`. Thiếu: changelog (2 site không có trên host gốc), nội dung sau tab / nút bấm (giá Dreamina theo năm).
Hai điểm cần xử lý khi đưa vào pipeline: `fit_markdown` làm rơi thẻ giá (phải dùng raw cho trang pricing) và chấm điểm bằng regex URL để lọt trang SEO (~8/27 trang Dreamina). Bộ nhận diện anti-bot sẵn có của Crawl4AI báo nhầm 404 là "bị chặn".

**2. Model Flash-Lite nào trích giá và tên plan đúng hơn, rẻ hơn?**
`gemini-3.1-flash-lite` rẻ hơn ~30 % (batch: $0.0085–0.0099 so với $0.0129–0.0135 mỗi product), cùng số plan và thời gian tương đương.
`gemini-3.5-flash-lite` đúng hơn ở chi tiết: giữ giá nguyên văn (17 $, không tự tính 16.67), điền `currency` từng plan. Cả hai cùng lỗi lấy giá tháng đầu khuyến mãi làm `price` ở Dreamina.
Đề xuất cho ADR-002: dùng **3.5-flash-lite cho trang pricing** (sai giá đắt hơn chênh lệch ~$0.004/product), cân nhắc 3.1 cho trang features nếu cần tiết kiệm. Cần golden set để kết luận chắc chắn; mẫu hiện chỉ 2 product.

**3. Chi phí LLM mỗi product? Có đạt ≤ $0.05 (NFR-02) không?**
- Mode `batch` (10 trang, 1 lời gọi): **$0.008–0.013 / product → đạt NFR-02** với dư địa ~4×.
- Mode `per_page` (mọi trang, 27–29 lời gọi): **$0.065–0.110 / product → không đạt**.
- Hai mode khác nhau ở 2 điểm cùng lúc (số lời gọi **và** số trang), nên tách tác động bằng kết quả `per_page` đã cache của đúng 10 trang mà `batch` dùng (không tốn thêm API):

  | Product | Model | per_page, 10 trang | batch, 10 trang | Gom 1 lời gọi | Thêm trang (10 → 27–29) |
  |---|---|---|---|---|---|
  | Claude | 3.1-flash-lite | $0.0256 (in 25 162 / out 12 870) | $0.0099 (in 22 354 / out 2 863) | ÷ 2.6 | × 2.6 |
  | Claude | 3.5-flash-lite | $0.0355 | $0.0135 | ÷ 2.6 | × 2.5 |
  | Dreamina | 3.1-flash-lite | $0.0254 | $0.0085 | ÷ 3.0 | × 2.6 |
  | Dreamina | 3.5-flash-lite | $0.0464 | $0.0129 | ÷ 3.6 | × 2.4 |

  Gom vào 1 lời gọi chỉ giảm input ~11 % (system prompt + schema lặp lại), phần tiết kiệm chính là **output**: mỗi trang tự sinh lại identity, plan, feature (11–15 K token ra cho 10 trang so với 2–3 K). Số trang gửi đi có tác động ngang bằng.
  Ngay cả `per_page` trên 10 trang cũng gần chạm ngưỡng ($0.025–0.046).
- Cách giảm hiệu quả nhất, theo thứ tự đã đo: (1) gom trang vào 1 lời gọi (÷ 2.6–3.6, chủ yếu nhờ giảm token ra); (2) chỉ gửi top-k trang theo điểm (÷ 2.4–2.6 khi đi từ ~28 xuống 10 trang); (3) bỏ ảnh và URL của link trước khi gửi (raw trang pricing Claude giảm 36 % ký tự); (4) cache theo `content_hash` để lần cập nhật sau chỉ gọi LLM cho trang đổi (SP-07, lần chạy lại $0).
- **NFR-01** (≤ 5 phút / product): crawl 165–198 s + trích xuất batch 6–7 s → **đạt** (~3.4 phút). Mode `per_page` chạy tuần tự thêm 102–123 s → Claude ~5.1 phút, **không đạt**.

## Đề xuất cho đặc tả v0.2

1. **Tách giá niêm yết và giá khuyến mãi trong schema pricing.** Hiện `Plan` chỉ có 1 trường `price`, nên ở Dreamina cả 2 model ghi giá tháng đầu khuyến mãi vào `price` (giá thường chỉ còn trong `price_text`). Đề xuất thêm trường riêng, vd. `list_price` (giá niêm yết) và `promo_price` kèm `promo_terms` (điều kiện, vd. "tháng đầu").
2. **Prompt cấm model tự tính hay quy đổi giá, chỉ chép nguyên văn.** `gemini-3.1-flash-lite` tự chia giá năm thành 16.67 thay vì chép "17 $" như trên trang. Giá số phải là con số in trên trang; muốn quy đổi (năm → tháng, VND → USD) thì code làm sau, có ghi nguồn.
3. **Mode `batch` là mặc định.** Mode này đạt NFR-01 và NFR-02 ($0.008–0.014 / product, ~3.4 phút), còn `per_page` thì không đạt và sinh plan nhiễu (xem câu 3 và mục đối chiếu giá).
4. **`period` bắt buộc và tách nghĩa.** Spike đã bắt buộc trường này (tên `billing_period`), nên cả 8 file đều có giá trị, nhưng nghĩa bị lẫn: Pro "17 $ / tháng, trả theo năm" ghi `price = 17`, `billing_period = year`, nên không biết 17 là giá của kỳ nào. Đề xuất 2 trường bắt buộc: `price_unit` (giá tính cho: tháng, năm, seat/tháng…) và `billing_cycle` (trả tháng / trả năm / 1 lần). Không cho giá trị `unknown` ở trang pricing (3/4 file mode `per_page` có 2–5 dòng `unknown`).
5. **Tách plan trả phí khỏi giá API và giá theo đơn vị.** Giá theo token, theo giây video (Seedance), theo credit không phải plan nhưng vẫn bị ghi vào `plans` ở mode `per_page`. Đề xuất mục riêng, vd. `pricing.usage_prices` (đơn vị, giá, tiền tệ), và prompt chỉ cho đưa vào `plans` các gói đăng ký.
6. **Ghi lại tab / chu kỳ mặc định của trang giá.** Crawl chỉ thấy tab đang mở (Dreamina mở tab Monthly; còn Yearly, Quarterly, 1-month). PKB cần ghi trang hiển thị chu kỳ nào và còn tab nào chưa lấy (vd. `pricing.default_view`, `pricing.other_views`), để biết giá đã đủ hay chưa.

## Kết quả v0.2

Chạy ngày 07/10/2026. Schema PKB v0.2 (`schema.py`), prompt có 5 quy tắc giá + 1 ví dụ (`extract.py`). Chỉ chạy `gemini-3.5-flash-lite`, mode `batch`, 10 trang/product. Không dùng lại cache v0.1 vì prompt và schema đổi.

**Gamma không crawl được.** `GET https://gamma.app/robots.txt` (UA của dự án) trả `403`, `server: cloudflare`, `cf-mitigated: challenge`, `cf-ray: a46b266308fbdd4b-HKG`, body là trang HTML của app. Đây là trang thử thách của Cloudflare WAF, không phải robots.txt. Crawler dừng ở trang chủ, 0 trang. Không đổi UA, không retry, không dùng proxy. `crawl.py` nay ghi lý do `waf_challenge` (không ghi "robots.txt không cho phép"). `output/gamma/crawl.json` được sửa tay theo kết quả chẩn đoán này, không request lại. Gamma đã nhận 3 request, cả 3 đều 403 (robots.txt, sitemap.xml trong lần crawl, và 1 lần chẩn đoán). Golden Facts của Gamma chưa có trong repo (qa-log #11): **chờ đối chiếu với Golden Facts**.

Đối chiếu giá (AC-04 v0.2): so từng plan trong PKB mới với markdown raw của trang pricing đã crawl (`pages/*.raw.md`), không mở web lần 2. Vì thế kết quả chỉ chứng minh "PKB đúng với những gì crawler thấy", chưa chứng minh "đúng với website".

| Product | v0.1 (3.5-flash-lite, batch) | v0.2 (3.5-flash-lite, batch) |
|---|---|---|
| Claude | Đúng giá, nhưng Pro trả năm ghi `billing_period=year` cho giá 17 $/tháng (mơ hồ) | **Đúng 9/9 plan**: Pro `17, month, yearly` và `20, month, monthly`; Team, Enterprise tính theo `seat_month`; 16 `usage_prices` khớp trang |
| Dreamina | Sai: Advanced, Ultra lấy giá tháng đầu khuyến mãi làm giá chính | **Đúng 4/4 plan**: Advanced `4.145.379` (promo `2.487.227`, "first month"), Ultra `13.557.213` (promo `8.134.328`) |
| Gamma | chưa chạy | Không có PKB (WAF). Chờ Golden Facts |
| Chi phí / product | $0.0135 / $0.0129 | $0.0195 / $0.0129 |
| Evidence khớp nguyên văn | 1.00 / 0.92 | 1.00 / 0.81 |

Số liệu: `price_plan_correct` 2/2 product đã chạy (v0.1: 1/2 ở cùng model + mode, 1/8 cả ma trận). Mẫu nhỏ, chưa phải NFR-03 (cần golden set 10 product). Chi phí API thật của lần chạy: **$0.0324** (ngân sách $0.20). Schema hợp lệ 2/2, 0 fact thiếu `source_id` hoặc `evidence`.

**Lỗi còn lại, không làm đẹp:**
1. Dreamina `other_views` rỗng dù trang có tab Yearly / Quarterly / 1-month. Quy tắc 5 chưa đạt. Dreamina cũng không có dòng plan Free (trang không in giá cho Free).
2. Claude `other_views` ghi các tab đối tượng (Developer, Team & Enterprise, API), không phải chu kỳ. Plan Team và Enterprise vẫn được lấy.
3. Claude "Max" chỉ có 1 dòng `From 100 $`: trang pricing không in giá riêng cho Max 5x và Max 20x.
4. Dreamina `evidence_in_source` giảm từ 0.92 xuống 0.81 (4 trong 21 fact có evidence không tìm thấy nguyên văn). Chưa tìm nguyên nhân (không so được từng fact với v0.1, vì khác schema).
5. `region = VN` và `locale = en-US` là hằng số đặt tay trong `config.py` (`CRAWL_REGION`, `CRAWL_LOCALE`), crawler chưa đo vùng IP và locale thật.
6. `price_unit` và `billing_cycle` chỉ cho phép null khi `list_price` null (plan "Contact sales"). Validator của `Plan` bắt buộc cả hai khi có giá. Spec M1 chưa nói rõ trường hợp này.
7. Chỉ 2 product, 1 lần chạy mỗi product. Chưa đo độ ổn định giữa các lần chạy.

## Acceptance criteria

- [x] AC-01: 2/2 product ra markdown; `crawl.json` ghi robots.txt từng host, 30 lần mở trang / product, khoảng cách request nhỏ nhất ≥ 1.0 s.
- [x] AC-02: 8/8 file `pkb.*.json` hợp lệ theo `schema.PKB` (sau bước cắt evidence quá dài, xem trên).
- [x] AC-03: 0 fact thiếu `source_id` hoặc `evidence` (schema bắt buộc); 92–100 % evidence khớp nguyên văn trang nguồn.
- [x] AC-04: đã đối chiếu tay với website (06/10/2026, IP VN) và điền `price_plan_correct` + `price_plan_note`: 1/8 đúng (xem mục đối chiếu giá).
- [x] AC-05: `metrics.csv` có 8 dòng = 2 product × 2 model × 2 mode.
- [x] AC-06: tổng chi phí API ≈ $0.40 ≤ $2.
- [x] AC-07: `.env` bị gitignore, `.env.example` chỉ có `GEMINI_API_KEY=`.
- [x] AC-08: README trả lời 3 câu hỏi (mục trên).
