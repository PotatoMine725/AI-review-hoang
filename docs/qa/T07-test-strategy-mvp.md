# CHIẾN LƯỢC KIỂM THỬ MVP (MVP TEST STRATEGY)

- **Dự án:** AI Review Content Factory & Affiliate Network
- **Mã công việc:** `T07` (Sprint 0)
- **Phiên bản:** 1.0
- **Ngày lập:** 05/10/2026

- **Phê duyệt:** Nhóm Kiểm thử & Tech Lead
- **Mục tiêu hoàn thành:** Đáp ứng tiêu chí nghiệm thu của Sprint 0 (Hạn 06/10/2026), sẵn sàng bước vào Sprint 1.

---

## 1. Mục tiêu kiểm thử (Test Objectives)

1. **Bảo đảm tính toàn vẹn của chuỗi giá trị MVP (End-to-End Flow):**
   Kiểm chứng 8 bước demo khép kín chạy trơn tru từ đầu đến cuối mà không cần can thiệp trực tiếp vào database:
   $$\text{Nhập sản phẩm} \to \text{AI tạo Script/Hook} \to \text{Tạo video demo} \to \text{Admin duyệt} \to \text{Creator tải video + lấy tracking link} \to \text{Ghi nhận click} \to \text{Import CSV doanh thu giả} \to \text{Tính hoa hồng & Dashboard}$$
2. **Kiểm soát phân quyền & an toàn dữ liệu (Authorization & RLS):**
   Đảm bảo chính sách Row Level Security (RLS) của Supabase hoạt động tuyệt đối: Creator A không bao giờ thấy video, chiến dịch, link tracking, hoặc dữ liệu hoa hồng của Creator B; Creator không có quyền thao tác vào các chức năng của Admin.
3. **Đảm bảo tính chính xác của thuật toán quy thuộc & hoa hồng (Attribution & Commission):**
   Bảo đảm việc import CSV đơn hàng không bị nhân đôi doanh thu (Idempotency), xử lý đúng dòng lỗi, dòng không khớp (unmatched), và tính đúng tỷ lệ hoa hồng theo quy tắc snapshot.
4. **Kiểm soát chất lượng nội dung & Video (QC Content & Video):**
   Ngăn chặn AI bịa đặt tính năng/giá (Anti-hallucination/Anti-slop); video xuất ra đạt chuẩn kỹ thuật dọc 9:16, âm thanh rõ ràng, phụ đề khớp kịch bản.

---

## 2. Phạm vi kiểm thử (Test Scope)

### 2.1. Trong phạm vi MVP (In-Scope)

| STT | Phân hệ / Tính năng | Trọng tâm kiểm thử | Mức ưu tiên |
|:---:|---|---|:---:|
| 1 | **Xác thực & Phân quyền (Auth & RLS)** | Đăng nhập Admin/Creator, chặn truy cập trái phép qua URL, RLS bảo vệ bảng dữ liệu | **P0** |
| 2 | **Quản lý sản phẩm (Product Intelligence)** | Nhập URL/thủ công, sửa và lưu Product Knowledge Base, validate schema JSON facts | **P0** |
| 3 | **Kịch bản & Phê duyệt (Content Strategy & QC)** | Sinh hook/script/caption theo schema JSON 30s, Admin duyệt (Approve) / từ chối (Reject) | **P0** |
| 4 | **Quản lý Video (Video Factory)** | Video dọc 9:16 (15–30s), âm thanh đọc rõ, phụ đề, Admin preview & duyệt, chặn Creator xem video chưa duyệt | **P0** |
| 5 | **Creator Library & Tracking Link** | Creator xem chiến dịch được giao, tải video (signed URL), tạo link tracking cá nhân duy nhất | **P0** |
| 6 | **Click Tracking & Redirect** | Endpoint redirect chuyển hướng đúng URL sản phẩm, ghi nhận đúng 1 click event, chống Open Redirect | **P0** |
| 7 | **Import CSV & Đối soát doanh thu** | Upload CSV, validate định dạng cột, cảnh báo dòng lỗi/trùng, chống nạp đúp cùng order ID | **P0** |
| 8 | **Tính hoa hồng (Commission Calculation)** | Tính hoa hồng theo tỷ lệ (%) snapshot, lưu trạng thái pending/approved, xử lý đơn 0đ/hoàn tiền | **P0** |
| 9 | **Dashboard Báo cáo** | Tổng hợp Clicks, Conversions, Revenue, Commission theo Product/Creator/Campaign; hiển thị rõ nhãn Demo Data | **P0** |
| 10 | **Kịch bản E2E Demo xuyên suốt** | Chạy 1 vòng hoàn chỉnh từ nhập URL sản phẩm đến hiển thị hoa hồng trên Dashboard | **P0** |

### 2.2. Ngoài phạm vi MVP (Out-of-Scope - Không kiểm thử)

- **Không kiểm thử:** AI Avatar nói chuyện 24/7, lip-sync thời gian thực, livestream AI.
- **Không kiểm thử:** Tự động đăng bài hàng loạt lên TikTok/Reels/Shorts qua bot/API mạng xã hội.
- **Không kiểm thử:** Cổng thanh toán tiền thật (Payout/Stripe/PayPal), ví tiền điện tử, rút tiền đa quốc gia.
- **Không kiểm thử:** Ứng dụng di động (Mobile App iOS/Android).
- **Không kiểm thử:** Kiểm thử tải nặng (Load/Stress Test hàng triệu CCU) — chỉ test cơ bản $\le 50$ requests đồng thời.
- **Không kiểm thử:** Kiểm thử bảo mật chuyên sâu (Penetration Testing) — chỉ kiểm tra cơ bản về RLS, Auth, Open Redirect.

---

## 3. Chiến lược & Công cụ kiểm thử (Test Approach & Tooling)

### 3.1. Ma trận phương pháp kiểm thử

```
┌────────────────────────────────────────────────────────┐
│               End-to-End (E2E) Testing                 │
│      Công cụ: Playwright (TypeScript)                  │
│      Phạm vi: Luồng Admin duyệt, Creator tải, Click    │
├────────────────────────────────────────────────────────┤
│             Integration & API Testing                  │
│      Công cụ: Playwright Test / Postman / Supertest    │
│      Phạm vi: Redirect endpoint, Import CSV, Auth/RLS  │
├────────────────────────────────────────────────────────┤
│                 Data & QC Testing                      │
│      Công cụ: CSV Fixtures, SQL Queries, Manual QC     │
│      Phạm vi: Golden Facts, Lỗi dòng CSV, Checklist QC │
└────────────────────────────────────────────────────────┘
```

1. **Tự động hóa E2E & API (Automation):**
   * **Framework:** **Playwright với TypeScript** (đồng bộ với stack Next.js/TypeScript của nhóm phát triển).
   * **Kịch bản tự động:**
     * API Test: Test kiểm tra chính sách RLS trên Supabase (Creator token không gọi được API của Creator khác).
     * API Test: Test endpoint Redirect ghi nhận click event và chuyển hướng an toàn.
     * E2E Test: Kịch bản login $\to$ xem thư viện $\to$ click link $\to$ nạp CSV $\to$ kiểm tra số dư Dashboard.
2. **Kiểm thử dữ liệu (Data & Fixture Testing):**
   * Đội Test (Duyên/Nhi) chuẩn bị sẵn 3 file CSV mẫu để nạp thử:
     * `fixture_clean.csv`: 10 đơn chuẩn, khớp mã click, doanh thu hợp lệ.
     * `fixture_dirty.csv`: Chứa dòng thiếu tiền tệ, sai định dạng ngày, order ID rỗng.
     * `fixture_duplicate.csv`: Chứa các dòng trùng lặp order ID để kiểm tra tính năng chặn nạp đúp (Idempotency).
3. **Kiểm soát chất lượng nội dung & Video (Manual QC):**
   * Áp dụng **Checklist QC Video v0 (T08)** cho mọi video demo:
     * Tỷ lệ khung hình: 9:16 dọc.
     * Thời lượng: 15–30 giây.
     * Âm thanh: Voice đọc to, rõ, không ngắt quãng.
     * Phụ đề: Đồng bộ đúng từng câu nói.
     * Fact-checking: Không chứa claim sai sự thật hoặc bịa đặt tính năng không có trong Golden Facts.

---

## 4. Quản lý môi trường & Dữ liệu kiểm thử (Test Environment & Data)

* **Môi trường (Environment):**
  * Localhost / Supabase Local (Docker) hoặc Supabase Dev Project do Tech Lead (Thông/Tài) cấp.
  * Các biến môi trường `.env.test` được quản lý riêng, không commit secrets lên GitHub.
* **Dữ liệu mồi (Seed Data):**
  * 01 Tài khoản Admin: `admin@demo.local` / `Demo@123456`
  * 02 Tài khoản Creator: `creator1@demo.local`, `creator2@demo.local` (phục vụ test phân quyền chéo)
  * 01 Sản phẩm mẫu chuẩn hóa (Golden Facts): **Gamma App** (`gamma.app`) hoặc sản phẩm được chốt tại `T10`.

---

## 5. Quy trình quản lý lỗi (Defect Triage & Severity)

Mọi lỗi phát hiện trong quá trình test được tạo issue trên board dự án theo mẫu chuẩn (`T09`):

| Mức độ nghiêm trọng (Severity) | Định nghĩa | Tiêu chí xử lý |
|---|---|---|
| **P0 - Blocker** | Không thể đăng nhập, lỗi server 500, Creator xem được dữ liệu của Creator khác, tính sai tiền hoa hồng, redirect hỏng | Phải sửa ngay lập tức, chặn release Sprint |
| **P1 - Critical** | Import CSV bị crash khi gặp dòng lỗi, video đã duyệt nhưng Creator không tải được, mất nút bấm quan trọng | Sửa trong vòng 24h |
| **P2 - Major** | Dashboard tính toán chậm, sai format tiền tệ ($ vs VNĐ), lỗi giao diện trên màn hình nhỏ | Sửa trong Sprint |
| **P3 - Minor** | Lỗi chính tả, màu sắc nút bấm chưa chuẩn UI, thông báo toast chưa mượt | Sửa khi có thời gian |

---

## 6. Tiêu chí bắt đầu & Tiêu chí nghiệm thu (Entry & Exit Criteria)

### 6.1. Tiêu chí bắt đầu kiểm thử (Entry Criteria cho Sprint 1)
- [x] Có bảng phân chia phạm vi MVP thống nhất (T05).
- [ ] Repo backend/frontend khởi tạo xong, có script seed dữ liệu mẫu chạy được (T13, T14).
- [ ] Nhóm AI/Video cung cấp ít nhất 01 kịch bản JSON và 01 video clip 9:16 demo (T22, T24).
- [ ] Có bộ fixture CSV chuẩn và Golden Facts (T12).

### 6.2. Tiêu chí nghiệm thu kiểm thử (Exit Criteria cho Demo MVP 9 tuần)
- [ ] **100% các Test Case P0** chạy thành công (Pass).
- [ ] **Không còn bất kỳ lỗi P0 (Blocker) hay P1 (Critical)** nào còn mở trước ngày diễn tập demo.
- [ ] Trình diễn thành công kịch bản End-to-End liên tục 8 bước trước toàn đội và giảng viên/khách hàng.
- [ ] Toàn bộ tài liệu kiểm thử, checklist, kịch bản test Playwright được lưu trữ đầy đủ trong thư mục `/docs` và `README` có hướng dẫn chạy rõ ràng.
