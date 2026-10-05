# AI-review-BE

Backend của dự án **AI-Content-Factory**. Đây là một nửa của split repo, frontend nằm ở repo `PotatoMine725/AI-review-FE`
(trên máy: `../AI-review-FE`).

## Stack
Chưa chọn. Khi chọn xong, ghi vào đây: ngôn ngữ, framework, cách cài dependency, lệnh run/test/lint.

## Repo này sở hữu API contract
- `docs/api-contract.md` là nguồn sự thật duy nhất cho API giữa BE và FE.
- Muốn đổi endpoint, request hay response thì sửa contract trong cùng PR (hoặc PR trước), rồi mới sửa code.
- Thay đổi contract làm hỏng FE thì ghi rõ trong mô tả PR và tạo issue tương ứng bên FE.

## Quy trình làm việc
1. Mỗi việc gắn với 1 GitHub Issue của repo này.
2. Branch: `<type>/<issue#>-<slug>`, ví dụ `feat/12-upload-content`. Không commit thẳng vào `main`.
3. Commit theo Conventional Commits.
4. Mở PR vào `main` với `Closes #N`, điền checklist trong PR template.
5. Không commit secret. Cấu hình đọc từ biến môi trường; tạo `.env.example` khi có biến đầu tiên.
