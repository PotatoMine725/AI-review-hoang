# Tuần 1 (05–09/10/2026) — Báo cáo

> **Quyết định crawl/LLM đã chốt:** ADR-001/002 đã chốt, người xác nhận phương án @VV6505; xem decision-log #20 và [đặc tả M1](../specs/m1-product-intelligence.md). ADR-003/004 vẫn còn mở; đây là chốt thiết kế, chưa nghiệm thu tích hợp/QA. Nội dung báo cáo bên dưới giữ trạng thái ghi nhận tại mốc tuần 1.

- **Plan:** `plan/week-1.md` · **Ngày:** 2026-10-07 (nháp, chốt ở buổi review T6 09/10 14:00) · **Người viết:** @PotatoMine725
- **Nguồn:** chỉ những gì có trên GitHub (2 repo, issue, PR). Mục ghi "❓ chưa thấy" nghĩa là chưa có trong repo — **người phụ trách bổ sung link** (Figma, Google Sheet…) trước buổi review.

## 8 đầu ra tuần 1

| # | Đầu ra | Trạng thái | Bằng chứng | Phụ trách |
|---|---|---|---|---|
| 1 | Cả team đọc PRD; Q&A không còn câu hỏi chặn việc | ✅ | `logs/qa-log.md`: 9 câu, đã trả lời #1–#4, #6, #8; còn mở #5, #9 (không chặn), #7 trả lời tạm | BA, cả team |
| 2 | Phạm vi MVP (MoSCoW + danh sách cắt) | ❓ chưa thấy | — | BA |
| 3 | Repo, board, quy ước Git, CI | ✅ phần repo · ❌ board | 2 repo; nhánh `dev → staging → main` có ruleset; CI worker + FE; `CONTRIBUTING.md`; `docs/` theo SDD. Chưa có GitHub Projects board | @PotatoMine725 (repo), BA (board) |
| 4 | 4 ADR (crawl, LLM, render, avatar + TTS) | ⏳ | ADR-0005 (cấu trúc repo) đã có. ADR-001, ADR-002: #7, #8, hạn 09/10. ADR-003, ADR-004: ❓ chưa thấy | AI-1, Video-1, Video-2 |
| 5 | Sơ đồ kiến trúc + ERD v0 | ❌ | Chưa có ERD; đã có 2 migration Module 5 (PR #13, #17) — xem #23 | BE |
| 6 | Wireframe low-fi Merchant / Creator / Admin | ❓ chưa thấy | — | FE-1, FE-2 |
| 7 | Golden set 10 product (5 có đáp án) | ❓ chưa thấy | Đang hỏi qua issue | QA-2 |
| 8 | Backlog sprint 1 có user story + AC + ước lượng | ⏳ | Task list BE / AI (`plan/be-tasks.md`, `plan/ai-tasks.md`, PR #19) và FE (AI-review-FE PR #5); đang lệch đặc tả (#21) | BA, @VV6505 |

## Đã làm (theo GitHub, đến 07/10)

**Nền tảng và quy trình**
- Split repo `AI-review-BE` / `AI-review-FE`, cấu trúc `services/<tên>/` (ADR-0005).
- Luồng nhánh `dev → staging → main`, ruleset chặn xoá / force push / bắt buộc PR, tự xoá branch sau merge.
- CI: worker (ruff + pyright), FE (eslint + typecheck).
- `docs/` theo Spec-driven development: `specs/`, `plan/`, `report/`, `review/`, `snapshot/`, `prompts/`, `logs/`, `templates/`.
- Quy trình có AI hỗ trợ: coordinator lập kế hoạch + review; coding agent nhận prompt trong `docs/prompts/`, mỗi agent 1 issue → 1 PR.
- 19 PR đã merge (BE 14, FE 5); issue câu hỏi nghiệp vụ được BA trả lời trong ngày (#14, #15).

**Module 1 — Product Intelligence (AI-1)**
- Đặc tả M1 v0.2 (PR #20): cập nhật model/giá Gemini 3.x, quy tắc trích xuất giá, câu trả lời của BA.
- Spike crawl → markdown → JSON trên 2 product thật (PR #12): **~$0.01/product, ~3.4 phút/product**, đạt NFR-01, NFR-02. Xem `report/m1-spike-crawl-extract.md`.
- Phân tích video tham khảo (`references/ref-videos-2026-10-06.md`).

**Module 5 — Creator / Merchant network (BE)**
- Migration bảng `creators`, `creator_accounts`, `merchants` có RLS (PR #13, #17).

**Kế hoạch sprint 1**
- Task list BE / AI / FE (PR #19 BE, PR #5 FE).

## Khác với plan
| Điểm | Plan tuần 1 | Thực tế | Ghi ở |
|---|---|---|---|
| Cấu trúc repo | Monorepo | Split repo FE/BE | decision-log #3 |
| Git | Trunk-based, squash vào `main` | `dev → staging → main` | decision-log #5 |
| Ra quyết định | "BE (tech lead) quyết về kỹ thuật" | Người phụ trách module đề xuất stack; team lead @VV6505 duyệt cuối | decision-log #12 |
| Phạm vi tuần 1 | Không viết tính năng | Đã có migration Module 5 | #23 |
| Spike M1 | Notebook, 2 product từ golden set | Script, 2 product tạm chọn | `report/m1-spike-crawl-extract.md` |

## Đang mở cần chốt ở buổi review
- #21 task list sprint 1 lệch stack / đặc tả · #22 quy ước tên nhánh + cách merge · #23 migration tuần 1 + ERD v0.
- qa-log #5 (phạm vi RAG), #9 (vùng giá cho MVP tiếng Anh).
- ADR-001, ADR-002 (đề xuất) → team lead duyệt.

## Demo T6 09/10 (đề xuất)
1. **Nền tảng và quy trình** (~3 phút): 2 repo, nhánh + ruleset, CI, `docs/` SDD, 1 vòng spec → prompt → PR → report.
2. **Module 1** (~5 phút): URL → PKB có nguồn (chạy từ cache, trang HTML tóm tắt), số liệu chi phí / thời gian, bài học về giá.
3. **Các module khác** (người phụ trách, team lead điều phối): wireframe, clip render thử, mẫu avatar / TTS, schema DB, golden set.
