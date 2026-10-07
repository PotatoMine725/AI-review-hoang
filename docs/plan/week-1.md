# Kế hoạch tuần 1 — AI Review Content Factory

Oct 5, 2026 · @Hoang Nguyen

Tuần 1 (05–09/10/2026) không viết tính năng: cả team hiểu PRD, chốt phạm vi MVP, dựng repo + quy trình, và giảm rủi ro công nghệ bằng nghiên cứu + spike nhỏ. Thứ Sáu chốt backlog sprint 1.

## Mục tiêu tuần 1

Tuần 1 đạt khi có đủ 8 đầu ra dưới đây trước buổi review chiều thứ Sáu 09/10; mọi quyết định chốt bằng đồng thuận team và ghi vào Decision log.

- [ ] 10/10 thành viên đã đọc PRD; Q&A log không còn câu hỏi “blocking” chưa trả lời
- [ ] Tài liệu phạm vi MVP (MoSCoW + danh sách cắt) được team đồng thuận
- [ ] Repo, board, quy ước Git, CI tối thiểu hoạt động
- [ ] 4 ADR đã chốt: crawl, LLM provider, render engine, avatar + TTS provider
- [ ] Sơ đồ kiến trúc tổng thể + ERD v0
- [ ] Wireframe low-fi cho các màn ưu tiên của Merchant, Creator, Admin
- [ ] Golden set: 10 AI product đã chọn, 5 product có đáp án nhập tay
- [ ] Backlog sprint 1 có user story + acceptance criteria + ước lượng

## Lịch họp chung

4 loại họp, tổng khoảng 5 giờ/người trong tuần; BA điều phối và ghi biên bản. Giờ là đề xuất, team chỉnh trong buổi kickoff.

| Buổi | Thời gian | Thời lượng | Nội dung | Đầu ra |
| --- | --- | --- | --- | --- |
| Kickoff | T2 05/10, 9:00 | 90 phút | Đi qua PRD theo 5 engine, giới thiệu vai trò, xác nhận bảng phân công này | Q&A log ban đầu, bảng phân công đã xác nhận |
| Daily standup | T3–T6, 9:00 | 15 phút | Hôm qua làm gì, hôm nay làm gì, đang bị chặn gì | Cập nhật cột Trạng thái |
| Sync kỹ thuật | T4 07/10, 15:00 | 60 phút | Dev trình bày kết quả nghiên cứu, thống nhất kiến trúc và hợp đồng dữ liệu giữa module | ADR nháp, danh sách điểm cần chốt |
| Review + retro + planning | T6 09/10, 14:00 | 120 phút | Duyệt 8 đầu ra tuần 1, retro, ước lượng và chốt sprint 1 | Decision log, backlog sprint 1 |

## Bảng phân công

34 nhiệm vụ cho 10 người; code chỉ xuất hiện ở spike/hello-world (≤ 1 ngày mỗi người) và khung repo. Mọi tài liệu đầu ra nằm trong `/docs` của repo hoặc link từ board.

| Thành viên | Vai trò | Nhiệm vụ | Hạn | Đầu ra yêu cầu | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| Cả team | — | Đọc PRD trước kickoff, ghi câu hỏi vào Q&A log | Oct 5, 2026 | Mỗi người ≥ 3 câu hỏi trong Q&A log | Chưa bắt đầu |
| Cả team | — | Review 8 đầu ra, retro, planning sprint 1 | Oct 9, 2026 | Decision log cập nhật, backlog sprint 1 đã ước lượng | Chưa bắt đầu |
| BA | BA + điều phối | Lập board (GitHub Projects), Q&A log, Decision log; tổ chức kickoff | Oct 5, 2026 | Board có cột Todo/Doing/Review/Done; 2 file log trong `/docs` | Chưa bắt đầu |
| BA | BA + điều phối | Glossary, 3 persona (Merchant, Creator, Admin), user journey end-to-end | Oct 6, 2026 | Doc ≤ 5 trang + 1 sơ đồ journey | Chưa bắt đầu |
| BA | BA + điều phối | Phạm vi MVP: MoSCoW toàn bộ tính năng PRD §50–51 + danh sách cắt | Oct 7, 2026 | Doc scope, trình bày tại sync kỹ thuật | Chưa bắt đầu |
| BA | BA + điều phối | Epic, user story, acceptance criteria cho sprint 1 | Oct 9, 2026 | ≥ 25 story trên board, mỗi story có AC | Chưa bắt đầu |
| QA-1 | Tester (quy trình) | Test strategy: unit, API, E2E, kiểm định video | Oct 6, 2026 | Doc 1–2 trang | Chưa bắt đầu |
| QA-1 | Tester (quy trình) | Checklist QC video v0: 1080×1920, ≤ 60 giây, safe zone, lip-sync, giá/tính năng đúng, nhãn AI, forbidden claims | Oct 7, 2026 | Checklist dùng được cho Module 4 | Chưa bắt đầu |
| QA-1 | Tester (quy trình) | Template test case, bug report, quy trình triage, Definition of Done cho task | Oct 8, 2026 | Template trên board + mục DoD trong CONTRIBUTING | Chưa bắt đầu |
| QA-2 | Tester (dữ liệu) | Chọn 10 AI product cho golden set, chia 3 nhóm (video, productivity, coding), có affiliate program công khai | Oct 6, 2026 | Sheet: tên, URL, link affiliate program, nhóm | Chưa bắt đầu |
| QA-2 | Tester (dữ liệu) | Thu thập 20 video review AI tool trên TikTok/Shorts, phân loại hook, format, độ dài, CTA | Oct 7, 2026 | Sheet reference library | Chưa bắt đầu |
| QA-2 | Tester (dữ liệu) | Nhập tay đáp án (gói, giá, tính năng chính) cho 5 product đầu | Oct 9, 2026 | Sheet golden set v0 | Chưa bắt đầu |
| BE | Backend + tech lead | GitHub org + monorepo (`apps/web`, `services/worker`, `docs`), branch protection, PR template, CODEOWNERS | Oct 5, 2026 | Repo + README | Chưa bắt đầu |
| BE | Backend + tech lead | CONTRIBUTING.md (Git flow, quy ước branch/commit, review); Supabase project dev + `.env.example` | Oct 6, 2026 | Doc + project Supabase dev, mọi dev truy cập được | Chưa bắt đầu |
| BE | Backend + tech lead | Kiến trúc tổng thể (C4 mức 1–2) + ERD v0 từ PRD §61 | Oct 7, 2026 | Sơ đồ + ERD trình bày tại sync kỹ thuật | Chưa bắt đầu |
| BE | Backend + tech lead | CI tối thiểu: lint + type check khi mở PR | Oct 8, 2026 | GitHub Actions chạy xanh trên PR mẫu | Chưa bắt đầu |
| AI-1 (Hoàng) | AI dev (Module 1) | Review đặc tả Module 1 cùng team, thu góp ý | Oct 6, 2026 | Đặc tả Module 1 v0.2 | Chưa bắt đầu |
| AI-1 (Hoàng) | AI dev (Module 1) | Spike notebook: crawl 2 product → markdown → Gemini trích xuất JSON | Oct 8, 2026 | Notebook + 2 JSON mẫu + ghi chú chất lượng, token, chi phí | Chưa bắt đầu |
| AI-1 (Hoàng) | AI dev (Module 1) | ADR-001 crawl tool, ADR-002 LLM provider | Oct 9, 2026 | 2 ADR trong `/docs/adr` | Chưa bắt đầu |
| AI-2 | AI dev (Module 2, 4) | Phân tích PRD §10–14 (content matrix, hook, script) dựa trên sheet tham khảo của QA-2 | Oct 7, 2026 | Danh sách content angle + loại hook đã chuẩn hóa | Chưa bắt đầu |
| AI-2 | AI dev (Module 2, 4) | JSON schema script (danh sách scene: thời điểm, lời thoại, screenshot, caption) làm hợp đồng M2 → M3 | Oct 8, 2026 | Schema v0 đã thống nhất với Video-1 | Chưa bắt đầu |
| AI-2 | AI dev (Module 2, 4) | Prompt template v0 cho hook + script, thử tay trên 1 product | Oct 9, 2026 | File prompt + 5 hook và 1 script mẫu | Chưa bắt đầu |
| Video-1 | Video dev (render) | So sánh HyperFrames, Revideo, FFmpeg/MoviePy: license, tính năng, độ khó | Oct 6, 2026 | Bảng so sánh | Chưa bắt đầu |
| Video-1 | Video dev (render) | Hello-world: render 1 clip 9:16 dài 15 giây gồm screenshot + caption + audio | Oct 8, 2026 | 1 file MP4 + ghi chú thời gian render | Chưa bắt đầu |
| Video-1 | Video dev (render) | Spec layout 9:16 (vùng screenshot, avatar, caption, safe zone) cùng FE-2; ADR-003 render engine | Oct 9, 2026 | Spec layout + ADR-003 | Chưa bắt đầu |
| Video-2 | Video dev (avatar, TTS) | So sánh avatar/lip-sync: HeyGen API, fal (LatentSync, Kling Avatar), MuseTalk self-host | Oct 6, 2026 | Bảng chất lượng, giá/phút, thời gian xử lý | Chưa bắt đầu |
| Video-2 | Video dev (avatar, TTS) | Thử tạo 2 clip avatar 10 giây trên provider rẻ nhất, ngân sách ≤ $5 | Oct 8, 2026 | 2 clip + đánh giá | Chưa bắt đầu |
| Video-2 | Video dev (avatar, TTS) | So sánh TTS (Google Chirp 3 HD, ElevenLabs, Kokoro) trên cùng 1 script; ADR-004 avatar + TTS | Oct 9, 2026 | 3 file audio + ADR-004 | Chưa bắt đầu |
| FE-1 | Frontend (Merchant, Admin) | Liệt kê màn hình + user flow Merchant/Creator/Admin từ PRD §30–32, §62 | Oct 6, 2026 | Screen inventory + flow | Chưa bắt đầu |
| FE-1 | Frontend (Merchant, Admin) | Wireframe low-fi (Figma): onboarding product, review PKB, AI Factory dashboard, content library, admin overview | Oct 8, 2026 | Link Figma 5 màn | Chưa bắt đầu |
| FE-1 | Frontend (Merchant, Admin) | Scaffold Next.js + Tailwind + shadcn/ui trong repo, chưa có tính năng | Oct 9, 2026 | App chạy local + preview deploy | Chưa bắt đầu |
| FE-2 | Frontend (Creator, design) | Design foundation: màu, typography, danh sách component shadcn sử dụng | Oct 6, 2026 | Trang Figma style guide | Chưa bắt đầu |
| FE-2 | Frontend (Creator, design) | Wireframe phía Creator: dashboard, campaign, tải video, affiliate link, earnings | Oct 8, 2026 | Link Figma | Chưa bắt đầu |
| FE-2 | Frontend (Creator, design) | Mockup layout video 9:16 cùng Video-1 | Oct 9, 2026 | Frame Figma 1080×1920 | Chưa bắt đầu |

## Quy ước làm việc mặc định

Áp dụng ngay từ kickoff để không mất thời gian tranh luận; team sửa tại retro thứ Sáu nếu không hợp.

| Hạng mục | Quy ước |
| --- | --- |
| Ra quyết định | Người phụ trách đề xuất → thảo luận ≤ 1 ngày → đồng thuận hoặc người phụ trách module đề xuất + team lead @VV6505 duyệt cuối về kỹ thuật, BA quyết về nghiệp vụ; ghi Decision log (cập nhật 07/10, decision-log #12) |
| Tài liệu kỹ thuật | ADR ngắn (bối cảnh, lựa chọn, quyết định, hệ quả) trong `/docs/adr`, đánh số tuần tự |
| Board | GitHub Projects; mỗi nhiệm vụ trong bảng trên là 1 card, có người phụ trách và hạn |
| Git | Trunk-based: nhánh `feat/<module>-<mô-tả>`, `fix/…`, `docs/…`; PR cần ≥ 1 review; squash merge vào `main` |
| Commit | Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`) |
| Definition of Done | Đã review, CI xanh, có test hoặc ghi chú vì sao không, tài liệu liên quan đã cập nhật |
| Giao tiếp | 1 kênh chung + 1 kênh theo nhóm (AI, Video, Web, QA); câu hỏi nghiệp vụ vào Q&A log, không để trôi trong chat |
| Bị chặn | Báo ở standup hoặc kênh chung trong vòng 2 giờ, đổi trạng thái card thành “Bị chặn” |
| Chi phí API | Mọi API key qua `.env`, không commit; spike tuần 1 tổng ngân sách ≤ $20, ghi lại số tiền đã dùng |
