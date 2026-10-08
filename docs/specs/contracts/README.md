# Contract dùng chung

Các contract JSON dùng chung cho nhiều module (FE, BE, AI). Contract riêng của 1 module nằm trong thư mục của module đó (vd. PKB: `docs/specs/pkb/`).

| File | Dùng cho |
|---|---|
| `cost-breakdown.v1.schema.json` | Cột `cost_breakdown` của `generation_jobs` (job `crawl`, `video`) và `content_scripts` (đề xuất, chờ #23) |
| `script.v0.schema.json` | Kịch bản video dọc 9:16 (M2 -> M3), lưu vào `content_scripts` |


## `cost_breakdown` v1

Nguyên tắc đã chốt ở [issue #23](https://github.com/PotatoMine725/AI-review-BE/issues/23): **worker chỉ ghi `cost_breakdown`**; DB tự tính `cost_usd`, `tokens_in`, `tokens_out` từ cột này (generated column hoặc trigger `BEFORE INSERT/UPDATE`, @tranquangthong03 chọn). Nhờ vậy tổng và chi tiết không lệch nhau.

Gồm `schema_version` (= 1), `currency` (= `USD`) và `items[]`. Quy tắc:

1. `category` là `llm`, `tts`, `video_provider` hoặc `other`. Job crawl (M1) chỉ dùng `llm`; module video thêm `tts`, `video_provider`. Storage không tính theo job (hoá đơn theo tháng).
2. Retry: mỗi lần gọi có tốn tiền là 1 item (`attempt` = 1, 2, 3…), tất cả đều cộng vào tổng. Job `failed` vẫn ghi chi phí đã tiêu.
3. **`call_id`** (bắt buộc, mọi item): id của 1 lần gọi provider, worker sinh (UUID). BE dùng để chống ghi trùng khi retry ghi DB. JSON Schema **không kiểm được** "duy nhất theo `call_id`". BE kiểm trong RPC.
4. **Mọi item bắt buộc có `call_id`, `category`, `attempt`, `cache_hit`, `cost_usd`, `cost_status`. Item `llm` bắt buộc đủ 13 trường:** `call_id`, `step`, `provider`, `model`, `attempt`, `cache_hit`, `tokens_in`, `tokens_out`, `unit_price_in_per_1m`, `unit_price_out_per_1m`, `prices_checked_at`, `cost_usd`, `cost_status`. Schema kiểm bằng `if category = llm then required`.
5. **Cache có 2 loại:**
   - Cache nội bộ (`llm_cache` của worker, không gọi provider): `cache_hit: true`, `tokens_in = tokens_out = 0`, `cost_usd = 0`. Cột tổng chỉ cộng token có trả tiền.
   - Cache phía provider (vd. Gemini context caching, có gọi API nhưng token cache rẻ hơn): `cache_hit: false`. Token cache vẫn nằm trong `tokens_in`. Thêm trường tuỳ chọn `tokens_in_cached` (≤ `tokens_in`, BE kiểm trong RPC) và `unit_price_cached_in_per_1m`. `cost_usd` là số đã tính theo giá cache. MVP chưa dùng loại này.
6. **`cost_status`** ∈ `exact | estimated`. Mọi item bắt buộc có `cost_status`, mọi category (`llm`, `tts`, `video_provider`, `other`):
   - `exact`: token lấy từ `usage` provider trả về.
   - `estimated`: provider không trả `usage` (vd. lỗi giữa chừng). Token ước tính bằng `count_tokens` hoặc bằng chặn trên `max_output_tokens`.
   - Không có trạng thái "không biết". Lần gọi có tốn tiền thì luôn ghi 1 số, kể cả ước tính. Cột tổng vẫn cộng cả `estimated`. Muốn biết job có số ước tính thì BE truy vấn `cost_breakdown` (tìm item có `cost_status = 'estimated'`).
7. **6 chữ số thập phân:** schema không dùng `multipleOf` (lỗi số thực). Worker làm tròn `cost_usd` của item về 6 chữ số trước khi ghi. DB ép kiểu `numeric(12,6)` khi tính tổng.
8. `cost_usd` của job = `sum(items[].cost_usd)`, `numeric(12,6)`. `tokens_in`, `tokens_out` = tổng của các item `llm`.

Các điểm @tranquangthong03 bổ sung ở #23 (default của cột, kiểm tra cấu trúc không chặn cập nhật trạng thái job, chỉ thêm item không sửa/xoá): ghi vào đây khi chốt.

## Ví dụ

Các file đầy đủ nằm ở `examples/`. BE dùng làm case validation. Chạy `uv run python validate_contracts.py` trong `spikes/m1-crawl-extract/` để kiểm tra.

| File | Kỳ vọng | Ý nghĩa |
|---|---|---|
| `valid-exact.json` | pass | 1 lần gọi, token từ `usage` |
| `valid-estimated.json` | pass | Lần 1 lỗi giữa chừng (`estimated`), lần 2 retry thành công (`exact`) |
| `valid-internal-cache.json` | pass | 1 lần gọi + 1 lần lấy từ cache nội bộ |
| `invalid-missing-call-id.json` | fail | Thiếu `call_id` |
| `invalid-llm-missing-model.json` | fail | Item `llm` thiếu `model` |
| `invalid-cache-hit-with-cost.json` | fail | `cache_hit: true` mà `cost_usd > 0` |
| `invalid-missing-cost-status.json` | fail | Item `tts` thiếu `cost_status` |

### Ví dụ `exact`

Lấy từ `meta` của `spikes/m1-crawl-extract/output/claude/pkb.gemini-3.5-flash-lite.json` (22647 token vào, 5100 token ra, $0.019544):

```json
{
  "schema_version": 1,
  "currency": "USD",
  "items": [
    {
      "call_id": "6f1c2a52-3d0e-4b1a-9a57-0c1d2e3f4a01",
      "category": "llm",
      "step": "extract",
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "attempt": 1,
      "cache_hit": false,
      "tokens_in": 22647,
      "tokens_out": 5100,
      "unit_price_in_per_1m": 0.30,
      "unit_price_out_per_1m": 2.50,
      "prices_checked_at": "2026-10-06",
      "cost_usd": 0.019544,
      "cost_status": "exact"
    }
  ]
}
```

Với ví dụ này DB tính ra `tokens_in = 22647`, `tokens_out = 5100`, `cost_usd = 0.019544`.

### Ví dụ `estimated`

Lần gọi 1 lỗi giữa chừng, provider không trả `usage`. Worker lấy chặn trên `max_output_tokens = 8192` làm `tokens_out`. Lần 2 thành công. Tổng gồm cả hai: `cost_usd = 0.027274 + 0.019544 = 0.046818`.

```json
{
  "schema_version": 1,
  "currency": "USD",
  "items": [
    {
      "call_id": "6f1c2a52-3d0e-4b1a-9a57-0c1d2e3f4a02",
      "category": "llm",
      "step": "extract",
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "attempt": 1,
      "cache_hit": false,
      "tokens_in": 22647,
      "tokens_out": 8192,
      "unit_price_in_per_1m": 0.30,
      "unit_price_out_per_1m": 2.50,
      "prices_checked_at": "2026-10-06",
      "cost_usd": 0.027274,
      "cost_status": "estimated"
    },
    {
      "call_id": "6f1c2a52-3d0e-4b1a-9a57-0c1d2e3f4a03",
      "category": "llm",
      "step": "extract",
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "attempt": 2,
      "cache_hit": false,
      "tokens_in": 22647,
      "tokens_out": 5100,
      "unit_price_in_per_1m": 0.30,
      "unit_price_out_per_1m": 2.50,
      "prices_checked_at": "2026-10-06",
      "cost_usd": 0.019544,
      "cost_status": "exact"
    }
  ]
}
```

### Ví dụ cache nội bộ

Item thứ 2 lấy từ `llm_cache` của worker: không gọi provider, không tốn tiền. Tổng chỉ cộng item thứ 1.

```json
{
  "schema_version": 1,
  "currency": "USD",
  "items": [
    {
      "call_id": "6f1c2a52-3d0e-4b1a-9a57-0c1d2e3f4a01",
      "category": "llm",
      "step": "extract",
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "attempt": 1,
      "cache_hit": false,
      "tokens_in": 22647,
      "tokens_out": 5100,
      "unit_price_in_per_1m": 0.30,
      "unit_price_out_per_1m": 2.50,
      "prices_checked_at": "2026-10-06",
      "cost_usd": 0.019544,
      "cost_status": "exact"
    },
    {
      "call_id": "6f1c2a52-3d0e-4b1a-9a57-0c1d2e3f4a04",
      "category": "llm",
      "step": "extract",
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "attempt": 1,
      "cache_hit": true,
      "tokens_in": 0,
      "tokens_out": 0,
      "unit_price_in_per_1m": 0.30,
      "unit_price_out_per_1m": 2.50,
      "prices_checked_at": "2026-10-06",
      "cost_usd": 0,
      "cost_status": "exact"
    }
  ]
}
```

## `script.v0`

Hợp đồng kịch bản video dọc 9:16 (thời lượng 15–60 giây). Module 2 (Content Strategy) nhận PKB approved từ Module 1 để tạo script; Module 3 (AI Video Factory) đọc script để dựng video (FR-CONT-04, FR-VID-02).

### Quy tắc chính
1. **Định dạng và thời lượng:** `aspect_ratio = "9:16"`, `language = "en"`, `target_duration_s` từ 15 đến 60 giây. Tổng `duration_s` các phân cảnh phải nằm trong 15–60 giây (kiểm tra qua `validate_contracts.py`).
2. **Cấu trúc phân cảnh (`scenes[]`):** Tối thiểu 3 scene, khuyến nghị cấu trúc 6 scene: `hook` -> `problem` -> `demo` -> `result` -> `proof` -> `cta` (PRD §14).
3. **Truy xuất nguồn gốc (`fact_ref`):** Mọi phát biểu trong `claims[]` về giá, tính năng, giới hạn bắt buộc có `fact_ref` gồm `source_id` và `field_path` theo dot-bracket notation (vd. `pricing.plans[1]`, `features[0]`) trỏ tới fact trong PKB. Claim không có `fact_ref` là không hợp lệ (FR-QA-01, BRULE-05).
4. **AI Avatar Disclosure:** Khi `format = "ai_avatar"`, bắt buộc phải có `disclosure` (FR-VID-09).
5. **Call To Action (CTA):** Bắt buộc `uses_tracking_link: true` nhằm đảm bảo gắn link affiliate/attribution của campaign.
6. **Experience Claims:** Mặc định cấm các câu "I tested/I used" trừ khi có `evidence_ref` (FR-QA-07).

### Ánh xạ vào ERD (`content_scripts`)
Khi backend lưu script, các trường JSON v0 ánh xạ sang bảng `content_scripts`:
- `product_id` -> `content_scripts.product_id`
- `knowledge_version` -> `content_scripts.knowledge_version`
- `intent` -> `content_scripts.intent` (`awareness|education|consideration|conversion`)
- `platform` -> `content_scripts.platform`
- `language` -> `content_scripts.language`
- `hook.text` -> `content_scripts.hook`
- `hook.angle` -> `content_scripts.idea` (nếu có)

> [!NOTE]
> **Câu hỏi mở cho @tranquangthong03 (Issue #50):**
> Bảng `content_scripts` hiện có cột `script_text text [not null]`. Đề xuất lưu JSON script v0 ở đâu:
> - **Lựa chọn A:** Lưu chuỗi JSON serialized vào `script_text`.
> - **Lựa chọn B:** Bổ sung cột `script jsonb` (hoặc `script_json jsonb`) vào bảng `content_scripts`.
> *Tuân thủ nguyên tắc: Không tự ý sửa file `docs/specs/erd/` khi chưa chốt ở Issue #50.*

### Ví dụ kịch bản
Các file ví dụ được lưu tại `docs/specs/contracts/examples/`:

| File | Kỳ vọng | Ý nghĩa |
|---|---|---|
| `valid-script-elevenlabs.json` | pass | Kịch bản mẫu 30s (6 scenes), fact_ref trỏ tới fact thật trong PKB ElevenLabs |
| `invalid-script-missing-fact-ref.json` | fail | Claim về giá thiếu trường bắt buộc `fact_ref` |
| `invalid-script-avatar-missing-disclosure.json` | fail | Format `ai_avatar` nhưng thiếu khai báo `disclosure` |

