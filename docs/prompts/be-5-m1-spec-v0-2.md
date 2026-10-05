# Prompt: docs(m1): đặc tả Module 1 v0.2

- **Repo / cwd:** `AI-review-BE`
- **Issue:** PotatoMine725/AI-review-BE#5 · **Branch:** `docs/m1-spec-v0-2` (tạo từ `dev`)
- **Spec:** `docs/specs/m1-product-intelligence.md`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md`, `docs/README.md`
- `docs/specs/m1-product-intelligence.md`, `docs/logs/qa-log.md` (#4–#7), `docs/logs/decision-log.md` (#8, #9)

## Nhiệm vụ
Sửa đặc tả M1 lên v0.2 theo AC của issue #5. Chỉ sửa tài liệu.

## Phạm vi
- Làm: sửa đúng các mục trong AC; thêm mục "Lịch sử phiên bản" ở cuối file.
- Không làm: đổi kiến trúc, đổi requirement khác, tự trả lời câu hỏi trong qa-log.

## Acceptance criteria
Theo issue #5. Giá model phải tra lại trên trang giá chính thức của Gemini API tại thời điểm làm, ghi ngày tra cứu và link nguồn.
Câu hỏi nào trong qa-log chưa có câu trả lời thì ghi "chờ qa-log #N", không tự quyết.

## Ràng buộc
- Trình bày diff dự kiến (từng mục) trước khi sửa.
- Không dùng `git reset --hard`, force push.

## Khi xong
- Mở PR vào `dev`, tiêu đề `docs(m1): đặc tả Module 1 v0.2`, có `Closes #5`.
- Trả về: link PR, tóm tắt thay đổi theo từng AC.
