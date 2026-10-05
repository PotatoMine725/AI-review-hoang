# Prompt: docs(adr): ADR-002 LLM provider

- **Repo / cwd:** `AI-review-BE`
- **Issue:** PotatoMine725/AI-review-BE#8 · **Branch:** `docs/adr-0002-llm-provider` (tạo từ `dev`)
- **Chạy khi:** spike #6 đã merge và có `docs/report/m1-spike-crawl-extract.md`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt.

## Đọc trước
- `CLAUDE.md`, `docs/README.md`, `docs/adr/0000-template.md`, `docs/adr/0005-repo-structure-and-extensibility.md`
- `docs/specs/m1-product-intelligence.md`, `docs/specs/m1-spike-crawl-extract.md`
- `docs/report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/output/metrics.csv`

## Nhiệm vụ
Viết `docs/adr/0002-llm-provider.md` theo template. Nội dung cần so sánh: Model cho 1.4 (trích xuất) và 1.5–1.6 (merge/enrich); gọi SDK `google-genai` trực tiếp hay qua LiteLLM (nêu sự cố chuỗi cung ứng 03/2026, cách ghim phiên bản + hash); model embedding cho 1.8 (số chiều tương thích index HNSW của pgvector). Đối chiếu chi phí/product với NFR-02.

## Ràng buộc
- Mọi số liệu dẫn từ report/metrics của spike hoặc nguồn chính thức (ghi link + ngày tra cứu). Không bịa số.
- Trạng thái ADR: "Đề xuất" (team chốt ở buổi review thứ Sáu 09/10).
- Chỉ sửa tài liệu. Trình bày dàn ý trước khi viết.

## Khi xong
- Thêm 1 dòng vào `docs/logs/decision-log.md` (trạng thái đề xuất).
- Mở PR vào `dev`, tiêu đề `docs(adr): ADR-002 LLM provider`, có `Closes #8`.
- Trả về: link PR, tóm tắt quyết định đề xuất trong 3 dòng.
