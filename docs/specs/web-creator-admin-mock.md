# Đặc tả giao diện mock Reviewlab

Cập nhật: **16/10/2026**. Mốc FE: [commit dd25f64](https://github.com/PotatoMine725/AI-review-FE/commit/dd25f6419ced9e106a9789a3f3dc97f76287bef6), [PR FE #14](https://github.com/PotatoMine725/AI-review-FE/pull/14). Bản mô tả Creator/Admin trước đó: [PR BE #64](https://github.com/PotatoMine725/AI-review-BE/pull/64).

## 1. Phạm vi và trạng thái

UI mock đã có các trang công khai, đăng nhập/đăng ký và workspace Creator/Admin. Tài liệu này mô tả giao diện và hành vi của mốc FE trên; trạng thái merge/xuất bản xem tại PR FE, không mặc định đã triển khai lên môi trường dùng thật.

Auth, thu thập thông tin trong màn Creator, prompt, tạo video, token và quản trị workspace trong phạm vi này dùng dữ liệu phía trình duyệt. Hoàn thành UI mock không đồng nghĩa đã tích hợp Supabase Auth, API nghiệp vụ, crawl/LLM, render hoặc thanh toán. Các route review/API khác ngoài phạm vi này không được kết luận chỉ từ tài liệu này.

| Route | Quyền xem trong mock | Nội dung |
|---|---|---|
| `/` | Công khai | Landing Creative, quy trình, giới thiệu, gói minh họa, lời mời bắt đầu |
| `/price` | Công khai | Ba gói minh họa và câu hỏi thường gặp |
| `/about` | Công khai | Giới thiệu Reviewlab và cách sáng tạo cùng AI |
| `/credits` | Công khai | Ghi công Crawl4AI/UncleCode |
| `/login`, `/signup` | Công khai | Đăng nhập/đăng ký mock, bố cục riêng |
| `/creator/create`, `/creator/project/[id]` | Có phiên mock | Tạo dự án, xem và tiếp tục lịch sử dự án |
| `/admin/users`, `/admin/tokens`, `/admin/plans`, `/admin/pkb` | Admin mock | Quản trị dữ liệu mẫu |

## 2. Các trang công khai

- Dùng cùng tông xám/trắng, chữ tối, điểm nhấn tím và bảng màu sáng/tối của workspace; có bản Việt/Anh và bố cục desktop/mobile.
- Navigation gồm Home/Create/Price/About; Price và About mở `/price`, `/about`, không còn chỉ cuộn về section trên landing. Mục hiện tại được đánh dấu; navigation căn giữa, không nền capsule hay gạch dưới.
- Trên landing, navigation trong suốt nằm trên Creative Showcase. Settings là chữ đơn giản, mở menu thả xuống để đổi ngôn ngữ và giao diện. Trên mobile có menu điều hướng thu gọn; Escape hoặc chọn liên kết sẽ đóng menu.
- Hero dùng ảnh Creative nền trong suốt với biểu tượng phát và dải phim. Đổi phong cách/khung hình và Preview chỉ thay đổi minh họa/chuyển động CSS, không gọi AI hay phát video đã tạo. Ảnh chặn kéo và menu chuột phải; không có thanh `00:00–00:18`. Mô tả tiếng Anh nằm một dòng ở desktop và tự xuống dòng trên màn nhỏ.
- Phần dưới landing có ba bước minh họa, thông tin sản phẩm/ý tưởng video, bảng giá và CTA. Không đưa trạng thái giả thành bằng chứng video đã được AI tạo.
- Footer dùng chung cho landing, Price, About và Credits; có liên kết GitHub, góp ý, ghi công, Crawl4AI và UncleCode. Login/signup không có navigation hay footer này.

### Bảng giá minh họa

Landing và `/price` dùng chung dữ liệu hiển thị:

| Gói | Giá hiển thị (VND) | Token mẫu |
|---|---:|---:|
| Free | 0 | 500 |
| Creator | 299.000 | 5.000 |
| Pro | 799.000 | 15.000 |

Giá/token là dữ liệu mẫu, không có chu kỳ thanh toán hoặc quyền lợi trả phí được xác nhận. Nút khám phá chuyển sang `/signup`; chưa mua gói hay thanh toán. `/price` ghi rõ giới hạn này và có câu hỏi mở/đóng bằng phần tử `details`.

`/about` giới thiệu ba ý: hiểu đúng sản phẩm, giữ góc nhìn riêng và tập trung sáng tạo; dùng minh họa nhân vật tương tác với video, có liên kết bắt đầu và xem gói.

## 3. Đăng nhập và đăng ký

- Là hai trang riêng, giữ logo và liên kết về trang chủ. Desktop có nhân vật/video ở bên trái, form ở bên phải; bong bóng kính/ngôi sao tím nhạt trang trí quanh nhân vật, không chặn thao tác form. Mobile ưu tiên form; hỗ trợ giảm chuyển động theo thiết lập thiết bị.
- Login nhận tên tài khoản mẫu hoặc email, mật khẩu và nút hiện/ẩn mật khẩu; có liên kết đăng ký và phần tài khoản mẫu thu gọn.
- Demo Creator: `creator` hoặc `creator@reviewlab.demo`; Admin: `admin` hoặc `admin@reviewlab.demo`. Mật khẩu chung: `123456`. Đây chỉ là thông tin truy cập mock.
- Signup nhận họ tên 2–80 ký tự, email hợp lệ, mật khẩu 8–128 ký tự và xác nhận trùng khớp; email trùng trong dữ liệu trình duyệt bị từ chối. Tài khoản mới có vai trò Creator.
- Tài khoản/phiên nằm trong localStorage; mật khẩu được lưu dưới dạng hash có salt, không phải xác thực server. Hai tài khoản demo dùng chung dữ liệu workspace mẫu; tài khoản đăng ký mới có dữ liệu dự án/tệp riêng trong trình duyệt.
- Cập nhật tài khoản demo cũ sang thông tin mới giữ lại tài khoản đăng ký và dữ liệu dự án. Khi bộ nhớ lỗi, form bị khóa và có thông báo; trong lúc xử lý không cho gửi lặp.
- Chưa đăng nhập mà mở workspace sẽ chuyển về `/login?next=...`. Sau login, chỉ chấp nhận đường dẫn Creator/Admin phù hợp vai trò; mặc định về `/creator/create` hoặc `/admin/users`. Creator mở Admin sẽ thấy trang giới hạn quyền. Đây là kiểm tra giao diện mock, không thay quyền phía server.

## 4. Workspace Creator và Admin

### Navigation và cài đặt workspace

- Tên dự án ở bên trái, ô tìm dự án/video ở giữa, avatar và tên người dùng ở góc trên phải.
- Nút ẩn/hiện menu bên trái ở góc dưới trái.
- Cài đặt có Tiếng Việt/English, sáng/tối và kiểu xem video lưới/liệt kê.

### Creator

Menu bên trái có Tạo dự án mới và lịch sử dự án. Mỗi dự án hiển thị các lần tạo video mẫu và có thể mở lại để tiếp tục thao tác mock.

Khung nhập gồm:

- Link sản phẩm bắt buộc và ghi chú bổ sung.
- Dải phía trên: chọn khung hình và xem số token mô phỏng.
- Dải phía dưới: chọn số lượng video, phong cách và thời gian.
- Nút `+` thêm ảnh hoặc tài liệu tham khảo, nút Chi tiết mở thông tin sản phẩm và cấu hình dự án.
- Ô chọn model minh họa, nút mic mô phỏng nhập ghi chú và nút Tạo video mẫu.

Các lựa chọn hiển thị trong cấu hình mock:

- Model: các tên Veo, Kling, Sora dùng để minh họa ô chọn, chưa tích hợp model nào.
- Số lượng: nhập số nguyên dương an toàn; UI hiện không giới hạn cứng 4 video. Đầu vào không hợp lệ bị chặn. Giới hạn/quota thật cần do BE kiểm soát khi tích hợp.
- Phong cách: Điện ảnh, Hoạt hình, Chân thực, Tối giản.
- Thời gian: 5, 10, 15, 30 hoặc 60 giây.
- Khung hình: 16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3, 4:5, 5:4, 21:9, 9:21.

Chi tiết có luồng mô phỏng thu thập nguồn → chuẩn hóa → review thông tin sản phẩm. Người dùng kiểm tra/sửa tên, mô tả, giá, phiên bản và link nguồn, rồi xác nhận trước khi tạo video mẫu. Đổi link, thông tin hoặc tệp tham khảo sẽ làm mất xác nhận trước đó. Đóng hộp thoại hoặc đổi link hủy tiến trình mô phỏng đang chạy; không có truy cập website thật từ tiến trình này.

Chi tiết cũng có ô chỉnh prompt mẫu, khung mở đầu, độ phân giải 720p/1080p, ngôn ngữ video, máy quay và nội dung cần tránh. Nút tạo prompt từ link dựng nội dung mẫu. Thiếu xác nhận thông tin, link không hợp lệ, thiếu nội dung cần thiết, tài khoản bị tạm dừng hoặc không đủ token mẫu sẽ chặn tạo video mẫu và hiển thị lý do.

Mic mở giao diện mô phỏng gồm lựa chọn tiếng Việt/Anh, đoạn nói mẫu, ô sửa nội dung và nút thêm vào ghi chú; chưa thu âm hoặc nhận dạng giọng nói.

Tệp tham khảo hỗ trợ ảnh PNG/JPG/WebP/GIF và tài liệu PDF/Word/TXT/MD, tối đa 6 tệp, mỗi tệp 10 MB. Có thể xem trước ảnh/PDF, tải lại tài liệu hoặc gỡ tệp khỏi khung nhập.

Khi bấm Tạo video, các video mẫu có sẵn được hiển thị phía trên khung nhập trong hội thoại dự án. Mỗi lần thao tác có link nguồn, ghi chú, tệp tham khảo, cấu hình và số token mô phỏng. Có trình phát, tải MP4 mẫu, xem prompt mẫu và dùng lại cấu hình.

### Admin

Menu bên trái gồm bốn mục, các thao tác đều áp dụng trên dữ liệu mẫu:

- **Người dùng:** danh sách, thông tin, gói đăng ký và trạng thái tài khoản; có thao tác chỉnh sửa.
- **Token:** số dư từng người dùng, điều chỉnh token kèm lý do và lịch sử giao dịch.
- **Gói đăng ký:** danh sách gói, giá, số token và trạng thái; có thao tác chỉnh sửa.
- **PKB:** tìm kiếm, lọc danh sách và xem chi tiết thông tin sản phẩm, nguồn dữ liệu, giá và lịch sử phiên bản.

## 5. Lưu trạng thái và thông báo

- Ngôn ngữ, sáng/tối, kiểu xem video và trạng thái sidebar được lưu trên trình duyệt. Chuyển giữa trang công khai và auth giữ lựa chọn ngôn ngữ/giao diện.
- Draft, xác nhận sản phẩm và lịch sử dự án có thể mở lại sau khi tải lại trang. Tệp tham khảo được lưu cục bộ theo phạm vi tài khoản; chưa upload lên Storage thật.
- Các trạng thái đã có trong mock gồm mở workspace, thêm tệp, tiến trình xử lý sản phẩm, sai thông tin đăng nhập, email trùng, xác nhận không hợp lệ, thiếu token, lỗi lưu và không tìm thấy dự án.
- Chỉ báo/overlay phát triển Next.js được ẩn khỏi giao diện preview; thông tin chẩn đoán vẫn ở Console/terminal. Việc ẩn overlay không có nghĩa lỗi đã được sửa hoặc được bỏ qua khi nghiệm thu.

## 6. Bàn giao tích hợp BE

Đây là danh sách chỗ cần thay mock bằng dữ liệu thật, **không phải endpoint mới đã được chốt hoặc triển khai**. [API contract](api-contract.md), [đặc tả M1](m1-product-intelligence.md) và các ADR hiện hành tiếp tục là nguồn chuẩn về kiến trúc, quyền và trạng thái endpoint.

| Nhóm | FE hiện tại | Công việc tích hợp còn lại |
|---|---|---|
| Auth/phiên/quyền | Tài khoản, vai trò và phiên localStorage | Supabase Auth; truyền access token và kiểm quyền tại server cho API nghiệp vụ |
| Product/PKB | Tiến trình, dữ liệu và xác nhận mô phỏng | Tạo job/đọc trạng thái, lấy/sửa/xác nhận dữ liệu theo hợp đồng M1; xử lý lỗi, hủy/retry theo khả năng API đã chốt |
| Tệp tham khảo | Tệp cục bộ trong trình duyệt | Upload/đọc Storage với quyền sở hữu, loại/kích thước và thời hạn truy cập được kiểm tra phía server |
| Tạo video/lịch sử | Prompt, request hoàn thành, MP4 và số dư mẫu | Job/render thật, tiến độ, nguồn sản phẩm/phiên bản, kết quả và URL media có quyền truy cập |
| Token/gói | Công thức ước tính và dữ liệu gói mẫu | Server quyết định báo giá, quota, ghi nhận giao dịch; tránh trừ lặp khi retry; chưa có thanh toán |
| Admin | CRUD và giới hạn vai trò trên mock | Xác thực Admin, phân quyền server, validation, xử lý xung đột và lưu thay đổi thật |

Không lấy tên model, lựa chọn UI, giá hoặc công thức token mẫu làm cam kết năng lực provider/chi phí thật. Khi nối API, từng luồng cần bổ sung loading/empty/error, hành vi retry và mapping request/response theo hợp đồng tương ứng, không tạo lớp nghiệp vụ thứ hai trong Next.js.

## 7. Tiêu chí nghiệm thu UI mock và bằng chứng

- [x] `/`, `/price`, `/about`, `/credits`, `/login`, `/signup` mở được khi chưa có phiên; liên kết navigation/footer tới đúng trang.
- [x] Login/signup độc lập với navigation/footer công khai; đổi Việt/Anh và sáng/tối được giữ khi chuyển trang/tải lại.
- [x] Có bố cục desktop/mobile, menu bàn phím và trạng thái hiện tại; kiểm tra không tràn ngang ở 320/390/768/1024/1440px theo các route trong bộ browser test.
- [x] Đăng ký/đăng nhập/đăng xuất, sai thông tin, email trùng, cập nhật demo và phạm vi dữ liệu tài khoản hoạt động trong mock.
- [x] Link bắt buộc, tiến trình có thể hủy, thông tin cần xác nhận, cấu hình/số lượng, token mẫu và mở lại dự án được kiểm tra.
- [ ] Tích hợp auth, crawl/LLM/render, Storage, quyền server và thanh toán thật: chưa nghiệm thu trong tài liệu này.

Bằng chứng đã chạy tại FE commit `dd25f64` ngày 16/10/2026: `corepack pnpm test` đạt 25 bài; `corepack pnpm lint`, `corepack pnpm exec tsc --noEmit` và `corepack pnpm build` đạt. Browser suites: `node tests/landing.browser.cjs` (public pages, auth độc lập, Việt/Anh, sáng/tối, responsive), `node tests/auth-product.browser.cjs` (auth/review sản phẩm/phạm vi tài khoản) và `node tests/studio.browser.cjs` (Creator/Admin/cấu hình/lịch sử/mobile) đều đạt. Đây là bằng chứng UI mock, không phải kiểm thử end-to-end với BE thật.
