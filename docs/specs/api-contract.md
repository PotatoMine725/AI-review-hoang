# API contract — FastAPI nghiệp vụ và Supabase CRUD

Tài liệu interface chung cho FE–BE–AI: API nghiệp vụ FastAPI trong `services/worker/`, các RPC mà backend gọi và CRUD hồ sơ trực tiếp qua Supabase dưới RLS/column privileges. ERD là nguồn chuẩn của thiết kế data model; `supabase/migrations/` ghi schema đã triển khai.

## Kiến trúc áp dụng cho Sprint 1 (#59, #61)

- **FastAPI là API nghiệp vụ** cho Product/PKB/job và các thao tác cần backend tin cậy. API và worker nền chạy thành hai tiến trình riêng; API tạo job rồi trả ID, worker nhận job từ DB và ghi kết quả vào DB/Storage. FE gọi FastAPI để đọc trạng thái, không gọi worker thực thi crawl/LLM đồng bộ.
- **Supabase Auth cấp phiên đăng nhập.** Với API nghiệp vụ cần đăng nhập, FE gửi access token qua `Authorization: Bearer <access_token>`. FastAPI phải xác minh JWT và kiểm quyền sở hữu/vai trò trước khi dùng quyền server. Các kiểm tra này là PLANNED, chưa được triển khai chỉ bằng việc cập nhật tài liệu. Khóa `service_role` chỉ nằm ở server, không cấp cho FE.
- **CRUD hồ sơ đã triển khai giữ nguyên**: `merchants`, `creators`, `creator_accounts` được web đọc/ghi qua Supabase với phiên của người dùng, RLS và column privileges. Quyền gọi trực tiếp này không mở rộng sang Product/PKB/job hoặc các thao tác duyệt/chuyển đổi/hoa hồng.
- **Thao tác nhiều bước cần transaction** đi qua FastAPI và có thể dùng RPC để bảo đảm nguyên tử; RPC không thay thế kiểm tra quyền. Next.js Route Handler nếu dùng chỉ làm proxy, không xây lớp nghiệp vụ thứ hai.
- **Queue còn là đề xuất**: worker poll `generation_jobs` và claim nguyên tử bằng `FOR UPDATE SKIP LOCKED`; BE hoàn thiện ADR lease, retry, quota và phục hồi. Sprint 1 chưa thêm Redis/Celery/pgmq; chưa có queue runtime được xác nhận.

Ước tính 12 nhóm/~51 operations là baseline của #61, không mặc định tương ứng 51 HTTP endpoint cần tự viết. BE sẽ bổ sung inventory và phân loại FastAPI, Supabase CRUD, RPC hoặc Server Route/proxy; mỗi operation cần request/response, quyền, nhóm phụ trách, dependency và trạng thái IMPLEMENTED/PLANNED. Các phần còn lại của #61 sẽ được các nhóm liên quan cập nhật sau.

Swagger tự sinh khi chạy local: http://127.0.0.1:8000/docs. Bản máy đọc được là http://127.0.0.1:8000/openapi.json.

`openapi.json` là dạng hợp đồng **không phụ thuộc ngôn ngữ**: dù sau này service đổi ngôn ngữ hay web đổi framework,
hai bên vẫn khớp nhau qua file này. Việc sinh TypeScript types tự động từ nó cần thêm tool, sẽ quyết định khi có endpoint thật đầu tiên.

## Quy ước
- JSON, UTF-8; thời gian dùng ISO 8601 UTC.
- Lỗi trả về dạng `{ "detail": "..." }` (mặc định của FastAPI) cho tới khi có ADR khác.
- Đổi endpoint, request hay response thì cập nhật file này **trong cùng PR**, và tạo issue bên `AI-review-FE` nếu web bị ảnh hưởng.

## Endpoints

### `GET /health` (IMPLEMENTED)
Response `200`:
```json
{ "status": "ok" }
```

Các endpoint dự kiến của Module 1 (`POST /products`, `GET /jobs/{id}`, đọc/sửa/duyệt PKB, …) được mô tả trong
[đặc tả M1](m1-product-intelligence.md) và có trạng thái PLANNED. Không có `/knowledge/search` trong MVP vì embedding/vector RAG đã hoãn. Khi triển khai, bổ sung request/response và quyền vào file này, sau đó chuyển trạng thái endpoint sang IMPLEMENTED kèm bằng chứng code/kiểm thử. OpenAPI hiện tại chỉ phản ánh endpoint đã có trong code, không phải toàn bộ inventory dự kiến.

## P1 pilot (#99): lưu Product / PKB / script / job qua RPC (đề xuất)

Migration `supabase/migrations/20261117020000_p1_pipeline_persistence.sql` (**IMPLEMENTED** ở tầng DB, có test `supabase/tests/`). Năm RPC chỉ cấp cho `service_role`; FastAPI xác minh JWT rồi truyền `p_actor`. Endpoint HTTP bên dưới là **IMPLEMENTED** ở `services/worker` (chưa chạy với Supabase thật; FE/n8n cần xác nhận hình dạng).

| RPC (IMPLEMENTED) | Việc | Lỗi |
|---|---|---|
| `create_pkb_version(p_product_id, p_data, p_sources) → int` | Cấp PKB version kế tiếp, trạng thái `draft` | `foreign_key_violation` nếu không có product |
| `review_pkb(p_product_id, p_version, p_actor, p_decision, p_note)` | `submit` / `approve` / `reject`; approve đặt `products.current_knowledge_version` | `insufficient_privilege` nếu actor không sở hữu product; `restrict_violation` nếu chuyển trạng thái sai |
| `create_script_revision(p_product_id, p_knowledge_version, p_content, p_idempotency_key, p_parent_revision, p_report, p_cost_breakdown) → int` | Cấp revision kế tiếp; cùng `idempotency_key` trả lại revision cũ | `check_violation` nếu PKB chưa `approved` |
| `review_script_revision(p_product_id, p_revision, p_actor, p_decision, p_note)` | như `review_pkb` | như trên |
| `create_generation_job(p_product_id, p_job_type, p_idempotency_key, p_input_snapshot, p_pkb_version, p_script_revision, p_n8n_execution_id, p_render_profile) → uuid` | Tạo job; cùng `(product_id, idempotency_key)` trả job cũ | `check_violation` nếu video thiếu script `approved` |

| Endpoint (IMPLEMENTED, `worker.api.routes`) | Việc | Quyền |
|---|---|---|
| `POST /products` (`website_url`, `name?`) → 201 `{id, website_url, name, status}` | Tạo product; URL chuẩn hoá bằng `normalize_product_url`; `409` nếu URL đã có | owner (JWT) |
| `GET /products/{id}` | Đọc product | owner (RLS) hoặc service |
| `POST /products/{id}/crawl` (`idempotency_key`, `n8n_execution_id?`) → 202 `{job_id}` | Tạo job `crawl` | owner hoặc service |
| `POST /products/{id}/videos` (`pkb_version`, `script_revision`, `idempotency_key`, `render_profile?`, `options?`, `n8n_execution_id?`) → 202 `{job_id}` | Tạo job `video`; `422` nếu script chưa `approved`. `options` cho runner video: `assets_path` (bắt buộc khi runner chạy), `mode` `preview`\|`final`, `ratios` (xem README worker) | owner (JWT, product của mình) hoặc service |
| `GET /jobs/{id}` | `status`, `error`, `pkb_version`, `script_revision`, `n8n_execution_id`, `result_manifest`, chi phí | owner (RLS) hoặc service |
| `GET /jobs/{id}/video?ratio=16:9` → `video/mp4` (hỗ trợ `Range`) | Phát MP4 của job `video` đã `completed`: lấy đường dẫn từ `result_manifest.outputs[]` (`ratio`, `ok`, `mp4`), chỉ phục vụ file nằm dưới `WORKER_VIDEO_DIR/<job_id>` (máy render); `409` job chưa xong, `404` không có tỉ lệ đó hoặc file không còn. `<video src>` không gửi được header `Authorization`, nên FE tải bằng `fetch` rồi dùng blob URL | owner (RLS) hoặc service |
| `PATCH /jobs/{id}` (`status`, `error`, `attempts`, `pkb_version`, `result_manifest`, `n8n_execution_id`, `cost_breakdown`) | Worker/n8n cập nhật job; chuyển trạng thái sai → `409` | service |
| `POST /products/{id}/pkb` (`data`, `sources`) → 201 `{version}` | Tạo PKB `draft` | service |
| `GET /products/{id}/pkb/{version}` | Đọc PKB | owner (RLS) hoặc service |
| `POST /products/{id}/pkb/{version}/review` (`decision` `submit`\|`approve`\|`reject`, `note?`) → `{status}` | Duyệt điểm 1 | owner (JWT) |
| `POST /products/{id}/scripts` (`knowledge_version`, `content`, `idempotency_key`, `parent_revision?`, `report?`, `cost_breakdown?`) → 201 `{revision}` | Tạo script revision từ PKB đã duyệt | service |
| `GET /products/{id}/scripts/{revision}` | Đọc script | owner (RLS) hoặc service |
| `POST /products/{id}/scripts/{revision}/review` | Duyệt điểm 2 | owner (JWT) |
| `POST /products/{id}/scripts/generate` (`knowledge_version`, `idempotency_key`, `parent_revision?`, `permitted_assets?`, `content_context?`, `qa_feedback?`) → 201 `{revision}` (200 nếu key đã dùng) | Đọc PKB `approved`, dựng input M2 (`p1-ac-03-input.v1`), sinh script, lưu revision `draft`. Chạy đồng bộ (LLM, có thể vài phút): n8n đặt timeout HTTP đủ lớn. `qa_feedback` (≤ 20 mục `{message, scene_id?, segment_id?, path?}`) làm M2 dùng đúng một lượt sửa theo góp ý QA (kèm `parent_revision` khi sửa từ revision trước). `422` PKB chưa duyệt / script không đạt validator, `502` lỗi provider, `503` thiếu `GEMINI_API_KEY` (bộ sinh M2 = `generate_script`, sinh + tối đa 1 lượt sửa). `permitted_assets`/`content_context` được lưu vào `script_revisions.report.input` để runner video dựng lại đúng input khi kiểm kịch bản | service |

CORS: worker chỉ cho các origin trong `WORKER_CORS_ORIGINS` (mặc định `http://localhost:3000`, `http://127.0.0.1:3000`); FE gửi Bearer token, không dùng cookie.

Xác thực: owner gửi `Authorization: Bearer <access_token>`, API hỏi Supabase Auth (`/auth/v1/user`) để lấy `auth.users.id` rồi truyền làm `p_actor`; đọc thay mặt owner dùng khoá anon + token nên RLS giới hạn dữ liệu. Service (n8n) gửi `X-Service-Token` (so sánh hằng thời gian với `N8N_SERVICE_TOKEN`; chưa đặt biến thì endpoint service trả `503`). Lỗi trả `{"detail": "..."}`; SQLSTATE → HTTP: `42501`→403, `23503`/`P0002`→404, `23505`/`23001`→409, `23514`/`22P02`→422, thiếu cấu hình→503. Kiểm thử: `services/worker/tests/api/` (DB giả). **Chưa có**: bảng assets (tạm truyền `permitted_assets` trong request), kiểm schema PKB trong API (chờ #90; hiện DB chỉ kiểm dạng). Khoá API và hạn mức: [`p1-secrets-and-quota.md`](p1-secrets-and-quota.md).

n8n chỉ gọi các endpoint service theo Job ID và ghi `n8n_execution_id`; không giữ dữ liệu chuẩn, không nhận secret từ FE. Hợp đồng DB đầy đủ (vòng đời, mã lỗi, idempotency, truy vết): [`p1-pipeline-db-contract.md`](p1-pipeline-db-contract.md). Dữ liệu pilot: [`p1-pilot-pdfcraft.md`](p1-pilot-pdfcraft.md) mục 6.

## Dữ liệu đọc/ghi trực tiếp qua Supabase

**Scope note:** mục này giữ hợp đồng CRUD hồ sơ qua Supabase đã ghi ở #23. Kiến trúc FastAPI tại #59/#61 không đổi các migration, RLS hoặc column privileges hiện có.

CRUD hồ sơ `merchants`, `creators`, `creator_accounts` **không** đi qua FastAPI: web gọi thẳng Supabase Data API
và bị giới hạn bởi RLS/column privileges. Schema đã triển khai nằm trong `supabase/migrations/`, dùng chung cho FE và BE.

Các bảng CRUD được mô tả bằng hai nhãn **IMPLEMENTED** và **PLANNED** ngay trong cùng file này:

- **IMPLEMENTED** nghĩa là đã có trong migration/code hiện có và kiểm chứng được;
- **PLANNED** nghĩa là interface hoặc chức năng dự kiến **chưa** triển khai — chưa gọi được. Nhãn này không thay cho việc duyệt các ADR hoặc request/response còn mở.

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
