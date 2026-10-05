# Decision log

Mọi quyết định đã chốt được ghi ở đây, kể cả quyết định nhỏ. Quyết định kỹ thuật lớn thì viết ADR trong `docs/adr/` và link vào cột "Chi tiết".

Quy trình: người phụ trách đề xuất → thảo luận tối đa 1 ngày → đồng thuận. Nếu không đồng thuận: tech lead quyết về kỹ thuật, BA quyết về nghiệp vụ.

| # | Ngày | Quyết định | Lý do ngắn | Người quyết | Chi tiết |
|---|---|---|---|---|---|
| 1 | 2026-10-05 | Stack: Next.js (App Router) + TS + Tailwind + shadcn/ui (pnpm); worker Python 3.12 + FastAPI (uv, Pydantic v2); Supabase (Postgres, pgvector, Auth, Storage) | Theo PRD §60 và đặc tả Module 1 | | |
| 2 | 2026-10-05 | Không dùng Remotion | License yêu cầu trả phí với team > 3 người | | |
| 3 | 2026-10-05 | Split repo: `AI-review-FE` (web) và `AI-review-BE` (worker + supabase + docs) | | | |
