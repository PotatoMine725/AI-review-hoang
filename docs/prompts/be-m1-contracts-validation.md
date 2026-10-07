# Prompt: siết validation cho contract PKB v0.2 và cost_breakdown v1 (góp ý BE ở #23)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #23 (comment của @tranquangthong03 lúc 08:07 07/10) · **Branch:** `docs/contracts-validation` (tạo từ `dev` mới nhất)
- **Liên quan:** `docs/specs/pkb/`, `docs/specs/contracts/`, `spikes/m1-crawl-extract/schema.py`, `export_schema.py`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản.

## Bối cảnh
BE (@tranquangthong03) đồng ý dùng `PKBData` / `sources` và `cost_breakdown` làm contract, nhưng cần siết validation trước khi viết migration/RPC. Team lead (@VV6505) đã duyệt hướng này. Hai contract chưa được service nào dùng, nên sửa tại chỗ, **giữ số version** (PKB `0.2`, cost_breakdown `1`).

## Đọc trước
- Issue #23: các comment từ 07:54 đến 08:15 ngày 07/10.
- `docs/specs/pkb/README.md`, `docs/specs/pkb/*.schema.json`, `docs/specs/contracts/README.md`, `docs/specs/contracts/cost-breakdown.v1.schema.json`
- `spikes/m1-crawl-extract/schema.py`, `export_schema.py`, `output/*/pkb.gemini-3.5-flash-lite.json`

## Nhiệm vụ

### A. PKB v0.2 (`schema.py` → `export_schema.py` → `docs/specs/pkb/`)
1. `schema_version`: bắt buộc trong JSON Schema xuất ra, `const: "0.2"`. Bỏ mặc định khỏi phần `required` (Pydantic: dùng `Literal["0.2"]` và không để default, hoặc chỉnh `json_schema_extra`).
2. `Plan`: đưa luật của validator vào JSON Schema bằng `if/then`. Khi `list_price` khác null thì `price_unit` và `billing_cycle` bắt buộc và khác null. Làm bằng `model_config = ConfigDict(json_schema_extra=...)` hoặc hàm `__get_pydantic_json_schema__`, không viết tay file JSON.
3. Chạy lại `export_schema.py`. 2 PKB đã có (Claude, Dreamina) phải pass schema mới. Nếu fail vì thiếu `schema_version` thì chỉ thêm trường đó, không gọi lại LLM.

### B. `cost_breakdown` v1 (`docs/specs/contracts/`)
Sửa schema và README theo các quy tắc sau (M1 chốt, BE đã đề nghị):
1. **`call_id`** (string, bắt buộc, duy nhất trong `items`): id của 1 lần gọi provider, do worker sinh (UUID). BE dùng để chống ghi trùng khi retry ghi DB. Ghi rõ: JSON Schema không kiểm được "duy nhất theo `call_id`", BE kiểm trong RPC.
2. **Item `llm` bắt buộc:** `call_id`, `step`, `provider`, `model`, `attempt`, `cache_hit`, `tokens_in`, `tokens_out`, `unit_price_in_per_1m`, `unit_price_out_per_1m`, `prices_checked_at`, `cost_usd`, `cost_status`. Dùng `if category = llm then required [...]`.
3. **Cache, có 2 loại, ghi rõ trong README:**
   - Cache nội bộ (`llm_cache` của worker, không gọi provider): `cache_hit: true`, `tokens_in = tokens_out = 0`, `cost_usd = 0`.
   - Cache phía provider (vd. Gemini context caching, có gọi API nhưng token cache rẻ hơn): `cache_hit: false`. Token cache vẫn nằm trong `tokens_in`; thêm trường tuỳ chọn `tokens_in_cached` (≤ `tokens_in`) và `unit_price_cached_in_per_1m`. `cost_usd` là số đã tính theo giá cache. MVP chưa dùng loại này.
4. **Chi phí chưa đầy đủ:** thêm `cost_status` ∈ `exact | estimated`.
   - `exact`: token lấy từ `usage` provider trả về.
   - `estimated`: provider không trả `usage` (vd. lỗi giữa chừng), token ước tính bằng `count_tokens` hoặc bằng chặn trên `max_output_tokens`.
   - Không có trạng thái "không biết": lần gọi có tốn tiền thì luôn ghi 1 số, kể cả ước tính. Cột tổng vẫn cộng cả `estimated`. README ghi: muốn biết job có số ước tính thì BE truy vấn `cost_breakdown`.
5. **6 chữ số thập phân:** không dùng `multipleOf` (lỗi số thực). Quy tắc: worker làm tròn `cost_usd` của item về 6 chữ số trước khi ghi; DB ép kiểu `numeric(12,6)` khi tính tổng. Ghi vào description và README.
6. Thêm 1 ví dụ `estimated` và 1 ví dụ cache nội bộ vào README (ngoài ví dụ Claude đã có, ví dụ Claude thêm `call_id`, `cost_status: "exact"`).
7. Viết `docs/specs/contracts/examples/` gồm các file JSON: 3 ví dụ hợp lệ + 3 ví dụ **không hợp lệ** (thiếu `call_id`; item llm thiếu `model`; `cache_hit: true` mà `cost_usd > 0`). BE dùng làm case validation.

### C. `result_manifest` (`docs/specs/pkb/README.md`)
- 3 key (`pkb_version`, `pages_used`, `model`) chỉ áp dụng khi job crawl `completed`.
- Job `failed` (gồm bị WAF chặn) chưa tạo PKB: `result_manifest = null`, lỗi ghi ở cột `error` với mã ngắn đứng đầu, vd. `waf_challenge: 403 cf-mitigated=challenge`. `cost_breakdown` vẫn ghi chi phí đã tiêu.

### D. Script kiểm tra
Thêm `spikes/m1-crawl-extract/validate_contracts.py`: validate các file trong `docs/specs/contracts/examples/` và 2 PKB của spike theo schema. Ví dụ hợp lệ phải pass, ví dụ không hợp lệ phải fail. In bảng kết quả. Dùng `jsonschema` nếu đã có trong `uv.lock`; nếu chưa có thì hỏi người dùng trước khi thêm (chỉ thêm vào dependency-group `dev` của spike).

## Phạm vi
- Làm: `docs/specs/pkb/**`, `docs/specs/contracts/**`, `spikes/m1-crawl-extract/schema.py`, `export_schema.py`, `validate_contracts.py`.
- Không làm: gọi LLM, crawl, sửa ERD (`docs/specs/erd/**`), spec M1, decision-log, `services/worker`.

## Acceptance criteria
- [ ] `pkb-data.v0.2.schema.json`: `schema_version` có trong `required`, `const "0.2"`; `Plan` có `if/then` cho `list_price`.
- [ ] `cost-breakdown.v1.schema.json`: `call_id` bắt buộc; `if category = llm` bắt buộc đủ trường; có `cost_status`; luật `cache_hit` giữ nguyên.
- [ ] `uv run python validate_contracts.py`: 3/3 ví dụ hợp lệ pass, 3/3 không hợp lệ fail, 2/2 PKB spike pass.
- [ ] README 2 thư mục ghi đủ quy tắc C và B.3–B.5.
- [ ] `export_schema.py` chạy lại không đổi nội dung (idempotent). `uvx ruff check .` và `uvx ruff format --check .` sạch.

## Ràng buộc
- Trình bày danh sách file sẽ sửa trước khi làm, chờ duyệt. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(contracts): siết validation PKB v0.2 và cost_breakdown v1 theo #23`), kèm file prompt này. Mở PR vào `dev`, body có `Refs #23` và `cc @tranquangthong03`.
- Trả về: link PR, bảng kết quả `validate_contracts.py`.
