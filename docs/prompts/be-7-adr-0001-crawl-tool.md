# Prompt: docs(adr): ADR-001 crawl tool

- **Repo / cwd:** `AI-review-BE`
- **Issue:** PotatoMine725/AI-review-BE#7 · **Branch:** `docs/adr-0001-crawl-tool` (tạo từ `dev`)
- **Chạy khi:** spike #6 đã merge và có `docs/report/m1-spike-crawl-extract.md` (đã có từ 07/10)
- **Người đề xuất:** @PotatoMine725 (phụ trách M1) · **Người quyết định:** team lead @VV6505 (decision-log #12)

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt.

## Đọc trước
- `CLAUDE.md`, `docs/README.md`, `docs/adr/0000-template.md`, `docs/adr/0005-repo-structure-and-extensibility.md`
- `docs/specs/m1-product-intelligence.md`, `docs/specs/m1-spike-crawl-extract.md`
- `docs/report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/output/metrics.csv`

## Nhiệm vụ
Viết `docs/adr/0001-crawl-tool.md` theo template. Nội dung cần so sánh: Crawl4AI so với ≥ 1 lựa chọn khác (ví dụ Playwright tự viết + trích markdown, Firecrawl self-host — lưu ý AGPL-3.0). Tiêu chí: license, render JS, chất lượng markdown, tốc độ, bảo trì, lỗ hổng bảo mật đã biết.

## Ràng buộc
- Đọc thêm `docs/specs/m1-product-intelligence.md` v0.2 (Quy tắc trích xuất giá, mục Tech stack) để ADR khớp đặc tả.
- Mọi số liệu dẫn từ report/metrics của spike hoặc nguồn chính thức (ghi link + ngày tra cứu). Không bịa số.
- Trạng thái ADR: "Đề xuất" (team chốt ở buổi review thứ Sáu 09/10).
- Chỉ sửa tài liệu. Trình bày dàn ý trước khi viết.

## Khi xong
- Thêm 1 dòng vào `docs/logs/decision-log.md` (trạng thái đề xuất).
- Mở PR vào `dev`, tiêu đề `docs(adr): ADR-001 crawl tool`, có `Closes #7`.
- Trả về: link PR, tóm tắt quyết định đề xuất trong 3 dòng.
