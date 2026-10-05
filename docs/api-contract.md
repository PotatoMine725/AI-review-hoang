# API contract — Worker

Đây là nguồn sự thật duy nhất cho API nội bộ của `services/worker/` (FastAPI), nơi web gọi các job như crawl hoặc trích xuất.
Dữ liệu CRUD thông thường thì web đọc/ghi thẳng Supabase (RLS); schema DB nằm trong `supabase/migrations/`.

Swagger tự sinh khi chạy local: http://127.0.0.1:8000/docs. Bản máy đọc được là http://127.0.0.1:8000/openapi.json.

`openapi.json` là dạng hợp đồng **không phụ thuộc ngôn ngữ**: dù sau này service đổi ngôn ngữ hay web đổi framework,
hai bên vẫn khớp nhau qua file này. Việc sinh TypeScript types tự động từ nó cần thêm tool, sẽ quyết định khi có endpoint thật đầu tiên.

## Quy ước
- JSON, UTF-8; thời gian dùng ISO 8601 UTC.
- Lỗi trả về dạng `{ "detail": "..." }` (mặc định của FastAPI) cho tới khi có ADR khác.
- Đổi endpoint, request hay response thì cập nhật file này **trong cùng PR**, và tạo issue bên `AI-review-FE` nếu web bị ảnh hưởng.

## Endpoints

### `GET /health`
Response `200`:
```json
{ "status": "ok" }
```

Các endpoint dự kiến của Module 1 (`/products`, `/jobs/{id}`, `/knowledge/search`, …) được mô tả trong
`docs/module-1-product-intelligence.md`. Endpoint nào được implement thì chuyển mô tả về file này.
