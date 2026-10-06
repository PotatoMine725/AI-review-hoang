# Prompt: feat(m1): spike crawl → markdown → JSON trên 2 product

- **Repo / cwd:** `AI-review-BE`
- **Issue:** PotatoMine725/AI-review-BE#6 · **Branch:** `feat/m1-spike-crawl-extract` (tạo từ `dev`)
- **Spec / plan:** `docs/specs/m1-spike-crawl-extract.md`, `docs/plan/m1-spike-crawl-extract.md`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là AI dev, mới với Python: giải thích ngắn, đúng trọng tâm.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md`, `docs/README.md`
- `docs/specs/m1-spike-crawl-extract.md` (yêu cầu + acceptance criteria), `docs/plan/m1-spike-crawl-extract.md` (cấu trúc, thư viện)
- `docs/specs/m1-product-intelligence.md` mục 1.2, 1.4, Output (schema PKB đầy đủ)
- `docs/references/ref-videos-2026-10-06.md` mục "Ảnh hưởng tới Module 1" (vì sao cần `identity.version`)
- `docs/adr/0005-repo-structure-and-extensibility.md` (adapter, không import chéo)
- Docs chính thức của Crawl4AI và `google-genai` bản mới nhất. Không dựa vào API nhớ sẵn.

## Nhiệm vụ
Tạo spike `spikes/m1-crawl-extract/` theo plan: crawl 2 product → markdown → Gemini trích xuất PKB rút gọn → ghi `metrics.csv`.
Làm theo 2 bước, dừng lại báo cáo sau mỗi bước:
1. Khung project + `crawl.py` (SP-01, SP-02). Chạy trên 2 product, in bảng trang lấy/bỏ.
2. `schema.py`, `extract.py`, `run.py` (SP-03…SP-06). Chạy 2 model, ghi output.

## Phạm vi
- Làm: đúng cấu trúc trong plan; `products.json` gồm 2 product trong spec v1.1: Claude (`https://claude.com`) và Dreamina (`https://dreamina.capcut.com`). Nếu site chặn bot, bắt đăng nhập hoặc chặn theo vùng: dừng, ghi vào README, hỏi người dùng đổi product. Không vượt chặn (không giả trình duyệt, không proxy).
- Không làm: DB, queue, API, UI, screenshot, `media_sample`, enrichment, RAG, Langfuse, test framework. Không sửa `services/worker`.

## Acceptance criteria
AC-01…AC-08 trong spec. Cột `price_plan_correct` để trống cho người dùng đối chiếu tay.

## Ràng buộc
- Thư viện đã duyệt: `crawl4ai>=0.9.4`, `google-genai`, `pydantic>=2`. Thư viện khác: hỏi trước. Không dùng LiteLLM, Remotion.
- Quản lý bằng `uv` (`uv init --app`, `uv add`), Python 3.12, commit `uv.lock`.
- Crawl lịch sự: tôn trọng `robots.txt`, ≤ 1 request/giây/domain, ≤ 30 trang, User-Agent định danh dự án.
- Gọi Gemini qua 1 hàm adapter trong `extract.py`; model và bảng giá đặt trong config, ghi ngày tra cứu giá.
- Không commit secret. `.env.example` chỉ có `GEMINI_API_KEY=`. `.gitignore` chặn `.env` và `output/*/pages/`.
- Tổng chi phí API ≤ $2. Báo người dùng trước khi chạy lần gọi LLM đầu tiên.
- Không dùng `git reset --hard`, force push. Trình bày danh sách file trước khi tạo.

## Khi xong
- `uv run ruff check .` sạch (dùng `uvx ruff` nếu không thêm ruff vào project).
- Commit theo Conventional Commits, mở PR vào `dev`, tiêu đề `feat(m1): spike crawl → markdown → JSON`, body theo PR template, có `Closes #6`.
- README spike có bảng kết quả và trả lời 3 câu hỏi của spec.
- Trả về: link PR, danh sách file, tổng chi phí, lệnh để tự chạy lại.

