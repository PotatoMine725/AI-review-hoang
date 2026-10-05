# Spike M1 — Crawl → Markdown → JSON: Đặc tả

- **Trạng thái:** Đã duyệt
- **Phiên bản:** v1.0 · **Ngày:** 2026-10-05 · **Người viết:** @PotatoMine725
- **Liên quan:** issue #6 · đặc tả `specs/m1-product-intelligence.md` (1.2, 1.4) · `plan/week-1.md` (AI-1) · ADR-001 (#7), ADR-002 (#8)

## Mục tiêu
Chứng minh luồng URL → markdown → PKB JSON chạy được trên 2 product thật.
Đo chất lượng, token, chi phí, thời gian. Số liệu là đầu vào cho ADR-001 (crawl tool) và ADR-002 (LLM provider), và để kiểm tra NFR-02.

Câu hỏi spike phải trả lời:
1. Crawl4AI có lấy đủ trang quan trọng (pricing, features, docs, FAQ) và render được trang SPA không?
2. Model Flash-Lite nào trích xuất giá và tên plan đúng hơn, rẻ hơn?
3. Chi phí LLM mỗi product là bao nhiêu? Có đạt ≤ $0.05 (NFR-02) không? Nếu không, cách giảm nào hiệu quả nhất?

## Phạm vi
- **Trong phạm vi:** sub-module 1.2 (discover + crawl) và 1.4 (structured extraction) ở mức tối thiểu; gộp fact đơn giản; đo số liệu.
- **Ngoài phạm vi:** DB, queue, API, UI, screenshot (1.3), merge nâng cao và enrichment (1.5–1.6), RAG (1.8), Langfuse, test tự động. Code spike không đưa thẳng vào worker.

## Input
| Trường | Giá trị |
|---|---|
| Product | 2 product từ golden set của QA-2 (qa-log #7). Ưu tiên 1 site tĩnh + 1 site SPA |
| Giới hạn | ≤ 30 trang/product, ≤ 1 request/giây/domain, User-Agent định danh dự án, chỉ crawl trong domain gốc |
| Model | `gemini-3.1-flash-lite` và `gemini-3.5-flash-lite` (giá tra cứu 05/10/2026: $0.25/$1.50 và $0.30/$2.50 mỗi 1M token vào/ra) |
| Key | `GEMINI_API_KEY` trong `.env`, ưu tiên gói miễn phí |

## Output
| Artifact | Commit? | Mô tả |
|---|---|---|
| `output/<product>/pages/*.md` | Không | Markdown từng trang + `page_type` |
| `output/<product>/crawl.json` | Có | Danh sách trang tìm thấy / lấy / bỏ, lý do, `content_hash` |
| `output/<product>/pkb.<model>.json` | Có | PKB rút gọn, hợp lệ theo schema |
| `output/metrics.csv` | Có | 1 dòng / product × model × cách gọi |
| `README.md` | Có | Cách chạy + bảng kết quả + nhận xét chất lượng |

**Schema PKB rút gọn** (tập con của đặc tả M1): `identity`, `pricing` (plans, free_plan, trial_days, currency), `features`, `use_cases`, `limitations`, `sources`.
Mọi fact có `origin: "crawled"`, `source_id`, `evidence` (≤ 200 ký tự).

**Cột `metrics.csv`:** product, model, mode, pages_found, pages_used, crawl_seconds, llm_calls, input_tokens, output_tokens, cost_usd, extract_seconds, schema_valid, price_plan_correct.

## Yêu cầu
| ID | Yêu cầu | Ưu tiên |
|---|---|---|
| SP-01 | Đọc `robots.txt`, `sitemap.xml`; chấm điểm link theo `page_type` (pricing, features, docs, faq, changelog, compare, other) | Must |
| SP-02 | Render JavaScript (trang SPA) và xuất markdown đã lọc nội dung thừa | Must |
| SP-03 | Trích xuất theo JSON schema bằng structured output của Gemini | Must |
| SP-04 | Đo token từ `usage_metadata`, tính chi phí theo bảng giá trong config | Must |
| SP-05 | Chạy cả 2 model trên cùng markdown | Must |
| SP-06 | So sánh 2 cách gọi: (a) 1 lời gọi / trang; (b) gom các trang điểm cao vào 1 lời gọi | Should |
| SP-07 | Chạy lại không đổi nội dung → bỏ qua LLM nhờ `content_hash` | Could |

## Acceptance criteria
- [ ] AC-01: 2/2 product ra markdown; `crawl.json` cho thấy tôn trọng `robots.txt`, ≤ 30 trang, ≤ 1 request/giây
- [ ] AC-02: Mỗi `pkb.<model>.json` hợp lệ theo schema Pydantic
- [ ] AC-03: 0 fact thiếu `source_id` hoặc `evidence`
- [ ] AC-04: Giá và tên plan được đối chiếu tay với website; kết quả ghi trong cột `price_plan_correct` và README
- [ ] AC-05: `metrics.csv` có đủ dòng cho 2 product × 2 model (× 2 mode nếu làm SP-06)
- [ ] AC-06: Tổng chi phí API ≤ $2, ghi trong README
- [ ] AC-07: Không commit `.env` hoặc key; `.env.example` để giá trị rỗng
- [ ] AC-08: README trả lời 3 câu hỏi ở mục "Mục tiêu"

## Câu hỏi mở
qa-log #6 (NFR-02), #7 (chọn product).
