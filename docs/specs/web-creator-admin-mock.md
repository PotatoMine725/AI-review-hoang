# Mô tả giao diện mock Creator và Admin

Đây là giao diện mock data gồm hai khu vực Creator và Admin. Chưa kết nối backend, model AI, cào dữ liệu hoặc tạo video thật. Tên model, prompt, video, token, người dùng, gói đăng ký và PKB hiển thị bằng dữ liệu mẫu để xem giao diện.

### Navigation và cài đặt

- Tên dự án ở bên trái, ô tìm dự án/video ở giữa, avatar và tên người dùng ở góc trên phải.
- Nút ẩn/hiện menu bên trái ở góc dưới trái.
- Cài đặt có Tiếng Việt/English, sáng/tối và kiểu xem video lưới/liệt kê.

### Creator

Menu bên trái có Tạo dự án mới và lịch sử dự án. Mỗi dự án hiển thị các lần tạo video mẫu và có thể mở lại để tiếp tục thao tác mock.

Khung nhập gồm:

- Link sản phẩm bắt buộc và ghi chú bổ sung.
- Dải phía trên: chọn khung hình và xem số token mô phỏng.
- Dải phía dưới: chọn số lượng video, phong cách và thời gian.
- Nút `+` thêm ảnh hoặc tài liệu tham khảo, nút Custom mở cài đặt chi tiết.
- Ô chọn model minh họa, nút mic mô phỏng nhập ghi chú và nút Tạo video mẫu.

Các lựa chọn hiển thị trong cấu hình mock:

- Model: các tên Veo, Kling, Sora dùng để minh họa ô chọn, chưa tích hợp model nào.
- Số lượng: 1–4 video.
- Phong cách: Điện ảnh, Hoạt hình, Chân thực, Tối giản.
- Thời gian: 5, 10, 15, 30 hoặc 60 giây.
- Khung hình: 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21.

Custom có ô chỉnh prompt mẫu, khung mở đầu, độ phân giải 720p/1080p, ngôn ngữ video, máy quay và nội dung cần tránh. Nút tạo prompt từ link hiển thị nội dung mẫu.

Mic mở giao diện mô phỏng gồm lựa chọn tiếng Việt/Anh, đoạn nói mẫu, ô sửa nội dung và nút thêm vào ghi chú; chưa thu âm hoặc nhận dạng giọng nói.

Tệp tham khảo hỗ trợ ảnh PNG/JPG/WebP/GIF và tài liệu PDF/Word/TXT/MD, tối đa 6 tệp, mỗi tệp 10 MB. Có thể xem trước ảnh/PDF, tải lại tài liệu hoặc gỡ tệp khỏi khung nhập.

Khi bấm Tạo video, các video mẫu có sẵn được hiển thị phía trên khung nhập trong hội thoại dự án. Mỗi lần thao tác có link nguồn, ghi chú, tệp tham khảo, cấu hình và số token mô phỏng. Có trình phát, tải MP4 mẫu, xem prompt mẫu và dùng lại cấu hình.

### Admin

Menu bên trái gồm bốn mục, các thao tác đều áp dụng trên dữ liệu mẫu:

- **Người dùng:** danh sách, thông tin, gói đăng ký và trạng thái tài khoản; có thao tác chỉnh sửa.
- **Token:** số dư từng người dùng, điều chỉnh token kèm lý do và lịch sử giao dịch.
- **Gói đăng ký:** danh sách gói, giá, số token và trạng thái; có thao tác chỉnh sửa.
- **PKB:** tìm kiếm, lọc danh sách và xem chi tiết thông tin sản phẩm, nguồn dữ liệu, giá và lịch sử phiên bản.
