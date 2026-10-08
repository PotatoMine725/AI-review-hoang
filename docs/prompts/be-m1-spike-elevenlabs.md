# Prompt: spike v0.2 cho ElevenLabs + điều tra evidence_in_source của Dreamina

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #38 (QA chọn sản phẩm thay Gamma; M1 đề xuất ElevenLabs) · **Branch:** `feat/m1-spike-elevenlabs` (tạo từ `origin/dev` mới nhất)
- **Liên quan:** `spikes/m1-crawl-extract/README.md` (mục Kết quả v0.2), `docs/references/golden-set-t10-v2.md`, `docs/specs/pkb/`

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Người dùng là AI dev, mới với Python: giải thích ngắn, đúng trọng tâm.

## Bối cảnh
- Gamma (sản phẩm chính sprint 1) bị Cloudflare chặn. M1 đề xuất **ElevenLabs** thay thế: cùng nhóm Productivity, Golden Facts đã xong. Kiểm tra sơ bộ 08/10: `robots.txt` và `/pricing` trả 200, không có challenge.
- Cần bằng chứng đầy đủ (crawl ≤ 30 trang + trích giá) để QA chốt, và để demo T6 09/10 có sản phẩm chính.
- Dreamina v0.2 có `evidence_in_source` = 0.81 (v0.1: 0.92), chưa rõ nguyên nhân.

## Đọc trước
- `CLAUDE.md`, `spikes/m1-crawl-extract/README.md`, `crawl.py`, `run.py`, `extract.py` (`check_evidence`, `_norm`), `config.py`, `products.json`, `demo.py`
- `output/dreamina/pkb.gemini-3.5-flash-lite.json`, `output/v0.1/dreamina/pkb.gemini-3.5-flash-lite.json`

## Nhiệm vụ

### 1. ElevenLabs
- Thêm vào `products.json`: `{"slug": "elevenlabs", "name": "ElevenLabs", "url": "https://elevenlabs.io"}`. Không bật `allow_subdomains` (trừ khi trang giá nằm ở subdomain; nếu vậy hỏi trước).
- `uv run python crawl.py elevenlabs`. Giữ nguyên quy tắc NFR-05 (robots, ≥ 1 s/request, UA dự án, ≤ 30 trang).
  - Nếu gặp `waf_challenge` hoặc robots cấm trang giá: **dừng**, không vượt chặn, ghi vào `crawl.json` + README, báo lại.
- `uv run python run.py elevenlabs --models gemini-3.5-flash-lite --modes batch --dry-run` rồi chạy thật. Ngân sách ≤ $0.05.
- Đối chiếu giá (AC-04) với **raw markdown** trang pricing đã crawl, không mở web lần 2. Ghi `price_plan_correct` + `price_plan_note` vào `metrics.csv`.
  - Ghi rõ vùng giá thấy được (USD hay tiền khác) vì crawl từ IP Việt Nam (qa-log #9).
  - Ghi chú: "chờ đối chiếu Golden Facts của QA" (file chưa có trong repo, qa-log #11).
- PKB phải pass `uv run python validate_contracts.py` (thêm ElevenLabs vào danh sách PKB kiểm, nếu script đang liệt kê cứng).

### 2. Điều tra `evidence_in_source` của Dreamina (không gọi LLM)
- Liệt kê các fact có evidence không tìm thấy trong trang nguồn (dùng lại `check_evidence`, in ra `source_id`, evidence, trang được so).
- Phân loại nguyên nhân, ví dụ:
  - (a) so với bản `fit` trong khi LLM nhận bản `raw` (trang pricing), hoặc ngược lại;
  - (b) gán sai `source_id`;
  - (c) evidence ghép 2 câu / đổi chữ;
  - (d) chuẩn hoá (`_norm`) chưa xử lý ký tự đặc biệt (vd. dấu phân cách hàng nghìn, xuống dòng).
- Nếu nguyên nhân là lỗi của **bước kiểm tra** (a hoặc d): sửa `check_evidence` cho đúng, tính lại số cho Claude và Dreamina từ file đã có (không gọi LLM), ghi số cũ → mới.
- Nếu là lỗi của **LLM** (b hoặc c): không sửa prompt trong PR này, chỉ ghi kết luận + đề xuất vào README.

### 3. Demo và README
- `demo.py`: hiện thêm thẻ ElevenLabs (giữ thẻ Gamma "không crawl được").
- README, mục "Kết quả v0.2": thêm ElevenLabs (số trang, chi phí, thời gian, kết quả giá) và kết luận điều tra evidence.

## Phạm vi
- Làm: `spikes/m1-crawl-extract/**` (code, `products.json`, output của ElevenLabs, `metrics.csv`, README).
- Không làm: sửa spec M1, ERD, contracts, decision-log; không crawl product khác; không sửa prompt trích xuất.

## Acceptance criteria
- [ ] ElevenLabs: crawl xong (hoặc dừng đúng quy tắc nếu bị chặn), có `crawl.json`.
- [ ] Nếu crawl được: 1 PKB v0.2 hợp lệ, `validate_contracts.py` pass, chi phí ≤ $0.05, có dòng trong `metrics.csv` với `price_plan_correct` + note.
- [ ] Có bảng các evidence không khớp của Dreamina kèm phân loại nguyên nhân; nếu sửa `check_evidence` thì ghi số cũ → mới.
- [ ] `uv run python demo.py` chạy được, có thẻ ElevenLabs.
- [ ] `uvx ruff check .` và `uvx ruff format --check .` sạch.

## Ràng buộc
- Trình bày danh sách file sẽ sửa trước khi làm, chờ duyệt. Dừng và báo trước khi gọi LLM thật (kèm số dry-run).
- Không commit `.env`, `pages/`, `llm_cache/`, `output/demo.html`. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`feat(m1): spike v0.2 cho ElevenLabs, điều tra evidence Dreamina`), kèm file prompt này. Mở PR vào `dev`, body có `Refs #38`.
- Trả về: link PR, bảng giá ElevenLabs, chi phí, kết luận evidence.
