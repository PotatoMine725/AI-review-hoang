# Prompt: Module 2 v0 — contract script theo Scene + prompt template 20 hooks (bản tối thiểu)

- **Repo / cwd:** `AI-review-BE`
- **Issue:** #38 (mục AI Dev, việc M2) · **Branch:** `feat/m2-script-schema-v0` (tạo từ `origin/dev` mới nhất)
- **Chạy khi:** đến 15:30 08/10 mà @VoHoangDinh (AI-2, owner M2) chưa nhận việc. Đây là **bản v0 để bàn giao**, không phải thiết kế cuối của M2.

---

Bạn là coding agent của repo `AI-review-BE`. Làm việc bằng tiếng Việt. Viết tài liệu bằng câu ngắn, đơn giản (xem `docs/README.md`).

## Bối cảnh
- Module 2 (Content Strategy) nhận **PKB approved** của M1 và sinh hook, script. M3 (video) đọc script để dựng video dọc 9:16, 15–60 giây.
- Hạn 17:30 08/10 (#38). Không gọi LLM, không viết code worker. Chỉ viết contract + template + ví dụ.

## Đọc trước
- `docs/specs/PRD.md` §13 (AI Hook Factory), §14 (Script Factory), §15 (AI Video Factory), §41 (AI Quality Control)
- `docs/specs/srs.md`: FR-CONT-01…08, FR-VID-02 (9:16, 15–60 s, safe zone), FR-VID-03 (Screen Recording), FR-QA-01…07 (không bịa, "I tested" cần evidence)
- `docs/specs/erd/erd.dbml`: bảng `content_scripts` (cột `idea`, `hook`, `intent`, `script_text`, `platform`, `language`, `knowledge_version`)
- `docs/specs/pkb/README.md`, `docs/specs/pkb/pkb-data.v0.2.schema.json`, `docs/specs/contracts/README.md` (cách viết contract, examples, validate)
- `spikes/m1-crawl-extract/output/elevenlabs/pkb.gemini-3.5-flash-lite.json` (PKB mẫu)
- `spikes/m1-crawl-extract/validate_contracts.py`

## Nhiệm vụ

### 1. `docs/specs/contracts/script.v0.schema.json` (JSON Schema draft 2020-12, viết tay)
Một script = 1 video. Trường chính:
- `schema_version` = `"0"`, `product_id`, `knowledge_version` (PKB approved đã dùng), `platform` (`tiktok|reels|shorts`), `language` (`en`), `intent` (`awareness|education|consideration|conversion`, khớp CHECK của ERD), `format` (`screen_recording|faceless|hybrid|ai_avatar`), `target_duration_s` (15–60), `aspect_ratio` = `"9:16"`.
- `hook`: `text`, `type` (theo PRD §13, vd. `problem|curiosity|result|comparison|mistake|…`), `hook_id` (tham chiếu bộ 20 hook).
- `scenes[]` (≥ 3): `index`, `role` (`hook|problem|demo|result|proof|cta`, theo FR-CONT-04), `duration_s`, `voiceover`, `on_screen_text`, `visual` (`kind`: `screenshot|screen_recording|text_card|logo`, `ref`: đường dẫn ảnh từ `sources[].image_paths` hoặc mô tả shot), `claims[]`.
- `claims[]`: mỗi claim về sản phẩm (giá, tính năng, giới hạn) **bắt buộc** có `fact_ref` trỏ về fact trong PKB (`source_id` + đường dẫn JSON của fact, vd. `pricing.plans[2]`). Claim không có `fact_ref` = không hợp lệ (FR-QA-01, BRULE-05).
- `cta`: `text`, `uses_tracking_link: true`.
- `disclosure`: bắt buộc khi `format = ai_avatar` (FR-VID-09).
- `experience_claims`: mặc định cấm câu kiểu "I tested…"; chỉ cho phép khi có `evidence_ref` (FR-QA-07).
- Luật kiểm được bằng schema: tổng `duration_s` các scene trong 15–60 (ghi rõ nếu schema không kiểm được tổng → để validator kiểm).

### 2. `docs/specs/m2/hooks-prompt.v0.md` — Prompt Template v0 cho 20 hooks
- Input: PKB approved (chỉ fact `crawled`/`merchant`, fact `inferred` chưa duyệt không dùng — FR-05), audience (nếu có), platform, `forbidden_claims`/`approved_claims` của campaign.
- Output: JSON 20 hook, mỗi hook: `hook_id`, `text` (≤ 15 từ, tiếng Anh), `type`, `angle` (theo nhóm Content Idea của FR-CONT-01), `fact_refs[]`.
- Quy tắc trong prompt: không bịa giá/tính năng; số liệu phải lấy nguyên văn từ PKB; không "I tested" khi không có evidence; đa dạng `type` (≥ 6 loại khác nhau trong 20 hook — BR-20); không dùng forbidden claims.
- Ghi rõ biến của template (`{{pkb_json}}`, `{{platform}}`, …) và JSON schema output (inline trong file, ngắn).

### 3. Ví dụ và kiểm tra
- `docs/specs/contracts/examples/`: thêm `valid-script-elevenlabs.json` (1 script ~30 s, 6 scene, viết tay từ PKB ElevenLabs, claim giá/tính năng có `fact_ref` đúng) và 2 ví dụ không hợp lệ (claim thiếu `fact_ref`; `format = ai_avatar` thiếu `disclosure`).
- Mở rộng `validate_contracts.py` để kiểm `script.v0` (+ kiểm tổng thời lượng 15–60 s và `fact_ref` trỏ tới fact có thật trong PKB ElevenLabs). Hợp lệ pass, không hợp lệ fail.
- `docs/specs/contracts/README.md`: thêm mục `script.v0` (ngắn: dùng cho ai, map vào `content_scripts` thế nào).

### 4. Map với ERD (chỉ ghi, không sửa ERD)
`content_scripts` hiện có `script_text text`. Ghi trong README: đề xuất lưu JSON script v0 ở đâu (vd. `script_text` chứa JSON, hoặc thêm cột `script jsonb`) → **câu hỏi mở cho @tranquangthong03, ghi vào #50**. Không tự sửa `docs/specs/erd/`.

## Phạm vi
- Làm: `docs/specs/contracts/script.v0.schema.json`, `docs/specs/contracts/examples/*script*`, `docs/specs/contracts/README.md`, `docs/specs/m2/hooks-prompt.v0.md` (+ `docs/specs/m2/README.md` 5–10 dòng: đây là bản v0 do M1 viết tạm, owner M2 là AI-2), `spikes/m1-crawl-extract/validate_contracts.py`.
- Không làm: gọi LLM, code worker, sửa ERD/PKB contract/spec M1, đặc tả M2 đầy đủ.

## Acceptance criteria
- [ ] Schema hợp lệ draft 2020-12; ví dụ hợp lệ pass, 2 ví dụ không hợp lệ fail đúng lý do.
- [ ] Mọi `fact_ref` trong ví dụ ElevenLabs trỏ tới fact có thật trong PKB (validator kiểm).
- [ ] Template hooks có đủ: biến input, quy tắc chống bịa, đa dạng type, JSON output.
- [ ] `validate_contracts.py` chạy đạt toàn bộ (cũ + mới). `uvx ruff check .` và `uvx ruff format --check .` sạch.
- [ ] README ghi rõ "v0, do M1 viết tạm, bàn giao AI-2" và câu hỏi mở về cột lưu script.

## Ràng buộc
- Trình bày danh sách file trước khi làm, chờ duyệt. Hạn 17:30: giữ tối giản.
- Không thêm thư viện. Không dùng `git reset --hard`, force push.

## Khi xong
- Commit (`docs(m2): contract script v0 theo scene và prompt template 20 hooks`), kèm file prompt này. Mở PR vào `dev`, body có `Refs #38`, `cc @VoHoangDinh @VV6505`.
- Trả về: link PR, kết quả `validate_contracts.py`.
