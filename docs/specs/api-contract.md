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
`docs/specs/m1-product-intelligence.md`. Endpoint nào được implement thì chuyển mô tả về file này.

## Dữ liệu đọc/ghi trực tiếp qua Supabase

Một số dữ liệu là CRUD thông thường nên **không** đi qua worker: web gọi thẳng Supabase Data API
và bị giới hạn bởi RLS. Schema nằm trong `supabase/migrations/`, nguồn sự thật cho cả FE lẫn BE.

### Module 5 — Creator Network: `creators`, `creator_accounts`

Migration: `supabase/migrations/20261006020041_creator_network.sql`.

| Bảng | Mô tả | Creator gửi khi INSERT | Creator sửa được khi UPDATE |
|---|---|---|---|
| `creators` | Hồ sơ creator, quan hệ 1–1 với user qua `user_id → auth.users(id)` | `display_name`, `bio`, `niche`, `language`, `country`, `avatar_url` | `display_name`, `bio`, `niche`, `language`, `country`, `avatar_url` |
| `creator_accounts` | Tài khoản mạng xã hội của creator (mỗi nền tảng 1 dòng) | `platform`, `handle`, `url`, `follower_count` | `platform`, `handle`, `url`, `follower_count` |

Quy tắc:

- **Quyền truy cập**: mỗi người dùng chỉ thấy và sửa được hồ sơ của chính mình (`user_id = auth.uid()`),
  và các `creator_accounts` thuộc hồ sơ đó. Không có đường đọc hồ sơ của creator khác.
- **SELECT / INSERT / UPDATE**. Chưa mở DELETE cho `authenticated` ở task này.
- **Cột hệ thống không sửa được**: `id`, `user_id`, `creator_id`, `created_at`, `updated_at`, `status`,
  `platform_handle`. Thực thi bằng **column-level privileges** (`grant insert/update (<cột>)`), không chỉ dựa vào RLS.
  `status` chỉ service_role đổi được (`pending` → `active`/`suspended`), nên creator tự đăng ký luôn ở trạng thái `pending`.

**Cơ chế gán chủ sở hữu (client không gửi các cột này):**

- **`creators.user_id`** có `default auth.uid()`. Khi client INSERT chỉ với các cột hồ sơ,
  `user_id` tự lấy từ phiên đăng nhập. RLS giữ `with check (user_id = auth.uid())` như lớp phòng thủ thứ hai
  (không thay bằng `with check (true)`), nên kể cả nếu cột này bị ghi thì cũng không thể gán cho user khác.
- **`creator_accounts.creator_id`** do trigger `before insert` (`set_creator_id_from_auth`) suy ra:
  `auth.uid()` → tìm `creators` theo `user_id` → gán `new.creator_id`. Client **không** gửi `creator_id`.
  Nếu user chưa có hồ sơ creator, trigger raise `creator profile not found for authenticated user`.
  Vì `creator_id` không nằm trong grant insert/update, creator **không thể** gán account cho creator khác,
  và **không thể** chuyển account sang creator khác bằng UPDATE. RLS `with check exists (...)` giữ làm phòng thủ thứ hai.
- **Trigger và service_role**: nếu `new.creator_id` đã có giá trị thì trigger giữ nguyên (không ghi đè) —
  nhánh này chỉ tới được khi role có quyền INSERT trên cột `creator_id`, mà `authenticated` không có.
  Nên quản trị/service_role vẫn gán `creator_id` tùy ý được (FK vẫn kiểm tra creator tồn tại);
  còn client `authenticated` (không có quyền trên cột đó → `new.creator_id` là NULL) luôn bị suy ra từ `auth.uid()`.

**Chuẩn hóa `platform` / `handle` (lưu giá trị canonical):**

- Trước INSERT/UPDATE, trigger `creator_accounts_normalize` đặt
  `platform := lower(btrim(platform))` và `handle := ltrim(lower(btrim(handle)), '@')`,
  rồi lưu chính giá trị đã chuẩn hóa vào hai cột này.
- **`creator_accounts.platform_handle`** là cột `generated always as (platform || ':' || handle) stored`,
  sinh từ giá trị đã chuẩn hóa, và **unique toàn cục**: cùng một handle trên cùng nền tảng không thể
  thuộc về hai creator. Đây là chống trùng lặp, **không phải** xác minh quyền sở hữu (task này chưa có verify).
  Constraint `unique (creator_id, platform, handle)` cũ đã bỏ vì key chuẩn hóa toàn cục đã đủ.
- Khi UPDATE `platform` hoặc `handle`, cột generated tự tính lại `platform_handle` (đổi sang key mới,
  vẫn chịu ràng buộc unique toàn cục).
- CHECK: `platform` 1–30 ký tự, `handle` 1–50 ký tự; giá trị sau chuẩn hóa không được rỗng
  (vi phạm `char_length(...) between 1 and ...`).

- `updated_at` tự cập nhật bằng trigger `public.set_updated_at()`.
- Cột `is_verified` **không** tồn tại — chưa có quy trình xác minh.

TypeScript cho web: sinh từ schema bằng `supabase gen types typescript` (xem CONTRIBUTING §5).
