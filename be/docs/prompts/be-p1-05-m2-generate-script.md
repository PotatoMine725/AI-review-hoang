# Prompt: P1-05 — `generate_script(input)` trong worker (M2, lần chạy LLM thật đầu tiên)

- **Repo / cwd:** `AI-review-BE`
- **Branch:** `feat/m2-generate-script`, tạo từ `origin/feat/m1-extract-worker` (#90, chưa merge; cần adapter `LLM`). Ghi "chồng lên #90" trong PR.
- **PR:** vào `dev`. Mốc lead + Định: **có kết quả chạy thật và báo cáo đối chiếu trước 31/10**.
- **Đọc trước:** #67 (comment lead 29/10 03:11, Định 29/10 06:33), #83 (contract M2, commit **`8f86523`**, comment lead 29/10 07:14), #90 (adapter `worker/m1/llm/`).

Bạn là coding agent của repo `AI-review-BE`, chạy trên máy Windows. Làm việc bằng tiếng Việt. Người dùng là AI dev nền C#/.NET, mới với Python: giải thích ngắn, comment code tiếng Việt ngắn.

## Phân công (đã được lead chốt)
- **Định** sở hữu contract M2: prompt, schema, validator, mapping PKB → input. **Không sửa** các file đó ở `docs/specs/m2/**` và phần M2 trong `validate_contracts.py`; cần đổi thì ghi đề xuất trong PR để Định sửa ở #83.
- **AI (PR này)** làm phần gọi LLM trong worker + chạy validator của Định + lần chạy thật.

## Việc cần làm
1. **Lấy contract đúng commit `8f86523`** (nhánh của #83): `docs/specs/m2/p1-ac-03-script-vi.prompt.md`, `p1-ac-03-script-vi.v1.schema.json`, `p1-ac-03-input.v1.schema.json`, ví dụ trong `docs/specs/m2/examples/`. Chép vào worker (vd `worker/m2/contract/`) kèm ghi chú nguồn: commit `8f86523` của #83. Có test so trùng byte với bản ở commit đó (như PKB schema ở #90).
2. **Validator:** logic M2 hiện nằm trong `spikes/m1-crawl-extract/validate_contracts.py`. Port phần kiểm M2 sang `worker/m2/validate.py` (không đổi luật). Test parity: mọi ví dụ valid/invalid trong `docs/specs/m2/examples/` cho cùng kết quả như script của Định.
3. **`generate_script(input, llm, *, settings=None) -> ScriptResult`** (async), trong `worker/m2/generate.py`:
   - Gọi `LLM.generate_json` (#90) với system prompt từ file prompt của Định, `response_schema` từ schema output (chuyển sang dạng Gemini chấp nhận nếu cần, ghi rõ chỗ lược bớt).
   - Chạy validator. Sai schema/refs → `llm_invalid_output` kèm danh sách lỗi; không tự "sửa hộ" claim.
   - Worker tự thêm `estimated_duration_s` = tổng âm tiết lời thoại ÷ tốc độ cấu hình (`M2_SYLLABLES_PER_S`, mặc định **3.75** theo Định; ghi chú VieNeu đo 3,6–3,9). Ghi rõ là ước tính.
   - `ScriptResult(status, data, cost_breakdown, warnings, error_code, error_message, retryable, retry_after)` giống `ExtractResult`: lỗi trả trong kết quả, không raise; cost giữ đủ mọi lần gọi.
   - Chưa làm `llm_revise` (sau lần chạy đầu).
4. **Input PDFCraft:** dựng `p1-ac-03-input.v1` từ PKB PDFCraft chạy thật của #90 (`D:\tmp\extract-*`). **Chỉ dùng fact đã xác nhận**: không lấy fact có warning/conflict chưa xử lý (lead: "không mặc định toàn bộ output extract đã được duyệt"). Đối chiếu với bộ 9 fact `D:\Code\AI-Content-Review\_refs\notebooklm\pdfcraft-thong-tin-san-pham.md` mà BA đã dùng; fact nào thiếu căn cứ thì bỏ và ghi lại. File input ghi rõ: "PKB PDFCraft, chọn fact thủ công theo bộ đã kiểm, chờ BA xác nhận". Asset: 4 clip `D:\Code\AI-Content-Review\_refs\assets\pdfcraft\*.mp4` + 1 ảnh AI, chỉ tham chiếu ID, không commit media.
5. **CLI:** `uv run python -m worker.m2.generate <input.json> --out <dir>`. Ghi `script.json`, `validation.json`, `cost.json`.
6. **Chạy thật:** 2 lần với Gemini (free tier, xem RPD còn lại), cùng input. Không chạy thêm để "thử prompt".
7. **Báo cáo đối chiếu** (trong PR + file `docs/report/m2-first-run-pdfcraft.md`), theo yêu cầu lead:
   - cấu trúc JSON (qua validator chưa, lỗi gì);
   - độ đúng claim so với nguồn (từng claim → fact_ref → câu nguồn);
   - mapping fact / segment / asset;
   - cảnh mà template hiện có (#88 HyperFrames: hook, stat, feature_clip, cta; FE#16: feature_clip, steps, before_after, highlight_zoom) chưa hỗ trợ;
   - `estimated_duration_s` so với 40–45 s;
   - mức sửa tay cần thiết. So **tham khảo** với kịch bản viết tay ở #88 (không phải đáp án).
   - Tách rõ kết quả test fixture với kết quả gọi LLM thật.

## Phạm vi
- **Làm:** `services/worker/src/worker/m2/**`, test, README worker, file prompt này, `docs/report/m2-first-run-pdfcraft.md`.
- **Không làm:** sửa contract của Định, DB/API/queue/Storage (BE), TTS/renderer, `llm_revise`, màn FE.
- Không thêm thư viện mới (jsonschema đã có từ #90). Không commit `.env`, output LLM lớn, media.

## Tiêu chí hoàn thành
- [ ] Contract chép đúng commit `8f86523`, test so trùng byte.
- [ ] Validator port có test parity với ví dụ của Định.
- [ ] `generate_script` có test fixture (thành công, sai schema, sai fact_ref, 429 RPD) không cần mạng.
- [ ] 2 lần chạy thật PDFCraft + báo cáo đối chiếu.
- [ ] ruff, ruff format, pyright, pytest xanh.

## Khi xong
Trước khi push và comment: dừng, gửi tóm tắt diff + kết quả chạy thật để người dùng duyệt. Sau khi được duyệt: commit kèm file prompt, push, mở PR vào `dev`, body có `Refs #67, #83`, kết quả chạy thật, giới hạn; `cc @VoHoangDinh @VV6505 @tranquangthong03 @tua0201n`.
