# Prompt: T2 (US-02) — đưa crawl từ spike vào `services/worker`, kèm hàm chuẩn hoá URL (phần AI của T1)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #42 (US-02), #41 (US-01, phần chuẩn hoá URL), #59 (chia việc sprint 1) · **Branch:** `feat/m1-worker-crawl` (tạo từ `origin/dev` mới nhất)
- **Phụ thuộc:** không cần DB, hàng đợi hay API. Các phần đó của BE (T0, ADR hàng đợi) sẽ gọi vào module này sau.

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là AI dev, nền C#/.NET, mới với Python: giải thích ngắn, đúng trọng tâm, comment code bằng tiếng Việt ngắn.

## Đọc trước
- `CLAUDE.md`, `docs/README.md`, `docs/adr/0005-repo-structure-and-extensibility.md` (provider sau adapter, không dựng trước cấu trúc chưa dùng).
- `docs/adr/0001-crawl-tool.md` (Crawl4AI như thư viện, mục License: điều khoản ghi công).
- `docs/specs/m1-product-intelligence.md`: 1.1 Intake (chuẩn hoá URL), 1.2 Discover & Crawl, **Quy tắc crawl** (robots RFC 9309, WAF, `login_redirect`), FR-02, NFR-01, NFR-04, NFR-05.
- `docs/specs/pkb/README.md` mục bảng `sources[]` (trường mỗi trang nguồn).
- Issue #42 (AC của US-02), #41 (AC trùng URL), #59 (comment của @VV6505 ngày 11/10).
- **Code nguồn:** `spikes/m1-crawl-extract/crawl.py` (739 dòng, đã chạy thật trên Claude, Dreamina, ElevenLabs; Gamma ra `waf_challenge`). Đây là bản để port, **giữ nguyên hành vi**, chỉ tách module và bỏ phần chỉ dành cho spike (đọc `products.json`, in báo cáo, ghi `output/`).
- `services/worker/pyproject.toml`, `.github/workflows/worker.yml` (CI: `uv sync --locked`, ruff, ruff format, pyright).

## Nhiệm vụ

### 1. Cấu trúc (đề xuất, trình bày lại trước khi làm)
```
services/worker/src/worker/m1/
  url.py              # chuẩn hoá URL product (T1) + URL trang (dùng lại trong crawl)
  crawl/
    errors.py         # mã lỗi job + lý do bỏ qua trang (bảng ở mục 3)
    robots.py         # parse robots.txt RFC 9309, quyết định allow/disallow
    throttle.py       # ≤ 1 request/giây/host
    discover.py       # sitemap + chấm điểm link + phân loại page_type + quota theo loại
    fetcher.py        # adapter Crawl4AI (render JS, raw + fit markdown); interface để test thay bằng fake
    store.py          # PageStore (interface) + LocalPageStore (ghi thư mục). Supabase Storage làm sau
    service.py        # crawl_product(url, options, fetcher, store) -> CrawlResult
    __main__.py       # CLI chạy tay: uv run python -m worker.m1.crawl <url> --out <dir>
services/worker/tests/m1/...   # test + fixtures
```
- Kiểu dữ liệu vào/ra dùng Pydantic v2 (đã có trong FastAPI), không dùng dict trần.
- `CrawlResult` gồm: `status` (`completed` | `failed`), `error_code` + `retryable` khi failed, danh sách trang (mỗi trang đủ trường như `sources[]` của contract PKB: `source_id`, `url`, `page_type`, `content_hash`, `fetched_at`, region, locale, đường dẫn markdown raw và fit trong store), danh sách trang bỏ qua kèm lý do, tóm tắt robots từng host, số trang tìm thấy / dùng, thời gian.
- Hằng số (UA, 30 trang, 5 trang host phụ, 1 giây, timeout, quota theo `page_type`) đưa vào 1 chỗ cấu hình, đọc được từ biến môi trường; giá trị mặc định **bằng spike**.

### 2. Chuẩn hoá URL (phần AI của T1)
- `normalize_product_url(url) -> str` dùng cho `products.website_url` (unique sau chuẩn hoá, ERD gate 2). Viết rõ quy tắc trong docstring + test, theo đặc tả 1.1. Gợi ý: chỉ nhận `http`/`https`; hạ chữ thường scheme và host; bỏ port mặc định, fragment, tham số theo dõi (`utm_*`, `ref`, `fbclid`, `gclid`); bỏ `/` cuối; **giữ path** (Copilot, Notion là product theo path, qa-log #10). Quy tắc nào đặc tả chưa nói (vd. có bỏ `www.` không, giữ query khác không): **hỏi chủ dự án, không tự quyết**.
- URL không hợp lệ → lỗi rõ ràng (để API trả lỗi theo trường, AC của #41).

### 3. Mã lỗi crawl (gửi BE dùng cho hàng đợi)
Lỗi cấp **job** (job `failed`, ghi vào `generation_jobs.error`, chuỗi bắt đầu bằng mã). Mỗi mã có cờ `retryable`:

| Mã | Khi nào | `retryable` |
|---|---|---|
| `invalid_url` | URL sai dạng, scheme khác http(s) | không |
| `waf_challenge` | Trang chủ bị WAF / challenge (vd. `cf-mitigated: challenge`) | **không** (không đổi UA, không proxy) |
| `robots_disallow` | robots.txt cấm trang chủ | không |
| `robots_unavailable` | robots.txt trả 5xx, 429 hoặc timeout → coi như cấm toàn bộ (RFC 9309) | **có** (thử lại sau) |
| `login_redirect` | Trang chủ chuyển sang trang đăng nhập | không |
| `home_unreachable` | DNS lỗi, kết nối lỗi, timeout ở trang chủ | có |
| `no_content` | Trang chủ render được nhưng quá ít chữ, hoặc 0 trang dùng được | không |

Lý do bỏ qua cấp **trang** (job vẫn chạy tiếp): `robots_disallowed`, `login_redirect`, `over_limit`, `duplicate`, `not_english`, `non_html`, `fetch_error`, `unchanged` (content_hash không đổi, NFR-04). Đối chiếu tên với spike; nếu spike dùng tên khác thì giữ tên spike và ghi bảng đối chiếu.
- Retry tối đa 3 lần có backoff (AC của #42) là việc của **hàng đợi**; module này chỉ trả `retryable`. Ghi rõ trong docstring.

### 4. NFR-04: bỏ qua trang không đổi
- `crawl_product` nhận thêm `previous_hashes: dict[url, content_hash]` (rỗng ở lần đầu). Trang có hash không đổi: không ghi lại vào store, đánh dấu `unchanged`, vẫn nằm trong danh sách trang của kết quả (để PKB giữ nguồn).

### 5. Dependency và CI
- Thêm `crawl4ai` **cùng phiên bản spike** (0.9.4, ghim trong `uv.lock`) vào `services/worker`. Không bật `enable_stealth`. Ghi chú trong README worker: Crawl4AI kéo `unclecode-litellm` và `patchright` (đã kiểm tra ở ADR-001); cài trình duyệt bằng `uv run playwright install chromium` khi chạy thật.
- Test chạy **không cần mạng, không cần trình duyệt**: `fetcher` và HTTP (robots, sitemap) thay bằng fake đọc fixture. Fixture: robots.txt mẫu (allow, disallow, 404, 5xx), HTML challenge của Cloudflare (lấy marker từ spike), markdown mẫu ngắn.
- Thêm `pytest` vào dev group và bước `uv run pytest` vào `.github/workflows/worker.yml`. **Đây là thư viện mới: nêu trong kế hoạch, chờ chủ dự án duyệt trước khi thêm.**
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` phải sạch (CI đang chạy pyright trên `src`).

### 6. Kiểm tra bằng chạy thật (chạy tay, không đưa vào CI)
- `uv run python -m worker.m1.crawl https://elevenlabs.io --out <thư mục tạm ngoài repo>`: so với `spikes/m1-crawl-extract/output/elevenlabs/crawl.json` (số trang tìm thấy / dùng, có trang pricing, khoảng cách request nhỏ nhất ≥ 1.0 s). Lệch thì giải thích.
- `https://gamma.app` phải ra `failed` + `waf_challenge`, không retry.
- Không commit output của lần chạy tay.

## Phạm vi
- Làm: `services/worker/**` (code M1 crawl, test, README, `pyproject.toml`, `uv.lock`), `.github/workflows/worker.yml` (thêm pytest), `docs/specs/m1-product-intelligence.md` (thêm mục ngắn "Mã lỗi crawl" = bảng mục 3, và dòng lịch sử phiên bản).
- Không làm: DB / migration, Supabase Storage, hàng đợi, endpoint FastAPI, trích xuất LLM (T3), chụp ảnh màn hình (#52), upload tài liệu (#53). Không sửa `spikes/`.

## Acceptance criteria
- [ ] `crawl_product` cho kết quả đúng dạng `CrawlResult`; trang đủ trường `sources[]` của contract PKB.
- [ ] Test (không mạng) phủ: chuẩn hoá URL (≥ 10 ca, gồm path giữ nguyên, `utm_*`, URL sai), robots RFC 9309 (2xx / 4xx trừ 429 / 5xx / 429 / timeout), throttle ≥ 1 s/host, phát hiện WAF, `login_redirect` ở trang con (bỏ qua) và trang chủ (failed), quota theo `page_type`, ≤ 30 trang và ≤ 5 trang host phụ, `unchanged` theo hash.
- [ ] Bảng mã lỗi có trong code (enum + `retryable`) và trong đặc tả M1.
- [ ] Chạy tay ElevenLabs khớp spike; Gamma ra `waf_challenge`.
- [ ] CI worker xanh: ruff, ruff format, pyright, pytest.

## Ràng buộc
- Trình bày cấu trúc file và danh sách thư viện mới trước khi làm, chờ duyệt.
- Không thêm thư viện ngoài `crawl4ai` và `pytest` khi chưa hỏi. Không vượt chặn bot (không stealth, không đổi UA, không proxy). Không commit `.env`, output chạy tay. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit theo từng phần hợp lý (vd. `feat(m1): chuẩn hoá URL product`, `feat(m1): crawl trong worker theo spike`), kèm file prompt này. Mở PR vào `dev`, body có `Refs #42`, `Refs #41`, `Refs #59`, bảng mã lỗi, kết quả chạy tay; `cc @tranquangthong03 @tua0201n` (mã lỗi dùng cho hàng đợi).
- Trả về: link PR, kết quả test, so sánh chạy tay với spike.
