# PKB v0.3: hợp đồng JSON

PKB là Product Knowledge Base do Module 1 tạo ra. FE, BE và AI dùng chung 1 contract này (ERD gate 2, gate 16; `docs/specs/erd/data-dictionary.md` mục 7).

- **Bản hiện hành: v0.3** (P1, issue #67). Schema máy đọc được: `pkb-data.v0.3.schema.json`, `pkb-sources.v0.3.schema.json`.
- **v0.3 là superset của v0.2.** PKB `schema_version: "0.2"` vẫn hợp lệ ở schema 0.3 và được coi là `software`. File `pkb-*.v0.2.schema.json` giữ nguyên, không sửa.
- Nguồn của schema: `spikes/m1-crawl-extract/schema.py` (v0.2) và `schema_v03.py` (v0.3, dùng lại kiểu của v0.2). Sinh lại cả 4 file bằng `uv run python export_schema.py` trong thư mục spike. File v0.2 sinh lại phải không đổi.
- Ví dụ: `examples/` (xem [Ví dụ](#ví-dụ)). Kiểm: `uv run python validate_contracts.py` trong thư mục spike.
- Đặc tả nghiệp vụ: `docs/specs/m1-product-intelligence.md` v0.4.0 (mục Output, Quy tắc trích xuất giá, Sản phẩm vật lý (P1)).
- Trạng thái: v0.3 là hợp đồng thiết kế, chưa có service nào sinh ra nó. Worker extract cho `physical` làm ở PR sau.

## Hai loại sản phẩm (`identity.product_kind`)

| Giá trị | Là gì | Input | Phần riêng |
|---|---|---|---|
| `software` | Website hoặc công cụ AI (như v0.2) | URL website | `pricing` (plans, usage_prices…) |
| `physical` | Hàng vật lý bán trên shop | Link sản phẩm trên shop | `offers[]`, `variants[]`, `specs[]`, `media.images[]` |

`product_kind` do code đặt (heuristic `classify_input_url`, xem spec M1) và người dùng sửa được ở bước 2. Bắt buộc khi `schema_version` là `0.3`. PKB v0.2 không có trường này và được coi là `software`.

### Quy tắc theo loại

| | `software` | `physical` |
|---|---|---|
| `pricing` | **Bắt buộc** (như v0.2) | Không bắt buộc. `pricing.plans` không cần |
| `offers[]` | Không được có phần tử | **Bắt buộc, ≥ 1 phần tử** |
| `variants[]`, `specs[]` | Không được có phần tử | Tuỳ chọn |
| `media.images[]` | Tuỳ chọn | Tuỳ chọn (BE chặn duyệt nếu không có ảnh, xem dưới) |
| `features[]`, `use_cases[]`, `audiences[]`, `usp[]` | như v0.2 | Dùng lại. `features[]` ghi lợi ích / điểm bán, `usp[]` ghi điểm khác biệt |

Các luật này có ở 2 chỗ: model Pydantic (`PKBData.kind_rules`) và `if/then/else` ở gốc của `pkb-data.v0.3.schema.json`. `validate_contracts.py` kiểm 2 nơi cho cùng kết quả.

## PKB nằm ở đâu

| Nội dung | Chỗ lưu |
|---|---|
| Toàn bộ PKB (identity, pricing, offers, features…) | cột `product_knowledge.data` (jsonb) |
| Danh sách trang nguồn | cột `product_knowledge.sources` (jsonb, mảng) |

Các trường sau là **cột của bảng**, không nằm trong JSON: `product_id`, `version`, `status`, `reviewed_by`, `reviewed_at`, `reviewer_role`, `review_note`.
JSON chỉ có `schema_version`. Đó là version của contract, khác với cột `version` (số lần sửa PKB của 1 product).

## Bảng trường chính (`data`)

Cột "Ai điền": 1.4 = LLM, 1.5 = code chuẩn hoá, 1.6 = suy luận hoặc người dùng nhập, **code** = bóc từ dữ liệu có cấu trúc (không LLM), **owner** = người dùng xác nhận ở bước 2. **Mới v0.3** đánh dấu trường thêm ở 0.3.

| Trường | Kiểu | Bắt buộc | Ai điền | Ví dụ |
|---|---|---|---|---|
| `schema_version` | string, `"0.2"` hoặc `"0.3"` | có (không có mặc định) | code | `"0.3"` |
| `identity.product_kind` **mới v0.3** | `software` \| `physical` | có khi `0.3` | code, owner | `"physical"` |
| `identity.name` | fact text, owner sửa được | có | 1.4, code, owner | `{"value": "Claude", "origin": "crawled", "source_id": "src_01", "evidence": "…"}` |
| `identity.website` | string | không | code | `"https://claude.com"`. Với `physical` là URL trang sản phẩm đã chuẩn hoá |
| `identity.description`, `category` | fact text, owner sửa được | không | 1.4, owner | `"AI assistant"`. Với `physical`, `category` là ngành hàng |
| `identity.tagline`, `company`, `version` | fact text (chỉ `crawled`) | không | 1.4 | |
| `identity.brand_name` **mới v0.3** | fact text, owner sửa được | không | code, owner | `"Acme Demo"` (khác `company`) |
| `identity.sku`, `identity.gtin` **mới v0.3** | fact text, owner sửa / nhập được | không | code, owner | `"AD-500"`. `owner` nhập = chưa kiểm chứng |
| `identity.models[]` | fact + `name` | không | 1.4 | `{"name": "Opus 5.5", …}` |
| `pricing` | object | **chỉ `software`** | 1.4 | xem `pricing.plans[]` dưới |
| `pricing.currency`, `region`, `locale`, `default_view`, `other_views[]`, `free_plan`, `trial_days` | như v0.2 | không | 1.4, code | |
| `pricing.plans[]`, `usage_prices[]` | fact + các trường dưới | không (mảng) | 1.4 | xem dưới |
| `offers[]` **mới v0.3** | xem [`offers[]`](#offers-mới-v03) | **bắt buộc ≥ 1 khi `physical`** | code, owner | |
| `variants[]` **mới v0.3** | xem [`variants[]`](#variants-mới-v03) | không | code, owner | |
| `specs[]` **mới v0.3** | xem [`specs[]`](#specs-mới-v03) | không | code, owner | |
| `media.images[]` **mới v0.3** | xem [`media.images[]`](#mediaimages-mới-v03) | không | code, owner | |
| `features[]` | fact + `name`, `description`, `id`, `screenshot_ids` | không (mảng) | 1.4 (`id` do code) | `{"id": "f1", "name": "Projects"}` |
| `use_cases[]` | fact + `title` | không (mảng) | 1.4 | `{"title": "Viết code"}` |
| `limitations[]` | fact + `text` | không (mảng) | 1.4 | `{"text": "Giới hạn dùng theo tuần"}` |
| `audiences[]` | `origin` + `segment`, `jtbd` | không | 1.6, owner | `{"segment": "Students", "origin": "inferred"}` |
| `usp[]` | `origin` + `text` | không | 1.6, owner | `{"text": "…", "origin": "owner"}` |
| `competitors[]` | `origin` + `name`, `url` | không | 1.6 | `{"name": "ChatGPT", "origin": "inferred"}` |
| `brand` | `origin` + `logo_asset_id`, `colors[]`, `tone` | không | 1.6, owner | `{"colors": ["#000000"], "origin": "owner"}` |
| `compliance` | `origin` + `forbidden_claims[]`, `approved_claims[]` | không | owner | |
| `affiliate` | **DEPRECATED**, xem [bảng deprecated](#deprecated-và-đổi-tên-v02--v03) | không; **cấm ở `0.3`** | không sinh mới | |
| `quality` | `completeness` (0–1), `conflicts[]` | không | 1.5 | `{"completeness": 0.82}` |

### Fact và bằng chứng

**Fact** là 1 giá trị kèm bằng chứng: `origin` (`crawled`), `source_id` (`src_NN`), `evidence` (≤ 200 ký tự). Giữ nguyên như v0.2 cho `pricing.*`, `features[]`… (luôn `crawled`). Các trường `identity` owner được sửa dùng **fact có thể sửa** (`IdentityFact`, xem [Mục do owner nhập hoặc sửa](#mục-do-owner-nhập-hoặc-sửa-mới-v03)); fact v0.2 của các trường này đọc được như `crawled`.

Mục mới của `physical` (`offers[]`, `variants[]`, `specs[]`, `media.images[]`) dùng **mục có nguồn** (`SourcedItem`):

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `origin` | `crawled` \| `owner` | `crawled`: bắt buộc `source_id` + `evidence`. `owner`: người dùng nhập hoặc sửa ở bước 2, có thể không có nguồn; bắt buộc `edited_by` + `edited_at` |
| `edited_by`, `edited_at` | xem [bên dưới](#mục-do-owner-nhập-hoặc-sửa-mới-v03) | Chỉ khi `origin: owner` (cấm với `crawled`) |
| `source_id` | `src_NN` hoặc null | Trang chứa dữ liệu |
| `evidence` | string 1–200 hoặc null | Xem quy tắc dưới |
| `extracted_via` | `jsonld` \| `microdata` \| `og` \| `embedded` \| `dom` hoặc null | Code lấy ra bằng cách nào. Null nếu `owner`. Để kiểm quy tắc "ưu tiên dữ liệu có cấu trúc" |

**Evidence của dữ liệu có cấu trúc** (không có câu trích trong markdown):

- `evidence` là **chuỗi giá trị gốc** nguyên văn trong HTML / JSON, vd. `"price":"520000"`, `<meta property="og:price:amount" content="690,000₫" />`.
- `source_id` là **trang chứa chuỗi đó** (trang sản phẩm), không phải CDN hay host ảnh.
- Chuỗi gốc phải tìm thấy nguyên văn trong bản chụp dữ liệu có cấu trúc của trang (`sources[].structured_path`) hoặc trong HTML của trang. Không viết lại, không chuẩn hoá trong `evidence`; phần chuẩn hoá nằm ở `amount`, `currency`.
- Giá trị lấy từ dữ liệu có cấu trúc không được LLM tạo ra hay sửa.

### Mục do owner nhập hoặc sửa (mới v0.3)

Áp dụng cho **mọi mục có `origin: owner`**: `identity.*` (các trường dưới), `offers[]`, `variants[]`, `specs[]`, `media.images[]`, `audiences[]`, `usp[]`, `competitors[]`, `brand`, `compliance`. Quyết định của @PotatoMine725 trên #68, theo đề xuất của lead (#67).

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `edited_by` | UUID (user id, không phải email) | **Bắt buộc khi `origin: owner`**; cấm (null hoặc vắng) với mọi `origin` khác, kể cả `crawled`, `inferred`, `merchant` |
| `edited_at` | ISO 8601 UTC, `…Z` hoặc `…+00:00` | Như `edited_by`. Không chấp nhận múi giờ khác (vd. `+07:00`) |
| `previous` | `{value, source_id, evidence}` hoặc null | Chỉ ở `identity.*`, chỉ khi `origin: owner`. Xem dưới |

**Trường `identity` owner được sửa:** `name`, `description`, `category`, `brand_name`, `sku`, `gtin`. Các trường `tagline`, `company`, `version`, `models[]`, `website` chỉ `crawled`; chưa cho owner sửa (cần thì đề xuất riêng).

**`previous`: giữ giá trị đã crawl để đối chiếu.**

- Chỉ giữ **1 giá trị** và **luôn là giá trị đã crawl**, không bao giờ là giá trị owner nhập trước đó. Owner sửa nhiều lần thì `previous` **không đổi**; lịch sử sửa đầy đủ do BE lưu (DB), không nằm trong PKB.
- `source_id` của `previous` phải có trong `sources[]` (validator kiểm, JSON Schema không diễn đạt được). `evidence` ≤ 200 ký tự như mọi fact.
- Trường chưa từng có giá trị crawl (owner tự nhập, vd. `gtin`) thì không có `previous`.

**Chưa kiểm chứng.** `origin: owner` nghĩa là giá trị do người dùng khai, chưa được đối chiếu với nguồn nào. Điều này đúng cho **mọi** giá trị owner nhập, và đặc biệt cho `sku` / `gtin`: không có cờ `verified`, "chưa kiểm chứng" **suy ra từ `origin: owner`**. FE hiển thị nhãn theo `origin`; mã chỉ coi là đã kiểm chứng khi có fact `crawled` với `source_id` + `evidence`.

**BE kiểm, ngoài schema:**

| Quy tắc | Ghi chú |
|---|---|
| Chỉ sửa bản `draft` | Bản đã xác nhận (`approved`) không sửa trực tiếp; sửa thì tạo bản nháp / version mới |
| `edited_by`, `edited_at` do server ghi | Lấy từ phiên đăng nhập và đồng hồ server; bỏ giá trị client gửi lên |
| Lưu lịch sử sửa | Đầy đủ trong DB (ai, lúc nào, giá trị cũ → mới). PKB chỉ giữ `previous` (giá trị crawl) |
| Giữ `previous` nguyên khi sửa lại | Chỉ đặt `previous` ở lần sửa đầu tiên một fact `crawled`; các lần sau giữ nguyên |
| Ai được sửa | Chủ sở hữu Product; phụ thuộc quan hệ sở hữu BE đang đề xuất (spec M1, danh sách thay đổi cho BE, mục 4) |

**Dữ liệu v0.2 cũ:** mục `origin: merchant` không có `edited_by` / `edited_at`. Khi chuyển lên 0.3 (`merchant` → `owner`) hai trường này trở thành bắt buộc; BE cần điền (đề xuất: user id chủ sản phẩm và thời điểm lưu bản v0.2). **Chờ BE xác nhận.**

### `offers[]` (mới v0.3)

1 phần tử = 1 mức giá của sản phẩm. Giá cho biến thể nào thì liên kết bằng `variant_ref`.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| (mục có nguồn) | | `origin`, `source_id`, `evidence`, `extracted_via` |
| `price_text` | string hoặc null | Giá nguyên văn, vd. `"690,000₫"` |
| `amount` | number ≥ 0 hoặc null | Giá đã chuẩn hoá thành số. Null nếu trang không có giá hoặc chỉ có khoảng giá |
| `currency` | ISO 4217 (3 chữ in hoa) hoặc null | Lấy từ trang (`priceCurrency`, `og:price:currency`). **Không mặc định VND, không quy đổi.** Bắt buộc khi có `amount` hoặc `original_amount` |
| `original_amount` | number hoặc null | Giá gốc (trước giảm) nếu trang ghi |
| `availability` | `in_stock` \| `out_of_stock` \| `preorder` \| `unknown` | Mặc định `unknown`. Không đoán |
| `seller`, `platform` | string hoặc null | Người bán / shop và nền tảng hoặc host (vd. `shop.example.com`, `haravan`) |
| `variant_ref` | `vN` hoặc null | `variants[].id` mà giá này áp dụng. Null = giá chung |

Quy tắc giá:

- `amount` là con số in trên trang. Giá trong JSON-LD chỉ áp dụng cho biến thể đang được chọn: đặt `variant_ref` là biến thể đó.
- **Không suy ra giá của biến thể chưa kiểm.** Không sao chép giá của biến thể này sang biến thể khác, không coi giá của biến thể đang chọn là giá chung của mọi biến thể. Biến thể chưa có giá thì không có offer cho nó. Với sản phẩm nhiều biến thể, mỗi offer mang `variant_ref` của đúng biến thể.
- `AggregateOffer` có `lowPrice` ≠ `highPrice`: `amount = null`, ghi khoảng giá vào `price_text`. `lowPrice` = `highPrice`: dùng giá đó.
- Trang không có giá chuẩn (vd. `AggregateOffer` không có `price`): `amount = null`, offer vẫn có evidence cho thấy offer tồn tại (vd. `availability`). Người dùng nhập giá ở bước 2 (`origin: owner`). Chưa có giá thì không được duyệt (xem [Điều kiện duyệt](#điều-kiện-duyệt-be-kiểm-ngoài-schema)).
- Giá trong JSON nhúng của nền tảng có thể khác đơn vị (Haravan ×100). Ưu tiên nguồn chuẩn (`jsonld`, `og`); nếu phải dùng `embedded` thì code chuẩn hoá và ghi `extracted_via: embedded`.

### `variants[]` (mới v0.3)

Biến thể (màu, size, dung tích…). **Không chứa giá**: giá nằm ở `offers[]`, liên kết bằng `variant_ref`.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| (mục có nguồn) | | `origin`, `source_id`, `evidence`, `extracted_via` |
| `id` | `^v\d{1,3}$` | Code điền (`v1`, `v2`…). Duy nhất trong PKB |
| `name` | string | Tên hiển thị |
| `attributes[]` | `{key, value}` | vd. `{"key": "Màu", "value": "BEG"}` |
| `sku` | string hoặc null | |
| `selected` | bool, mặc định `false` | Biến thể đang được chọn khi crawl. Tối đa 1 |

JSON-LD gần như không có biến thể (0/7 trang đã khảo sát). Biến thể lấy từ `embedded` (JSON riêng của nền tảng) hoặc `dom` (swatch) và chỉ là tuỳ chọn.

### `specs[]` (mới v0.3)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| (mục có nguồn) | | `origin`, `source_id`, `evidence`, `extracted_via` |
| `key`, `value` | string | vd. `"Mã model"`, `"B80015105"` |
| `unit` | string hoặc null | vd. `ml`, `kg` |

Code lấy `specs[]` từ dữ liệu có cấu trúc (JSON-LD `additionalProperty`, `model`, microdata, bảng thông số trong DOM). LLM không điền `specs[]`. Chưa lấy được thì để trống, người dùng bổ sung ở bước 2.

### `media.images[]` (mới v0.3)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| (mục có nguồn) | | `origin`, `source_id` (**trang chứa URL ảnh**, không phải host CDN), `evidence`, `extracted_via` |
| `url` | string hoặc null | URL ảnh gốc, chỉ để ghi nguồn |
| `storage_path` | string hoặc null | Đường dẫn Storage (private) của ảnh đã tải. Cần `url` hoặc `storage_path` |
| `alt` | string hoặc null | |
| `role` | `hero` \| `gallery` | Tối đa 1 ảnh `hero` |
| `variant_ref` | `vN` hoặc null | Ảnh của biến thể nào. Null = chung. Dùng để lọc ảnh theo biến thể |
| `generic` | bool, mặc định `false` | `true` nếu là ảnh chung của site (banner `og:image`), không phải ảnh sản phẩm. Không dùng làm cảnh video |

Ảnh gallery có thể lẫn ảnh của biến thể khác (ảnh mang mã màu khác); code lọc theo mã sản phẩm / `variant_ref`. **Mỗi ảnh gắn đúng `variant_ref`; không dùng ảnh của màu khác thay thế cho biến thể chưa có ảnh.** `media.images[]` mô tả ảnh tìm thấy; việc được phép lưu và dùng ảnh là điều kiện riêng (quyền sử dụng, quy tắc #52): xem [spec M1, mục Ảnh sản phẩm: quyền sử dụng](../m1-product-intelligence.md#ảnh-sản-phẩm-quyền-sử-dụng).

### `pricing.plans[]` (chỉ `software`)

1 dòng = 1 plan × 1 chu kỳ trả. Plan nhiều chu kỳ thì có nhiều dòng.

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `name` | string | Tên đúng như trên trang |
| `currency` | string | ISO 4217, tiền tệ in trên trang |
| `list_price` | number hoặc null | Giá niêm yết, đúng con số trên trang. `0` nếu Free. `null` nếu "Contact sales" |
| `promo_price`, `promo_terms` | number, string hoặc null | Giá khuyến mãi và điều kiện, vd. "first month" |
| `price_unit` | `month`, `year`, `seat_month`, `seat_year`, `one_time` | Bắt buộc khi có `list_price`. Không có `unknown` |
| `billing_cycle` | `monthly`, `quarterly`, `yearly`, `one_time` | Bắt buộc khi có `list_price`. Không có `unknown` |
| `price_text` | string | Giá nguyên văn |
| `limits[]`, `audience` | string | Giới hạn và đối tượng của plan |

`price_unit` và `billing_cycle` chỉ được null khi `list_price` là null. Luật này có ở 2 chỗ: validator Pydantic của `Plan`, và `if/then` trong schema (khi `list_price` là số thì `price_unit`, `billing_cycle` bắt buộc và khác null). Ví dụ Claude Pro: `17, month, yearly` và `20, month, monthly`.

## Deprecated và đổi tên (v0.2 → v0.3)

P1 bỏ merchant, campaign, creator, tracking, attribution, affiliate; 1 chủ sở hữu xác nhận PKB ở bước 2.

| Mục | v0.2 | v0.3 | Với dữ liệu v0.2 cũ |
|---|---|---|---|
| `affiliate` | Có (`origin`, `link`, `commission`) | **Deprecated.** Cấm trong dữ liệu `0.3`, không sinh mới | Vẫn đọc được ở schema 0.3 khi `schema_version` là `0.2`. Khi chuyển lên 0.3 thì bỏ trường này |
| `origin: merchant` | Giá trị hợp lệ của `audiences`, `usp`, `competitors`, `brand`, `compliance`, `affiliate` | **Đổi tên thành `owner`** (người dùng xác nhận ở bước 2). Cấm `merchant` trong dữ liệu `0.3` | Đọc `merchant` như `owner`. Khi chuyển lên 0.3 thì đổi `merchant` → `owner` và điền `edited_by` / `edited_at` (xem [Mục do owner nhập hoặc sửa](#mục-do-owner-nhập-hoặc-sửa-mới-v03)) |
| `origin` (tập giá trị) | `crawled` \| `merchant` \| `inferred` | `crawled` \| `owner` \| `inferred` | |
| Fact của `pricing.*`, `features[]`, `identity.tagline` / `company` / `version` | `origin` luôn `crawled` | Không đổi | Không đổi |
| Fact của `identity.name`, `description`, `category` (và `brand_name`, `sku`, `gtin` mới) | `origin` luôn `crawled` | `crawled` hoặc `owner` (kèm `edited_by`, `edited_at`, `previous`) | Fact cũ đọc được như `crawled` |

Bảng đổi tên `origin` (chỉ chiều v0.2 → v0.3):

| v0.2 | v0.3 |
|---|---|
| `crawled` | `crawled` |
| `merchant` | `owner` |
| `inferred` | `inferred` |

Schema 0.3 cho phép `merchant` về mặt kiểu để đọc dữ liệu `0.2`, nhưng khi `schema_version` là `0.3` luật gốc cấm `merchant` và `affiliate`. Mục `inferred` vẫn phải được duyệt trước khi Module 2 dùng (FR-05). Mục `owner` không cần `source_id` / `evidence`, nhưng bắt buộc `edited_by` + `edited_at`.

## Điều kiện duyệt (BE kiểm, ngoài schema)

Schema chỉ kiểm hình dạng. Khi chuyển `draft → in_review` / `approved`, BE kiểm thêm cho `physical`:

- Có ≥ 1 offer với `amount` và `currency` khác null (do crawl hoặc `origin: owner`).
- Có ≥ 1 ảnh không `generic` (video cần ảnh sản phẩm).
- Mọi `source_id` có trong `sources[].id`; mọi `variant_ref` trỏ tới `variants[].id` có thật (JSON Schema không diễn đạt được; `validate_contracts.py` kiểm hai luật này cho ví dụ).

## Bảng trường `sources[]` (1 phần tử)

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `id` | string `src_NN` | có | Các fact trỏ về đây bằng `source_id` |
| `url`, `page_type`, `fetched_at`, `content_hash` | string | có | `content_hash` dùng cho idempotent (NFR-04). `page_type` của shop: `product`, `policy`, `specs`… (chuỗi tự do) |
| `variant` | `raw` hoặc `fit` | có | Bản markdown đã gửi cho LLM |
| `region`, `locale` | string | không | Vùng IP và locale lúc crawl |
| `markdown_path` | string | không | Đường dẫn Storage (private) của markdown |
| `image_paths[]` | string | không | Đường dẫn Storage (private) của ảnh |
| `structured_path` **mới v0.3** | string | không | Storage (private) của bản chụp dữ liệu có cấu trúc (JSON-LD, meta, microdata) đã trích từ trang. Evidence của fact lấy từ dữ liệu có cấu trúc được đối chiếu với file này |

Trong spike, `markdown_path` là đường dẫn file cục bộ. Khi lên production nó là đường dẫn Supabase Storage.

## Ví dụ

Cả hai loại ở dạng `{data, sources}` trong [`examples/`](examples/). **Mọi ví dụ `physical` là dữ liệu giả**: thương hiệu giả "Acme Demo", URL `example.com`, tên sản phẩm ghi "(dữ liệu mẫu)". Không dùng dữ liệu hay ảnh của shop thật làm fixture dùng chung. Evidence của ví dụ là chuỗi nguyên văn trong trang giả dựng kèm lúc sinh ví dụ, nên chỉ chứng minh dạng dữ liệu, không chứng minh trích xuất đúng trên trang thật. Ví dụ `physical` rút gọn (đầy đủ ở `valid-v03-physical-jsonld-variants.json`):

```json
{
  "schema_version": "0.3",
  "identity": {
    "product_kind": "physical",
    "name": { "value": "Bình giữ nhiệt Acme Demo 500ml (dữ liệu mẫu)", "origin": "crawled", "source_id": "src_01", "evidence": "\"name\":\"Bình giữ nhiệt Acme Demo 500ml (dữ liệu mẫu)\"" },
    "brand_name": { "value": "Acme Demo", "origin": "crawled", "source_id": "src_01", "evidence": "\"brand\":{\"@type\":\"Brand\",\"name\":\"Acme Demo\"}" }
  },
  "offers": [{
    "origin": "crawled", "source_id": "src_01", "extracted_via": "jsonld", "evidence": "\"price\":\"350000\"",
    "price_text": "350000", "amount": 350000, "currency": "VND", "availability": "in_stock", "variant_ref": "v1"
  }],
  "variants": [
    { "origin": "crawled", "source_id": "src_01", "extracted_via": "dom", "evidence": "data-attr-value=\"AD-500-BE\"", "id": "v1", "name": "Be", "selected": true },
    { "origin": "crawled", "source_id": "src_01", "extracted_via": "dom", "evidence": "data-attr-value=\"AD-500-XA\"", "id": "v2", "name": "Xanh" }
  ],
  "media": { "images": [{ "origin": "crawled", "source_id": "src_01", "extracted_via": "dom", "evidence": "AD-500-BE_1.jpg", "role": "hero", "variant_ref": "v1", "url": "https://cdn.example.com/acme-demo/AD-500-BE_1.jpg" }] }
}
```

Biến thể `v2` không có offer: giá chưa kiểm thì không suy từ `v1`.

| File | Loại | Kỳ vọng | Ý nghĩa |
|---|---|---|---|
| `valid-v02-software.json` | `software` 0.2 | pass (schema 0.2 và 0.3) | Dữ liệu cũ, có `origin: merchant` |
| `valid-v03-software.json` | `software` 0.3 | pass | `origin: owner`, có `product_kind` |
| `valid-v03-physical-jsonld-variants.json` | `physical` | pass | Dữ liệu giả. JSON-LD, 3 biến thể (chỉ biến thể đang chọn có offer), ảnh gắn `variant_ref`, ảnh `og:image` chung (`generic`) |
| `valid-v03-physical-no-jsonld.json` | `physical` | pass | Dữ liệu giả. Không JSON-LD: giá từ `og:price`, biến thể từ JSON nhúng |
| `valid-v03-physical-price-missing.json` | `physical` | pass | Dữ liệu giả. Trang không có giá: `amount = null`, chờ owner nhập |
| `valid-v03-physical-out-of-stock.json` | `physical` | pass | Dữ liệu giả. Ca `out_of_stock`: có giá, `availability = out_of_stock` |
| `valid-v03-owner-edited-identity.json` | `physical` | pass | Dữ liệu giả. Owner sửa `name` (kèm `edited_by`, `edited_at`, `previous` là giá trị crawl) và thêm `description` |
| `valid-v03-owner-entered-price-gtin.json` | `physical` | pass | Dữ liệu giả. Trang không có giá: owner điền giá (offer `owner`) và nhập `gtin` (chưa kiểm chứng) |
| `invalid-v03-physical-missing-offers.json`, `…-empty-offers.json` | `physical` | fail | Thiếu `offers` hoặc rỗng |
| `invalid-v03-offer-missing-evidence.json` | `physical` | fail | `crawled` mà thiếu `evidence` |
| `invalid-v03-amount-without-currency.json` | `physical` | fail | Có `amount` mà thiếu `currency` |
| `invalid-v03-missing-product-kind.json` | (không rõ loại) | fail | `0.3` mà thiếu `product_kind` (dựng từ ví dụ `software` có `pricing`, nên lỗi duy nhất là thiếu `product_kind`) |
| `invalid-v03-two-selected-variants.json` | `physical` | fail | 2 biến thể `selected` |
| `invalid-v03-merchant-origin.json`, `…-affiliate-present.json` | `software` | fail | `merchant` / `affiliate` trong dữ liệu `0.3` |
| `invalid-v03-software-missing-pricing.json`, `…-software-with-offers.json` | `software` | fail | Thiếu `pricing`, hoặc có `offers` |
| `invalid-v03-dangling-variant-ref.json` | `physical` | fail | `variant_ref` trỏ tới variant không có (kiểm tham chiếu chéo) |
| `invalid-v03-owner-missing-edited-by.json` | `physical` | fail | `identity.name` là `owner` mà thiếu `edited_by` |
| `invalid-v03-previous-on-crawled.json` | `physical` | fail | `previous` trên fact `crawled` (chỉ dùng khi `owner`) |
| `invalid-v03-previous-unknown-source-id.json` | `physical` | fail | `previous.source_id` không có trong `sources[]` (kiểm tham chiếu chéo) |
| `invalid-v03-unknown-source-id.json` | `physical` | fail | `source_id` không có trong `sources` (kiểm tham chiếu chéo) |

Evidence trong các ví dụ `physical` thật được lấy nguyên văn từ HTML đã khảo sát ngày 13/10/2026 (`docs/report/p1-shop-url-survey.md`). Đây chỉ là chuỗi ngắn làm ví dụ, không phải bản crawl thô.

## Quy tắc version

- Đổi tên hoặc xoá trường, đổi kiểu, hoặc thu hẹp giá trị cho phép: **tăng version** (`0.3` → `0.4`, hoặc sang `1.0`) và có file schema mới `*.vX.Y.schema.json`.
- Thêm trường optional: không phá bản cũ. PKB cũ vẫn hợp lệ. Vẫn nên ghi vào README này.
- Mỗi PKB lưu `schema_version` của nó. Code đọc PKB phải kiểm tra trường này và chọn luật theo nó: `0.2` đọc `merchant`, `affiliate`; `0.3` cấm hai thứ đó, bắt buộc `product_kind`, và bắt buộc `edited_by` + `edited_at` cho mọi mục `origin: owner`.
- File schema cũ không xoá, để đọc được PKB cũ.
- Lịch sử: v0.2 (spike M1) → **v0.3** (13/10/2026, P1: thêm `physical`, `merchant` → `owner`, `affiliate` deprecated, `sources[].structured_path`; 14/10/2026: owner sửa `identity.*` với `edited_by`, `edited_at`, `previous`).

## Chi phí job crawl (generation_jobs)

Chi phí và token nằm ở **cột riêng** của `generation_jobs` (`tokens_in`, `tokens_out`, `cost_usd`, `cost_breakdown`), không nằm trong `result_manifest`. Worker chỉ ghi `cost_breakdown`; DB tự tính 3 cột còn lại. Schema và quy tắc: [`docs/specs/contracts/`](../contracts/README.md) (issue #23).

### `result_manifest`

`result_manifest` của job `crawl` chỉ có 3 key, và **chỉ áp dụng khi job `completed`**:

| Key | Kiểu | Ý nghĩa |
|---|---|---|
| `pkb_version` | int | Giá trị cột `product_knowledge.version` vừa tạo |
| `pages_used` | int | Số trang đã gửi cho LLM |
| `model` | string | Model đã dùng, vd. `gemini-3.5-flash-lite` |

Job `failed` (gồm bị WAF chặn) chưa tạo PKB: `result_manifest = null`. Lỗi ghi ở cột `error`, mã ngắn đứng đầu, vd. `waf_challenge: 403 cf-mitigated=challenge`. `cost_breakdown` vẫn ghi chi phí đã tiêu.

Số đo của spike (`meta` trong `pkb.<model>.json`) có `input_tokens`, `output_tokens`, `cost_usd`, `model` để ghi vào các cột và key trên.

Đề xuất cho BE: thêm `product_kind` và `crawl_mode` vào `result_manifest` (xem danh sách thay đổi BE ở spec M1). Chưa áp dụng trong contract này.
