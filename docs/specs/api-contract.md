# API contract — Worker và Supabase CRUD

Nguồn sự thật cho API nội bộ của `services/worker/` (FastAPI), nơi web gọi các job như crawl hoặc trích xuất,
**và** cho các bảng CRUD trực tiếp qua Supabase (RLS); schema DB nằm trong `supabase/migrations/`.

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

**Scope note:** mục này mở rộng phạm vi của file để bao gồm các bảng CRUD của Supabase. Header đã được
cập nhật tương ứng. Việc xác nhận với team được theo dõi ở Issue #23.

Một số dữ liệu là CRUD thông thường nên **không** đi qua worker: web gọi thẳng Supabase Data API
và bị giới hạn bởi RLS. Schema nằm trong `supabase/migrations/`, nguồn sự thật cho cả FE lẫn BE.

Các bảng CRUD được mô tả bằng hai nhãn **IMPLEMENTED** và **PLANNED** ngay trong cùng file này:

- **IMPLEMENTED** nghĩa là đã có trong migration/code hiện có và kiểm chứng được;
- **PLANNED** nghĩa là thiết kế đã duyệt nhưng **chưa** triển khai — chưa gọi được.

### Module 5 — Merchant Network: `merchants` (IMPLEMENTED)

Migration: `supabase/migrations/20261006052010_merchant_registration.sql`.

Hồ sơ merchant, quan hệ **1–1** với user qua `user_id → auth.users(id)`. Không có endpoint worker:
bảng này là CRUD thường, web đọc/ghi thẳng qua Supabase Data API dưới RLS.

**RLS (quyết định *row nào* được chạm) — 3 policy, đều `to authenticated`:**

| Policy | Lệnh | Điều kiện |
|---|---|---|
| `merchants_select_own` | SELECT | `using (user_id = (select auth.uid()))` |
| `merchants_insert_own` | INSERT | `with check (user_id = (select auth.uid()))` |
| `merchants_update_own` | UPDATE | `using` **và** `with check` `user_id = (select auth.uid())` |

**Không có policy DELETE** → `authenticated` không xóa được, dù có quyền ở tầng bảng.

**Column privileges (quyết định *cột nào* được ghi) — lớp thứ hai, không thay RLS:**

- `grant select on public.merchants to authenticated`
- `grant insert/update (company_name, company_slug, website, logo_url, description, contact_email, country) to authenticated`
- `revoke insert, update, delete ... from anon, authenticated` trước khi grant lại, nên cột hệ thống không ghi được.
- `service_role` bypass RLS và giữ full grant → công cụ quản trị đổi được `status`.

| Bảng | Merchant gửi khi INSERT | Merchant sửa được khi UPDATE |
|---|---|---|
| `merchants` | `company_name`, `company_slug`, `website`, `logo_url`, `description`, `contact_email`, `country` | như INSERT (đủ 7 cột) |

**Cột hệ thống không sửa được** (không nằm trong grant): `id`, `user_id`, `status`, `created_at`, `updated_at`.

**Cơ chế gán chủ sở hữu:** `merchants.user_id` có `default auth.uid()` và `not null`. Client INSERT chỉ gửi
7 cột hồ sơ → `user_id` tự lấy từ phiên đăng nhập. RLS `with check (user_id = auth.uid())` giữ làm
phòng thủ thứ hai, và insert-grant không có `user_id` nên client không thể gán cho user khác.

**Validation, normalization và uniqueness (đã có):**

- `company_name`: `btrim`, 1–200 ký tự.
- `company_slug`: `lower(btrim(...))`, 3–80 ký tự, khớp `^[a-z0-9-]+$`; **UNIQUE toàn bảng**.
- `website`, `logo_url`: phải khớp `^https?://`; `''`/khoảng trắng → NULL (`nullif(btrim(...),'')`).
- `description`: ≤ 2000 ký tự; `''` → NULL.
- `contact_email`: `lower(btrim(...))`, khớp mẫu email, ≤ 254 ký tự; `''` → NULL.
- `country`: `upper(btrim(...))`, khớp `^[A-Z]{2}$`; `''` → NULL.
- `status`: `check (status in ('pending','active','suspended'))`, default `'pending'`.
- `user_id` UNIQUE → **mỗi user tối đa một hồ sơ merchant**.
- `updated_at` tự cập nhật bằng trigger `public.set_updated_at()`.
- **Slug lifecycle:** `company_slug` chỉ sửa được khi `status = 'pending'`; trigger `merchants_slug_lifecycle`
  chặn đổi slug sau đó với `restrict_violation`. Áp dụng cho **mọi role, kể cả `service_role`** — không có
  đường bypass lúc chạy; sửa slug sau activation là quy trình bảo trì có review, không phải đường runtime.

**Vai trò cùng tồn tại (role coexistence):** `merchants.user_id` và `creators.user_id` là hai UNIQUE
riêng biệt trên hai bảng, không ràng buộc chéo → **một user vừa có merchant vừa có creator profile**.
Điều này khớp ERD (`auth.users` → 0–1 mỗi loại profile). Không có bảng role trung tâm trong migration hiện có.

**PLANNED — chưa có API:** duyệt/từ chối PKB, chi phí job (`tokens_in`, `tokens_out`, `cost_usd`,
`cost_breakdown`) và việc merchant báo video (`merchant_flagged_at`, `merchant_flag_reason`) **chưa**
được implement. Các mục đó là cột ERD đã duyệt, **không phải** endpoint hay đường ghi hiện có.

### Module 5 — Creator Network: `creators`, `creator_accounts` (IMPLEMENTED)

Migration: `supabase/migrations/20261006020041_creator_network.sql`.

| Bảng | Mô tả | Creator gửi khi INSERT | Creator sửa được khi UPDATE |
|---|---|---|---|
| `creators` | Hồ sơ creator, quan hệ 1–1 với user qua `user_id → auth.users(id)` | `display_name`, `bio`, `niche`, `language`, `country`, `avatar_url` | `display_name`, `bio`, `niche`, `language`, `country`, `avatar_url` |
| `creator_accounts` | Tài khoản mạng xã hội của creator (mỗi nền tảng 1 dòng) | `platform`, `handle`, `url`, `follower_count` | `platform`, `handle`, `url`, `follower_count` |

Quy tắc:

- **Quyền truy cập**: mỗi người dùng chỉ thấy và sửa được hồ sơ của chính mình (`user_id = auth.uid()`),
  và các `creator_accounts` thuộc hồ sơ đó. Không có đường đọc hồ sơ của creator khác.
- **SELECT / INSERT / UPDATE**. Chưa mở DELETE cho `authenticated` ở task này. (IMPLEMENTED)
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
