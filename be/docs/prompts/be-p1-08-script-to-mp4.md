# Prompt: P1-08 — Đường ghép kịch bản M2 → TTS → render → MP4 (2 tỉ lệ)

- **Repo / cwd:** `AI-review-BE`
- **Branch:** `feat/p1-script-to-mp4`, tạo từ `origin/spike/p1-pipeline-bench` (#95, đã chứa #90, #92).
- **PR:** draft vào `dev`, ghi "chồng lên #95".
- **Bối cảnh:** mục tiêu tuần = tốc độ + chất lượng video (lead #94, 31/10). Số đo #95: HyperFrames chiếm ~89% thời gian mỗi video. Lead hỏi đường tích hợp template → MP4 (#61, 01/11). Mốc hoàn thiện chức năng 05/11.

Bạn là coding agent, máy Windows (i7-12700H, RTX 4050, 16GB). Tiếng Việt, giải thích ngắn.

## Việc cần làm
1. **Module ghép** `services/worker/src/worker/produce/` (hoặc tên tương đương, trình bày trước):
   - Đầu vào: kịch bản theo contract #83 (đã qua validator M2 của worker), map `asset_id` → file media (tạm: file JSON cấu hình đường dẫn, ghi rõ là thay cho BE Storage), PKB/facts để hiển thị stat nếu cần.
   - **TTS theo `segment_id`** qua adapter VieNeu (#73): ONNX CPU mặc định, CUDA nếu có. **Cache** theo hash (model, backend, giọng, bảng phát âm theo provider, lời đã chuẩn hoá); model nạp 1 lần cho cả video. Log `segment_id`, lời gốc, lời chuẩn hoá, `duration_s` đo thật.
   - **Timeline** từ audio đo thật (khoảng nghỉ cấu hình, mặc định 0,12–0,15 s); tính khoảng nghỉ và chuyển cảnh đúng 1 lần.
   - **Chuyển kịch bản M2 → render plan của #88** (`render-plan.v2-spike`): ánh xạ `role`/`kind` → layout (hook, stat, feature_clip, cta…), lời đọc/phụ đề, `fact_refs` → chữ trên hình. Cảnh M2 không có layout tương ứng → báo lỗi rõ, không bịa layout.
   - **Render HyperFrames (#88)**: 16:9 và 9:16 **chạy song song**, `--workers 3` mỗi bên; chế độ `preview` (`-q draft`) và `final` (`-q looks`). FFmpeg ghép voice + phụ đề như #88.
   - **Kiểm MP4 cuối** (ffprobe): 40–45 s đọc từ config chung (#77 `config.py`); ngoài khoảng thì báo, KHÔNG kéo dài / tua chậm / cắt câu.
   - **`render_report.json`**: mỗi cảnh `{scene_id, layout, footage, duration_s_actual, warnings[]}`, `target_s`, `actual_s`, thời gian từng bước, đường dẫn MP4.
   - Gọi spike #73/#88 qua subprocess như #95 nếu chưa port được; ghi rõ phần nào là gọi spike, phần nào code worker.
2. **CLI:** `uv run python -m worker.produce <script.json> --assets <assets.json> --out <dir> [--mode preview|final] [--ratios 16:9,9:16]`.
3. **Chạy thật 2 đầu vào:**
   - (a) `docs/report/m2-first-run-pdfcraft/run4-2026-10-30/script.json` (LLM sinh, qua validator, ~19 s): kiểm đường ghép chạy được; MP4 dự kiến ngắn hơn 40 s → báo đúng là ngoài khoảng.
   - (b) bản kịch bản PDFCraft chỉnh tay ~40 s của Khánh khi Khánh đẩy lên (#92). Chưa có thì dừng ở (a) và ghi "chờ".
   Assets: 4 clip `D:\Code\AI-Content-Review\_refs\assets\pdfcraft\*.mp4`, 1 ảnh AI ở `spikes/p1-render-v2/local/ai/`. Không commit media.
4. **Test** không cần mạng/GPU: ánh xạ M2 → plan, timeline, cache key, kiểm thời lượng, cảnh không hỗ trợ.
5. Báo cáo `docs/report/script-to-mp4-2026-11.md`: thời gian từng bước, MP4 thực tế, cảnh/layout chưa hỗ trợ, khác biệt so với render thủ công #88.

## Phạm vi
- Không sửa contract #83 (của Định), không sửa template #88 ở lượt này (góp ý hình ảnh làm ở lượt sau), không làm API/queue/Storage (BE).
- Không thêm thư viện ngoài stack khi chưa hỏi.

## Khi xong
Dừng, gửi tóm tắt + đường dẫn MP4 + `render_report.json` để duyệt trước khi push.
