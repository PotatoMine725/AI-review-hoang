# services/worker

Python 3.12 + FastAPI, quản lý bằng **uv**. Cấu trúc và cách mở rộng: `docs/adr/0005-repo-structure-and-extensibility.md`.

```bash
uv sync
uv run uvicorn worker.main:app --reload --port 8000
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest   # giống CI
```

## M1 — crawl (`src/worker/m1/`)

Điểm vào: `worker.m1.crawl.service.crawl_product(url, options, fetcher, store, previous_hashes=...)` trả `CrawlResult`
(`status`, `error_code`, `retryable`, `pages` đủ trường `sources[]` của PKB). Module không biết DB, hàng đợi hay API:
hàng đợi gọi hàm này, ghi `error_message` vào `generation_jobs.error` và tự retry theo `retryable`.
Mã lỗi và quy tắc crawl: `docs/specs/m1-product-intelligence.md` (Quy tắc crawl, Mã lỗi crawl).

| File | Việc |
|---|---|
| `url.py` | `normalize_product_url` (khoá `products.website_url`), `normalize_page_url` |
| `config.py` | `CrawlSettings` (giá trị mặc định bằng spike, đè bằng biến môi trường `M1_CRAWL_<TÊN_HOA>`), `CrawlOptions` (host phụ, bật theo từng product) |
| `crawl/robots.py`, `throttle.py`, `discover.py`, `blocks.py` | robots RFC 9309, ≤ 1 request/giây/host, sitemap + chấm điểm + quota, nhận diện WAF / đăng nhập |
| `crawl/fetcher.py` | adapter Crawl4AI sau interface `PageFetcher` (đổi provider chỉ sửa file này) |
| `crawl/store.py` | `PageStore` + `LocalPageStore`; Supabase Storage cắm vào sau |

### Chạy thật bằng tay

```bash
uv run playwright install chromium     # một lần: cài trình duyệt cho Crawl4AI
uv run python -m worker.m1.crawl https://elevenlabs.io --out <thư mục tạm ngoài repo>
```

Ghi `pages/*.md` và `crawl.json` vào thư mục `--out`. Không commit output.

### Crawl4AI

- Dùng như thư viện (không chạy Docker server), ghim `crawl4ai==0.9.4` như spike. Không bật `enable_stealth`, không đổi User-Agent, không proxy.
- Kéo theo `unclecode-litellm` (fork của litellm, đụng tên module `litellm`) và `patchright`; đã kiểm tra ở ADR-0001.
- License: Apache-2.0 **kèm điều khoản ghi công**; web app phải ghi credit (xem ADR-0001, mục License Crawl4AI).

### Ngôn ngữ trang

`M1_CRAWL_LANGUAGES=en,vi` (mặc định) là các ngôn ngữ được crawl, theo thứ tự ưu tiên. Ngôn ngữ dò theo tiền tố path
(`/vi/`, `/en-us/`); path không có tiền tố coi là `en`. Trang ngôn ngữ khác: `language_not_allowed`. Bản dịch của trang
đã giữ ở ngôn ngữ ưu tiên hơn: `translation_duplicate`.

## M1 — extract 1.4 (`src/worker/m1/extract/`, `llm/`, `pkb/`)

Điểm vào: `await extract_product(crawl_result, page_store, llm)` trả `ExtractResult(data, sources, cost_breakdown,
warnings)`: PKB v0.3 `software` đã validate, `cost_breakdown` v1. Lỗi: `ExtractError` có `code`, `retryable`,
`retry_after` (hết quota ngày) và `cost_breakdown`. Mã lỗi, warning, cách nhận diện 429: đặc tả M1, mục
"Extract 1.4 trong worker".

| File | Việc |
|---|---|
| `llm/client.py` | `LLM.generate_json`: retry 429 RPM / 500 / 503 (5 → 10 → 20 → 40 → 60 s), 429 RPD → `llm_quota_daily`, 1 item chi phí mỗi lần gọi |
| `llm/gemini.py` | nơi duy nhất import `google-genai`; SDK không tự retry |
| `llm/fixture.py` | `LLM_PROVIDER=fixture`: đọc response đã lưu (`LLM_FIXTURE_PATH`), không gọi mạng |
| `llm/quota.py`, `cost.py` | nhận diện RPM / RPD, giờ reset 0h giờ Thái Bình Dương (`tzdata`); `CostItem` theo contract v1 |
| `pkb/models.py`, `validate.py` | model PKB v0.3 port từ spike; kiểm `source_id` có trong `sources` |
| `extract/service.py` | chọn top-k trang, gọi LLM, kiểm evidence, gộp, conflicts, nâng lên v0.3 |

```bash
# Cần GEMINI_API_KEY trong .env. Mỗi lần chạy = 1 lời gọi generate, tính vào 500 RPD của project.
uv run python -m worker.m1.extract <thư mục crawl> --out <thư mục tạm ngoài repo>
```

Ghi `pkb.json` ({data, sources}), `cost_breakdown.json`, `extract.json` (warnings hoặc lỗi). Không commit output.

**Thời gian xấu nhất của 1 lần extract** (đặt timeout job BE theo số này): `LLM_TIMEOUT_S × (1 + số bước của
LLM_RETRY_DELAYS_S) + tổng thời gian chờ`. Với mặc định: 180 s × 6 lần = 1080 s, cộng 135 s chờ (5 + 10 + 20 + 40 +
60) = **1215 s (~20 phút)**. Khi 429 RPM kèm `RetryInfo` ≥ 60 s ở mọi lần, mỗi lần chờ là 60 s: 1080 + 300 =
**1380 s (~23 phút)**. 429 RPD không retry nên kết thúc ngay. Chạy thật 21/10: mỗi lần 1 lời gọi, không retry.
Model PKB là bản port: sửa luật ở `spikes/m1-crawl-extract/schema_v03.py` thì sửa cả `pkb/models.py`
(`tests/m1/test_pkb.py` chạy model trên `docs/specs/pkb/examples/`).

### Test

`uv run pytest` chạy không cần mạng và không cần trình duyệt: `PageFetcher`, HTTP (robots, sitemap) và đồng hồ throttle
được thay bằng fake trong `tests/m1/fakes.py`; LLM dùng `FixtureTransport`; fixture ở `tests/m1/fixtures/`. Fixture 429
(`fixtures/llm/error-429-*.json`) là dữ liệu synthetic: chưa có response 429 thật.

## Bộ chạy job (`src/worker/runner/`)

Tiến trình riêng, tách khỏi API: `uv run python -m worker.runner` (`--once` để xử lý hết job rồi thoát). Cần `.env` có `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` (hoặc `LLM_PROVIDER=fixture`) và `uv run playwright install chromium`.

Nhận job `crawl` ở trạng thái `queued` (cũ nhất trước), claim bằng `UPDATE ... WHERE status='queued'` (nguyên tử, không cần migration), chạy M1 crawl, rồi extract (M1, Gemini, 1 lời gọi/job) → `create_pkb_version` → ghi `pkb_version` và `result_manifest` → `completed`. Lỗi `retryable` được xếp lại `queued` (tối đa `RUNNER_MAX_ATTEMPTS`, chờ lũy thừa 2 từ `RUNNER_RETRY_BACKOFF_S`), còn lại `failed` kèm `error`. Markdown trang lưu ở `WORKER_PAGE_STORE_DIR/<job_id>/pages/` (đặt ngoài repo).

Bước nặng nằm sau Protocol `CrawlStep`/`ExtractStep` (`runner/steps.py`); test dùng fake, không cần trình duyệt hay LLM. **Chưa có:** timeout cho cả job (extract xấu nhất ~20 phút, xem mục extract), dọn job kẹt `running` khi runner chết (bảng chưa có `updated_at`), job `video`, `previous_hashes` giữa các lần crawl.
