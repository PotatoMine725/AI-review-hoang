# AI-review-FE

Web app của **AI Review Content Factory & Affiliate Network**: màn hình cho Merchant, Creator và Admin.

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
cp .env.example .env.local    # điền giá trị (Supabase local: chạy "pnpm dlx supabase status" trong AI-review-BE)
pnpm dev                      # http://localhost:3000
```

Lint và type check giống CI:
```bash
pnpm lint
pnpm exec next typegen && pnpm exec tsc --noEmit
pnpm test
```

## Màn hình Merchant / Admin (demo local ngày 08/10)

Trang `/` mở Dashboard Merchant. Menu riêng theo khu vực; nút **Chuyển sang Admin/Merchant** dùng để thử vai trò, không phải đăng nhập hoặc phân quyền thật.

| Màn theo issue BE #38 | Route | Thao tác demo |
| --- | --- | --- |
| Dashboard Merchant | `/merchant` | Thống kê từ dữ liệu local, PKB cần xử lý, nội dung gần đây |
| Onboarding | `/merchant/onboarding` | Nhập Website + affiliate URL, tạo product/job rồi mở review |
| Review PKB | `/merchant/products/:id` | Sửa draft, nguồn/evidence, gửi review, Merchant approve, lịch sử phiên bản |
| Content Library | `/merchant/library` và `/:id` | Lọc trạng thái, xem video/transcript, tải video + caption khi đã duyệt, báo sai |
| Admin QA Video | `/admin/videos` và `/:id` | Hàng đợi và báo sai, 4 mục QA, approve hoặc reject với lý do |

Admin có `/admin` và `/admin/pkb`: kiểm tra và reject PKB `in_review`, không có thao tác approve PKB. Merchant không có thao tác approve/reject video. `/merchant/content` giữ trình biên tập template từ PKB đã duyệt; `/merchant/products` là danh sách sản phẩm, onboarding đã tách riêng.

Trạng thái video demo lưu ở `reviewlab.video-qa.mock.v1` trong localStorage; trạng thái M1 cũ được giữ ở `reviewlab.m1.mock.v2`. Báo sai làm video xuất hiện lại trong hàng đợi Admin. Chỉ approve khi PKB nguồn đã approved và đủ 4 mục QA; reject bản pending_review cần lý do. Video đã approved chỉ giữ duyệt hoặc chuyển archived; firstApprovedAt và metadata duyệt ban đầu được giữ, archived không duyệt lại được. Storage video dùng schema 2 trên key hiện có; bản schema 1 được chuyển đổi khi đọc, metadata bổ sung chỉ là dữ liệu demo. Reload giữ quyết định; lỗi lưu không báo thành công. Video là clip workspace không âm thanh, không phải video sản phẩm 9:16 hoặc kết quả AI thật. Đây là 5 màn prototype để review, chưa xác nhận tích hợp backend hoặc nghiệm thu Figma.

Kiểm tra các màn mới: `node tests/roles.browser.cjs` với `PLAYWRIGHT_MODULE`, `CHROME_PATH`, `TEST_BASE_URL`, `TEST_OUTPUT_DIR` như các test trình duyệt bên dưới. Test bao gồm quyền thao tác theo màn, PKB chặn duyệt video, tải file, báo sai → giữ duyệt/lưu trữ, lỗi lưu và responsive 390/320 px. Các route cũ `/products`, `/content`, `/reviews`, `/review/:id` được giữ để không làm mất luồng demo trước đó.

## Các luồng FE Sprint 1 trước đó

- Header/sidebar responsive và Footer dùng chung cho mọi trang.
- `/reviews`: ReviewCard, tìm kiếm qua `/search` với debounce 300 ms, loading, trạng thái trống, lỗi và thử lại.
- `/review/:id`: video HTML5, transcript đồng bộ khi phát/tua, chọn đoạn để tua và tải lại video khi lỗi.
- ErrorBoundary, route error và global error có giao diện phục hồi.
- Các trang `/`, `/products`, `/content` giữ luồng quản lý sản phẩm và biên tập content hiện có.

## Mock M1 theo tài liệu ngày 07/10

`/products` → `/products/:id`: nhập Website URL + Merchant affiliate URL, điều khiển job crawl mock (`queued/running/completed/failed`), review PKB tiếng Anh có nguồn/evidence mẫu, lưu draft, gửi review và merchant duyệt. Bản approved chỉ đọc; sửa tạo draft vN+1 và giữ lịch sử. Admin demo chỉ có thao tác reject, không approve. Đây là mô phỏng vai trò, không phải authentication/authorization thật.

Website URL được chuẩn hóa scheme/www/dấu slash cuối; đường dẫn và query được giữ, không chặn toàn domain. Chính sách canonicalization production chờ hợp đồng BE. Không tự chuyển job sang hoàn tất bằng timer.

Workspace mock lưu trong localStorage (`reviewlab.m1.mock.v2`): product, job, PKB versions, vai trò và content được khôi phục sau reload. Lưu lỗi giữ nội dung đang sửa; cảnh báo khi refresh/đóng trang, bấm link hoặc Back/Forward rời editor chưa lưu. Hủy Back/Forward giữ nội dung đang sửa và phục hồi entry hiện tại, không thêm entry lịch sử giả. Draft/content chỉ được lưu khi bấm nút tương ứng. Đây là lưu local theo trình duyệt, không phải Supabase hoặc đồng bộ server.

`/content` tạo template tiếng Anh từ snapshot PKB đã duyệt, ghi version nguồn; tạo draft PKB mới không xóa content và phiên bản đã duyệt cũ. `/reviews` dùng tiêu đề/transcript mẫu tiếng Anh. Gamma là sản phẩm demo ưu tiên; giá và evidence đều mang nhãn minh họa.

Kiểm tra luồng M1 bằng `node tests/m1.browser.cjs` với cùng các biến môi trường Playwright phía trên. Báo cáo: [BE/docs/report/fe-m1-mock-2026-10-07.md](../AI-review-BE/docs/report/fe-m1-mock-2026-10-07.md).

Mặc định chạy bằng dữ liệu mẫu và video local tự tạo trong `public/media/`; điểm/transcript chưa phải kết quả AI. Khi BE cung cấp hợp đồng review/search, đặt `REVIEW_API_BASE_URL` (server-only) và restart server. Worker hiện tại chỉ có `/health`, nên chưa thể kiểm thử tích hợp BE thật.

Đặc tả adapter, checklist nghiệm thu và kết quả kiểm tra nằm ở [BE/docs/specs/fe-sprint1-review.md](../AI-review-BE/docs/specs/fe-sprint1-review.md).

`pnpm test` chạy test dữ liệu/tìm kiếm/transcript bằng Node.js 24, không thêm thư viện. Sau `pnpm build`, chạy `node tests/reviews-proxy.integration.cjs` để kiểm tra adapter với BE giả lập. Kiểm tra giao diện: khởi động ứng dụng, cung cấp Playwright qua `PLAYWRIGHT_MODULE` (hoặc cài sẵn trong môi trường kiểm thử), rồi chạy `node tests/sprint1.browser.cjs`. Có thể đặt `CHROME_PATH`, `TEST_BASE_URL`, `TEST_OUTPUT_DIR` để chọn trình duyệt, server và nơi lưu ảnh.

`node tests/unsaved.browser.cjs` kiểm tra Back/Forward với PKB và content, hủy nhiều lần, xác nhận rời trang và điều hướng sau khi lưu. Dùng cùng các biến môi trường Playwright.

`node tests/error-boundary.browser.cjs` dùng cùng môi trường Playwright để kiểm tra lỗi render React thật và phục hồi bằng nút Thử lại.

## Tài liệu
- [CONTRIBUTING.md](CONTRIBUTING.md): Git flow, commit, PR, Definition of Done
- [AI-review-BE/docs](https://github.com/PotatoMine725/AI-review-BE/tree/main/docs): PRD, kế hoạch, đặc tả module, API contract
