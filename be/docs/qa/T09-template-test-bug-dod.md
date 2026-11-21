# BỘ TEMPLATE TEST CASE, BUG REPORT & DEFINITION OF DONE (TASK T09)

- **Dự án:** AI Review Content Factory & Affiliate Network
- **Mã công việc:** `T09` (Sprint 0)
- **Phiên bản:** 1.0
- **Ngày lập:** 05/10/2026

- **Phạm vi áp dụng:** Toàn bộ thành viên dự án (BA, Dev, AI, Video, Tester)

---

## PHẦN 1: TEMPLATE TEST CASE (MẪU KỊCH BẢN KIỂM THỬ)

Mỗi test case được quản lý trên Notion/Jira/Excel theo cấu trúc chuẩn sau:

| Trường thông tin | Ý nghĩa | Ví dụ mẫu |
|---|---|---|
| **Test Case ID** | Mã định danh duy nhất | `TC_CSV_001` |
| **Module / Phân hệ** | Phân hệ chức năng | Module 6: Affiliate & Attribution (CSV Import) |
| **Tiêu đề (Title)** | Mục tiêu kiểm thử ngắn gọn | Kiểm tra hệ thống báo lỗi khi import file CSV chứa order ID trùng lặp |
| **Mức ưu tiên (Priority)** | P0 (Bắt buộc) / P1 (Quan trọng) / P2 (Bình thường) | **P0** |
| **Loại kiểm thử (Type)** | Functional / Security / Boundary / Integration | Integration & Data Validation |
| **Điều kiện tiên quyết (Pre-conditions)** | Trạng thái cần có trước khi test | 1. Admin đã đăng nhập hệ thống.<br>2. Đã có 1 đơn hàng ID `ORD-101` nạp thành công trước đó. |
| **Các bước thực hiện (Test Steps)** | Các thao tác tuần tự | 1. Truy cập màn hình Admin $\to$ Revenue Import.<br>2. Chọn file `fixture_duplicate.csv` (có chứa dòng `ORD-101`).<br>3. Bấm nút "Upload & Process". |
| **Dữ liệu kiểm thử (Test Data)** | File hoặc giá trị truyền vào | File `fixture_duplicate.csv` |
| **Kết quả mong đợi (Expected Result)** | Hành vi chuẩn của phần mềm | 1. Hệ thống hiển thị bảng preview cảnh báo dòng chứa `ORD-101` bị trùng lặp.<br>2. Không ghi đè hoặc cộng đôi doanh thu của đơn `ORD-101`.<br>3. Các đơn hàng hợp lệ khác vẫn được xử lý bình thường. |
| **Kết quả thực tế (Actual Result)** | Ghi khi chạy test | (Điền khi test: Pass / Fail / Blocked) |
| **Trạng thái (Status)** | Pass / Fail / Pending | Draft |

---

## PHẦN 2: TEMPLATE BUG REPORT (MẪU BÁO CÁO LỖI)

Khi phát hiện bug, Tester tạo Issue trên GitHub / Jira theo đúng mẫu sau:

```markdown
### [BUG-{ID}] [Severity] Tiêu đề ngắn gọn mô tả lỗi
- **Module:** [Ví dụ: Auth / Tracking Link / CSV Import / Commission]
- **Mức độ nghiêm trọng (Severity):** [Blocker (P0) / Critical (P1) / Major (P2) / Minor (P3)]
- **Người báo cáo (Reporter):** Phú (hoặc Duyên/Nhi)
- **Người xử lý (Assignee):** [Tên Dev chịu trách nhiệm, ví dụ: Thông / Tài / Vũ]
- **Môi trường (Environment):** Localhost (Chrome v128) / Supabase Dev

#### 1. Mô tả tóm tắt (Description):
Mô tả hiện tượng lỗi xảy ra là gì, ảnh hưởng ra sao đến luồng demo.

#### 2. Các bước tái hiện (Steps to Reproduce):
1. Đăng nhập bằng tài khoản Creator (`creator1@demo.local`).
2. Vào thư viện video, sao chép link tracking cá nhân.
3. Dán link vào tab ẩn danh trình duyệt và bấm Enter.
4. Quan sát URL được chuyển hướng đến.

#### 3. Kết quả mong đợi (Expected Result):
Trình duyệt phải chuyển hướng người dùng đến đúng trang sản phẩm `https://gamma.app` và ghi nhận 1 click event vào database.

#### 4. Kết quả thực tế (Actual Result):
Trình duyệt báo lỗi "404 Not Found" hoặc redirect về trang trắng; database không ghi nhận click nào.

#### 5. Bằng chứng đính kèm (Evidence):
- Ảnh chụp màn hình lỗi (Screenshot).
- Log console trình duyệt (F12 Console).
- Network tab response (Status code: 500 / 404).
```

---

## PHẦN 3: QUY TRÌNH PHÂN LOẠI & XỬ LÝ LỖI (BUG TRIAGE & SLA)

| Mức độ | Định nghĩa | Thời hạn cam kết xử lý (SLA) |
|---|---|---|
| **P0 - Blocker** | Lỗi làm tắc hoàn toàn luồng demo: không login được, sập server, tính sai hoa hồng, lộ dữ liệu chéo giữa các Creator | **Xử lý ngay lập tức (trong 4 giờ)**. Dừng các task khác để fix. |
| **P1 - Critical** | Lỗi chức năng chính không chạy đúng nhưng có cách đi vòng tạm thời (Workaround): import file CSV không hiện danh sách lỗi, video duyệt xong không tải được | **Sửa trong vòng 24 giờ**. |
| **P2 - Major** | Lỗi giao diện gây hiểu lầm số liệu, định dạng ngày tháng/tiền tệ hiển thị sai, bộ lọc dashboard không hoạt động mượt | **Sửa trong Sprint hiện tại**. |
| **P3 - Minor** | Lỗi chính tả, lệch khoảng cách (margin/padding), hiệu ứng chuyển trang chưa mượt | **Sửa khi có thời gian rảnh**. |

---

## PHẦN 4: DEFINITION OF DONE (DoD - ĐỊNH NGHĨA HOÀN THÀNH)

Một User Story / Task trong Sprint chỉ được coi là **"DONE" (Hoàn thành)** khi thỏa mãn toàn bộ checklist sau:

- [ ] **1. Đạt tiêu chí nghiệm thu (AC):** Chức năng đáp ứng 100% các Acceptance Criteria đã được BA Khánh viết trong Story.
- [ ] **2. Kiểm thử hợp lệ (Test Pass):**
  - Đã được nhóm Test chạy kiểm thử thủ công hoặc tự động.
  - 100% test case P0 liên quan đều Passed.
  - Không còn bug P0 (Blocker) hay P1 (Critical) tồn đọng.
- [ ] **3. Code Review & Phân quyền:**
  - Code được review bởi ít nhất 1 thành viên khác qua Pull Request trên GitHub.
  - Đã bật và kiểm tra RLS (Row Level Security) cho các bảng mới tạo trên Supabase.
- [ ] **4. An toàn bảo mật (No Secrets):**
  - Tuyệt đối không commit API key (OpenAI, Supabase Service Role Key) vào Git. File `.env.example` chỉ chứa tên biến mẫu.
- [ ] **5. Tài liệu & Fixtures:**
  - Các tài liệu giải thích logic hoặc dữ liệu mẫu liên quan đã được đưa vào thư mục `/docs` của dự án.
