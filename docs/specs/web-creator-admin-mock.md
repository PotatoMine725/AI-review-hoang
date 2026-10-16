# Mô tả UI mock Reviewlab

Cập nhật 16/10/2026, theo [PR FE #14](https://github.com/PotatoMine725/AI-review-FE/pull/14).

## Trang công khai

- Landing: giới thiệu Reviewlab, quy trình tạo video và các gói mẫu.
- Price: bảng giá Free, Creator, Pro và câu hỏi thường gặp.
- About: giới thiệu sản phẩm và cách sáng tạo cùng AI.
- Credits: ghi công Crawl4AI/UncleCode.
- Navigation, footer và menu điều hướng trên điện thoại.

## Tài khoản

- Đăng nhập, đăng ký, đăng xuất; có tài khoản mẫu Creator/Admin.
- Hiện/ẩn mật khẩu, kiểm tra thông tin nhập và báo lỗi.
- Phân biệt khu vực Creator/Admin; yêu cầu đăng nhập trước khi vào workspace.

## Creator

- Tạo dự án, tìm kiếm và mở lại lịch sử dự án.
- Nhập link sản phẩm, ghi chú; thêm, xem và gỡ tệp tham khảo.
- Xem tiến trình xử lý mẫu, sửa và xác nhận thông tin sản phẩm trước khi tạo video.
- Chọn model, số lượng, phong cách, thời lượng, khung hình và độ phân giải.
- Chỉnh prompt, khung mở đầu, ngôn ngữ, máy quay và nội dung cần tránh.
- Mô phỏng nhập ghi chú bằng giọng nói.
- Xem, tải video mẫu và dùng lại cấu hình; hiển thị token ước tính.

## Admin

- Người dùng: xem và sửa thông tin, gói, trạng thái tài khoản.
- Token: xem số dư, điều chỉnh và lịch sử giao dịch.
- Gói đăng ký: xem và sửa giá, token, trạng thái.
- PKB: tìm kiếm, lọc, xem thông tin sản phẩm, nguồn và lịch sử phiên bản.

## Chức năng chung và trạng thái

Có chuyển Việt/Anh, sáng/tối, kiểu xem video và thu gọn sidebar; lưu lựa chọn và dữ liệu dự án trên trình duyệt.

Các chức năng trên đang là UI mock dùng dữ liệu mẫu. Chưa kết nối xác thực BE, crawl/AI, tạo video, upload tệp hoặc thanh toán thật.
