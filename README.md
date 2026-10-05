# AI-review-BE

Backend của **AI Review Content Factory & Affiliate Network**. MVP này tạo video review AI product ≤ 60 giây, khung dọc 9:16
(screenshot demo + AI avatar thuyết minh). Video được phân phối qua mạng creator/affiliate, hệ thống track click → signup → revenue.

Frontend: [AI-review-FE](https://github.com/PotatoMine725/AI-review-FE).

## Cấu trúc

```
AI-review-BE/
├── worker/              # Python 3.12 + FastAPI (internal API), quản lý bằng uv
│   ├── src/worker/main.py
│   ├── pyproject.toml · uv.lock · .python-version
│   └── .env.example
├── supabase/            # Supabase CLI: config.toml, migrations/
├── docs/
│   ├── PRD.md                              # tổng quan sản phẩm
│   ├── week-1-plan.md                      # kế hoạch + quy ước tuần 1
│   ├── module-1-product-intelligence.md    # đặc tả Module 1
│   ├── api-contract.md                     # API của worker (nguồn sự thật)
│   ├── adr/                                # Architecture Decision Records
│   ├── qa-log.md · decision-log.md
└── .github/             # CI (worker.yml), PR/issue template, CODEOWNERS
```

## Chạy local

Yêu cầu: [uv](https://docs.astral.sh/uv/), Node.js + pnpm (để chạy Supabase CLI), Docker Desktop (cho Supabase local).

### Worker
```bash
cd worker
cp .env.example .env        # điền key
uv sync                     # tự tải Python 3.12 nếu máy chưa có
uv run uvicorn worker.main:app --reload --port 8000
```
Kiểm tra bằng `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`. Swagger có ở http://127.0.0.1:8000/docs.

Lint và type check giống CI:
```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

### Supabase (local)
```bash
pnpm dlx supabase start     # cần Docker đang chạy; in ra URL + anon key + service role key
pnpm dlx supabase status
pnpm dlx supabase stop
```
Tạo migration mới bằng `pnpm dlx supabase migration new <ten>`.

## Tài liệu
- [CONTRIBUTING.md](CONTRIBUTING.md): Git flow, commit, PR, Definition of Done
- [docs/](docs/): PRD, kế hoạch, đặc tả, ADR, log
