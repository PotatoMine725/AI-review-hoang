# Công việc AI / Worker (AI) – Sprint 1

| # | Công việc (câu) | Thời gian ước tính (h) | Tiêu chí chấp nhận |
|---|-----------------|------------------------|---------------------|
| AI‑1 | **Xây dựng thư viện template Prompt** – các prompt tái sử dụng cho việc tóm tắt video và tính điểm. | 1.0 | Thư viện xuất ra ít nhất 2 template; có unit test kiểm tra thay thế placeholder. |
| AI‑2 | **Viết handler chính cho Worker** – lấy job từ queue, gọi LLM, lưu kết quả JSON vào Supabase. | 2.0 | Handler xử lý payload test, lưu các trường cần thiết, log thành công. |
| AI‑3 | **Xây dựng post‑processor kết quả** – xác thực schema JSON, tính confidence score, gắn metadata. | 1.0 | Processor trả về object hợp lệ; validation schema thành công. |
| AI‑4 | **Tạo scaffold test Jest (hỗ trợ AI)** – tự động tạo file test cho worker. | 1.0 | File test tồn tại, chạy `npm test` và vượt qua baseline. |

**Tổng thời gian AI:** ~5 h
