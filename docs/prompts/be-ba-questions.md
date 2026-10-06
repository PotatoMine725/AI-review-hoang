# Prompt: chuyển câu hỏi nghiệp vụ M1 thành issue cho BA

- **Repo / cwd:** `AI-review-BE`
- **Issue:** chưa có (prompt này tạo issue) · **Branch:** `docs/qa-log-ba-issues` (tạo từ `dev`)
- **BA:** @khanhphi27 (đã là collaborator của repo BE)

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là @PotatoMine725 (AI-1, người setup repo).

## Bối cảnh
Các câu hỏi nghiệp vụ của Module 1 đang nằm trong `docs/logs/qa-log.md`, chưa ai được báo. Quy ước dự án: việc liên quan thành viên khác được nhắc qua issue.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md`, `docs/README.md`
- `docs/logs/qa-log.md` (#1–#8), `docs/specs/m1-product-intelligence.md`, `docs/specs/m1-spike-crawl-extract.md`
- Issue hiện có: `gh issue list -R PotatoMine725/AI-review-BE` và `gh issue view 5 -R PotatoMine725/AI-review-BE --comments`

## Nhiệm vụ
1. **Tạo 2 issue** ở repo BE, label `question`, assignee `khanhphi27`, dùng template `.github/ISSUE_TEMPLATE/task.md`:
   - **Issue 1 (chặn việc):** `question(m1): ai làm sub-module 1.4–1.6?` — qa-log #4. Hạn trả lời: trước buổi sync kỹ thuật **T4 07/10 15:00**. Ghi rõ: đặc tả M1 giao "AI dev 2", kế hoạch tuần 1 giao AI-2 làm M2/M4; trong spike #6, AI-1 đang tạm làm. Nêu lựa chọn: (a) AI-1 làm hết M1; (b) AI-2 làm 1.4–1.6; (c) khác. Ghi issue bị chặn: #5.
   - **Issue 2:** `question(m1): câu hỏi nghiệp vụ Module 1 (approve PKB, tài liệu sau login, ngôn ngữ)` — gồm qa-log #1, #2, #3 + #8 dạng checklist, mỗi mục 1–2 câu bối cảnh và ảnh hưởng. #3 và #8 gộp thành 1 mục "ngôn ngữ" (site merchant + video/PKB). Hạn trả lời: buổi review **T6 09/10 14:00**.
   - Mỗi issue có mục "Cách trả lời": BA trả lời bằng comment trên issue; @PotatoMine725 cập nhật qa-log rồi đóng issue.
2. **Cập nhật `docs/logs/qa-log.md`:**
   - Cột "Liên quan": thêm link issue mới cho #1, #2, #3, #4, #8.
   - Cột "Người trả lời": `@khanhphi27` cho #1–#4; `@khanhphi27 + tech lead` cho #8.
   - Không sửa nội dung câu hỏi, không tự điền câu trả lời.
3. **Sửa issue cũ nếu cần:** issue #5, mục AC về "AI dev 2" và "Ngôn ngữ", thêm link sang issue mới. Chỉ sửa body/thêm comment; không đổi tiêu đề, assignee, phạm vi của #5–#8.

## Phạm vi
- Không làm: trả lời câu hỏi thay BA; sửa CODEOWNERS; tạo board/milestone; sửa issue ngoài #5; tạo issue cho người khác ngoài BA.

## Ràng buộc
- **Trình bày trước** tiêu đề + body đầy đủ của 2 issue và diff dự kiến của qa-log, chờ người dùng duyệt rồi mới tạo issue / sửa file.
- Tạo issue bằng `gh issue create -R PotatoMine725/AI-review-BE`; nếu không gán được assignee thì báo lại, không bỏ qua.
- Không dùng `git reset --hard`, force push.

## Khi xong
- Commit qa-log theo Conventional Commits (`docs(qa): …`), mở PR vào `dev`, body ghi `Refs` tới 2 issue mới (không `Closes`).
- Trả về: link 2 issue, link PR, danh sách thay đổi ở issue #5, lệnh để tự kiểm tra.
