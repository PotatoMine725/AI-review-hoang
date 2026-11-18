# services/n8n

Khung workflow n8n cho pilot P1 (#99). **Chưa chạy thử trên n8n thật** (chưa có instance trong môi trường dựng); `check_workflows.py` chỉ kiểm cấu trúc JSON.

n8n **không** giữ dữ liệu chuẩn và không đọc/ghi DB: chỉ gọi API worker bằng header `X-Service-Token`, truyền `n8n_execution_id` để truy vết. Hợp đồng: [`docs/specs/api-contract.md`](../../docs/specs/api-contract.md) (mục P1), [`p1-pipeline-db-contract.md`](../../docs/specs/p1-pipeline-db-contract.md).

## Dùng

1. Chạy API: `cd services/worker && uv run uvicorn worker.main:app --port 8000` (cần `.env`, xem `docs/specs/p1-secrets-and-quota.md`).
2. n8n → Credentials → tạo **Header Auth** tên `AI Review Worker (X-Service-Token)`: Name `X-Service-Token`, Value = `N8N_SERVICE_TOKEN`. Không dán token vào node.
3. Import `workflows/p1-pilot-skeleton.json`, gán credential cho các node HTTP.
4. Sửa node `Config`: `baseUrl`, `productId` (owner tạo product trước bằng `POST /products`).

## Luồng

`Create crawl job` → (TODO chạy crawl/extract) → chờ job `completed` → **điểm duyệt 1** (poll PKB tới `approved`) → (TODO sinh script M2) → `Create script revision` → **điểm duyệt 2** (poll script tới `approved`) → `Create video job` với đúng `pkb_version`/`script_revision` đã duyệt → (TODO render).

- Idempotency key: `<execution_id>:<bước>`; n8n retry cùng execution không tạo trùng.
- `rejected` ở hai điểm duyệt thì workflow dừng bằng lỗi.
- Poll 30–60 s trong node Wait; có thể đổi sang webhook khi FE/API có callback.

## Chưa có

Bộ nhận job chạy crawl/extract (job hiện dừng ở `queued`), sinh script M2 (#92), render/TTS/ảnh AI (ADR-003/004), giới hạn số lần poll, workflow chạy thử trên n8n thật.
