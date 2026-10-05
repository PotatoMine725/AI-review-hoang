# AI-review-FE

Frontend của dự án **AI-Content-Factory**. Đây là một nửa của split repo, backend nằm ở repo `PotatoMine725/AI-review-BE`
(trên máy: `../AI-review-BE`).

## Stack
Chưa chọn. Khi chọn xong, ghi vào đây: framework, package manager, lệnh dev/build/test/lint.

## API contract nằm ở BE
- Nguồn sự thật: `../AI-review-BE/docs/api-contract.md` (repo BE). Không tự định nghĩa API ở repo này.
- Cần endpoint mới hoặc muốn đổi response thì tạo issue bên BE trước. Trong lúc chờ, FE có thể mock theo contract đã thống nhất.
- URL của backend lấy từ biến môi trường, không hard-code.

## Quy trình làm việc
1. Mỗi việc gắn với 1 GitHub Issue của repo này.
2. Branch: `<type>/<issue#>-<slug>`, ví dụ `feat/8-login-page`. Không commit thẳng vào `main`.
3. Commit theo Conventional Commits.
4. Mở PR vào `main` với `Closes #N`, điền checklist trong PR template.
5. Không commit secret. Tạo `.env.example` khi có biến đầu tiên.
