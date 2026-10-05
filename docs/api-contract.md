# API Contract — AI-Content-Factory

Đây là nguồn sự thật duy nhất cho API giữa `AI-review-BE` và `AI-review-FE`.
Khi đã chọn stack, file này có thể được thay hoặc bổ sung bằng OpenAPI (`openapi.yaml`).

## Quy ước chung
- Base URL: `/api/v1`
- Định dạng: JSON, UTF-8
- Thời gian: ISO 8601 UTC (`2026-10-05T04:35:00Z`)
- Lỗi trả về dạng:
  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "Mô tả lỗi" } }
  ```

## Endpoints

### `GET /api/v1/health`
Kiểm tra server còn sống.

Response `200`:
```json
{ "status": "ok" }
```

<!-- Mẫu khi thêm endpoint mới:
### `METHOD /api/v1/<path>`
Mô tả ngắn.
Request: ...
Response `200`: ...
Lỗi: ...
-->

## Lịch sử thay đổi
| Ngày | Thay đổi | PR |
|---|---|---|
| 2026-10-05 | Khởi tạo contract, thêm `/health` | — |
