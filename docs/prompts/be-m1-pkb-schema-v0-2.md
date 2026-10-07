# Prompt: schema PKB v0.2 (quy tắc giá) + chạy lại spike + hợp đồng JSON cho ERD

- **Repo / cwd:** `AI-review-BE`
- **Issue:** không có (việc của owner M1, nối tiếp spike #6) · **Branch:** `feat/m1-pkb-schema-v0-2` (tạo từ `dev` mới nhất)
- **Liên quan:** `docs/specs/m1-product-intelligence.md` (v0.2, mục Output + Quy tắc trích xuất giá), `docs/specs/erd/` (ERD v1.3.1), `docs/adr/0002-llm-provider.md`, `spikes/m1-crawl-extract/README.md`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là AI dev, mới với Python: giải thích ngắn, đúng trọng tâm.

## Bối cảnh
- Spike #6 chỉ đạt **1/8** lần chạy đúng giá + tên plan (AC-04). Đặc tả M1 v0.2 đã có 7 quy tắc giá, nhưng `schema.py` và prompt của spike vẫn là bản v0.1 (1 trường `price`, `billing_period`).
- ERD v1.3.1 (`docs/specs/erd/erd.dbml`) lưu PKB ở `product_knowledge.data` (jsonb) và nguồn ở `product_knowledge.sources` (jsonb). Không có bảng `crawled_pages`, `product_assets`, `knowledge_chunks`, không có vector RAG. ERD yêu cầu FE/BE/AI dùng chung **1 JSON contract có version** (gate 2, gate 16; `data-dictionary.md` mục 7). M1 tạo ra PKB, nên M1 viết contract này.
- ADR-002 đề xuất `gemini-3.5-flash-lite`, mode `batch` cho 1.4.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md`, `docs/README.md`
- `docs/specs/m1-product-intelligence.md`: mục Output (JSON mẫu), Quy tắc trích xuất giá, FR-04, FR-05, NFR-02, NFR-03
- `docs/specs/erd/erd.dbml`: bảng `products`, `product_knowledge`, `generation_jobs`; `docs/specs/erd/data-dictionary.md` mục 7 (Hợp đồng dữ liệu JSON)
- `spikes/m1-crawl-extract/`: `README.md` (mục Đối chiếu giá, Đề xuất cho đặc tả v0.2), `schema.py`, `extract.py`, `run.py`, `demo.py`, `products.json`, `config.py`
- `docs/references/golden-set-t10-v2.md` (Gamma là sản phẩm chính sprint 1)

## Nhiệm vụ

### 1. Schema v0.2 (`spikes/m1-crawl-extract/schema.py`)
- Thêm `PKB_SCHEMA_VERSION = "0.2"`.
- `Plan` theo Quy tắc trích xuất giá: `list_price`, `promo_price`, `promo_terms`, `price_unit` (`month|year|seat_month|seat_year|one_time`), `billing_cycle` (`monthly|quarterly|yearly|one_time`), `currency`, `price_text`, `limits`, `audience`. Bỏ `price` và `billing_period`. **Không** có giá trị `unknown`.
- `Pricing`: thêm `usage_prices[]` (name, unit, price, currency + fact), `default_view`, `other_views[]`, `region`, `locale`.
- Tách 2 lớp:
  - `PKBExtract`: phần LLM điền ở 1.4 (identity, pricing, features, use_cases, limitations).
  - `PKBData`: toàn bộ nội dung cột `product_knowledge.data` theo JSON mẫu của đặc tả M1, gồm cả các trường 1.5–1.6 (audiences, usp, competitors, brand, compliance, affiliate, quality). Các trường 1.6 để optional, có `origin` (`crawled|merchant|inferred`). Có `schema_version`.
  - `Source`: 1 phần tử của cột `product_knowledge.sources` (id, url, page_type, fetched_at, content_hash, region, locale, variant). Đường dẫn Storage của markdown và ảnh đặt ở đây (ERD: "private Storage paths").
- **Không** đưa `product_id`, `version`, `status`, `approved_by` vào JSON: đó là cột của bảng.

### 2. Prompt trích xuất (`extract.py`)
Thêm quy tắc 1–5 của đặc tả vào `SYSTEM_PROMPT`: tách niêm yết / khuyến mãi, cấm tự tính hay quy đổi giá, 1 plan có nhiều chu kỳ thì ghi nhiều dòng, giá theo token/giây/credit đưa vào `usage_prices`, ghi tab mặc định của trang giá. Viết ngắn, có 1 ví dụ đúng (Claude Pro: `17, month, yearly` và `20, month, monthly`).

### 3. Chạy lại
- Thêm Gamma vào `products.json` (`https://gamma.app`), crawl Gamma.
- Chạy **chỉ** `gemini-3.5-flash-lite`, mode `batch`, cho Claude, Dreamina, Gamma. Claude và Dreamina dùng lại markdown đã crawl nếu còn trong `output/<slug>/pages/`; nếu không còn thì crawl lại.
- Chạy `--dry-run` trước. Ngân sách lần này **≤ $0.20**; vượt thì dừng và báo.
- Giữ kết quả v0.1: chuyển các file `pkb.*.json` và `metrics.csv` cũ sang `output/v0.1/` bằng `git mv`. Kết quả mới ghi vào `output/<slug>/pkb.<model>.json` và `output/metrics.csv` (thêm cột `schema_version`).

### 4. Đối chiếu giá (AC-04 v0.2)
- So từng plan trong PKB mới với raw markdown của trang pricing đã crawl (không mở web lần 2). Điền `price_plan_correct` + `price_plan_note` trong `metrics.csv`.
- Ghi bảng so sánh v0.1 → v0.2 vào README (mục mới "Kết quả v0.2"). Nêu rõ lỗi còn lại, không làm đẹp số.
- Golden Facts của Gamma chưa có trong repo (qa-log #11): ghi "chờ đối chiếu với Golden Facts" cho Gamma.

### 5. Xuất JSON Schema làm contract
- Viết `spikes/m1-crawl-extract/export_schema.py`: xuất `PKBData` và `Source` ra `docs/specs/pkb/pkb-data.v0.2.schema.json` và `docs/specs/pkb/pkb-sources.v0.2.schema.json` (Pydantic `model_json_schema()`).
- Viết `docs/specs/pkb/README.md` (ngắn, câu đơn giản):
  - PKB nằm ở cột nào (`product_knowledge.data`, `.sources`), field nào là cột bảng, không nằm trong JSON.
  - Bảng trường chính: tên, kiểu, bắt buộc, ai điền (1.4 / 1.5 / 1.6 / merchant), ví dụ.
  - Quy tắc version: đổi tên hay xoá trường thì tăng số version; thêm trường optional thì không phá bản cũ.
  - Đề xuất key bắt buộc trong `generation_jobs.result_manifest` cho `job_type = 'crawl'`: `pkb_version`, `pages_used`, `tokens_in`, `tokens_out`, `cost_usd`, `model`. Ghi rõ "đề xuất, chờ chốt ở issue #23".

### 6. `demo.py`
Đọc được PKB v0.2 (bảng plan hiện `list_price`, `promo_price`, `price_unit`, `billing_cycle`; có mục `usage_prices`) và có Gamma. Demo dùng ở buổi T6 09/10, nên phải chạy được.

## Phạm vi
- Làm: `spikes/m1-crawl-extract/**`, `docs/specs/pkb/**`.
- Không làm: sửa `docs/specs/m1-product-intelligence.md`, `docs/specs/erd/**`, ADR, decision-log, qa-log (sẽ làm ở PR M1 spec v0.3). Không sửa `services/worker`. Không crawl thêm product ngoài Gamma.

## Acceptance criteria
- [ ] `schema.py` không còn `price` / `billing_period` / `unknown`; có `PKB_SCHEMA_VERSION = "0.2"`.
- [ ] 3/3 PKB mới hợp lệ theo schema; 0 fact thiếu `source_id` hoặc `evidence`.
- [ ] `metrics.csv` có 3 dòng v0.2 (Claude, Dreamina, Gamma × 3.5-flash-lite × batch), điền `price_plan_correct` / `price_plan_note`; chi phí mỗi product ≤ $0.05.
- [ ] Tổng chi phí API lần này ≤ $0.20 (ghi số thật trong README).
- [ ] README có bảng v0.1 → v0.2, nêu lỗi còn lại.
- [ ] `uv run python export_schema.py` sinh 2 file JSON Schema; chạy lại không đổi nội dung.
- [ ] `docs/specs/pkb/README.md` có bảng trường + quy tắc version + đề xuất `result_manifest`.
- [ ] `uv run python demo.py` chạy được, hiện 3 product.
- [ ] `uvx ruff check .` và `uvx ruff format --check .` sạch.

## Ràng buộc
- Không thêm thư viện. Không commit `.env`, key, `output/demo.html`, `pages/`, `llm_cache/`.
- Trình bày danh sách file sẽ tạo/sửa/chuyển trước khi làm, chờ người dùng duyệt.
- Không dùng `git reset --hard`, force push.

## Khi xong
- Commit theo Conventional Commits (vd. `feat(m1): schema PKB v0.2 theo quy tắc giá, chạy lại spike`). Commit kèm file prompt này (`docs/prompts/be-m1-pkb-schema-v0-2.md`).
- Mở PR vào `dev`, body có bảng v0.1 → v0.2 và chi phí.
- Trả về: link PR, bảng kết quả giá, tổng chi phí, lệnh chạy demo.
