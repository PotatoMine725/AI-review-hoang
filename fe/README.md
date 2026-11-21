# AI-review-FE

Web app của **AI Review Content Factory & Affiliate Network**: giao diện mock Creator tạo video và Admin quản lý người dùng, token, gói đăng ký, PKB.

Backend, schema DB và tài liệu (PRD, ADR, log) nằm ở [AI-review-BE](https://github.com/PotatoMine725/AI-review-BE).

## Stack
Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui, pnpm.

## Cấu trúc

```
AI-review-FE/
├── src/
│   ├── app/             # App Router: layout.tsx, page.tsx, globals.css
│   ├── components/ui/   # component shadcn/ui (thêm bằng: pnpm dlx shadcn@latest add <tên>)
│   ├── features/        # (khi có) code theo tính năng: features/<module>/
│   └── lib/
│       ├── utils.ts
│       ├── api/         # (khi có) MỌI lời gọi HTTP tới worker/service đi qua đây
│       └── supabase/    # (khi có) client Supabase server + browser
├── components.json      # cấu hình shadcn/ui
├── .env.example
└── .github/             # CI (ci.yml), PR/issue template, CODEOWNERS
```

## Chạy local

Yêu cầu: Node.js 24, pnpm (phiên bản trong `packageManager` của `package.json`).

```bash
pnpm install
cp .env.example .env.local    # tùy chọn khi cấu hình kết nối; giao diện mock không cần backend
pnpm dev                      # http://localhost:3000
```

## Mô tả giao diện

Trang `/` dùng minh họa Creative bằng chữ trắng/bạc, nút phát và dải phim trên nền trong suốt để giới thiệu sáng tạo video sản phẩm cùng AI. Có thể đổi phong cách, khung hình và phát/tạm dừng chuyển động minh họa. Navigation trong suốt trên hero, có menu Cài đặt thả xuống để chuyển Việt/Anh và sáng/tối, cùng menu điều hướng di động. Các trang `/price` (gói minh họa và câu hỏi thường gặp), `/about` (giới thiệu Reviewlab) và `/credits` dùng chung header/footer với landing. Đăng nhập, đăng ký là các trang riêng không có navigation/footer, dùng cùng bảng màu xám/trắng của workspace, minh họa 3D nhân vật tương tác với video AI và các chi tiết bong bóng/ngôi sao nhẹ. Liên kết Crawl4AI nằm trong footer. Các trang này xem được khi chưa đăng nhập. Hình minh họa không gọi AI hoặc tạo video; navigation giữ đủ Home / Create / Price / About (có bản dịch Việt/Anh), bảng giá vẫn là dữ liệu mẫu, chưa có thanh toán.

Đăng nhập tại `/login`, đăng ký tại `/signup`. Đây là **mock phía trình duyệt**, chưa có xác thực server hoặc kết nối BE. Dùng mật khẩu mẫu, không nhập mật khẩu đang dùng ở dịch vụ khác.

- Creator: `creator`
- Admin: `admin`
- Mật khẩu chung: `123456`

Đăng nhập bằng tên tài khoản mẫu hoặc email đã đăng ký. Tài khoản mẫu đã lưu trên trình duyệt được cập nhật mật khẩu, giữ nguyên dữ liệu dự án.

Tài khoản đăng ký được lưu trên trình duyệt; mỗi tài khoản mới có dữ liệu dự án và tệp tham khảo riêng. Đăng xuất trong phần Cài đặt tài khoản. Hai tài khoản mẫu dùng chung workspace demo hiện có.

Trong màn tạo video, nhập link rồi mở **Chi tiết** để xem tiến trình mô phỏng thu thập nguồn → chuẩn hóa thông tin → review sản phẩm. Kiểm tra/sửa thông tin và xác nhận trước khi tạo video mẫu. Đóng hộp thoại sẽ hủy tiến trình đang chạy; tiến trình không truy cập website hoặc gọi AI.

Kiểm tra: `corepack pnpm test`, `corepack pnpm lint`, `corepack pnpm exec tsc --noEmit`. Khi dev server đang chạy, dùng `node tests/landing.browser.cjs` để kiểm tra landing, navigation, Việt/Anh, giao diện và đăng nhập; `node tests/auth-product.browser.cjs` và `node tests/studio.browser.cjs` kiểm tra các luồng mock. Có thể đặt `TEST_BASE_URL` khi server dùng host/cổng khác.

[Mô tả giao diện mock Creator và Admin](https://github.com/PotatoMine725/AI-review-BE/blob/dev/docs/specs/web-creator-admin-mock.md) nằm ở repo BE.

## Tài liệu

- [CONTRIBUTING.md](CONTRIBUTING.md): Git flow, commit, PR, Definition of Done
- [AI-review-BE/docs](https://github.com/PotatoMine725/AI-review-BE/tree/dev/docs): PRD, API contract và tài liệu backend
