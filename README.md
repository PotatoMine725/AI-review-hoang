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

## Năm màn mock theo yêu cầu leader (08/10)

Trang `/` mở Dashboard Merchant. Menu chuyển Merchant / Admin / Creator chỉ mô phỏng vai trò; chưa có authentication hoặc authorization thật.

| Màn | Route | Thao tác mock đã có |
| --- | --- | --- |
| Onboarding | `/merchant/onboarding` | URL + affiliate bắt buộc, optional name/tagline/pricing/features/claims/logo/color, Save Draft, upload PDF/ảnh, processing 3 bước và WAF fallback |
| Review PKB | `/merchant/products/:id` | 4 tab, bảng giá/giới hạn, feature cards, origin badge, evidence popover ≤200 ký tự, conflict radios, inline edit, history/diff, recrawl, submit/approve khóa version |
| Dashboard | `/merchant` | 4 metrics, crawl/extract/render monitor, progress mock, lỗi/retry và product table với PKB/video/campaign actions |
| Content Library | `/merchant/library`, `/creator/library` và `/:id` | Product/Angle/loại Hook/status filters, card 9:16, preview modal/player + scene/voiceover/screenshot, report modal; MP4/caption/hashtags/clipboard/tracking cho Creator |
| Admin QA | `/admin/videos` và `/:id` | Queue table/split view, Safe Zone toggle, 6 checklist items, PKB snapshot, approve/reject có lý do, dismiss report hoặc archive |

`/merchant/content` tạo template và job video từ PKB approved. Render được điều khiển thủ công ở Dashboard, giữ version PKB nguồn rồi đưa vào QA; chưa gọi AI hoặc worker. `/merchant/campaigns` mở/đóng campaign mock; `/creator/campaigns` tham gia với 1 Creator demo. Views/clicks hiện 0 vì chưa có tracking thật. Link mẫu có dạng `/r/<slug>`; backend phải tạo `click_id` cho từng click, không nhúng một `click_id` cố định vào link chia sẻ.

Website trùng được kiểm tra theo normalized URL, vẫn cho phép các sản phẩm khác path trên cùng domain theo M1/ERD. Xung đột ưu tiên Merchant nhưng cần xác nhận; giá Merchant dạng text cần nhập lại số tiền ở PKB trước khi gửi duyệt. Không tự quy đổi giá hoặc giả định giá sản phẩm thực tế.

Trạng thái DB video giữ `pending_review / approved / rejected / archived`. Processing/Ready được suy ra từ render, Flagged là cờ báo sai. Approved chỉ giữ duyệt hoặc archive; metadata duyệt đầu tiên, caption và snapshot nguồn được giữ nguyên. Archived là trạng thái kết thúc. Chỉ approve khi render hoàn tất, media 1080×1920 / 15–60s, PKB nguồn approved và đủ checklist.

Dữ liệu mock lưu trong localStorage (`reviewlab.m1.mock.v2`, `reviewlab.video-qa.mock.v1`); PDF/ảnh gốc lưu bằng IndexedDB (`reviewlab.uploads`). Reload khôi phục drafts/jobs/decisions. Lỗi lưu giữ nội dung đang nhập; cảnh báo rời trang khi có chỉnh sửa chưa lưu. Cache video cũ được migrate checklist/media mẫu, không xóa thư viện hoặc quyết định đã lưu.

`public/media/leader-demo.mp4` là video workspace tự tạo, 1080×1920, 15 giây, có giọng TTS hệ thống và không nhạc nền. Tất cả sản phẩm dùng clip mẫu này; chưa phải footage/render riêng theo sản phẩm. Screenshot, PKB, giá, progress và Safe Zone phục vụ review mock. Các route cũ `/products`, `/content`, `/reviews`, `/review/:id` vẫn giữ luồng demo trước đó.

Kiểm tra thêm qua `node tests/leader.browser.cjs` và `node tests/roles.browser.cjs`. Đặt `PLAYWRIGHT_MODULE`, `CHROME_PATH`, `TEST_BASE_URL`, `TEST_OUTPUT_DIR` theo phần test bên dưới. Test bao gồm WAF/upload bytes, conflict/price guards, version locks, render retry, kích thước MP4 thực, Creator clipboard/tracking/download, report lifecycle và responsive 320/390px.

Đây là triển khai UI/mock local; chưa thay thế việc bàn giao 5 frame Figma và link nghiệm thu Issue BE #38.

Rà soát bổ sung ngày 08/10: stepper đánh dấu bước Review PKB; PKB approved có badge và conflict chỉ đọc dạng text. Bộ lọc Hook dùng Curiosity/Pain/Challenge, Angle dùng Problem/Comparison/Tutorial/Demo; cache cũ vẫn được giữ. Đổi currency trong draft cập nhật currency từng gói và nguồn thành Merchant, không quy đổi số tiền hoặc sửa snapshot đã lưu. Dashboard dùng logo sản phẩm và chỉ đếm video đã render, đã duyệt ở cột sẵn sàng. Caption phân phối bổ sung hashtags mẫu khi thiếu, giữ nguyên caption gốc đã duyệt.

Kiểm chứng lần rà soát: 18 unit test, lint, TypeScript và production build đạt; chạy lại `leader.browser.cjs` và `roles.browser.cjs` trên production build, gồm luồng đầy đủ và responsive 1440/390/320px. Kết quả đủ cho review phần UI/mock của 5 màn; chưa phải nghiệm thu Figma hoặc tích hợp backend.

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
