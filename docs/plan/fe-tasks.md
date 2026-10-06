# Công việc Front‑End (FE) – Sprint 1

| # | Công việc (câu) | Thời gian ước tính (h) | Tiêu chí chấp nhận |
|---|-----------------|------------------------|---------------------|
| FE‑1 | **Triển khai component `Header`** – xây dựng header đáp ứng, hiển thị logo và nút điều hướng, export để các phần khác dùng. | 1.5 | Header hiển thị đúng trên desktop và mobile, nút điều hướng mở sidebar. |
| FE‑2 | **Tạo component `Footer`** – thêm nội dung bản quyền và các link bên ngoài, đảm bảo luôn ở cuối trang. | 1.0 | Footer xuất hiện trên mọi trang, các link mở trong tab mới. |
| FE‑3 | **Phát triển UI `ReviewCard`** – thẻ hiển thị thumbnail video, tiêu đề, điểm số do AI tạo, và cho phép click tới trang chi tiết. | 2.0 | Thẻ khớp thiết kế, khi click dẫn tới `/review/:id`. |
| FE‑4 | **Xây dựng component `SearchBar`** – ô input có debounce, gọi endpoint BE `/search` và hiển thị kết quả. | 1.5 | Yêu cầu search được gửi sau 300 ms tạm dừng, danh sách kết quả cập nhật đúng. |
| FE‑5 | **Tạo trang `VideoPlayer`** – nhúng thẻ `<video>`, hiển thị overlay transcript AI, xử lý trạng thái loading. | 2.0 | Video phát được, transcript đồng bộ, spinner loading biến mất khi sẵn sàng. |
| FE‑6 | **Thêm `ErrorBoundary` toàn cục** – bắt lỗi React và hiển thị UI dự phòng thân thiện. | 1.0 | Khi có lỗi bất kỳ component, UI fallback xuất hiện mà không làm sụp app. |

**Tổng thời gian FE:** ~9 h
