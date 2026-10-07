# PKB v0.2: hợp đồng JSON

PKB là Product Knowledge Base do Module 1 tạo ra. FE, BE và AI dùng chung 1 contract này (ERD gate 2, gate 16; `docs/specs/erd/data-dictionary.md` mục 7).

- Schema máy đọc được: `pkb-data.v0.2.schema.json`, `pkb-sources.v0.2.schema.json`.
- Nguồn của schema: `spikes/m1-crawl-extract/schema.py` (Pydantic). Sinh lại bằng `uv run python export_schema.py` trong thư mục spike.
- Đặc tả nghiệp vụ: `docs/specs/m1-product-intelligence.md` (mục Output, Quy tắc trích xuất giá).
- Trạng thái: v0.2 là bản thử từ spike, chưa có service dùng.

## PKB nằm ở đâu

| Nội dung | Chỗ lưu |
|---|---|
| Toàn bộ PKB (identity, pricing, features…) | cột `product_knowledge.data` (jsonb) |
| Danh sách trang nguồn | cột `product_knowledge.sources` (jsonb, mảng) |

Các trường sau là **cột của bảng**, không nằm trong JSON: `product_id`, `version`, `status`, `approved_by`.
JSON chỉ có `schema_version`. Đó là version của contract, khác với cột `version` (số lần sửa PKB của 1 product).

## Bảng trường chính (`data`)

Cột "Bắt buộc": có nghĩa là schema không cho thiếu. "Ai điền": 1.4 = LLM, 1.5 = code chuẩn hoá, 1.6 = suy luận hoặc người dùng nhập, merchant = chủ product.

| Trường | Kiểu | Bắt buộc | Ai điền | Ví dụ |
|---|---|---|---|---|
| `schema_version` | string, `const "0.2"` | có (không có mặc định) | code | `"0.2"` |
| `identity.name` | fact text | có | 1.4 | `{"value": "Claude", "origin": "crawled", "source_id": "src_01", "evidence": "…"}` |
| `identity.website` | string | không | code | `"https://claude.com"` |
| `identity.tagline`, `description`, `category`, `company`, `version` | fact text | không | 1.4 | `"AI assistant"` |
| `identity.models[]` | fact + `name` | không | 1.4 | `{"name": "Opus 5.5", …}` |
| `pricing.currency` | fact text | không | 1.4 | `"USD"` |
| `pricing.region`, `pricing.locale` | string | không | code | `"VN"`, `"en-US"` |
| `pricing.default_view` | string | không | 1.4 | `"monthly"` |
| `pricing.other_views[]` | string | không | 1.4 | `["yearly", "quarterly"]` |
| `pricing.plans[]` | fact + các trường dưới | không (mảng) | 1.4 | xem dưới |
| `pricing.usage_prices[]` | fact + `name`, `unit`, `price`, `currency` | không (mảng) | 1.4 | `{"name": "Opus 5.5 - Input", "unit": "1M tokens", "price": 4, "currency": "USD"}` |
| `pricing.free_plan`, `trial_days` | fact bool, fact int | không | 1.4 | `true` |
| `features[]` | fact + `name`, `description`, `id`, `screenshot_ids` | không (mảng) | 1.4 (`id` do code) | `{"id": "f1", "name": "Projects"}` |
| `use_cases[]` | fact + `title` | không (mảng) | 1.4 | `{"title": "Viết code"}` |
| `limitations[]` | fact + `text` | không (mảng) | 1.4 | `{"text": "Giới hạn dùng theo tuần"}` |
| `audiences[]` | `origin` + `segment`, `jtbd` | không | 1.6 | `{"segment": "Students", "origin": "inferred"}` |
| `usp[]` | `origin` + `text` | không | 1.6, merchant | `{"text": "…", "origin": "merchant"}` |
| `competitors[]` | `origin` + `name`, `url` | không | 1.6 | `{"name": "ChatGPT", "origin": "inferred"}` |
| `brand` | `origin` + `logo_asset_id`, `colors[]`, `tone` | không | 1.6, merchant | `{"colors": ["#000000"], "origin": "merchant"}` |
| `compliance` | `origin` + `forbidden_claims[]`, `approved_claims[]` | không | merchant | |
| `affiliate` | `origin` + `link`, `commission` | không | merchant | `{"commission": "30% recurring", "origin": "merchant"}` |
| `quality` | `completeness` (0–1), `conflicts[]` | không | 1.5 | `{"completeness": 0.82}` |

**Fact** là 1 giá trị kèm bằng chứng: `origin` (`crawled`), `source_id` (`src_NN`), `evidence` (≤ 200 ký tự, trích nguyên văn từ trang nguồn). Mục của 1.5–1.6 dùng `origin` ∈ `crawled | merchant | inferred`. Mục `inferred` phải được duyệt trước khi Module 2 dùng (FR-05).

### `pricing.plans[]`

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

`price_unit` và `billing_cycle` chỉ được null khi `list_price` là null. Luật này có ở 2 chỗ: validator Pydantic của `Plan`, và `if/then` trong `pkb-data.v0.2.schema.json` (khi `list_price` là số thì `price_unit`, `billing_cycle` bắt buộc và khác null). Ví dụ Claude Pro: `17, month, yearly` và `20, month, monthly`.

## Bảng trường `sources[]` (1 phần tử)

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `id` | string `src_NN` | có | Các fact trỏ về đây bằng `source_id` |
| `url`, `page_type`, `fetched_at`, `content_hash` | string | có | `content_hash` dùng cho idempotent (NFR-04) |
| `variant` | `raw` hoặc `fit` | có | Bản markdown đã gửi cho LLM |
| `region`, `locale` | string | không | Vùng IP và locale lúc crawl |
| `markdown_path` | string | không | Đường dẫn Storage (private) của markdown |
| `image_paths[]` | string | không | Đường dẫn Storage (private) của ảnh |

Trong spike, `markdown_path` là đường dẫn file cục bộ. Khi lên production nó là đường dẫn Supabase Storage.

## Quy tắc version

- Đổi tên hoặc xoá trường, đổi kiểu, hoặc thu hẹp giá trị cho phép: **tăng version** (`0.2` → `0.3`, hoặc sang `1.0`) và có file schema mới `*.vX.Y.schema.json`.
- Thêm trường optional: không phá bản cũ. PKB cũ vẫn hợp lệ. Vẫn nên ghi vào README này.
- Mỗi PKB lưu `schema_version` của nó. Code đọc PKB phải kiểm tra trường này.
- File schema cũ không xoá, để đọc được PKB cũ.

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
