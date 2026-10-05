# Decision log

Mọi quyết định đã chốt được ghi ở đây, kể cả quyết định nhỏ. Quyết định kỹ thuật lớn thì viết ADR trong `docs/adr/` và link vào cột "Chi tiết".

Quy trình: người phụ trách đề xuất → thảo luận tối đa 1 ngày → đồng thuận. Nếu không đồng thuận: tech lead quyết về kỹ thuật, BA quyết về nghiệp vụ.

| # | Ngày | Quyết định | Lý do ngắn | Người quyết | Chi tiết |
|---|---|---|---|---|---|
| 1 | 2026-10-05 | Stack lõi: Next.js (App Router) + TS + Tailwind + shadcn/ui (pnpm); worker Python 3.12 + FastAPI (uv, Pydantic v2); Supabase (Postgres, pgvector, Auth, Storage). **Provider còn mở**: crawl, LLM, render engine, avatar + TTS | Theo PRD §60 và đặc tả Module 1 | | ADR-001…004 (đang làm) |
| 2 | 2026-10-05 | Không dùng Remotion | License yêu cầu trả phí với team > 3 người | | |
| 3 | 2026-10-05 | Split repo: `AI-review-FE` (web) và `AI-review-BE` (services + supabase + docs). Kế hoạch tuần 1 ghi monorepo, cần xác nhận ở sync kỹ thuật | _cần bổ sung_ | | [ADR-0005](adr/0005-repo-structure-and-extensibility.md) (có lộ trình gộp monorepo) |
| 4 | 2026-10-05 | Cấu trúc `services/<tên>/` tự chứa; provider nằm sau adapter, chọn bằng config | Để thêm service khác ngôn ngữ (ví dụ render bằng Node) và đổi provider mà không phải tái cấu trúc | | [ADR-0005](adr/0005-repo-structure-and-extensibility.md) |
