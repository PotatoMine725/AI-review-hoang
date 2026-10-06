# Công việc Back‑End (BE) – Sprint 1

| # | Công việc (câu) | Thời gian ước tính (h) | Tiêu chí chấp nhận |
|---|-----------------|------------------------|---------------------|
| BE‑1 | **Định nghĩa schema Supabase `reviews`** – các cột `id`, `url`, `status`, `result_json`. | 1.0 | Bảng được tạo, migration chạy thành công, `SELECT * FROM reviews` trả về kết quả. |
| BE‑2 | **Triển khai endpoint GET `/reviews`** – trả về danh sách review paginated. | 1.5 | API trả về JSON có metadata pagination; status 200 OK khi thành công. |
| BE‑3 | **Triển khai endpoint POST `/reviews`** – nhận URL, tạo bản ghi, đưa job vào queue. | 1.5 | Trả về 201 kèm job ID; bản ghi xuất hiện trong bảng `reviews` với status `queued`. |
| BE‑4 | **Triển khai endpoint GET `/reviews/:id`** – trả về trạng thái job và kết quả cuối cùng. | 1.5 | Trả về 200 với trường `status`; khi hoàn tất kèm `result_json`. |
| BE‑5 | **Kết nối Supabase Realtime → queue Worker** – tự động kích hoạt worker khi có bản ghi `reviews` mới. | 2.0 | Worker nhận payload trong vòng vài giây sau khi insert. |
| BE‑6 | **Thêm middleware JWT auth** – bảo vệ các API nội bộ, trả về 401 khi không xác thực. | 1.0 | Các request thiếu token hợp lệ nhận status 401. |

**Tổng thời gian BE:** ~9 h
