# Contract dùng chung

Các contract JSON dùng chung cho nhiều module (FE, BE, AI). Contract riêng của 1 module nằm trong thư mục của module đó (vd. PKB: `docs/specs/pkb/`).

| File | Dùng cho |
|---|---|
| `cost-breakdown.v1.schema.json` | Cột `cost_breakdown` của `generation_jobs` (job `crawl`, `video`) và `content_scripts` (đề xuất, chờ #23) |

## `cost_breakdown` v1

Nguyên tắc đã chốt ở [issue #23](https://github.com/PotatoMine725/AI-review-BE/issues/23): **worker chỉ ghi `cost_breakdown`**; DB tự tính `cost_usd`, `tokens_in`, `tokens_out` từ cột này (generated column hoặc trigger `BEFORE INSERT/UPDATE`, @tranquangthong03 chọn). Nhờ vậy tổng và chi tiết không lệch nhau.

Gồm `schema_version` (= 1), `currency` (= `USD`) và `items[]`. Quy tắc:

1. `category` là `llm`, `tts`, `video_provider` hoặc `other`. Job crawl (M1) chỉ dùng `llm`; module video thêm `tts`, `video_provider`. Storage không tính theo job (hoá đơn theo tháng).
2. Retry: mỗi lần gọi có tốn tiền là 1 item (`attempt` = 1, 2, 3…), tất cả đều cộng vào tổng. Job `failed` vẫn ghi chi phí đã tiêu.
3. Item `cache_hit: true`: `cost_usd = 0`, `tokens_in = 0`, `tokens_out = 0`. Cột tổng chỉ cộng token có trả tiền. *(Đề xuất, chờ #23.)*
4. `cost_usd = sum(items[].cost_usd)`, **không làm tròn**. Cột và từng item cùng độ chính xác 6 chữ số thập phân: `cost_usd numeric(12,6)`. *(Đề xuất, chờ #23.)*
5. `tokens_in`, `tokens_out` = tổng của các item `llm`.

Các điểm @tranquangthong03 bổ sung ở #23 (default của cột, kiểm tra cấu trúc không chặn cập nhật trạng thái job, chỉ thêm item không sửa/xoá): ghi vào đây khi chốt.

Ví dụ, lấy từ `meta` của `spikes/m1-crawl-extract/output/claude/pkb.gemini-3.5-flash-lite.json` (22647 token vào, 5100 token ra, $0.019544):

```json
{
  "schema_version": 1,
  "currency": "USD",
  "items": [
    {
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
      "cost_usd": 0.019544
    }
  ]
}
```

Với ví dụ này DB tính ra `tokens_in = 22647`, `tokens_out = 5100`, `cost_usd = 0.019544`.
