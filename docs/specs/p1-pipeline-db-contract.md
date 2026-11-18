# P1 pilot: hợp đồng database cho FastAPI và n8n

**Issue:** #99 · **PR:** #100 · **Migration:** `supabase/migrations/20261117020000_p1_pipeline_persistence.sql` · **Test:** `supabase/tests/`
**Trạng thái:** đã được lead đồng ý cho pilot P1 (18/11/2026, xem decision-log #24). Đây là hợp đồng **tầng DB**. Endpoint FastAPI và workflow n8n làm ở đầu việc sau; nội dung dưới đây là thứ chúng được phép dựa vào.

## 1. Truy vết và nguồn dữ liệu chuẩn

```
Product → PKB version → script revision → n8n execution → generation job
```

BE/database lưu dữ liệu nghiệp vụ chính (Product, PKB, script revision, trạng thái job). `generation_jobs.n8n_execution_id` chỉ để liên kết lần chạy workflow và tra log, **không** là nguồn dữ liệu chuẩn; n8n không phải đọc/ghi bảng trực tiếp mà đi qua FastAPI.

Truy vết một MP4 về nguồn:

```sql
select j.id as job_id, j.status, j.n8n_execution_id,
       j.script_revision, s.status as script_status, s.knowledge_version,
       k.status as pkb_status, k.version as pkb_version, p.website_url
from public.generation_jobs j
join public.script_revisions s on s.product_id = j.product_id and s.revision = j.script_revision
join public.product_knowledge k on k.product_id = s.product_id and k.version = s.knowledge_version
join public.products p on p.id = j.product_id
where j.id = :job_id;
```

## 2. Bảng

| Bảng | Khoá | Ghi chú |
|---|---|---|
| `products` | `id`; `website_url` unique | `affiliate_url` nullable (khi có phải là URL http(s)); `current_knowledge_version` chỉ trỏ PKB `approved` |
| `product_knowledge` | `(product_id, version)` | `data`, `sources` là JSON PKB v0.3 (worker kiểm schema, DB kiểm dạng và `schema_version`) |
| `script_revisions` | `(product_id, revision)` | FK `(product_id, knowledge_version)` → PKB; `parent_revision`; `content` (script M2), `report`, `cost_breakdown` |
| `generation_jobs` | `id` (Job ID) | `job_type` `crawl` \| `video`; `pkb_version`, `script_revision`, `render_profile`, `n8n_execution_id` |

Chi tiết cột và ràng buộc: `docs/specs/erd/erd.dbml` (Table `products`, `product_knowledge`, `script_revisions`, `generation_jobs`).

## 3. Vòng đời

**PKB và script revision:** `draft → in_review → approved | rejected` (và `draft → rejected`). `approved` và `rejected` bất biến; sửa nội dung tạo version/revision mới. `rejected` cần `review_note` không rỗng. Script chỉ tạo được từ PKB `approved`.

**Job:** `queued → running → completed | failed` (và `queued → failed`, `running → queued` khi retry). `completed` và `failed` bất biến. `failed` bắt buộc có `error`. `finished_at` tự đặt khi kết thúc. `product_id`, `job_type`, `idempotency_key`, `input_snapshot`, `render_profile` bất biến sau khi tạo.

**Điều kiện tạo job `video`:** `pkb_version` và `script_revision` bắt buộc, script ở trạng thái `approved` và `knowledge_version = pkb_version`. Job `crawl` không có `script_revision`; `pkb_version` điền khi PKB đã tạo.

**Hai điểm owner duyệt:** `review_pkb` (điểm 1) và `review_script_revision` (điểm 2). n8n dừng khi chưa `approved` và tiếp tục với **đúng** `pkb_version`/`script_revision` đã duyệt, truyền vào job video.

## 4. RPC (chỉ `service_role`)

FastAPI xác minh JWT, kiểm vai trò rồi gọi RPC; `p_actor` là `auth.users.id` đã xác minh. `authenticated` và `anon` **không** gọi được RPC và không ghi được bảng; owner chỉ `SELECT` dữ liệu của product mình (RLS qua `merchants.user_id`).

| RPC | Việc | Trả | Lỗi (SQLSTATE) |
|---|---|---|---|
| `create_pkb_version(p_product_id, p_data, p_sources)` | Cấp version kế tiếp (khoá dòng product), `draft` | version `int` | `23503` không có product; `23514` `data` sai dạng |
| `review_pkb(p_product_id, p_version, p_actor, p_decision, p_note)` | `submit` \| `approve` \| `reject`; approve đặt `products.current_knowledge_version` | `void` | `42501` actor không sở hữu product; `23001` chuyển trạng thái sai/bản đã khoá; `P0002` không thấy version; `23514` reject thiếu lý do |
| `create_script_revision(p_product_id, p_knowledge_version, p_content, p_idempotency_key, p_parent_revision, p_report, p_cost_breakdown)` | Cấp revision kế tiếp; cùng key trả revision cũ | revision `int` | `23514` PKB chưa `approved` |
| `review_script_revision(p_product_id, p_revision, p_actor, p_decision, p_note)` | như `review_pkb` | `void` | như trên |
| `create_generation_job(p_product_id, p_job_type, p_idempotency_key, p_input_snapshot, p_pkb_version, p_script_revision, p_n8n_execution_id, p_render_profile)` | Tạo job; cùng key trả job cũ | `uuid` (Job ID) | `23503`; `23514` video thiếu script `approved`; `23505` vi phạm chỉ mục chống chạy trùng (xem mục 5) |

Sau khi tạo, worker cập nhật job bằng `UPDATE` trực tiếp qua `service_role` (`status`, `attempts`, `pkb_version`, `result_manifest`, `error`, chi phí, `n8n_execution_id`).

## 5. Idempotency và chạy lại

- `idempotency_key` duy nhất **theo product**: `(product_id, idempotency_key)` ở cả `script_revisions` và `generation_jobs`. Hai product khác nhau dùng cùng key không xung đột. Key nên gồm ID lần chạy n8n và tên bước, ví dụ `<execution_id>:script`.
- **Retry cùng một request** (cùng product, cùng key): `create_script_revision` và `create_generation_job` trả bản đã có, không tạo bản mới và **không kiểm lại tham số**. Gọi lại với tham số khác mà giữ key cũ vẫn nhận bản cũ.
- **Chạy lại có chủ đích** sau khi job `failed`: dùng key mới.
- Chống chạy trùng ở tầng chỉ mục (không phụ thuộc client): tối đa 1 job `crawl` đang `queued`/`running` mỗi product; tối đa 1 job `video` chưa `failed` cho mỗi `(script_revision, render_profile)` (`render_profile` NULL được coi là một giá trị riêng).

## 6. Ánh xạ `script_revisions` → `content_scripts` khi có `campaigns`

`script_revisions` là **giải pháp chuyển tiếp** cho pilot P1, chưa mặc định thay thế `content_scripts` vĩnh viễn. Hướng đề xuất khi `campaigns` được triển khai (cần migration và quyết định riêng):

| `content_scripts` (ERD) | Lấy từ `script_revisions` |
|---|---|
| `product_id`, `knowledge_version` | cùng tên |
| `campaign_id` | do campaign chọn; không có trong `script_revisions` |
| `script_text`, `idea`, `hook`, `intent`, `platform`, `language` | suy từ `content` (concept, hook, narration, intent) |
| `cost_breakdown`, `cost_usd` | `cost_breakdown`; `cost_usd` do DB suy |
| `generation_jobs.content_script_id` | backfill từ `generation_jobs.script_revision` qua cột nối |

Cách làm gợi ý: thêm `content_scripts.source_revision int` với FK `(product_id, source_revision)` → `script_revisions`; mỗi revision đã `approved` và được campaign dùng thì tạo 1 dòng `content_scripts`, giữ `script_revisions` làm lịch sử revision. Lúc đó cân nhắc thay `generation_jobs.script_revision` bằng `content_script_id` hoặc giữ cả hai. Ranh giới "bản đã dùng thì bất biến" của `content_scripts` áp lên bản sao, không áp lên lịch sử.

## 7. Mở rộng không khoá cứng render

Phương án tạo `9:16` và `16:9` chưa chốt (bước tích hợp render). Schema hiện tại không ép cách chia:

- `generation_jobs.render_profile` (nullable, text 1–100 ký tự, bất biến). Chưa có ràng buộc giá trị; thêm `aspect_ratio` hay bảng preset sau chỉ cần migration cộng thêm cột/ràng buộc.
- Chỉ mục chống chạy trùng đã tính `render_profile`, nên có thể tạo song song 1 job mỗi profile cho cùng revision hoặc dùng 1 job chứa cả hai tỉ lệ (để `render_profile` NULL và ghi tỉ lệ trong `input_snapshot`/`result_manifest`). Cả hai cách đều dùng được mà không đổi migration này.
- Tham số render (preset, tỉ lệ, template) nằm trong `input_snapshot` cho tới khi có quyết định.

## 8. Chưa có trong hợp đồng này

Endpoint FastAPI; workflow n8n; hàng đợi claim job (`FOR UPDATE SKIP LOCKED`); bảng `videos` và Storage bucket; derive `tokens_*`/`cost_usd` từ `cost_breakdown`; vai trò admin (reject PKB vì vi phạm chính sách); schema JSON đầy đủ của `data` và `content` (worker kiểm).
