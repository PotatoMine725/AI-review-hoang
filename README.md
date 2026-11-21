# AI-review-hoang

Monorepo cá nhân (free style) của **AI Review Content Factory & Affiliate Network**.
Gộp 2 repo của team, giữ nguyên toàn bộ history bằng `git subtree`:

| Thư mục | Nguồn | Nội dung |
|---|---|---|
| `fe/` | [AI-review-FE](https://github.com/PotatoMine725/AI-review-FE) | Web Next.js + TypeScript + Tailwind + shadcn/ui (pnpm) |
| `be/` | [AI-review-BE](https://github.com/PotatoMine725/AI-review-BE) | `services/worker` (Python + FastAPI, uv), `supabase/`, `docs/` |

Repo team **chỉ đọc**: remote `upstream-fe` / `upstream-be` đã tắt push (`no_push`). Không bao giờ push lên team repo từ đây.

## Chạy local

```bash
# 1. Supabase (cần Docker)
cd be && pnpm dlx supabase start

# 2. Worker (be/services/worker, cần file .env, xem .env.example)
cd be/services/worker
uv sync
uv run uvicorn worker.main:app --reload --port 8000 --env-file .env

# 3. Runner
uv run python -m worker.runner --types crawl,video

# 4. Web (fe/, cần .env.local, xem .env.example)
cd fe && pnpm install && pnpm dev     # http://localhost:3000
```

Trong `.env` trên Windows, đường dẫn viết bằng `/` (ví dụ `D:/tmp/e2e-videos`). File `.env` và `.env.local` không bao giờ được commit.

## Lấy code mới từ team repo

```bash
git fetch upstream-fe dev && git subtree pull --prefix=fe upstream-fe dev -m "chore: sync fe from upstream"
git fetch upstream-be dev && git subtree pull --prefix=be upstream-be dev -m "chore: sync be from upstream"
```

Monorepo này đang theo nhánh `dev` của cả hai repo (ban đầu import từ `dev`), nên pull từ `dev`; đổi tên nhánh nếu muốn theo `main`. Không dùng `--squash` để giữ history đầy đủ (hai subtree đã được thêm không squash, đừng trộn hai kiểu).
Khi pull có conflict, thường ở các file đã sửa cho monorepo (xem dưới): giữ phần sửa của monorepo rồi commit.

## Khác biệt so với team repo

- `.github/workflows/ci-web.yml`, `ci-worker.yml` ở **root** (GitHub chỉ đọc workflow ở root), dùng `working-directory`. Bản gốc `fe/.github/` và `be/.github/` giữ nguyên để subtree pull không conflict nhưng không có tác dụng.
- `.gitignore` ở root, bên cạnh `.gitignore` riêng của `fe/` và `be/`.
- `fe/CLAUDE.md`, `be/CLAUDE.md`, `fe/.env.example`: đổi đường dẫn `../AI-review-BE` thành `../be`.
- Các tài liệu khác (CONTRIBUTING, PR template, link giữa 2 repo) giữ nguyên nội dung gốc; quy trình PR/review của team không áp dụng cho repo cá nhân này.
