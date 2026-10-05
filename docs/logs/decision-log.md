# Decision log

Mọi quyết định đã chốt được ghi ở đây, kể cả quyết định nhỏ. Quyết định kỹ thuật lớn thì viết ADR trong `docs/adr/` và link vào cột "Chi tiết".

Quy trình: người phụ trách đề xuất → thảo luận tối đa 1 ngày → đồng thuận. Nếu không đồng thuận: tech lead quyết về kỹ thuật, BA quyết về nghiệp vụ.

| # | Ngày | Quyết định | Lý do ngắn | Người quyết | Chi tiết |
|---|---|---|---|---|---|
| 1 | 2026-10-05 | Stack lõi: Next.js (App Router) + TS + Tailwind + shadcn/ui (pnpm); worker Python 3.12 + FastAPI (uv, Pydantic v2); Supabase (Postgres, pgvector, Auth, Storage). **Provider còn mở**: crawl, LLM, render engine, avatar + TTS | Theo PRD §60 và đặc tả Module 1 | | ADR-001…004 (đang làm) |
| 2 | 2026-10-05 | Không dùng Remotion | License yêu cầu trả phí với team > 3 người | | |
| 3 | 2026-10-05 | Split repo: `AI-review-FE` (web) và `AI-review-BE` (services + supabase + docs). Kế hoạch tuần 1 ghi monorepo, cần xác nhận ở sync kỹ thuật | _cần bổ sung_ | | [ADR-0005](../adr/0005-repo-structure-and-extensibility.md) (có lộ trình gộp monorepo) |
| 4 | 2026-10-05 | Cấu trúc `services/<tên>/` tự chứa; provider nằm sau adapter, chọn bằng config | Để thêm service khác ngôn ngữ (ví dụ render bằng Node) và đổi provider mà không phải tái cấu trúc | | [ADR-0005](../adr/0005-repo-structure-and-extensibility.md) |
| 5 | 2026-10-05 | Đổi từ trunk-based sang 3 nhánh lâu dài: `dev` (tích hợp) → `staging` (tester kiểm thử) → `main` (bản ổn định theo milestone). Branch làm việc squash vào `dev`; promote giữa các nhánh bằng merge commit | Tester cần bản ổn định riêng để test; `main` chỉ giữ bản đã duyệt theo milestone. Brief tuần 1 ghi trunk-based, đổi theo yêu cầu của chủ dự án | | [CONTRIBUTING §2, §4](../../CONTRIBUTING.md) |
| 6 | 2026-10-05 | Tổ chức `docs/` theo Spec-driven development: `specs/` (làm gì), `plan/` (làm thế nào), `report/` (đã làm gì), `review/` (nghiệm thu), `snapshot/` (bản ghi cuối ngày, viết theo Simplified Technical English), `prompts/` (prompt giao việc cho coding agent), `logs/`, `references/`, `templates/`. Repo FE không giữ tài liệu, chỉ trỏ về đây | Mỗi việc có chuỗi tài liệu spec → plan → report → review truy vết được; 1 nguồn sự thật cho cả 2 repo | @PotatoMine725 | [docs/README.md](../README.md) |
| 7 | 2026-10-05 | Ruleset `dev`/`staging`/`main` ở cả 2 repo: chặn xoá, chặn force push, bắt buộc PR, **không bắt buộc approve** (0). "≥ 1 review" trong CONTRIBUTING là quy ước, không bị GitHub ép. Bật tự xoá branch sau khi merge | Tránh chặn chủ dự án tự merge việc setup khi team chưa sẵn sàng review | @PotatoMine725 | [CONTRIBUTING §4](../../CONTRIBUTING.md) |
| 8 | 2026-10-05 | Spike đặt ở `spikes/<module>-<slug>/`, là project uv riêng. Không phải service theo ADR-0005, không chạy CI, không import từ `services/` | Thử nghiệm nhanh mà không làm bẩn dependency của worker; code spike không đưa thẳng vào production | @PotatoMine725 | [specs/m1-spike-crawl-extract.md](../specs/m1-spike-crawl-extract.md) |
| 9 | 2026-10-05 | Spike M1 gọi thẳng SDK `google-genai` qua 1 hàm adapter. Có dùng LiteLLM hay không do ADR-002 quyết | LiteLLM 1.82.7, 1.82.8 trên PyPI bị cài mã độc (24/03/2026); spike chỉ cần 1 provider | @PotatoMine725 | [plan/m1-spike-crawl-extract.md](../plan/m1-spike-crawl-extract.md) |
