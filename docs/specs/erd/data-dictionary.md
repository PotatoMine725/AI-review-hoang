<!--
Nguồn: @tranquangthong03 gửi nhóm ngày 2026-10-07 (file gốc: mo_ta_csdl_erd_v0.md). Đưa vào repo nguyên văn.
"erd_v1_3_1.dbml" trong tài liệu = docs/specs/erd/erd.dbml. Trạng thái: chờ @VV6505 duyệt. Góp ý: issue #23.
-->

# Từ điển dữ liệu hệ thống AI Review MVP v1.3.1
Tài liệu giải thích từng bảng và từng thuộc tính trong **erd_v1_3_1.dbml**, phục vụ BE, FE, AI và người phụ trách nghiệp vụ. Phạm vi là **16 bảng nghiệp vụ và một bảng Auth được tham chiếu**, hướng tới pilot một tháng. Đây là mô tả thiết kế mục tiêu, không phải xác nhận migration đã triển khai hoặc kiểm thử database đã pass.

Nguồn đối chiếu: ERD v1.3.1 ngày 07/10/2026. Tài liệu này không thay đổi ERD và không thêm bảng/cột. Các ví dụ tiền, ID, nội dung chỉ minh họa; không phải cấu hình kinh doanh đã được team chốt.

## 1. Cách đọc tài liệu

- **Một row**: đơn vị nghiệp vụ mà bảng lưu; cần phân biệt product, video, post, click và payment.
- **PK** là khóa chính; **FK** là khóa ngoại; **UNIQUE** chống trùng theo đúng tập cột được chỉ định.
- **Không NULL** chỉ nói trường phải có giá trị, không có nghĩa client phải gửi. Nhiều trường do default, trigger hoặc RPC điền.
- **Có NULL** nghĩa DBML cho phép NULL; CHECK hoặc quy tắc nghiệp vụ có thể bắt buộc giá trị ở một trạng thái cụ thể.
- **Default** chỉ áp dụng khi tạo row và không truyền giá trị; không tự chạy lại khi UPDATE.
- **DBML** mô tả cột/FK/UNIQUE/CHECK. Các Note `SQL REQUIRED` là yêu cầu phải lập trình thêm; không phải constraint đã tồn tại trên database.
- **RLS** quyết định ai được đọc/ghi row; **column grants/API DTO** quyết định trường nào được truy cập. FK không thay thế authorization.
- **RPC** trong tài liệu là thao tác database có transaction. Không tách các bước ghi tiền thành nhiều HTTP request độc lập.

| Kiểu | Ý nghĩa trong hệ thống |
|---|---|
| `uuid` | ID định danh; các bảng có default dùng `gen_random_uuid()`. |
| `text` | Chuỗi; bản thân kiểu này không kiểm tra URL/email hoặc chuỗi rỗng. |
| `text[]` | Mảng chuỗi, dùng cho quốc gia/claims/hashtags. |
| `int`, `bigint` | Số nguyên; bigint phù hợp bộ đếm lớn như views/followers. |
| `numeric(12,4)` | Số thập phân chính xác, tổng 12 chữ số, 4 chữ số sau dấu thập phân; dùng mức commission. |
| `numeric(14,2)` | Số tiền chính xác với 2 chữ số sau dấu thập phân. Quy tắc làm tròn vẫn phải chốt. |
| `varchar(3)` | Chuỗi tối đa 3 ký tự, dùng mã tiền tệ; CHECK USD mới giới hạn giá trị cho pilot. |
| `jsonb` | JSON có cấu trúc linh hoạt; không tự xác minh schema hoặc nguồn fact. |
| `timestamptz` | Thời điểm tuyệt đối; API cần thống nhất ISO 8601 và hiển thị theo múi giờ người dùng. |

## 2. Tổng quan mô hình

Merchant sở hữu product; product có nhiều phiên bản kiến thức và nhiều campaign. Mỗi campaign quảng bá đúng một product. Creator tham gia campaign bằng enrollment giữ snapshot commission. AI tạo script từ một PKB version đã duyệt, worker tạo video và admin duyệt video. Creator chọn video/account, nhận tracking link, đăng bài và xác nhận URL. Merchant gửi conversion có click_id; hệ thống xét quyền một lần rồi ghi commission đúng enrollment.

Bốn đơn vị không được nhầm lẫn: **video** là asset tái sử dụng; **post** là một lần đăng của creator; **click** là một redirect; **conversion** là một sự kiện khách hàng từ merchant.

| Nhóm | Bảng |
|---|---|
| Auth và hồ sơ | `auth.users`, `merchants`, `creators`, `creator_accounts` |
| Product Intelligence | `products`, `product_knowledge` |
| Campaign và network | `campaigns`, `creator_campaigns` |
| AI content | `content_scripts`, `generation_jobs`, `videos` |
| Phân phối và click | `published_posts`, `tracking_links`, `tracking_events` |
| Kết quả và thu nhập | `conversions`, `commission_eligibility`, `commissions` |

Phạm vi MVP cố định: USD, một language/template/provider, QA thủ công, creator tự đăng, views nhập thủ công, commission một lần flat/percentage. Không có recurring commission, vector RAG, wallet, chi tiền tự động hoặc partial-refund automation.

## 3. Chi tiết từng bảng

### 0. `auth.users` — Tài khoản xác thực

**Một row:** Một tài khoản đăng nhập của hệ thống. Đây chỉ là phần tham chiếu tối thiểu của bảng Supabase quản lý.

**Quy tắc và quyền sử dụng:** Không coi ERD là định nghĩa đầy đủ của Auth. Một user có tối đa một merchant và tối đa một creator; hai vai trò có thể cùng tồn tại. Không xóa tài khoản theo cách cascade làm mất lịch sử thu nhập.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | — | ID tài khoản xác thực do Supabase quản lý; đây là bảng có sẵn, không tạo lại từ ERD. PK. |
| `email` | `text` | Có | — | Email của tài khoản xác thực. ERD chỉ minh họa trường này, không mô tả toàn bộ schema hoặc constraint thật của Supabase Auth. |

**Giới hạn mô tả:** không suy ra email nullable/unique trong database Auth thật từ sơ đồ giản lược này; kiểm tra schema Supabase khi tích hợp.

### 1. `merchants` — Hồ sơ merchant

**Một row:** Một doanh nghiệp/chủ sản phẩm gắn với một user.

**Quy tắc và quyền sử dụng:** Owner đọc/sửa các trường profile được cấp quyền. ID, owner, status, timestamp do hệ thống quản lý. Bảo toàn validation và slug lifecycle đã có; CHECK status chỉ kiểm tra giá trị, không tự kiểm soát quyền đổi status.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `user_id` | `uuid` | Không | `auth.uid()` | Tài khoản Supabase Auth sở hữu hồ sơ. Server lấy từ phiên đăng nhập; client không tự gán. UNIQUE; FK → auth.users.id. |
| `company_name` | `text` | Không | — | Tên doanh nghiệp/đơn vị cung cấp sản phẩm. |
| `company_slug` | `text` | Không | — | Tên định danh ngắn duy nhất, thường dùng trên URL; giữ chuẩn hóa và quy tắc chỉ cho sửa khi trạng thái cũ là pending. UNIQUE. |
| `website` | `text` | Có | — | Website của doanh nghiệp, khác website riêng của từng product. |
| `logo_url` | `text` | Có | — | URL logo doanh nghiệp. |
| `description` | `text` | Có | — | Mô tả doanh nghiệp. |
| `contact_email` | `text` | Có | — | Email liên hệ nghiệp vụ; có thể khác email đăng nhập. |
| `country` | `text` | Có | — | Mã quốc gia của hồ sơ. Giữ validation hiện có khi viết migration. |
| `status` | `text` | Không | 'pending' | pending: chờ kích hoạt; active: đang hoạt động; suspended: bị đình chỉ. Chỉ luồng quản trị được đổi trạng thái. CHECK: status IN ('pending','active','suspended'). |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

**Khóa/index được khai báo ở cấp bảng:**

- `status`

### 2. `creators` — Hồ sơ creator

**Một row:** Một người làm nội dung/affiliate gắn với một user.

**Quy tắc và quyền sử dụng:** Cần bổ sung UNIQUE(user_id) nếu migration hiện có còn thiếu và kiểm tra dữ liệu trùng trước. Owner chỉ sửa profile; activation/suspension qua admin. Một creator có nhiều social accounts và nhiều enrollments.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `user_id` | `uuid` | Không | `auth.uid()` | Tài khoản Supabase Auth sở hữu hồ sơ. Server lấy từ phiên đăng nhập; client không tự gán. UNIQUE; FK → auth.users.id. |
| `display_name` | `text` | Không | — | Tên hiển thị của người làm nội dung. |
| `bio` | `text` | Có | — | Giới thiệu ngắn về creator. |
| `niche` | `text` | Có | — | Chủ đề/lĩnh vực creator tập trung, ví dụ productivity hoặc AI tools. |
| `language` | `text` | Có | — | Ngôn ngữ nội dung/hồ sơ; định dạng mã ngôn ngữ cần thống nhất trong validation. |
| `country` | `text` | Có | — | Mã quốc gia của hồ sơ. Giữ validation hiện có khi viết migration. |
| `avatar_url` | `text` | Có | — | URL ảnh đại diện. |
| `status` | `text` | Không | 'pending' | pending: chờ kích hoạt; active: được hoạt động; suspended: bị đình chỉ. Creator không tự kích hoạt. CHECK: status IN ('pending','active','suspended'). |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

### 3. `creator_accounts` — Tài khoản mạng xã hội

**Một row:** Một social account của một creator.

**Quy tắc và quyền sử dụng:** UNIQUE platform_handle chống khai báo trùng, không xác minh quyền sở hữu. Composite UNIQUE(id, creator_id) phục vụ FK post/account. Giữ generated column thật trong SQL; platform bị khóa sau khi đã có bất kỳ post selected/published tham chiếu.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `creator_id` | `uuid` | Không | — | Hồ sơ creator sở hữu hoặc tham gia bản ghi; khác với auth.users.id. FK → creators.id. |
| `platform` | `text` | Không | — | Nền tảng đích, ví dụ TikTok hoặc YouTube. DBML chưa quy định danh sách giá trị hợp lệ. |
| `handle` | `text` | Không | — | Tên tài khoản trên nền tảng; giữ cơ chế chuẩn hóa chữ thường, khoảng trắng và dấu @ của migration hiện có. |
| `platform_handle` | `text` | Có | — | Khóa chuẩn hóa toàn cục, ví dụ tiktok:alice. SQL phải giữ generated column ghép platform, dấu hai chấm và handle; không cho client ghi. UNIQUE. |
| `url` | `text` | Có | — | URL trang tài khoản mạng xã hội. |
| `follower_count` | `bigint` | Không | 0 | Số follower khai báo/cập nhật; không âm. Không phải bằng chứng đã xác minh quyền sở hữu account. CHECK: follower_count >= 0. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

**Khóa/index được khai báo ở cấp bảng:**

- `creator_id`
- `(id, creator_id) [unique]`

**Lưu ý nullability:** DBML không ghi NOT NULL cho platform_handle. Cột thực tế phải là generated từ platform/handle NOT NULL theo migration; không diễn giải cột này là trường client tùy chọn.

### 4. `products` — Sản phẩm cần quảng bá

**Một row:** Một product thuộc đúng một merchant.

**Quy tắc và quyền sử dụng:** Website URL unique toàn bảng; không unique domain. Merchant nhập dữ liệu qua luồng có kiểm tra quyền. Kích hoạt cần tên và PKB approved. Product giữ con trỏ version hiện hành; script cũ vẫn trỏ bản PKB lịch sử. Current version FK chỉ xác minh tồn tại, trigger/RPC còn phải xác minh approved.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `merchant_id` | `uuid` | Không | — | Hồ sơ merchant sở hữu product/campaign; khác với auth.users.id. FK → merchants.id. |
| `website_url` | `text` | Không | — | URL chuẩn hóa của product, duy nhất trên toàn bảng. Unique URL không có nghĩa unique domain. UNIQUE. |
| `affiliate_url` | `text` | Không | — | Đích affiliate hợp lệ để backend tạo tracking link; không phải trang mô tả chương trình affiliate. |
| `name` | `text` | Có | — | Tên product. Có thể chưa biết khi merchant chỉ nhập URL; phải có trước khi kích hoạt. |
| `description` | `text` | Có | — | Mô tả tóm tắt product phục vụ quản lý/hiển thị. |
| `category` | `text` | Có | — | Danh mục sản phẩm, ví dụ AI writing hoặc video tools. |
| `merchant_input` | `jsonb` | Không | `'{}'::jsonb` | JSON dữ liệu merchant cung cấp: thông tin sản phẩm, pricing, brand, claims hoặc tài liệu tham chiếu. Là đầu vào thô, không tự động là PKB đã duyệt. |
| `current_knowledge_version` | `int` | Có | — | Số version PKB hiện hành. Cùng products.id trỏ tới đúng (product_id, version) trong product_knowledge; NULL khi chưa có bản hiện hành. |
| `status` | `text` | Không | 'draft' | draft: đang chuẩn bị; active: đủ điều kiện sử dụng; archived: lưu trữ, không mở mới hoạt động. CHECK: status IN ('draft','active','archived'). |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

**Khóa/index được khai báo ở cấp bảng:**

- `merchant_id`
- `(id, merchant_id) [unique]`

### 5. `product_knowledge` — Kho kiến thức theo phiên bản

**Một row:** Một phiên bản kiến thức của một product.

**Quy tắc và quyền sử dụng:** PK ghép (product_id, version). PKB approved là nguồn fact cho AI; bản đã duyệt bất biến, thay đổi tạo version mới. **Chỉ merchant sở hữu product được approve**; admin chỉ reject được khi vi phạm policy và không sửa/approve nội dung — xem "Quyền duyệt PKB" cuối mục này (PLANNED, chưa enforce). Không có bảng pricing/features riêng và không có vector index trong MVP. PKB JSON không phải permission bypass: nguồn và nội dung vẫn cần validate.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `product_id` | `uuid` | Không | — | Product mà bản ghi thuộc về; không phải ID của merchant. FK → products.id. |
| `version` | `int` | Không | — | Số phiên bản kiến thức trong phạm vi một product, bắt đầu từ số dương. Product khác có thể cùng version. CHECK: version > 0. |
| `status` | `text` | Không | 'draft' | draft: chưa submit; in_review: đã submit chờ duyệt; approved: kiến thức được duyệt; rejected: không được chấp nhận. CHECK: status IN ('draft','in_review','approved','rejected'). |
| `data` | `jsonb` | Không | — | JSON kiến thức chuẩn: identity, pricing, features, audience, USP, limitations, brand và claims. Fact phải liên kết nguồn hoặc ghi rõ origin theo hợp đồng JSON. |
| `sources` | `jsonb` | Không | — | JSON danh mục nguồn: source ID, URL, thời điểm crawl, hash, đoạn bằng chứng và Storage path. Cần phân biệt dữ liệu crawl với suy luận/merchant nhập. |
| `approved_by` | `uuid` | Có | — | Tài khoản **merchant sở hữu product** đã duyệt PKB; không chỉ là tác giả nội dung. Theo PLANNED, admin không approve PKB. Xem GAP (ngữ nghĩa reject) bên dưới: cột này mang tên theo đường approve. FK → auth.users.id. |
| `approved_at` | `timestamptz` | Có | — | Thời điểm PKB được phê duyệt. Bắt buộc khi status=approved. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

**Khóa/index được khai báo ở cấp bảng:**

- `(product_id, version) [pk]`

**CHECK kết hợp nhiều trường trong DBML:**

- `status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)`

#### Quyền duyệt PKB (PLANNED — chưa enforce)

Các rule dưới đây là thiết kế đã duyệt cho phần duyệt PKB. Task này **không** thêm migration, trigger, RLS hay RPC nào để thực thi chúng.

**Vòng đời:** `draft → in_review → approved | rejected`. `in_review` là trạng thái merchant đã submit và đang chờ duyệt; `approved` cần merchant approve; `rejected` có thể do admin set khi vi phạm policy. Không thêm rule resubmit hay chuyển trạng thái nào ngoài chuỗi này.

- **Chỉ merchant sở hữu product được approve PKB của product đó**, suy theo `products.merchant_id`. Không merchant khác hay creator nào approve được.
- **Admin chỉ được reject PKB khi vi phạm policy**, và lần reject đó phải ghi lý do; **lý do phải được giữ lại**.
- **Admin không được sửa hoặc approve nội dung PKB.**
- **Cả approve và reject đều phải ghi actor và timestamp.**

**GAP (lý do reject):** ERD **không** có cột hay field JSON nào lưu được **lý do reject theo policy**. `approved_by` / `approved_at` chỉ ghi actor và timestamp. `data` và `sources` là payload PKB v0.2 bị ràng buộc schema (`additionalProperties: false`), không phải chỗ chứa lý do kiểm duyệt. Task này **không** thêm cột/bảng chưa được duyệt để biểu diễn lý do; gap này được báo lại để #23 quyết.

**GAP (ngữ nghĩa reject):** `approved_by` / `approved_at` mang tên theo **đường approve**. Dùng chúng để ghi **actor của rejection** là không nhất quán về ngữ nghĩa. Có thể cần một cột riêng như `reviewed_action` hoặc `rejection_actor`; quyết định **hoãn sang Issue #23**. Task này không thêm cột/bảng nào.

**CONFLICT lịch sử (đã note, không bỏ qua):** thay đổi status ở trên **được áp theo phê duyệt của Issue #23**. Xung đột lịch sử với SRS FR-PI-03 và đặc tả M1 FR-07 (hai tài liệu chỉ liệt kê `draft / in_review / approved`) được **đánh dấu để cập nhật trong chính 2 spec đó**; việc cập nhật đặc tả M1 v0.3 được theo dõi ở Issue #23.

**CONFLICT (admin và approve):** BRD (mục 5.3, dòng 542), SRS FR-PI-03 (dòng 356), đặc tả M1 FR-07 (dòng 143) và qa-log #1 / decision-log #11 đều nói **Platform Admin không tham gia từng lần approve PKB trong MVP**. Rule admin policy-reject ở trên chưa được đồng bộ với các tài liệu đó; theo ghi chú ưu tiên trong chính BRD/SRS, các tài liệu đã chốt được ưu tiên cho tới khi được cập nhật. Xem issue #23.

### 6. `campaigns` — Chiến dịch quảng bá

**Một row:** Một chiến dịch của merchant, quảng bá đúng một product.

**Quy tắc và quyền sử dụng:** Composite FK (product_id, merchant_id) bảo đảm product thuộc merchant. Join đầu tiên khóa row campaign, đặt terms_locked_at rồi snapshot trong cùng transaction. Sau khóa không đổi owner/product/commission/currency. Muốn đổi commission tạo campaign mới. Duyệt claim mới có thể buộc archive video cũ và tạo revision, không mở khóa video approved.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `merchant_id` | `uuid` | Không | — | Hồ sơ merchant sở hữu product/campaign; khác với auth.users.id. FK → merchants.id. |
| `product_id` | `uuid` | Không | — | Product mà bản ghi thuộc về; không phải ID của merchant. |
| `name` | `text` | Không | — | Tên chiến dịch quảng bá. |
| `slug` | `text` | Không | — | Định danh URL duy nhất của campaign. UNIQUE. |
| `description` | `text` | Có | — | Mô tả tổng quan chiến dịch. |
| `start_date` | `timestamptz` | Không | — | Thời điểm bắt đầu campaign. |
| `end_date` | `timestamptz` | Không | — | Thời điểm kết thúc; phải sau start_date. |
| `target_audience` | `text` | Có | — | Mô tả nhóm khách hàng mục tiêu. |
| `target_countries` | `text[]` | Có | — | Danh sách quốc gia mục tiêu. NULL hiện không tự mang nghĩa toàn cầu; FE/BE cần thống nhất cách hiểu. |
| `target_language` | `text` | Không | — | Ngôn ngữ campaign. MVP triển khai một ngôn ngữ dù vẫn lưu thuộc tính này để truy vết. |
| `content_brief` | `text` | Có | — | Yêu cầu nội dung merchant giao cho AI/creator. |
| `approved_claims` | `text[]` | Có | — | Các tuyên bố được phép dùng; không thay thế việc chứng minh fact và kiểm duyệt video. |
| `forbidden_claims` | `text[]` | Có | — | Các tuyên bố bị cấm trong nội dung. |
| `cta` | `text` | Có | — | Lời kêu gọi hành động, ví dụ đăng ký dùng thử sản phẩm. |
| `commission_type` | `text` | Không | — | flat: số tiền cố định; percentage: phần trăm của cơ sở doanh thu đã chốt. Không có recurring commission. CHECK: commission_type IN ('flat','percentage'). |
| `commission_value` | `numeric(12,4)` | Không | — | Giá trị commission. Ví dụ flat=5 nghĩa 5 USD; percentage=20 nghĩa 20%, không phải 0,20. |
| `currency` | `varchar(3)` | Không | — | Đơn vị tiền tệ. MVP chỉ xử lý USD; không thực hiện quy đổi nhiều tiền tệ. CHECK: currency = 'USD'. |
| `terms_locked_at` | `timestamptz` | Có | — | Mốc khóa terms vĩnh viễn, server đặt trong transaction tạo enrollment đầu tiên. Không cho client gán hoặc xóa. |
| `status` | `text` | Không | 'draft' | draft: chuẩn bị; active: đang nhận hoạt động; paused: tạm dừng; ended: đã kết thúc; archived: lưu trữ. CHECK không tự thực thi lịch chuyển trạng thái. CHECK: status IN ('draft','active','paused','ended','archived'). |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

**Khóa/index được khai báo ở cấp bảng:**

- `(id, product_id) [unique]`
- `status`

**CHECK kết hợp nhiều trường trong DBML:**

- `end_date > start_date`
- `commission_value >= 0 AND (commission_type <> 'percentage' OR commission_value <= 100)`

### 7. `creator_campaigns` — Creator tham gia campaign

**Một row:** Một cặp creator–campaign duy nhất trong suốt pilot.

**Quy tắc và quyền sử dụng:** Unique (creator_id, campaign_id). Rejoin dùng row cũ, giữ joined_at và snapshot, xóa left_at; removed chỉ admin khôi phục. Không xóa hoặc chuyển enrollment sang creator/campaign khác. Snapshot và mốc khóa phải được tạo dưới cùng khóa campaign để tránh race condition.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `creator_id` | `uuid` | Không | — | Hồ sơ creator sở hữu hoặc tham gia bản ghi; khác với auth.users.id. FK → creators.id. |
| `campaign_id` | `uuid` | Không | — | Campaign mà bản ghi thuộc về; liên kết tới sản phẩm và merchant thông qua campaign. FK → campaigns.id. |
| `status` | `text` | Không | 'active' | active: đang tham gia; left: creator đã rời; removed: bị quản trị loại khỏi campaign. CHECK: status IN ('active','left','removed'). |
| `commission_type_snapshot` | `text` | Không | — | Loại commission chụp lại từ campaign tại lần tham gia đầu tiên; client không nhập và không sửa. CHECK: commission_type_snapshot IN ('flat','percentage'). |
| `commission_value_snapshot` | `numeric(12,4)` | Không | — | Mức commission được cố định cho enrollment; giữ nguyên cả khi rejoin. |
| `currency_snapshot` | `varchar(3)` | Không | — | Đơn vị tiền tệ chụp lại cùng terms; chỉ USD. CHECK: currency_snapshot = 'USD'. |
| `joined_at` | `timestamptz` | Không | `now()` | Thời điểm tham gia đầu tiên, không thay bằng thời điểm rejoin. |
| `left_at` | `timestamptz` | Có | — | Thời điểm rời/bị loại; NULL khi active. Rejoin xóa left_at nhưng giữ joined_at và snapshot. |
| `updated_at` | `timestamptz` | Không | `now()` | Thời điểm cập nhật gần nhất. Default chỉ xử lý INSERT; cần trigger để tự cập nhật khi UPDATE. |

**Khóa/index được khai báo ở cấp bảng:**

- `(creator_id, campaign_id) [unique]`
- `(id, creator_id, campaign_id) [unique]`
- `status`

**CHECK kết hợp nhiều trường trong DBML:**

- `commission_value_snapshot >= 0 AND (commission_type_snapshot <> 'percentage' OR commission_value_snapshot <= 100)`
- `(status = 'active' AND left_at IS NULL) OR (status IN ('left','removed') AND left_at IS NOT NULL)`

### 8. `content_scripts` — Ý tưởng và kịch bản

**Một row:** Một script gắn campaign, product và version PKB cụ thể.

**Quy tắc và quyền sử dụng:** Hai composite FK bảo đảm cùng product và PKB. API sync có authorization/idempotency; backend ghi, merchant/admin đọc, creator nhận video đã duyệt. Script đã dùng không sửa; revision tạo row mới. Phương thức lưu idempotency của sync API là chi tiết triển khai chưa có cột riêng ở bảng này.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `campaign_id` | `uuid` | Không | — | Campaign mà bản ghi thuộc về; liên kết tới sản phẩm và merchant thông qua campaign. |
| `product_id` | `uuid` | Không | — | Product mà bản ghi thuộc về; không phải ID của merchant. |
| `knowledge_version` | `int` | Không | — | Version PKB được dùng để tạo script. FK ghép với product_id để tránh dùng kiến thức product khác. |
| `idea` | `text` | Có | — | Ý tưởng/concept nội dung, gộp ở đây thay vì bảng content_ideas riêng. |
| `hook` | `text` | Có | — | Câu/ý mở đầu nhằm thu hút người xem. |
| `intent` | `text` | Có | — | Mục tiêu nội dung: awareness (nhận biết), education (giáo dục), consideration (cân nhắc), conversion (chuyển đổi). CHECK: intent IN ('awareness','education','consideration','conversion'). |
| `script_text` | `text` | Không | — | Toàn bộ kịch bản dùng để dựng video; là dữ liệu đầu vào có thể truy vết. |
| `platform` | `text` | Không | — | Nền tảng đích, ví dụ TikTok hoặc YouTube. DBML chưa quy định danh sách giá trị hợp lệ. |
| `language` | `text` | Không | — | Ngôn ngữ nội dung/hồ sơ; định dạng mã ngôn ngữ cần thống nhất trong validation. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

**Khóa/index được khai báo ở cấp bảng:**

- `(id, campaign_id) [unique]`
- `campaign_id`

### 9. `generation_jobs` — Theo dõi công việc AI

**Một row:** Một công việc crawl hoặc dựng một output video, có retry trên cùng job.

**Quy tắc và quyền sử dụng:** Crawl bắt buộc script_id NULL, video bắt buộc có script. Worker kiểm tra script cùng product, claim nguyên tử và retry có giới hạn. Một request mới có chủ đích dùng key mới. Schema lưu trạng thái nhưng chưa tự cung cấp worker queue, lease hay lịch retry.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `product_id` | `uuid` | Không | — | Product mà bản ghi thuộc về; không phải ID của merchant. FK → products.id. |
| `content_script_id` | `uuid` | Có | — | NULL cho crawl job; bắt buộc cho video job. Script được chọn phải thuộc cùng product với job. FK → content_scripts.id. |
| `job_type` | `text` | Không | — | crawl: thu thập/tạo PKB; video: dựng video từ script. Script generation chạy API đồng bộ, không có job_type=script trong MVP. CHECK: job_type IN ('crawl','video'). |
| `status` | `text` | Không | 'queued' | queued: chờ; running: đang chạy; completed: hoàn tất; failed: thất bại. CHECK: status IN ('queued','running','completed','failed'). |
| `idempotency_key` | `text` | Không | — | Khóa duy nhất chống tạo lại cùng công việc khi retry. Một yêu cầu chạy mới có chủ đích dùng khóa mới. UNIQUE. |
| `input_snapshot` | `jsonb` | Không | — | JSON bản chụp đầu vào tại thời điểm chạy: URL/input hoặc script, phiên bản PKB, cấu hình provider/template liên quan. |
| `result_manifest` | `jsonb` | Có | — | JSON tham chiếu kết quả như PKB version, video ID, Storage path; không phải nơi lưu kiến thức chuẩn thứ hai. |
| `error` | `text` | Có | — | Thông tin lỗi của job để vận hành/debug; không nên trả chi tiết nhạy cảm cho creator. |
| `attempts` | `int` | Không | 0 | Bộ đếm số lần thử do worker quản lý. Cần thống nhất thời điểm tăng khi worker nhận việc. CHECK: attempts >= 0. |
| `tokens_in` | `int` | Có | — | Tổng token vào của job, DB suy ra từ `cost_breakdown`; worker không ghi trực tiếp. Chỉ cộng item `llm`. NULL khi chưa có dữ liệu chi phí. |
| `tokens_out` | `int` | Có | — | Tổng token ra của job, DB suy ra từ `cost_breakdown`; worker không ghi trực tiếp. Chỉ cộng item `llm`. NULL khi chưa có dữ liệu chi phí. |
| `cost_usd` | `numeric(12,6)` | Có | — | Tổng chi phí job bằng USD, DB suy ra từ `cost_breakdown`. 6 chữ số thập phân; không dùng làm tròn 4 chữ số. NULL khi chưa có dữ liệu chi phí. |
| `cost_breakdown` | `jsonb` | Có | `'{}'` | Chi tiết chi phí theo contract `cost_breakdown` v1 (`docs/specs/contracts/`). **Worker chỉ ghi cột này**; 3 cột tổng phía trên do DB suy ra. `{}` nghĩa là **chưa ghi dữ liệu chi phí**, không phải job tốn 0 USD, và `{}` **không phải** payload v1 hợp lệ. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |
| `finished_at` | `timestamptz` | Có | — | Thời điểm job kết thúc. DBML cho NULL và chưa có CHECK bắt buộc theo trạng thái; worker phải ghi đúng. |

**Giới hạn nullability (cost):** đầu vào chỉ nêu default `'{}'` cho `cost_breakdown`. Với `tokens_in`, `tokens_out`, `cost_usd` không đầu vào nào nêu NOT NULL hoặc default, nên DBML ghi chúng là nullable và **các thuộc tính này để mở**, không tự quyết. Không suy nullability/default của cột database từ yêu cầu JSON Schema của từng item chi phí.

**Chi phí và token (PLANNED — issue #23, contract `cost_breakdown` v1):** worker chỉ ghi `cost_breakdown`; DB suy ra `tokens_in`, `tokens_out`, `cost_usd`. Việc tổng hợp, suy dẫn, validation, hạn chế ghi, giới hạn ngân sách và cảnh báo **chưa được triển khai** trong task này (không thêm trigger, generated column hay RPC). Retry là item bổ sung và được cộng vào tổng theo contract đã merge; job `failed` vẫn giữ chi phí đã tiêu. `cost_usd` dùng `numeric(12,6)`. Hành vi cache, cách tính token và `cost_status` theo đúng contract v1. BE dự kiến kiểm thêm: (a) `call_id` duy nhất trong `items`, (b) `tokens_in_cached <= tokens_in` cho từng item liên quan. Chi phí `estimated` phải phân biệt được với `exact` bằng `cost_status` của item.

**CHECK kết hợp nhiều trường trong DBML:**

- `(job_type = 'crawl' AND content_script_id IS NULL) OR (job_type = 'video' AND content_script_id IS NOT NULL)`

### 10. `videos` — Video và gói nội dung đăng

**Một row:** Một video đã có file output, cùng caption/hashtag/evidence và QA.

**Quy tắc và quyền sử dụng:** Một job tối đa một video; variant/revision là row videos khác qua parent_video_id. Admin duyệt và khóa vĩnh viễn cả nội dung, lineage, evidence và approval metadata. Archived không mở khóa. File bytes cũng phải bất biến tại Storage path. Creator chỉ nhận DTO an toàn, không được đọc toàn bộ evidence/review notes.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `campaign_id` | `uuid` | Không | — | Campaign mà bản ghi thuộc về; liên kết tới sản phẩm và merchant thông qua campaign. FK → campaigns.id. |
| `content_script_id` | `uuid` | Không | — | Kịch bản được dùng làm đầu vào tạo video. |
| `generation_job_id` | `uuid` | Không | — | Job tạo ra video, duy nhất trên bảng videos: một job có tối đa một row output video. UNIQUE; FK → generation_jobs.id. |
| `parent_video_id` | `uuid` | Có | — | Video gốc nếu đây là revision/variant. Có thể NULL; phải khác chính nó và cùng campaign theo gate triển khai. FK → videos.id. |
| `storage_path` | `text` | Không | — | Đường dẫn đối tượng trong Storage, không phải URL tải công khai. Backend cấp URL tải có kiểm soát. |
| `thumbnail_path` | `text` | Có | — | Đường dẫn ảnh thumbnail trong Storage. |
| `caption` | `text` | Không | — | Nội dung mô tả đi kèm video để creator copy khi đăng. |
| `hashtags` | `text[]` | Có | — | Danh sách hashtag của gói nội dung. NULL chưa được đồng nhất với mảng rỗng trong DBML. |
| `cta` | `text` | Có | — | Lời kêu gọi hành động, ví dụ đăng ký dùng thử sản phẩm. |
| `posting_instructions` | `text` | Có | — | Hướng dẫn creator đăng: format, disclosure hoặc lưu ý dùng link. |
| `first_approved_at` | `timestamptz` | Có | — | Mốc lần đầu được duyệt. Khác reviewed_at ở vai trò khóa vĩnh viễn; không được xóa hoặc sửa sau khi đã đặt. |
| `evidence` | `jsonb` | Không | — | JSON bằng chứng hỗ trợ claim trong video: source ID, bản test, kết quả test, recording và đường dẫn liên quan. Không được lộ toàn bộ cho creator qua SELECT *. |
| `review_notes` | `text` | Có | — | Ghi chú nội bộ của admin, vẫn được sửa sau phê duyệt. Không dùng để thay đổi ngầm evidence hoặc nội dung đã duyệt. |
| `merchant_flagged_at` | `timestamptz` | Có | — | Thời điểm merchant báo video. Server cấp giá trị; client không gửi. NULL nghĩa là chưa có báo cáo. |
| `merchant_flag_reason` | `text` | Có | — | Lý do merchant gửi kèm báo cáo; phải không rỗng khi có báo cáo. NULL khi chưa báo cáo. |
| `status` | `text` | Không | 'pending_review' | pending_review: chờ QA; approved: được phát hành; rejected: không đạt; archived: không phát hành mới. Video đã approved chỉ chuyển sang archived. CHECK: status IN ('pending_review','approved','rejected','archived'). |
| `reviewed_by` | `uuid` | Có | — | Tài khoản admin duyệt video; metadata của lần approval gốc bị khóa sau first_approved_at. FK → auth.users.id. |
| `reviewed_at` | `timestamptz` | Có | — | Thời điểm review. Trước approval có thể phản ánh xử lý review; sau approval metadata gốc phải được giữ nguyên. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

**Khóa/index được khai báo ở cấp bảng:**

- `(id, campaign_id) [unique]`
- `campaign_id`
- `status`

**CHECK kết hợp nhiều trường trong DBML:**

- `status <> 'approved' OR first_approved_at IS NOT NULL`
- `first_approved_at IS NULL OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND status IN ('approved','archived'))`

**Giới hạn CHECK:** CHECK bảo đảm metadata tồn tại theo trạng thái; không tự chặn sửa metadata/nội dung. Cần trigger bảo vệ cả OLD và NEW, kể cả khi cập nhật đồng thời nội dung và status.

**Merchant báo video (PLANNED — chưa enforce):** hai cột `merchant_flagged_at` và `merchant_flag_reason` chưa được thực thi: task này không thêm trigger, RPC hay policy nào.

- Chỉ **merchant sở hữu product của video** được báo video đó. Quyền sở hữu suy theo chuỗi video → campaign → product → merchants (`merchant_id`), không dựa vào bảng videos.
- Một báo cáo hợp lệ cần **timestamp và lý do không rỗng**; `merchant_flagged_at` do **server cấp**, client không gửi.
- Báo cáo **không** tự approve, reject, archive hay xóa video, và **không** đổi `status`.
- **Admin vẫn chịu trách nhiệm duyệt video** (`first_approved_at`, `reviewed_by`, `reviewed_at`).
- Hai cột này lưu tối đa **một báo cáo hiện hành**: chúng **không** cung cấp lịch sử báo cáo và **không** phải quy trình kiểm duyệt.
- **Hành vi khi báo cáo lặp lại / ghi đè CHƯA được chốt** trong task này. Không thêm bảng report, status kiểm duyệt, logic tự động gỡ video hay trường audit khác.

**SQL REQUIRED (chưa implement):** khi `merchant_flagged_at IS NOT NULL` thì `merchant_flag_reason` phải **không rỗng**. CHECK:

```sql
(merchant_flagged_at IS NULL AND merchant_flag_reason IS NULL)
OR (merchant_flagged_at IS NOT NULL
    AND merchant_flag_reason IS NOT NULL
    AND char_length(btrim(merchant_flag_reason)) > 0)
```

### 11. `published_posts` — Bài đăng dự kiến hoặc đã đăng

**Một row:** Một lần creator chọn video để đăng trên một account.

**Quy tắc và quyền sử dụng:** Post được tạo từ lúc selected để nhận tracking link trước khi đăng. Client INSERT chỉ account_id/video_id; server suy ra owner/enrollment/campaign. Composite FK enforce cùng creator/campaign; RLS vẫn bắt buộc để tránh dùng ID người khác. Relationship IDs bất biến ngay từ đầu. confirm_post ghi URL/thời gian và status; views là dữ liệu thủ công.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `creator_campaign_id` | `uuid` | Không | — | Enrollment được server suy ra từ creator đang đăng nhập và campaign của video. |
| `creator_id` | `uuid` | Không | — | Creator từ auth.uid(); lưu trực tiếp để enforce composite FK và owner RLS, không cho client tự gán. |
| `campaign_id` | `uuid` | Không | — | Campaign lấy từ video, không phải dữ liệu client được tùy ý gửi. |
| `creator_account_id` | `uuid` | Không | — | Account mạng xã hội do creator chọn; FK ghép bắt buộc thuộc đúng creator của post. |
| `video_id` | `uuid` | Không | — | Video được creator chọn; FK ghép bắt buộc thuộc campaign của enrollment. |
| `status` | `text` | Không | 'selected' | selected: đã chọn video nhưng có thể chưa đăng; published: đã xác nhận đăng; removed: đã gỡ/loại, trạng thái kết thúc. CHECK: status IN ('selected','published','removed'). |
| `post_url` | `text` | Có | — | URL bài đăng thực tế. Có thể NULL khi selected; phải có khi published; unique sau chuẩn hóa URL. UNIQUE. |
| `posted_at` | `timestamptz` | Có | — | Thời điểm bài được đăng trên nền tảng, do creator gửi qua confirm_post và backend kiểm tra. |
| `views` | `bigint` | Không | 0 | Tổng lượt xem hiện tại nhập thủ công; không phải số tăng thêm mỗi ngày. Giá trị mặc định 0 không chứng minh đã đo được 0 views. CHECK: views >= 0. |
| `views_updated_at` | `timestamptz` | Có | — | Thời điểm cập nhật views gần nhất do server ghi. NULL thể hiện chưa có lần cập nhật metric được ghi nhận. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

**Khóa/index được khai báo ở cấp bảng:**

- `campaign_id`
- `creator_campaign_id`
- `status`

**CHECK kết hợp nhiều trường trong DBML:**

- `status <> 'published' OR (post_url IS NOT NULL AND posted_at IS NOT NULL)`

### 12. `tracking_links` — Link affiliate có tracking

**Một row:** Một link redirect riêng cho một post.

**Quy tắc và quyền sử dụng:** Một post có 0 hoặc 1 tracking link; link có đúng một post. Backend tạo destination từ affiliate_url và thêm click_id theo hợp đồng merchant. Link active vẫn bị từ chối nếu không đạt điều kiện campaign/enrollment/video/post. Post selected vẫn có thể có link trước URL đăng thật; link không chứng minh bài đã được đăng.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `published_post_id` | `uuid` | Không | — | Post dự kiến hoặc đã đăng mà link thuộc về; UNIQUE đảm bảo tối đa một link cho mỗi post. UNIQUE; FK → published_posts.id. |
| `slug` | `text` | Không | — | Mã ngắn duy nhất dùng trong route redirect, ví dụ /r/abc123. UNIQUE. |
| `destination_url` | `text` | Không | — | Đích redirect đã được backend kiểm tra và tạo từ affiliate_url của product; không nhận tùy ý từ client. |
| `status` | `text` | Không | 'active' | active: link có thể được xử lý; disabled: link bị vô hiệu. Active vẫn phải qua kiểm tra enrollment/campaign/video khi click. CHECK: status IN ('active','disabled'). |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

### 13. `tracking_events` — Lượt click được quan sát

**Một row:** Một lượt truy cập redirect hợp lệ được server ghi nhận.

**Quy tắc và quyền sử dụng:** Mỗi lần redirect có click_id riêng, không có commission cho click. Đếm row là raw clicks, không đồng nghĩa unique humans. Click lịch sử có thể tiếp tục được attribution trong window sau khi creator rời/campaign kết thúc; không phát sinh click hợp lệ mới nếu bị chặn.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | ID của một click, đồng thời là click_id gửi sang merchant để liên kết signup/payment về nguồn phân phối. PK. |
| `tracking_link_id` | `uuid` | Không | — | Link đã được truy cập, từ đó truy ra post → creator/campaign/video. FK → tracking_links.id. |
| `event_type` | `text` | Không | 'click' | Trong MVP luôn là click; chưa thu thập impression hoặc landing event riêng. CHECK: event_type = 'click'. |
| `visitor_id` | `text` | Có | — | Định danh khách truy cập ẩn danh nếu có. Không được dùng riêng lẻ để tự suy đoán attribution. |
| `occurred_at` | `timestamptz` | Không | `now()` | Thời điểm server ghi nhận redirect/click; không phải thời điểm conversion. |

**Khóa/index được khai báo ở cấp bảng:**

- `(tracking_link_id, occurred_at)`

### 14. `conversions` — Sự kiện đăng ký dùng thử và thanh toán

**Một row:** Một event từ merchant: signup, trial hoặc paid.

**Quy tắc và quyền sử dụng:** Backend xác minh nguồn, product, customer và click; idempotency theo event/order. Valid paid phải được xử lý eligibility trước commit, không để pending đã commit. Khác occurred_at và received_at nên first accepted không phải first occurred. Void trước payout phải đồng thời reverse commission nếu có. Không tự suy attribution chỉ từ visitor_id.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `product_id` | `uuid` | Không | — | Product mà bản ghi thuộc về; không phải ID của merchant. FK → products.id. |
| `attributed_click_id` | `uuid` | Có | — | Click được xác minh để ghi công cho conversion. NULL nghĩa chưa có attribution hợp lệ. FK → tracking_events.id. |
| `source` | `text` | Không | — | Namespace ổn định của hệ thống merchant/integration. Import và webhook cùng nguồn phải dùng chung giá trị để không né chống trùng. |
| `external_event_id` | `text` | Không | — | ID sự kiện ở nguồn merchant, chống xử lý trùng cùng webhook/import trong phạm vi product + source. |
| `external_user_id` | `text` | Không | — | ID khách hàng ở hệ thống merchant. Không phải tài khoản creator hoặc auth.users của platform. |
| `external_order_id` | `text` | Có | — | ID payment/invoice của paid event; không phải subscription ID. Bắt buộc cho paid; phải NULL với signup/trial. |
| `event_type` | `text` | Không | — | signup: đăng ký; trial: bắt đầu dùng thử; paid: thanh toán. Đây là event table, không phải một row cho toàn bộ vòng đời customer. CHECK: event_type IN ('signup','trial','paid'). |
| `amount` | `numeric(14,2)` | Có | — | Số tiền giao dịch paid, không âm. Signup/trial phải NULL, không dùng 0 thay cho không áp dụng. Không nhất thiết bằng basis_amount tính commission. CHECK: amount >= 0. |
| `currency` | `varchar(3)` | Có | — | Chỉ có ở paid event và phải là USD; signup/trial bắt buộc NULL. |
| `status` | `text` | Không | 'valid' | valid: sự kiện đang được công nhận; voided: sự kiện đã bị hủy trong phạm vi xử lý cho phép. Khác eligibility_status. CHECK: status IN ('valid','voided'). |
| `void_reason` | `text` | Có | — | Lý do hủy, bắt buộc khi status=voided. |
| `eligibility_status` | `text` | Không | 'not_applicable' | Nhãn kết quả xét commission: not_applicable, pending, eligible, already_claimed hoặc unattributed. Chỉ backend được ghi. |
| `eligibility_checked_at` | `timestamptz` | Có | — | Thời điểm hoàn tất đánh giá eligibility của paid event; server ghi cùng kết quả xử lý. |
| `attribution_snapshot` | `jsonb` | Có | — | JSON giải thích attribution: click được chọn/ID bị từ chối, policy version, cửa sổ thời gian và lý do quyết định. Không phải bằng chứng tự khai của creator. |
| `occurred_at` | `timestamptz` | Không | — | Thời điểm signup/trial/payment xảy ra theo merchant; có thể trước received_at. |
| `received_at` | `timestamptz` | Không | `now()` | Thời điểm platform nhận và tạo row. Thứ tự event đến không nhất thiết trùng thứ tự occurred_at. |

**Khóa/index được khai báo ở cấp bảng:**

- `(product_id, source, external_event_id) [unique]`
- `(product_id, source, external_order_id) [unique]`
- `(product_id, source, external_user_id)`
- `(id, product_id, source, external_user_id) [unique]`
- `eligibility_status`

**CHECK kết hợp nhiều trường trong DBML:**

- `(event_type = 'paid' AND external_order_id IS NOT NULL AND amount IS NOT NULL AND currency IS NOT NULL) OR (event_type IN ('signup','trial') AND external_order_id IS NULL AND amount IS NULL AND currency IS NULL)`
- `status <> 'voided' OR void_reason IS NOT NULL`
- `eligibility_status IN ('not_applicable','pending','eligible','already_claimed','unattributed')`
- `event_type = 'paid' OR (eligibility_status = 'not_applicable' AND eligibility_checked_at IS NULL)`
- `eligibility_status NOT IN ('eligible','already_claimed','unattributed') OR (event_type = 'paid' AND eligibility_checked_at IS NOT NULL)`
- `eligibility_status <> 'eligible' OR attributed_click_id IS NOT NULL`
- `eligibility_status <> 'unattributed' OR attributed_click_id IS NULL`
- `event_type <> 'paid' OR currency = 'USD'`

**Giới hạn CHECK:** default not_applicable không đủ cho paid hợp lệ. RPC phải gán pending rồi kết quả cuối trong cùng transaction. DBML chưa tự cấm một paid valid commit ở pending/not_applicable; gate này phải được enforce khi triển khai.

### 15. `commission_eligibility` — Quyền xét commission một lần

**Một row:** Một customer key đã tiêu thụ quyền xét commission của một product.

**Quy tắc và quyền sử dụng:** PK(product_id, source, external_user_id). Conversion được INSERT trước; claim gate trong cùng RPC bằng ON CONFLICT với đúng customer key. Không có attribution vẫn chiếm quyền. Bảng append-only; không UPDATE/DELETE sau refund. FK ghép bảo đảm customer key đúng conversion; logic còn phải kiểm paid valid và enrollment của click.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `product_id` | `uuid` | Không | — | Thành phần khóa khách hàng: quyền hưởng một lần được xét theo product, không theo từng campaign. FK → products.id. |
| `source` | `text` | Không | — | Thành phần khóa khách hàng: namespace khách hàng của merchant/integration; phải canonical để tránh cùng người bị coi là hai khách. |
| `external_user_id` | `text` | Không | — | Thành phần khóa khách hàng: ID customer trong source. Ba trường cùng tạo PK, bảng không có id riêng. |
| `first_paid_conversion_id` | `uuid` | Không | — | Paid conversion hợp lệ đầu tiên claim thành công eligibility theo thứ tự xử lý của hệ thống. UNIQUE. |
| `first_creator_campaign_id` | `uuid` | Có | — | Enrollment thắng attribution của paid đầu tiên. NULL nếu paid đầu tiên không có attribution hợp lệ; khi đó vẫn chiếm eligibility. FK → creator_campaigns.id. |
| `claimed_at` | `timestamptz` | Không | `now()` | Thời điểm quyền được claim trong transaction. Không thay thế timestamp mua hàng và không tự chứng minh đây là lần mua đầu tiên trong đời customer. |

**Khóa/index được khai báo ở cấp bảng:**

- `(product_id, source, external_user_id) [pk]`
- `(first_paid_conversion_id, first_creator_campaign_id) [unique]`

### 16. `commissions` — Khoản thu nhập của creator

**Một row:** Một khoản commission cho paid conversion thắng eligibility và có attribution.

**Quy tắc và quyền sử dụng:** Composite FK buộc (conversion_id, enrollment) khớp eligibility; UNIQUE conversion_id chống nhiều commission cùng event. Amount và calculation không sửa sau tạo. Manual settlement sau hold; payout và void cùng khóa conversion rồi commission. Reversed giữ amount gốc nhưng loại khỏi earnings. Chưa có wallet hoặc API chi tiền tự động.

| Thuộc tính | Kiểu | NULL | Mặc định | Mô tả nghiệp vụ |
|---|---|---|---|---|
| `id` | `uuid` | Không | `gen_random_uuid()` | Định danh duy nhất của bản ghi; dùng để tham chiếu từ các bảng khác. PK. |
| `conversion_id` | `uuid` | Không | — | Paid conversion được dùng tính commission. UNIQUE giới hạn một commission/conversion; composite FK còn buộc đây là conversion thắng eligibility. UNIQUE; FK → conversions.id. |
| `creator_campaign_id` | `uuid` | Không | — | Enrollment thực sự được hưởng; phải khớp enrollment trong eligibility, không chỉ tồn tại trong creator_campaigns. FK → creator_campaigns.id. |
| `basis_amount` | `numeric(14,2)` | Không | — | Số tiền làm cơ sở tính hoa hồng theo revenue_basis đã chốt, ví dụ phần doanh thu hợp lệ sau các khoản loại trừ. CHECK: basis_amount >= 0. |
| `amount` | `numeric(14,2)` | Không | — | Số commission được ghi nhận bằng USD. Percentage tính trên basis_amount; flat lấy mức cố định. Số gốc không sửa khi reversal. CHECK: amount >= 0. |
| `currency` | `varchar(3)` | Không | — | Đơn vị tiền tệ. MVP chỉ xử lý USD; không thực hiện quy đổi nhiều tiền tệ. CHECK: currency = 'USD'. |
| `calculation_snapshot` | `jsonb` | Không | — | JSON công thức đã áp dụng: snapshot type/value, revenue basis, làm tròn và policy version để giải thích số tiền lịch sử. |
| `status` | `text` | Không | 'pending' | pending: chờ đối soát; approved: đã duyệt; paid: đã ghi nhận trả tiền; reversed: bị đảo, loại khỏi thu nhập. CHECK: status IN ('pending','approved','paid','reversed'). |
| `approved_at` | `timestamptz` | Có | — | Thời điểm khoản commission được duyệt; bắt buộc với approved/paid. |
| `paid_at` | `timestamptz` | Có | — | Thời điểm ghi nhận đã thanh toán commission; không phải thời điểm khách hàng mua sản phẩm. |
| `payment_reference` | `text` | Có | — | Mã/chứng từ đối soát thanh toán thủ công, bắt buộc khi paid; không tự chứng minh đã gọi ngân hàng hay cổng thanh toán. |
| `payment_recorded_by` | `uuid` | Có | — | Tài khoản quản trị đã ghi nhận thanh toán, backend xác minh quyền. FK → auth.users.id. |
| `created_at` | `timestamptz` | Không | `now()` | Thời điểm tạo bản ghi trong hệ thống; giá trị mặc định được gán khi INSERT. |

**Khóa/index được khai báo ở cấp bảng:**

- `creator_campaign_id`
- `status`

**CHECK kết hợp nhiều trường trong DBML:**

- `status <> 'paid' OR (paid_at IS NOT NULL AND payment_reference IS NOT NULL AND payment_recorded_by IS NOT NULL)`
- `status NOT IN ('approved','paid') OR approved_at IS NOT NULL`

## 4. Quan hệ giữa các bảng và lý do có khóa ghép

### 4.1. Quan hệ nghiệp vụ chính

| Quan hệ | Số lượng | Ý nghĩa |
|---|---|---|
| Auth → merchant / creator | Một user có 0–1 mỗi loại profile | Cùng một user có thể đồng thời là merchant và creator. |
| Merchant → product | 1–N | Mỗi product chỉ thuộc một merchant. |
| Product → knowledge | 1–N | Nhiều phiên bản PKB, mỗi version duy nhất trong một product. |
| Product → campaign | 1–N | Nhiều chiến dịch có thể quảng bá cùng product. |
| Creator ↔ campaign | N–N qua enrollment | Mỗi cặp chỉ có một enrollment, kể cả rejoin. |
| Creator → social account | 1–N | Một creator có thể đăng trên nhiều account/nền tảng. |
| Campaign → script → video | 1–N, 1–N | Một campaign có nhiều script; một script có thể tạo nhiều video qua các job khác nhau. |
| Generation job → video | 1–0..1 | Job crawl/đang chạy/thất bại có thể không có video; video job output tối đa một video. |
| Video → post | 1–N | Cùng asset có thể được nhiều creator đăng nhiều lần. |
| Post → tracking link | 1–0..1 | Có thể chưa tạo link; khi có thì link riêng cho post đó. |
| Tracking link → click | 1–N | Mỗi redirect được ghi bằng một click ID. |
| Click → conversion | 1–N | Một click có thể dẫn tới signup, trial và paid; conversion cũng có thể không attribution. |
| Customer key → eligibility | 1–0..1 | Chưa có paid được chấp nhận thì chưa có row gate; đã claim thì giữ vĩnh viễn. |
| Eligibility → commission | 1–0..1 | Unattributed không tạo commission; attributed eligible mới có tối đa một khoản. |

### 4.2. Các composite FK đã có trong DBML

| Bảng con và tập cột | Tham chiếu | Ngăn lỗi gì |
|---|---|---|
| `products.(id, current_knowledge_version)` | `product_knowledge.(product_id, version)` | Chọn PKB hiện hành của product khác. NULL version cho phép chưa có PKB. |
| `campaigns.(product_id, merchant_id)` | `products.(id, merchant_id)` | Merchant A tạo campaign cho product thuộc merchant B. |
| `content_scripts.(campaign_id, product_id)` | `campaigns.(id, product_id)` | Script khai báo product không khớp campaign. |
| `content_scripts.(product_id, knowledge_version)` | `product_knowledge.(product_id, version)` | Script dùng version kiến thức của product khác. |
| `videos.(content_script_id, campaign_id)` | `content_scripts.(id, campaign_id)` | Video gắn script của campaign khác. |
| `published_posts.(creator_campaign_id, creator_id, campaign_id)` | `creator_campaigns.(id, creator_id, campaign_id)` | Post gắn enrollment không đúng creator/campaign. |
| `published_posts.(creator_account_id, creator_id)` | `creator_accounts.(id, creator_id)` | Post gắn social account của creator khác. |
| `published_posts.(video_id, campaign_id)` | `videos.(id, campaign_id)` | Post dùng video ngoài campaign tham gia. |
| `commission_eligibility.(first_paid_conversion_id, product_id, source, external_user_id)` | `conversions.(id, product_id, source, external_user_id)` | Eligibility mang customer key khác conversion đã claim. |
| `commissions.(conversion_id, creator_campaign_id)` | `commission_eligibility.(first_paid_conversion_id, first_creator_campaign_id)` | Trả commission cho conversion thua hoặc enrollment khác người được attribution. |

Các UNIQUE có `id` trong tập cột nhìn có vẻ lặp với PK nhưng được khai báo để làm đích FK ghép. Không tự động bỏ chúng chỉ vì ID đã unique.

FK chỉ chứng minh các ID khớp nhau. Ví dụ post có thể có ID của cùng một creator khác mà tất cả FK vẫn hợp lệ; RLS/derivation mới bảo đảm creator đó chính là người đang đăng nhập. Tương tự FK tới PKB không tự bảo đảm PKB approved.

## 5. Các luồng nghiệp vụ để đọc ERD

### 5.1. Merchant onboarding và tạo nội dung

1. User có profile merchant. Backend tạo product với website/affiliate URL và merchant_input.
2. Backend/worker tạo crawl job và xử lý input. Nguồn, assets nằm trong Storage; metadata lưu JSON, chưa có bảng asset/page riêng.
3. Worker ghi product_knowledge draft. Người có quyền kiểm tra và approve; sản phẩm trỏ tới version đã duyệt.
4. Merchant tạo campaign cho product của mình. Activation phải thỏa các gate trạng thái/PKB.
5. API tạo script đồng bộ từ PKB approved, gắn đúng product/version/campaign.
6. Worker nhận video job, tạo output videos và gói caption/hashtags. Admin review facts, evidence, brand và disclosure.
7. Approval đặt first_approved_at và khóa nội dung. Sau đó creator mới được nhận gói nội dung đã duyệt.

Quy trình không đòi phải làm ngay hệ thống crawler sâu, recommendation hoặc AI QA tự động. Tuy nhiên manual QA vẫn phải có người và thời điểm duyệt được ghi nhận.

### 5.2. Creator tham gia và đăng bài

1. User có creator active và social account thuộc mình.
2. Join campaign chạy trong transaction: khóa campaign, kiểm điều kiện, đặt terms_locked_at, chụp terms và tạo enrollment.
3. Creator gửi video_id + creator_account_id để tạo post selected. Server gán các ownership ID còn lại.
4. Backend tạo tracking link cho post selected. Chưa cần có URL bài đăng thật.
5. Creator tải video, copy caption/hashtag/link rồi đăng thủ công.
6. confirm_post nhận post_url/posted_at, kiểm owner và chuyển published.
7. Creator/admin theo quyền được thiết kế cập nhật views bằng API; cần hiển thị đây là số liệu thủ công, không phải kết quả xác minh từ social platform.

### 5.3. Click, conversion và commission

1. Khách truy cập slug; redirect handler kiểm tra campaign/enrollment/video/post.
2. Handler tạo tracking_events.id và truyền click_id sang đích merchant theo integration contract.
3. Merchant gửi event có product/source/customer/event/order IDs và click_id nếu có.
4. ingest_conversion RPC kiểm tra nguồn, policy và idempotency, sau đó INSERT conversion trước.
5. Với valid paid, RPC claim customer key trong commission_eligibility bằng cơ chế xử lý conflict nguyên tử.
6. Nếu claim thành công và attribution hợp lệ: gắn eligible, lưu enrollment thắng, tính và tạo commission.
7. Nếu claim thành công nhưng không có attribution: gắn unattributed, eligibility vẫn được giữ, không tạo commission.
8. Nếu customer đã có claim: gắn already_claimed, ghi nhận revenue hợp lệ nhưng không tạo commission mới.
9. Transaction commit khi tất cả bước cần thiết thành công; lỗi tạo commission phải rollback cả conversion/gate mới trong cùng transaction.

Không tạo gate trong BEFORE INSERT conversion: FK gate cần conversion đã được ghi. Retry cùng event/order trả kết quả cũ, không coi retry của chính winner là một lần mua mới.

### 5.4. Hủy giao dịch và ghi nhận thanh toán

- Full void trước settlement phải cập nhật conversion và reverse commission trong cùng transaction; gate eligibility vẫn giữ.
- Void và payout dùng cùng thứ tự khóa conversion → commission để không vừa thanh toán vừa hủy.
- Manual settlement ghi paid_at, payment_reference, payment_recorded_by; không thực hiện chuyển tiền tự động.
- Không hỗ trợ tự động hoàn tiền một phần hoặc thu hồi tiền sau payout. Tình huống đó cần đối soát thủ công và chính sách vận hành riêng.
- Row commission reversed giữ amount ban đầu để đọc lịch sử. Dashboard loại khỏi earnings, không xóa dữ liệu gốc.

## 6. Phân biệt các trạng thái dễ nhầm

### 6.1. Conversion status và eligibility_status

`status` trả lời **event còn được công nhận hay đã hủy**. `eligibility_status` trả lời **kết quả xét commission của event**. Không được dùng một cột thay cho cột kia.

| Eligibility status | Khi sử dụng | Tạo commission mới? | Paid valid còn tính revenue? |
|---|---|---|---|
| `not_applicable` | Signup/trial; event voided ngay khi tiếp nhận không claim | Không | Không áp dụng cho paid valid đã xử lý hoàn tất |
| `pending` | Trạng thái trung gian khi xử lý paid trong transaction | Chưa | Không được commit paid valid ở đây |
| `eligible` | Paid thắng gate và có attribution hợp lệ | Có, tối đa một | Có, nếu status vẫn valid |
| `already_claimed` | Paid khác của customer đã có gate | Không | Có |
| `unattributed` | Paid thắng gate nhưng không có attribution hợp lệ | Không | Có |

Paid đã xử lý rồi mới void giữ nhãn eligibility ban đầu cho audit, còn status đổi thành voided. Chỉ đọc nhãn eligible là chưa đủ để quyết định được thanh toán.

### 6.2. First accepted khác first occurred

Giả sử customer mua đơn A lúc 10:00 nhưng webhook đến sau đơn B mua lúc 10:05. Nếu B claim thành công trước, B là winner theo chính sách v1.3.1. A vẫn được ghi nhận nhưng không tự lấy lại eligibility. Đây là giới hạn pilot đã thể hiện trong ERD, không phải lỗi có thể sửa bằng ORDER BY đơn thuần.

Nếu merchant cần tính theo lần mua sớm nhất thực tế hoặc lifetime new customer, phải cung cấp lịch sử/định nghĩa và quy trình đối soát trước payout. ERD không tự suy được dữ liệu chưa nhận.

### 6.3. Ví dụ tài chính

Ví dụ giả định commission 20%, basis_amount bằng amount giao dịch, làm tròn đến cent:

| Sự kiện | Gate | Merchant revenue valid | Commission mới |
|---|---|---:|---:|
| Customer U mua 100 USD qua click hợp lệ, lần claim đầu | eligible | 100 USD | 20 USD |
| U mua tiếp 50 USD qua creator khác | already_claimed | 50 USD | 0 USD |
| Customer V mua 80 USD không có click hợp lệ, lần claim đầu | unattributed | 80 USD | 0 USD |
| V mua tiếp 30 USD qua click hợp lệ | already_claimed | 30 USD | 0 USD |

Tổng revenue valid là 260 USD; commission phát sinh là 20 USD. Nếu đơn đầu của U bị void trước thanh toán, khoản 20 USD bị reversed và đơn 100 USD không còn trong revenue valid. Gate của U vẫn giữ; không chuyển quyền sang lần mua 50 USD.

Đây chỉ là ví dụ để hiểu mô hình. `revenue_basis` thực tế có thể khác toàn bộ số tiền giao dịch; không mặc định 20% hoặc basis bằng amount trong code.

## 7. Hợp đồng dữ liệu JSON

ERD đã chốt **cột lưu JSON**, nhưng chưa chốt đầy đủ tên key/schema cho mọi JSON. FE, BE và AI cần thống nhất version của payload trước khi triển khai. Bảng sau là nội dung bắt buộc về ý nghĩa, không phải JSON schema máy đọc đã hoàn thiện.

| Cột | Nội dung phải thể hiện | Không nên hiểu thành |
|---|---|---|
| `products.merchant_input` | Input gốc của merchant, các trường/tài liệu được cung cấp | PKB đã approved |
| `product_knowledge.data` | Kiến thức chuẩn theo version, facts, pricing/features, origin/source ID | Một blob AI tùy ý không validate |
| `product_knowledge.sources` | Danh mục nguồn và bằng chứng có ID/path/time/hash | Quyền truy cập công khai mọi tài liệu |
| `generation_jobs.input_snapshot` | Đầu vào và cấu hình thực tế của lần chạy | Tham chiếu sống có thể đổi theo product hiện tại |
| `generation_jobs.result_manifest` | ID/path/version của kết quả | Bản dữ liệu chuẩn cạnh tranh với PKB/videos |
| `generation_jobs.cost_breakdown` | Chi tiết từng lần gọi tốn tiền theo contract `cost_breakdown` v1: `schema_version`, `currency`, `items[]` với `call_id`, `category`, `attempt`, `cache_hit`, `cost_usd`, `cost_status` | Một payload v1 hợp lệ khi giá trị là `{}`; `{}` chỉ là "chưa ghi dữ liệu chi phí", không phải job tốn 0 USD. Chi phí `estimated` vẫn là chi phí |
| `videos.evidence` | Bằng chứng cho claim cụ thể, test output/recording nếu có | Việc mặc định mọi screenshot chứng minh đã test sản phẩm |
| `conversions.attribution_snapshot` | Policy version, lý do, click/cửa sổ được kiểm tra | Chỉ một nhãn do client gửi |
| `commissions.calculation_snapshot` | Loại/mức commission, basis, rounding và policy version thực tế | Công thức lấy lại từ campaign hiện tại khi xem lịch sử |

Các bản chụp dùng để giải thích lịch sử. Khi input/terms đã được khóa, không cho đổi JSON để làm sai nội dung đã duyệt hoặc cách tính tiền đã áp dụng.

## 8. Ai được thao tác dữ liệu

Bảng này diễn giải gate quyền trong ERD; quyền cụ thể vẫn phải viết thành RLS, column grants, API authorization và Storage policy.

| Vai trò | Đọc chính | Ghi/thao tác chính | Không được tự làm |
|---|---|---|---|
| Merchant | Profile, product/PKB/campaign và kết quả thuộc mình; script theo quyền | Input product, campaign trước khi khóa, **approve PKB của product mình**, báo video bằng `merchant_flagged_at`/`merchant_flag_reason` (PLANNED) | Sửa terms đã khóa, ghi commission tùy ý, xem dữ liệu merchant khác, approve PKB của product khác |
| Creator | Profile, account, enrollment/post/earnings của mình; campaign đủ điều kiện và video approved | Profile/account được cấp quyền, join/leave, chọn video/account, confirm post, cập nhật views theo API | Tự active profile, tự chọn owner khác, tự approve video, tự ghi conversion/commission |
| Admin | Dữ liệu quản trị theo quyền | Kích hoạt/đình chỉ, **QA video**, khôi phục creator bị removed, đối soát và ghi thanh toán, **reject PKB khi vi phạm policy** (không sửa/approve PKB — PLANNED) | Bỏ qua bất biến lịch sử như sửa video đã approved hoặc xóa eligibility, **approve PKB** |
| Backend/worker | Đầu vào cần cho pipeline | Job, script, output, redirect, ingest event, eligibility và commission qua luồng được phép | Tin owner/actor/currency/amount tùy ý từ client; để lộ service credentials |
| Người truy cập link | Redirect hợp lệ | Tạo click gián tiếp thông qua handler | Ghi trực tiếp vào tracking_events hoặc bảng tài chính |

Một SELECT policy cấp row không tự ẩn cột `evidence`. Creator nhận video qua DTO/column grants phù hợp. File Storage cũng phải giữ quyền truy cập tương ứng, không chỉ bảng DB.

## 9. Cấu hình còn phải cung cấp trước launch

Các mục này không làm tăng số bảng và không thay đổi cấu trúc đã chốt. Giá trị thực tế chưa được ERD tự quyết định.

| Cấu hình/hợp đồng | Yêu cầu |
|---|---|
| `attribution_window_days` | Số ngày dương; kiểm conversion nằm trong cửa sổ tính từ click phù hợp. |
| `revenue_basis` | Cơ sở tính commission: khoản nào được tính, thuế/discount/fee xử lý thế nào. |
| `settlement_hold_days` | Số ngày không âm cần chờ trước xác nhận thanh toán. |
| `policy_version` | Phiên bản chính sách gắn trong snapshot để truy vết quyết định. |
| Returned-click policy | Merchant chọn/trả click nào, xử lý nhiều click ra sao; signup-to-paid reuse trong window khi xác minh được. |
| Customer namespace | Chuẩn hóa source/external_user_id nhất quán giữa import/webhook; tránh một customer chiếm nhiều key vì đổi tên source. |
| JSON schemas | Tên key, trường bắt buộc, origin/source và validation dùng chung FE/AI/BE. |
| Ngôn ngữ/template/provider | Chọn một bộ cụ thể cho pilot; ERD không chọn tên provider thay team. |

Không bật paid ingest khi thiếu các cấu hình bắt buộc. URL unique đã được khai báo nhưng domain unique không áp dụng; team M1 cần đồng bộ đặc tả để không tự thêm quy tắc trái ERD.

## 10. Phần DBML đã biểu diễn và phần phải triển khai thêm

| Đã thể hiện trong DBML | Phải thực thi bổ sung |
|---|---|
| Cột, kiểu, NULL/default, PK/UNIQUE | Chuẩn hóa input, chuỗi không rỗng và JSON schema |
| FK đơn và composite FK | RLS, column grants, API authorization |
| Danh sách status qua CHECK | Luồng chuyển trạng thái và điều kiện cross-table |
| Trường terms_locked_at / first_approved_at | Trigger bất biến và cập nhật nguyên tử dưới khóa |
| Eligibility gate và FK tới commission | RPC idempotent, concurrency handling, xác minh merchant/click |
| Trường timestamps | Trigger updated_at, thời điểm finished_at và các consistency gate chưa có CHECK |
| Storage path/evidence references | Storage permissions và bảo vệ không ghi đè file bytes |

DBML hợp lệ về cú pháp không đồng nghĩa SQL migration đã đầy đủ hoặc race condition đã được kiểm thử. Các Note SQL REQUIRED là acceptance criteria của task backend.

## 11. Thứ tự triển khai gợi ý

1. Kiểm tra/sửa UNIQUE Creator và bổ sung index hỗ trợ FK cho ba bảng profile hiện có.
2. Product + PKB: tạo hai bảng rồi thêm FK con trỏ current version để xử lý vòng tham chiếu; hoàn thiện approval/immutability.
3. Campaign + enrollment: ownership, terms lock, snapshot, rejoin và quyền đọc campaign.
4. Script + jobs + videos: contract AI, worker, QA và quyền tải file.
5. Post + link + click: server-derived ownership, confirm_post và redirect.
6. Conversion + eligibility + commission: tạo conversion trước gate, sau đó commission; triển khai RPC và cấu hình policy trước ingest thật.
7. Dashboard và kiểm thử đầu-cuối bằng dữ liệu pilot; đối soát giữa merchant revenue và creator earnings.

Các nhóm có thể được chia cho BE/AI/FE làm song song khi contract đã thống nhất; không đổi schema độc lập ở mỗi nhóm.

## 12. Kiểm thử bắt buộc trước nghiệm thu

- Hai request valid paid cùng customer key chạy đồng thời chỉ có một eligibility và tối đa một commission.
- Retry cùng external event/order không ghi thêm revenue hoặc commission.
- Paid đầu tiên unattributed, paid sau attributed: lần sau không được nhận commission.
- Lỗi khi tạo commission rollback conversion và eligibility mới trong transaction đó.
- Join đầu tiên chạy đồng thời với edit terms không tạo snapshot lệch commission đã khóa.
- Creator không tạo hoặc sửa post dùng account/enrollment của người khác.
- Video approved → archived vẫn không sửa được asset, evidence, caption, lineage hoặc approval metadata; file bytes cũng không bị thay thế.
- Paid void và commission payout đồng thời không cùng thành công trái điều kiện nghiệp vụ.
- Paid already_claimed/unattributed vẫn cộng doanh thu valid; signup/trial không cộng revenue.
- FK chặn commission dùng conversion/enrollment không thắng eligibility.
- Thiếu policy hoặc tiền tệ khác USD bị từ chối ở paid ingest.
- Merchant/creator không đọc được dữ liệu ngoài phạm vi hoặc private evidence qua truy vấn rộng.

## 13. Phạm vi xác minh của tài liệu

Tài liệu mô tả đủ 17 bảng được khai báo trong ERD v1.3.1, cùng các FK ghép và gate triển khai. `auth.users` chỉ là mô hình tham chiếu rút gọn; trạng thái triển khai/merge không suy ra từ ERD.

Bản v1.3.1 có 186 thuộc tính. Theo issue #23, task này thêm **6 cột đã được duyệt** vào ERD (không thêm bảng): `generation_jobs.tokens_in`, `.tokens_out`, `.cost_usd`, `.cost_breakdown` và `videos.merchant_flagged_at`, `.merchant_flag_reason` — tổng **192 thuộc tính**. Các cấu trúc JSON chi tiết và giá trị chính sách cần được ghi vào API/spec của team trước khi code phần tương ứng.
