# AI-review-hoang (monorepo cá nhân)

`fe/` = web (Next.js, pnpm), `be/` = worker + supabase + docs. Xem README.md ở root. Mỗi thư mục có CLAUDE.md riêng.

- KHÔNG push lên team repo (`upstream-fe`, `upstream-be` đã `no_push`). Chỉ `git subtree pull` từ đó.
- Không commit `.env*` (trừ `.env.example`). Chạy lệnh của từng project trong `fe/` hoặc `be/services/worker`.
- CI nằm ở `.github/workflows/` (root), các `.github/` trong `fe/`, `be/` không có tác dụng.
