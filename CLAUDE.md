# AI-review-BE

Backend của **AI Review Content Factory**, là một nửa của split repo. Frontend nằm ở `PotatoMine725/AI-review-FE` (trên máy: `../AI-review-FE`).

Đọc trước khi làm: `docs/adr/0005-repo-structure-and-extensibility.md` (cấu trúc và cách mở rộng), `docs/PRD.md` (§5–6, §50–52, §60–62),
`docs/week-1-plan.md` (mục "Quy ước làm việc mặc định"), `docs/module-1-product-intelligence.md`.
Quy ước Git/PR/DoD nằm trong `CONTRIBUTING.md` và phải tuân theo.

## Stack
- `services/worker/`: Python 3.12 + FastAPI + Pydantic v2, quản lý bằng **uv** (không dùng pip/poetry). Lint bằng ruff, type check bằng pyright.
- `supabase/`: Postgres + pgvector + Auth + Storage, dùng Supabase CLI qua `pnpm dlx supabase`.
- **Còn mở** (ADR-001…004): crawl tool, LLM, render engine, avatar + TTS. Code gọi các provider này phải đi qua adapter
  và chọn bằng config, không gọi SDK của provider rải rác (xem ADR-0005).
- KHÔNG dùng Remotion (vướng license). Không thêm thư viện ngoài stack khi chưa hỏi.

## Lệnh
```bash
cd services/worker
uv sync
uv run uvicorn worker.main:app --reload --port 8000
uv run ruff check . && uv run ruff format --check . && uv run pyright   # giống CI
```

## Quy tắc
- Branch `feat/<module>-<mô-tả>` | `fix/…` | `docs/…` | `chore/…`. Conventional Commits. Squash merge, cần ≥ 1 review.
- Mỗi `services/<tên>/` tự chứa mọi thứ của nó. Không import chéo code giữa các service; chúng chỉ giao tiếp qua HTTP, DB hoặc queue.
- Đổi API worker thì cập nhật `docs/api-contract.md` trong cùng PR. Đổi schema DB thì thêm migration trong `supabase/migrations/`.
- Thay đổi ảnh hưởng web thì tạo issue bên `AI-review-FE`.
- Secret chỉ để trong `.env`. Có biến mới thì cập nhật `.env.example` của service đó.
- Quyết định kỹ thuật lớn thì viết ADR trong `docs/adr/` và thêm 1 dòng vào `docs/decision-log.md`.
