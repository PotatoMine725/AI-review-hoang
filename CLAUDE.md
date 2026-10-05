@AGENTS.md

# AI-review-FE

Web app của **AI Review Content Factory**, là một nửa của split repo. Backend, schema DB và docs nằm ở `PotatoMine725/AI-review-BE`
(trên máy: `../AI-review-BE`). Đọc `../AI-review-BE/docs/PRD.md` (§30–32, §62 cho màn hình) trước khi làm UI.
Quy ước Git/PR/DoD nằm trong `CONTRIBUTING.md`.

## Stack
Next.js (App Router, `src/`) + TypeScript + Tailwind CSS v4 + shadcn/ui, pnpm. Không thêm thư viện ngoài stack khi chưa hỏi.
Component UI thêm bằng `pnpm dlx shadcn@latest add <tên>`, không tự viết lại component shadcn đã có.

## Lệnh
```bash
pnpm install
pnpm dev
pnpm lint && pnpm exec next typegen && pnpm exec tsc --noEmit   # giống CI
```

## Quy tắc
- Branch `feat/<module>-<mô-tả>` | `fix/…` | `docs/…` | `chore/…`. Conventional Commits. Squash merge, cần ≥ 1 review.
- API của worker theo `../AI-review-BE/docs/api-contract.md`. Schema DB theo `../AI-review-BE/supabase/migrations/`. Không tự đặt ra API.
- `SUPABASE_SERVICE_ROLE_KEY` chỉ được dùng ở code server. Biến dùng ở client phải có tiền tố `NEXT_PUBLIC_`.
- Có biến môi trường mới thì cập nhật `.env.example`.
