# Tài liệu — AI Review Content Factory

Nguồn sự thật cho cả 2 repo (BE và FE). Repo FE không giữ bản sao, chỉ trỏ về đây.
Tổ chức theo **Spec-driven development**: viết spec → lập plan → làm → report → review.

## Thư mục

| Thư mục | Trả lời câu hỏi | Nội dung | Ai viết |
|---|---|---|---|
| [`specs/`](specs/) | Làm gì? | PRD, đặc tả module, API contract. Có acceptance criteria | Người phụ trách module, BA duyệt |
| [`plan/`](plan/) | Làm thế nào? | Kế hoạch tuần/sprint, cách chia task cho 1 spec | Người phụ trách |
| [`adr/`](adr/) | Vì sao chọn vậy? | Quyết định kỹ thuật lớn, đánh số tuần tự | Người phụ trách module đề xuất, team lead duyệt |
| [`report/`](report/) | Đã làm gì? | Kết quả 1 task/sprint: thay đổi, số liệu, lệch so với plan | Người làm |
| [`review/`](review/) | Đạt chưa? | Nghiệm thu: đối chiếu từng acceptance criteria trong spec | Tester / người review |
| [`snapshot/`](snapshot/) | Hôm nay thế nào? | Bản ghi cuối ngày, viết câu ngắn (xem mẫu) | @PotatoMine725 |
| [`prompts/`](prompts/) | Giao cho agent cái gì? | Prompt giao việc cho coding agent (Claude Code) | Coordinator |
| [`logs/`](logs/) | — | `decision-log.md` (quyết định), `qa-log.md` (câu hỏi mở) | Mọi người |
| [`references/`](references/) | — | Tài liệu tham khảo bên ngoài. **Không** phải nguồn sự thật | Mọi người |
| [`templates/`](templates/) | — | Mẫu cho spec, plan, report, review, snapshot, prompt | — |

Template ADR nằm ở `adr/0000-template.md`.

## Quy ước đặt tên

- Cùng một việc dùng **chung slug** ở mọi thư mục: `specs/m1-product-intelligence.md` → `plan/m1-product-intelligence.md` → `report/m1-…` → `review/m1-…`.
- Slug: chữ thường không dấu, nối bằng `-`, bắt đầu bằng module nếu có (`m1`…`m8`, `web`, `worker`, `db`, `ci`).
- Việc theo thời gian: `plan/week-1.md`, `plan/sprint-1.md`, `snapshot/YYYY-MM-DD.md`.
- Prompt: `prompts/<be|fe>-<số issue>-<slug>.md`, ví dụ `prompts/be-12-m1-crawl-robots.md`. Prompt không gắn với 1 issue (ví dụ việc tạo issue): `prompts/<be|fe>-<slug>.md`.
- Mỗi file ghi rõ issue/PR liên quan ở đầu file.

## Vòng đời

1. **Spec** có acceptance criteria → BA (nghiệp vụ) / team lead (kỹ thuật) duyệt.
2. **Plan** chia spec thành issue. Mỗi issue giao cho agent có 1 file trong `prompts/`.
3. Làm: 1 issue → 1 branch → 1 PR vào `dev`.
4. **Report** khi xong task/sprint.
5. **Review** đối chiếu acceptance criteria. Đạt thì đóng issue.
6. Có quyết định mới → `logs/decision-log.md`. Có câu hỏi → `logs/qa-log.md`.
