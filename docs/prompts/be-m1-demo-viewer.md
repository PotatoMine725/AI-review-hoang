# Prompt: trang HTML tóm tắt PKB cho demo tuần 1

- **Repo / cwd:** `AI-review-BE`
- **Issue:** không có (việc chuẩn bị demo T6 09/10) · **Branch:** `feat/m1-demo-viewer` (tạo từ `dev`)
- **Liên quan:** `report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/README.md`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là AI dev, mới với Python: giải thích ngắn, đúng trọng tâm.

## Đọc trước
- `CLAUDE.md`, `CONTRIBUTING.md`
- `spikes/m1-crawl-extract/README.md`, `schema.py`, `run.py` (cách ghi output), `output/metrics.csv`, `output/*/pkb.*.json`, `output/*/crawl.json`

## Nhiệm vụ
Viết `spikes/m1-crawl-extract/demo.py`: đọc output đã có của spike, sinh **1 file HTML tĩnh** `output/demo.html` để trình bày trong buổi demo. Không gọi LLM, không crawl, không cần mạng.

Nội dung trang:
1. **Đầu trang:** luồng URL → crawl → PKB (1 dòng), ngày chạy, tổng chi phí spike.
2. **Mỗi product** (Claude, Dreamina), mặc định dùng PKB mode `batch` của `gemini-3.5-flash-lite`; tham số `--model` để đổi:
   - identity (tên, website, category, version / models nếu có);
   - bảng plan: tên, giá, tiền tệ, chu kỳ, `price_text` nguyên văn;
   - danh sách features / use cases / limitations, mỗi dòng có **evidence** và link tới URL nguồn (map `source_id` → `sources[].url`);
   - đánh dấu fact có evidence không khớp nguyên văn nguồn nếu output có thông tin này (không tự tính lại nếu không có sẵn).
3. **Bảng số liệu** từ `metrics.csv`: product × model × mode, chi phí, thời gian, số plan / fact, `price_plan_correct` + `price_plan_note`. Làm nổi bật mode `batch`.
4. **Bài học về giá** (ngắn, 3–4 dòng): lấy từ mục "Đề xuất cho đặc tả v0.2" trong README.

## Phạm vi
- Làm: chỉ `demo.py` (+ README thêm mục "Demo" 3–5 dòng, + `.gitignore` thêm `output/demo.html`).
- Không làm: sửa `crawl.py`, `extract.py`, `run.py`, `schema.py`, file trong `output/` đã commit; không sửa `services/worker`.

## Acceptance criteria
- [ ] `uv run python demo.py` chạy < 2 giây, tạo `output/demo.html`; `--model gemini-3.1-flash-lite` đổi được model.
- [ ] Chỉ dùng thư viện chuẩn Python (json, csv, html, pathlib, argparse). HTML tự chứa: CSS inline, không tải gì từ mạng.
- [ ] Mọi chuỗi lấy từ PKB / web được escape (`html.escape`) trước khi chèn vào HTML.
- [ ] Mở bằng trình duyệt hiển thị đủ 4 phần trên, đọc được trên màn hình máy chiếu (chữ ≥ 16px, bảng không tràn).
- [ ] `uvx ruff check .` và `uvx ruff format --check .` sạch.

## Ràng buộc
- Không thêm thư viện. Không commit `.env`, key, hay `output/demo.html`.
- Trình bày danh sách file sẽ tạo/sửa trước khi làm. Không dùng `git reset --hard`, force push.

## Khi xong
- Chạy thử, chụp 1 ảnh màn hình (không commit) để người dùng xem trước.
- Commit theo Conventional Commits (`feat(m1): trang demo PKB cho spike`), mở PR vào `dev`.
- Trả về: link PR, lệnh chạy demo, đường dẫn file HTML.
