# Prompt: hoàn thiện ADR-001, ADR-002 theo #59 (gói miễn phí, xác minh model)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #59 (comment của @VV6505 ngày 11/10, mục 3) · **Branch:** `docs/m1-adr-001-002-finalize` (tạo từ `origin/dev` mới nhất)
- **Liên quan:** `docs/adr/0001-crawl-tool.md`, `docs/adr/0002-llm-provider.md`, decision-log #13, #14, đặc tả M1 v0.3.1

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản (xem `docs/README.md`). Người dùng là AI dev, mới với Python: giải thích ngắn, đúng trọng tâm.

## Bối cảnh (team lead chốt ở #59, 11/10)
- API nghiệp vụ ở FastAPI; hàng đợi PostgreSQL (`generation_jobs`, `FOR UPDATE SKIP LOCKED`). Phần hàng đợi do BE viết ADR riêng, **không** thuộc PR này.
- ADR-001/002 phải hoàn tất trước khi tích hợp provider. Giữ Crawl4AI. Gemini: **xác minh model ID, quota miễn phí, chất lượng đầu ra** trước khi chốt. Không mặc định tên model hay "chế độ batch".
- **Không tự bật dịch vụ trả phí.** CI dùng fixture/mock. Demo nghiệm thu phải có lần chạy AI thật.
- Dự án chỉ dừng ở bản demo, không tạo doanh thu thật.

## Đã xác minh (coordinator tra ngày 12/10/2026, [trang giá](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits))
| Model ID | Free tier | Giá trả phí Standard (in / out, USD / 1M) | Batch API | Dữ liệu dùng để cải thiện sản phẩm Google |
|---|---|---|---|---|
| `gemini-3.5-flash-lite` | Miễn phí (in + out) | 0.30 / 2.50 | 0.15 / 1.25 | Free: **Có** · Paid: Không |
| `gemini-3.1-flash-lite` | Miễn phí (in + out) | 0.25 / 1.50 | 0.125 / 0.75 | Free: **Có** · Paid: Không |

- Rate limit tính **theo project**, không theo API key. RPD reset lúc 0h giờ Thái Bình Dương. Trang tài liệu không ghi số của free tier.
- **Quota thật của project (AI Studio, API key free tier, chủ dự án chụp 12/10/2026), giống nhau cho cả 2 model `gemini-3.5-flash-lite` và `gemini-3.1-flash-lite`:** **15 RPM · 250 000 input token/phút (TPM) · 500 RPD.**
- **Hệ quả:** 1 lời gọi gom 10 trang dùng ~22 000 input token (spike v0.2), xa dưới TPM. Giới hạn chặt nhất là **15 RPM**: biểu đồ AI Studio cho thấy ngày ~06/10 spike chạm 16–18 RPM (lúc chạy mode `per_page`, 27–29 lời gọi liên tiếp). Mode gom 1 lời gọi thì không vướng. RPD 500 đủ cho khoảng 250 product/ngày (1–2 lời gọi mỗi product).
- "Mode `batch`" của spike = gom 10 trang vào **1 lời gọi** `generate_content`. Đây **không phải** Gemini Batch API (bất đồng bộ, giảm 50%). Phải ghi rõ để tránh nhầm (team lead đã hỏi điểm này).

## Nhiệm vụ

### 1. Chạy lại spike trên gói miễn phí (đo thật, $0)
- Dùng `GEMINI_API_KEY` của project **không bật billing** (chủ dự án xác nhận trước khi chạy).
- Product: `elevenlabs` (sản phẩm chính sprint 1), `claude`, `dreamina`. Model: `gemini-3.5-flash-lite` và `gemini-3.1-flash-lite`. Chỉ mode gom 1 lời gọi, `--no-cache`. Không chạy `per_page`.
- Không crawl lại nếu `pages/` còn; chỉ chạy bước trích xuất. Chạy `--dry-run` trước, báo số lời gọi và token, chờ duyệt.
- **Chạy tuần tự** (6 lời gọi, không vượt 15 RPM). Không cần chờ giữa các lời gọi.
- Ghi vào `metrics.csv` như cũ (cột `cost_usd` vẫn tính theo giá niêm yết để so NFR-02). Ghi thêm vào README spike: số lần gặp 429 / retry, thời gian mỗi lời gọi, token vào / ra.
- Đối chiếu giá với raw markdown trang pricing (như spike v0.2). Nếu chủ dự án đưa file Golden Facts của QA (ElevenLabs = T12b), đối chiếu thêm; nếu không có, ghi "chờ Golden Facts".
- `validate_contracts.py` phải pass.

### 2. ADR-002
- Thêm mục **"Cập nhật 12/10/2026 theo #59"** ở đầu (không xoá nội dung cũ):
  - Bảng model ID đã xác minh (bảng trên) + quota free tier (số từ AI Studio, ghi ngày tra).
  - Kết quả chạy lại ở bước 1: so `3.5` với `3.1` (độ đúng giá + tên plan, evidence khớp nguồn, token, 429).
  - Làm rõ thuật ngữ: đổi tên "mode `batch`" trong ADR thành **"gom 1 lời gọi"**; Gemini Batch API **không dùng** (bất đồng bộ, không cần cho demo).
  - **Ràng buộc dữ liệu của free tier:** Google được dùng nội dung để cải thiện sản phẩm. Chỉ gửi nội dung public đã crawl. Tài liệu merchant upload (#53) **không gửi qua free tier** khi chưa có quyết định riêng; ghi là câu hỏi mở.
  - **Chi phí:** chạy free tier thì chi phí thật = $0. Đề xuất: vẫn ghi token và `cost_breakdown` tính theo giá niêm yết, `cost_status = "estimated"`, để NFR-02 vẫn đo được nếu sau này chuyển gói trả phí. Ghi là **đề xuất**, chờ @VV6505 duyệt.
  - CI: không có API key, test dùng fixture / mock của response Gemini (ghi 1–2 câu cách làm).
  - **Ràng buộc cho worker và hàng đợi (gửi BE, #59 mục 2):** quota tính chung cho cả project, nên mọi worker cộng lại không vượt 15 lời gọi Gemini/phút và 500/ngày. Không dùng mode `per_page` (1 lời gọi/trang) trong worker. Lỗi 429 là lỗi tạm thời: retry có chờ (backoff tới ~60 giây), không đánh dấu job `failed` ngay. Hết RPD thì job chờ tới 0h giờ Thái Bình Dương (14h hoặc 15h giờ Việt Nam, tuỳ giờ mùa hè).
- Bỏ các câu khuyên "production dùng gói trả phí".
- Trạng thái: **"Đã chốt (12/10/2026, #59)"** cho Quyết định 1–3 nếu kết quả bước 1 đạt (giá đúng ≥ spike v0.2, không bị chặn quota). Quyết định 4 (embedding) giữ "Hoãn". Nếu kết quả không đạt: giữ "Đề xuất", ghi lý do.

### 3. ADR-001
- Trạng thái → **"Đã chốt (12/10/2026, #59)"**: team lead đồng ý giữ Crawl4AI từ spike.
- Thêm 1 dòng tóm tắt bằng chứng sau spike v0.2: ElevenLabs crawl được (29 trang), Gamma bị WAF và job dừng đúng quy tắc. Không viết lại nội dung khác.

### 4. Logs và đặc tả
- `decision-log.md`: dòng #13, #14 bỏ chữ "Đề xuất", dẫn tới #59 và PR này (chỉ sửa trạng thái, giữ nội dung). Thêm dòng **#20** (2026-10-11): tóm tắt các điểm team lead chốt ở #59: API nghiệp vụ ở FastAPI; hàng đợi PostgreSQL; không tự bật dịch vụ trả phí; CI dùng mock; demo phải chạy AI thật; mở lại #52, #53. Người quyết: @VV6505.
- `docs/specs/m1-product-intelligence.md`: dòng Tech stack của LLM đổi "chờ ADR-002" thành dẫn ADR-002 đã chốt. Thêm dòng lịch sử phiên bản v0.3.2.

## Phạm vi
- Làm: `docs/adr/0001-*`, `docs/adr/0002-*`, `docs/logs/decision-log.md`, `docs/specs/m1-product-intelligence.md`, `spikes/m1-crawl-extract/**` (output, `metrics.csv`, README).
- Không làm: code `services/worker`, ERD, ADR hàng đợi (của BE), contract.

## Acceptance criteria
- [ ] Có số đo free tier cho 3 product × 2 model; không phát sinh chi phí; `validate_contracts.py` pass.
- [ ] ADR-002 có: model ID đã xác minh, quota từ AI Studio (15 RPM, 250 000 TPM, 500 RPD, ngày 12/10) và ràng buộc cho worker, làm rõ "gom 1 lời gọi" ≠ Batch API, ràng buộc dữ liệu free tier, đề xuất ghi chi phí, cách CI mock.
- [ ] Không còn câu "production dùng gói trả phí" trong ADR-002.
- [ ] decision-log có #20; #13, #14 hết chữ "Đề xuất".
- [ ] `uvx ruff check .` và `uvx ruff format --check .` sạch (nếu có sửa code spike).

## Ràng buộc
- Trình bày danh sách thay đổi trước khi sửa, chờ duyệt. Dừng trước khi gọi LLM thật (kèm số dry-run).
- Không commit `.env`, `pages/`, `llm_cache/`, `output/demo.html`. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(m1): hoàn thiện ADR-001, ADR-002 theo #59, đo lại trên gói miễn phí`), kèm file prompt này. Mở PR vào `dev`, body có `Refs #59`, `cc @VV6505`.
- Trả về: link PR, bảng kết quả 3 product × 2 model, quota đã dùng.
