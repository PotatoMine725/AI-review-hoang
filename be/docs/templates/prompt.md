# Prompt: <tiêu đề issue>

- **Repo / cwd:** `AI-review-BE` | `AI-review-FE`
- **Issue:** PotatoMine725/AI-review-XX#N · **Branch:** `feat/<module>-<mô-tả>` (tạo từ `dev`)
- **Spec / plan:** `docs/specs/...`, `docs/plan/...`

---

Bạn là coding agent của repo này. Làm việc bằng tiếng Việt.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md` của repo.
- <file spec/plan/ADR liên quan>

## Nhiệm vụ
<mô tả ngắn, 1 issue>

## Phạm vi
- Làm: 
- Không làm: 

## Acceptance criteria
- [ ] 

## Ràng buộc
- Không thêm thư viện ngoài stack khi chưa hỏi. Không dùng Remotion.
- Không commit secret. Biến mới thêm vào `.env.example` (giá trị rỗng).
- Không dùng lệnh phá huỷ lịch sử (`git reset --hard`, force push).
- Trình bày danh sách file sẽ tạo/sửa trước khi làm.

## Khi xong
- Chạy lint/type check như CI. Mở PR vào `dev`, tiêu đề theo Conventional Commits, có `Closes #N`.
- Viết `docs/report/<slug>.md` nếu issue yêu cầu.
- Trả về: link PR, danh sách file đổi, lệnh để tự kiểm tra.
