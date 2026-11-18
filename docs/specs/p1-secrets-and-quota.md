# P1: khoá API, nơi lưu và hạn mức

**Issue:** #99 · **Ngày:** 18/11/2026 · **Trạng thái:** đề xuất; tên biến cho provider ảnh/TTS là chỗ giữ chỗ cho tới khi Thông bàn giao khoá và xác nhận provider.

## 1. Nguyên tắc

- Giá trị thật **chỉ** nằm trong `.env` (đã gitignore) hoặc biến môi trường của nơi chạy. Không commit, không dán vào issue/PR/chat, không ghi vào workflow n8n.
- Mọi khoá là `SecretStr` trong `worker.settings.Settings`: `repr()`, log và lỗi chỉ in `**********`. Gọi `.get_secret_value()` ngay tại chỗ gửi request.
- Thiếu khoá thì lỗi nêu **tên biến** thiếu (`MissingConfigError`, API trả `503`), không bao giờ in giá trị.
- Khoá `SUPABASE_SERVICE_ROLE_KEY` và `N8N_SERVICE_TOKEN` chỉ ở server; FE chỉ biết `NEXT_PUBLIC_*`.
- Không tự bật billing. Chỉ gọi provider thật trong quota miễn phí đã xác minh hoặc ngân sách được cấp (decision-log #20; AC-P1-05 mục 5).

## 2. Biến môi trường (`services/worker/.env.example`)

| Biến | Dùng cho | Bước cần | Ai giữ |
|---|---|---|---|
| `SUPABASE_URL` | Mọi lời gọi DB/Auth | `api` | Hoàng |
| `SUPABASE_ANON_KEY` | Đọc thay mặt owner (RLS), xác minh JWT | `api` | Hoàng |
| `SUPABASE_SERVICE_ROLE_KEY` | RPC, ghi job (bỏ qua RLS) | `api` | Hoàng |
| `N8N_SERVICE_TOKEN` | n8n gọi endpoint dịch vụ (`X-Service-Token`) | `api_service` | Hoàng, tự sinh: `openssl rand -hex 32` |
| `GEMINI_API_KEY` | Extract PKB (M1), sinh script (M2) | `extract`, `script` | Thông giao |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Ảnh AI (cảnh AI, AC-P1-05) | `ai_scene` | Thông giao (chờ xác nhận provider) |
| `FAL_KEY` | Provider ảnh dự phòng (nếu Thông chọn) | chưa gắn bước | chờ Thông |
| `WORKER_PAGE_STORE_DIR`, `RUNNER_POLL_INTERVAL_S`, `RUNNER_MAX_ATTEMPTS`, `RUNNER_RETRY_BACKOFF_S` | Bộ chạy job (không phải khoá) | `runner` | Hoàng |
| `JOB_COST_LIMIT_USD` | Ngưỡng chi phí một job (tuỳ chọn) | `Settings.check_cost` | Hoàng |

`STEP_REQUIREMENTS` trong `settings.py` là nguồn duy nhất cho "bước nào cần biến nào"; thêm provider thì thêm vào đó và vào bảng này. Provider chỉ được gọi qua adapter, chọn bằng config (ADR-0005).

## 3. Nhận khoá từ Thông và đặt vào máy

1. Nhận khoá qua kênh riêng (không dán vào GitHub/chat nhóm).
2. `cp services/worker/.env.example services/worker/.env`, điền giá trị. Kiểm: `git status` không được hiện `.env`.
3. Chạy n8n: đặt `N8N_SERVICE_TOKEN` thành **credential** (Header Auth) của n8n, không ghi vào node. Workflow chỉ tham chiếu credential.
4. Thiếu biến nào, API báo tên biến đó; chạy `GET /health` rồi gọi thử endpoint của bước tương ứng.

Lộ khoá (lỡ commit/dán): coi như đã lộ, **xoay ngay** ở nhà cung cấp, cập nhật `.env`, rồi mới dọn lịch sử. Với `N8N_SERVICE_TOKEN`: sinh token mới, đổi ở `.env` và credential n8n.

## 4. Hạn mức và chi phí

Chưa có số quota đã xác minh trong repo cho Cloudflare/Fal; **không ghi số ở đây khi chưa kiểm trên dashboard của provider**. Việc cần làm khi nhận khoá:

| Việc | Ghi vào đâu |
|---|---|
| Xem gói đang dùng và hạn mức/ngày của từng khoá (Gemini, ảnh AI, TTS) | Bảng dưới (điền sau) |
| Xác nhận khoá là gói miễn phí, chưa gắn thẻ/billing | Ghi cùng bảng |
| Đặt `JOB_COST_LIMIT_USD` thấp (gợi ý bắt đầu 0.10) cho pilot | `.env` |

| Provider | Gói | Hạn mức đã xác minh | Ngày kiểm | Người kiểm |
|---|---|---|---|---|
| Gemini | _chưa điền_ | | | |
| Ảnh AI | _chưa điền_ | | | |
| TTS | _chưa điền_ | | | |

Chi phí mỗi lần chạy ghi vào `script_revisions.cost_breakdown` / `generation_jobs.cost_breakdown` (contract `cost-breakdown.v1`); `Settings.check_cost` chặn job vượt `JOB_COST_LIMIT_USD` (job `failed`, `error` nêu rõ). Một lần crawl+extract PDFCraft ngày 17/11 tốn khoảng $0,0056 theo giá niêm yết (xem `docs/report/p1-pilot-pdfcraft/README.md`).

## 5. Chưa làm

Adapter gọi provider ảnh/TTS (chờ Thông chốt provider và khoá); tự động kiểm quota; kho bí mật quản lý (hiện dùng `.env`).
