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

### Tốc độ crawl

- `M1_CRAWL_CONCURRENCY=3` (mặc định): mở tối đa 3 trang cùng lúc. Trang chủ luôn mở một mình trước. `Throttle` vẫn giữ ≤ 1 request/giây/host, nên chỉ phần chờ render chồng lên nhau. Thứ tự chọn trang và kết quả giống tuần tự (trừ link mới của các trang cùng lượt chưa có lúc chọn). Gặp chặn thì dừng, nhưng các trang đã mở trong lượt đó (tối đa `CONCURRENCY - 1`) vẫn hoàn tất. Muốn dừng tức thì: `M1_CRAWL_CONCURRENCY=1`.
- `M1_CRAWL_WAIT_STABLE=1` (mặc định): sau khi cuộn hết trang, trả về khi chữ không đổi trong `M1_CRAWL_STABLE_FOR_S` (1 giây), tối đa `RENDER_DELAY_S`. Trang SPA dựng chậm sau lúc chữ đứng yên có thể bị cắt sớm: so `content_hash` với lần chạy `WAIT_STABLE=0`, lệch nhiều thì tắt.
- `M1_CRAWL_TEXT_MODE=1` (mặc định): không tải ảnh/font.

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

## M2 — sinh kịch bản P1-AC-03 (`src/worker/m2/`)

Điểm vào: `await generate_script(input, llm, settings=None)` trả `ScriptResult(status, data, cost_breakdown,
warnings, error_code, error_message, retryable, retry_after, errors, raw_output)`. Lỗi trả trong kết quả, không
raise. `input` theo `p1-ac-03-input.v1`; `llm` là `LLM` của M1 (dùng chung retry / quota / cost).

| File | Việc |
|---|---|
| `contract/` | prompt, schema, ví dụ của Định, **chép nguyên byte** từ commit `e33827c` (#83). Không sửa tại đây (`SOURCE.md`) |
| `validate.py` | port luật M2 của `spikes/m1-crawl-extract/validate_contracts.py`, trả mọi lỗi; `validate_input` chạy cả `validate_pkb` của M1 |
| `schema.py` | schema output → dạng Gemini nhận: chỉ giữ từ khoá đã chạy thật, `const` → `enum`, bỏ `estimated_duration_s` |
| `prompt.py` | system prompt = khối ```text của Định, điền 3 placeholder; `product_id`, `knowledge_version` đi ở tin nhắn user |
| `kind.py` | chuẩn bị `visual_plan.kind` từ allowlist (chỉ `kind`, audit cũ → mới + hash allowlist, ID lạ / sai Product / trùng thì báo lỗi, không đoán) |
| `repair.py` | template sửa của Định + feedback (`schema`, `content_validator`, `qa`, `syllable_advisory`) |
| `generate.py` | `generate_script` (sinh → chuẩn bị kind → validator → tối đa 1 lượt sửa) + CLI |

Mã lỗi: `m2_input_invalid` (input sai hoặc allowlist trùng ID, không gọi LLM), các mã `llm_*` của M1. Output sai
schema / refs / asset / CTA: `llm_invalid_output` kèm `errors` và `raw_output`. Worker không vá nội dung; ngoài
`kind` (điền theo allowlist) thì chỉ có **tối đa 1 lời gọi sửa** (`generate_script_repair`) khi còn lỗi validator,
lỗi QA cụ thể (`qa_feedback`) hoặc số âm tiết ngoài 150–170 (khuyến nghị, không phải lỗi). Sau lượt sửa còn lỗi
thì dừng. Mọi tầng nằm trong `ScriptResult.stages` (thô → sau chuẩn bị kind → feedback → bản sửa → kết quả
kiểm); mỗi lời gọi một item trong `cost_breakdown`. `estimated_duration_s` do worker tính:
tổng âm tiết lời thoại ÷ `M2_SYLLABLES_PER_S` (mặc định 3.75). Đây là **ước tính**, không phải duration TTS hay MP4.

```bash
# Cần GEMINI_API_KEY trong .env. Mỗi lần chạy = 1 lời gọi sinh + tối đa 1 lời gọi sửa (--no-repair để tắt).
uv run python -m worker.m2.generate <input.json> --out <thư mục>
```

Ghi `script.json` (kịch bản, hoặc output thô nếu không hợp lệ), `validation.json`, `cost.json`, `stages.json`, `feedback.json`, `initial|repair.{raw,prepared,kind_audit}.json`. Khoá `_note` trong
file input (ghi chú cho người đọc) được bỏ trước khi kiểm. Lần chạy đầu: `docs/report/m2-first-run-pdfcraft.md`.

## P1-08 — kịch bản M2 → MP4 (`src/worker/produce/`)

```bash
uv run python -m worker.produce <script.json> --input <input.json> --assets <assets.json> --out <thư mục> \
    [--mode preview|final] [--ratios 16:9,9:16] [--on-unsupported fail|skip]
```

Kiểm kịch bản bằng validator M2, ánh xạ sang plan `render-plan.v2-spike` của #88, TTS VieNeu theo `segment_id`
(cache theo hash), timeline từ audio đo thật, dựng 2 tỉ lệ song song (`--workers 3` mỗi bên), kiểm MP4 bằng ffprobe,
ghi `render_report.json`. `preview` = `-q draft`, `final` = `-q looks`. Video ngoài 40–45 s (đọc từ config #77) chỉ bị báo,
không kéo dài/cắt. Cảnh M2 không có layout: mặc định dừng và báo đúng cảnh; `--on-unsupported skip` bỏ cảnh đó.
`text_card` có claim mà không có `stat_display` dùng layout chỉ-chữ `claim` (cần template #88 `spike/p1-render-v2` từ commit `4e9f04f`,
patch ở `docs/report/script-to-mp4-2026-11/patches/`); thiếu layout thì lỗi `layout_missing_in_template` ở đúng cảnh.
Phụ đề vượt giới hạn dòng của tỉ lệ (9:16: 2 × 24 ký tự) tự chia thành nhiều cue (`produce/cues.py`), thời gian chia theo số ký tự.
Mã thoát 0 = có MP4 (xem `status`), 2 = không ra MP4. Định dạng `assets.json`: docstring `produce/assets.py`.

**Phần gọi spike (chưa port):** VieNeu #73 (`drivers/tts_synth.py`) và HyperFrames + FFmpeg #88 (`drivers/hf_render.py`)
chạy bằng venv của spike. Đường dẫn qua `PRODUCE_TTS_SPIKE`, `PRODUCE_RENDER_V2`, `PRODUCE_RENDER_FF` (mặc định: worktree
anh em `.claude/worktrees/<tên>/spikes/<tên>`). Phần còn lại là code worker. Kết quả chạy thật: `docs/report/script-to-mp4-2026-11.md`.

## Tự quay clip demo (`src/worker/demo/`)

Thay quay tay bằng Playwright. **LLM không điều khiển trình duyệt lúc quay**: GPT (OpenAI) chỉ sinh một
action-script JSON cho mỗi công cụ (`schema.ActionScript`: goto/click/type/upload/wait_for/scroll, có thể
đánh dấu `focus` để zoom). Script được chạy thử trên trang thật; bước lỗi thì gửi lại GPT kèm DOM lúc đó
để sửa (tối đa 4 vòng). Sau đó Playwright chạy lại script y hệt mỗi lần: con trỏ giả, gõ chậm, di chuột
mượt, `recordVideo` → MP4 H.264 + đoạn `assets.json` (`produce.assets.Asset`, crop mặc định như clip tự quay).
UI đổi thì `generate --regen`. Brief pilot: `docs/report/p1-pilot-pdfcraft/demo-briefs/`.

```bash
uv run playwright install chromium         # một lần (cần FFmpeg có ffprobe trong PATH)
uv run python -m worker.demo samples --out D:\tmp\demo\fx          # PDF mẫu để upload
uv run python -m worker.demo run ..\..\docs\report\p1-pilot-pdfcraft\demo-briefs\pdfcraft-merge-auto.json ^
  --fixtures D:\tmp\demo\fx --scripts D:\tmp\demo\scripts --out D:\tmp\demo\out --assets D:\tmp\demo\out\assets.json
```

Cần `OPENAI_API_KEY` và `DEMO_LLM_MODEL` trong `.env`. Chỉ `record` (không gọi LLM, chạy lại được vô hạn): `python -m worker.demo record <script.json> ...`.
Mã thoát 3 = script hỏng trên trang thật. Test trình duyệt chạy với `DEMO_CHROMIUM_PATH=<chrome>` (CI không cài trình duyệt nên bỏ qua).

## Bộ chạy job (`src/worker/runner/`)

Tiến trình riêng, tách khỏi API: `uv run python -m worker.runner` (`--once` để xử lý hết job rồi thoát). Cần `.env` có `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` (hoặc `LLM_PROVIDER=fixture`) và `uv run playwright install chromium`.

Nhận job `crawl` ở trạng thái `queued` (cũ nhất trước), claim bằng `UPDATE ... WHERE status='queued'` (nguyên tử, không cần migration), chạy M1 crawl, rồi extract (M1, Gemini, 1 lời gọi/job) → `create_pkb_version` → ghi `pkb_version` và `result_manifest` → `completed`. Lỗi `retryable` được xếp lại `queued` (tối đa `RUNNER_MAX_ATTEMPTS`, chờ lũy thừa 2 từ `RUNNER_RETRY_BACKOFF_S`), còn lại `failed` kèm `error`. Markdown trang lưu ở `WORKER_PAGE_STORE_DIR/<job_id>/pages/` (đặt ngoài repo).

Bước nặng nằm sau Protocol `CrawlStep`/`ExtractStep` (`runner/steps.py`); test dùng fake, không cần trình duyệt hay LLM. **Job `video`:** `uv run python -m worker.runner --types video` (chạy trên máy render, cần VieNeu/HyperFrames/FFmpeg cục bộ và biến `PRODUCE_*`; `--types crawl,video` để nhận cả hai). Runner nạp script revision `approved` và PKB `approved` đúng `script_revision`/`pkb_version` của job, dựng lại input M2 (PKB + `script_revisions.report.input` do `/scripts/generate` lưu), kiểm lại bằng validator rồi gọi `worker.produce`. `input_snapshot.options`: `assets_path` (bắt buộc, đường dẫn `assets.json` trên máy render, tạm thời cho tới khi có bảng `assets`), `mode` (`preview` mặc định | `final`), `ratios` (mặc định `["16:9","9:16"]`). MP4 và `render_report.json` ghi ở `WORKER_VIDEO_DIR/<job_id>/`; `result_manifest` có trạng thái (`completed` | `out_of_range`), đường dẫn, độ dài từng tỉ lệ, cảnh báo. Lỗi dựng không retry tự động (mất nhiều phút, cần xem báo cáo); chạy lại bằng job mới với `idempotency_key` mới. Revision sinh trước khi có `report.input` phải sinh lại.

**Chưa có:** timeout cho cả job (extract xấu nhất ~20 phút, xem mục extract), dọn job kẹt `running` khi runner chết (bảng chưa có `updated_at`), upload MP4 lên Storage và bảng `videos`, `previous_hashes` giữa các lần crawl.
