# Spike M1 — Crawl → Markdown → JSON: Kế hoạch

- **Spec:** `specs/m1-spike-crawl-extract.md` · **Ngày:** 2026-10-05 · **Người viết:** @PotatoMine725
- **Issue:** #6 · **Prompt:** `prompts/be-6-m1-spike-crawl-extract.md`

## Cách làm
- Thư mục `spikes/m1-crawl-extract/`, project uv riêng, Python 3.12 (decision-log #8). Không import từ `services/worker`, không chạy CI.
- Thư viện (đã duyệt): `crawl4ai>=0.9.4` (bản vá SSRF), `google-genai`, `pydantic>=2`. Không thêm thư viện khác khi chưa hỏi.
- Gọi Gemini qua 1 hàm adapter nhỏ (`extract.py`), không rải SDK khắp nơi (ADR-0005). Không dùng LiteLLM (decision-log #9).
- Bảng giá model đặt trong 1 dict/config, ghi ngày tra cứu.
- Code viết dạng script, `run.py` chia cell `# %%` để chạy từng bước trong VS Code.

## Cấu trúc
```
spikes/m1-crawl-extract/
├── README.md · pyproject.toml · uv.lock · .python-version · .env.example · .gitignore
├── products.json        # [{ "slug", "name", "url" }]
├── schema.py            # Pydantic: PKB rút gọn
├── crawl.py             # robots, sitemap, chấm điểm link, crawl → markdown
├── extract.py           # adapter Gemini, structured output, đo token/chi phí
├── run.py               # chạy toàn bộ, ghi output/ và metrics.csv
└── output/              # pages/ bị gitignore
```

## Chia task
| # | Task | Issue | Người làm | Hạn | Phụ thuộc |
|---|---|---|---|---|---|
| 1 | Spec + plan + prompt (tài liệu này) | — | Coordinator | 05/10 | — |
| 2 | Chọn 2 product | qa-log #7 | QA-2 / @PotatoMine725 | 06/10 | — |
| 3 | Khung project + `crawl.py` (SP-01, SP-02) | #6 | Coding agent | 07/10 | 2 |
| 4 | Trình bày kết quả crawl ở sync kỹ thuật | — | @PotatoMine725 | 07/10 15:00 | 3 |
| 5 | `schema.py`, `extract.py`, `run.py` (SP-03…SP-06) | #6 | Coding agent | 08/10 | 3 |
| 6 | Đối chiếu tay giá/plan, viết `report/m1-spike-crawl-extract.md` | #6 | @PotatoMine725 | 08/10 | 5 |
| 7 | ADR-001, ADR-002 | #7, #8 | Coding agent + @PotatoMine725 | 09/10 | 6 |
| 8 | `review/m1-spike-crawl-extract.md` đối chiếu AC | — | QA-1 hoặc @PotatoMine725 | 09/10 | 6 |

Task 3 và 5 có thể là 1 PR hoặc 2 PR vào `dev`, cùng `Closes #6` ở PR cuối.

## Rủi ro
| Rủi ro | Cách xử lý |
|---|---|
| Quota gói miễn phí Gemini không đủ | Giảm số trang gửi LLM; nạp tối đa $2 (AC-06) |
| Site chặn bot / Cloudflare | Đổi product khác trong golden set, ghi lại trong report |
| Crawl4AI cài Playwright lỗi trên Windows | Chạy `crawl4ai-doctor`; ghi lỗi vào report |
| Chi phí vượt NFR-02 | So sánh SP-06, lọc markdown, giới hạn top-k trang; đề xuất trong ADR-002 |
| Lộ key | Chỉ `.env`, `.gitignore` có `.env`; kiểm tra `git status` trước commit |
