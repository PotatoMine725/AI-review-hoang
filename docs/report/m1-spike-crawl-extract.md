# Spike M1 — Crawl → Markdown → JSON: Báo cáo

- **Plan:** `plan/m1-spike-crawl-extract.md` · **Spec:** `specs/m1-spike-crawl-extract.md` (v1.1) · **Ngày:** 2026-10-07 · **Người viết:** @PotatoMine725
- **PR:** #12 (code + số liệu), #20 (đặc tả M1 v0.2 dùng kết quả spike) · **Issue:** #6 (đã đóng)
- **Chi tiết đầy đủ:** `spikes/m1-crawl-extract/README.md`, `spikes/m1-crawl-extract/output/metrics.csv`

## Đã làm
- Crawl 2 product thật (Claude: site tĩnh, nhiều plan; Dreamina: SPA) → markdown, tôn trọng `robots.txt` từng host, ≤ 30 trang, ≤ 1 request/giây, không vượt chặn.
- Trích xuất PKB rút gọn bằng Gemini (structured output), mỗi fact có `source_id` + `evidence`.
- So sánh 2 model (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`) × 2 cách gọi (`batch`: top 10 trang trong 1 lời gọi; `per_page`: 1 lời gọi/trang).
- Đo chi phí, thời gian, độ khớp evidence; đối chiếu tay giá + tên plan với website (AC-04).
- Cache theo `content_hash`: chạy lại khi nội dung không đổi tốn $0.

Code do coding agent (Claude Code) viết theo `prompts/be-6-m1-spike-crawl-extract.md`; AI-1 duyệt từng bước, quyết định 4 điểm giữa chừng (xem "Khác với plan").

## Số liệu

| Chỉ số | `batch` (đề xuất) | `per_page` | Mục tiêu |
|---|---|---|---|
| Chi phí LLM / product | **$0.008–0.014** | $0.065–0.110 | NFR-02 ≤ $0.05 |
| Thời gian / product (crawl + LLM) | **~3.4 phút** | ~4.5–5.1 phút | NFR-01 ≤ 5 phút |
| PKB hợp lệ schema | 4/4 | 4/4 | AC-02 |
| Evidence khớp nguyên văn nguồn | 92–100 % | 98–99 % | — |
| Giá + tên plan đúng (AC-04) | 1/4 | 0/4 | NFR-03 ≥ 95 % (golden set) |

- Crawl: Claude 29 trang / 198 s, Dreamina 27 trang / 165 s; khoảng cách request nhỏ nhất 1.0 s.
- `3.1-flash-lite` rẻ hơn ~30 %; `3.5-flash-lite` chép giá đúng nguyên văn hơn.
- Gom trang vào 1 lời gọi giảm chi phí 2.6–3.6× (chủ yếu nhờ giảm token ra); gửi ~28 thay vì 10 trang tăng 2.4–2.6×.
- **Tổng chi phí API của spike: ≈ $0.40** (ngân sách $2).

## Phát hiện chính
1. **Lỗi giá có quy luật, sửa được bằng schema + prompt:** giá khuyến mãi tháng đầu bị lấy làm giá plan (Dreamina); model tự tính giá (16.67 thay vì $17); chu kỳ tính tiền mơ hồ; giá API / theo giây lẫn vào danh sách plan (`per_page`). → Đã đưa vào "Quy tắc trích xuất giá" của đặc tả M1 v0.2.
2. **`fit_markdown` làm mất thẻ giá** → trang pricing phải gửi raw markdown.
3. **Giá theo vùng IP:** crawl từ Việt Nam nên Dreamina hiện VND → qa-log #9 (chọn vùng giá cho MVP tiếng Anh).
4. **Chấm điểm trang bằng regex URL để lọt trang SEO** (~8/27 trang Dreamina) → cần phạt path hoặc thêm bước phân loại rẻ.
5. **Thời gian chủ yếu là render** (5–6 s/trang); còn dư ~100 s cho trích xuất trong NFR-01.
6. `crawl4ai` 0.9.4 kéo theo `unclecode-litellm` 1.81.13 (fork LiteLLM trước sự cố 03/2026); đã kiểm tra wheel, chấp nhận là dependency gián tiếp → điểm trừ cho ADR-001.

## Khác với plan
| Điểm | Plan / spec ban đầu | Thực tế | Lý do |
|---|---|---|---|
| Product | Từ golden set của QA-2 | Claude + Dreamina (tạm, qa-log #7) | Golden set chưa có |
| Input LLM | Markdown đã lọc | Pricing: raw; trang khác: lọc | Bản lọc làm mất giá |
| Phạm vi host | Chỉ host gốc | Claude thêm `support.claude.com` (≤ 5 trang faq/pricing) | FAQ nằm ở host phụ |
| Tiền tệ | Không nêu | Chấp nhận VND theo vùng IP, không dùng proxy | Không vượt chặn |
| LiteLLM | "Không dùng" | Không dùng trong code; chấp nhận dependency gián tiếp | crawl4ai bắt buộc kéo theo |

## Việc còn lại
- [ ] ADR-001 crawl tool (#7), ADR-002 LLM provider (#8) — dùng số liệu báo cáo này, hạn 09/10.
- [ ] Đo NFR-03 trên golden set 10 product khi QA-2 bàn giao.
- [ ] qa-log #5 (phạm vi RAG), #9 (vùng giá) chờ trả lời.
- [ ] `review/m1-spike-crawl-extract.md`: nghiệm thu AC-01…AC-08 (README spike đã tự đánh dấu đạt cả 8).
