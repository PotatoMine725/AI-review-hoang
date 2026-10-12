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

### Test

`uv run pytest` chạy không cần mạng và không cần trình duyệt: `PageFetcher`, HTTP (robots, sitemap) và đồng hồ throttle
được thay bằng fake trong `tests/m1/fakes.py`; fixture ở `tests/m1/fixtures/`.
