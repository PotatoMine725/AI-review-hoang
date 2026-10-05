# AI-review-BE

Backend của **AI Review Content Factory**, là một nửa của split repo. Frontend nằm ở `PotatoMine725/AI-review-FE` (trên máy: `../AI-review-FE`).

Đọc trước khi làm: `docs/PRD.md` (§5–6, §50–52, §60–62), `docs/week-1-plan.md` (mục "Quy ước làm việc mặc định"),
`docs/module-1-product-intelligence.md`. Quy ước Git/PR/DoD nằm trong `CONTRIBUTING.md` và phải tuân theo.

## Stack
- `worker/`: Python 3.12 + FastAPI + Pydantic v2, quản lý bằng **uv** (không dùng pip/poetry). Lint bằng ruff, type check bằng pyright.
- `supabase/`: Postgres + pgvector + Auth + Storage, dùng Supabase CLI qua `pnpm dlx supabase`.
- KHÔNG dùng Remotion (vướng license). Không thêm thư viện ngoài stack khi chưa hỏi.

## Lệnh
```bash
cd worker
uv sync
uv run uvicorn worker.main:app --reload --port 8000
uv run ruff check . && uv run ruff format --check . && uv run pyright   # giống CI
```

## Quy tắc
- Branch `feat/<module>-<mô-tả>` | `fix/…` | `docs/…` | `chore/…`. Conventional Commits. Squash merge, cần ≥ 1 review.
- Đổi API worker thì cập nhật `docs/api-contract.md` trong cùng PR. Đổi schema DB thì thêm migration trong `supabase/migrations/`.
- Thay đổi ảnh hưởng web thì tạo issue bên `AI-review-FE`.
- Secret chỉ để trong `.env`. Có biến mới thì cập nhật `worker/.env.example`.
- Quyết định kỹ thuật lớn thì viết ADR trong `docs/adr/` và thêm 1 dòng vào `docs/decision-log.md`.
