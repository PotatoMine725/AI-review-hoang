# Prompt: P1-07 — Đo thời gian toàn luồng (baseline trước khi tối ưu)

- **Repo / cwd:** `AI-review-BE`
- **Branch:** `spike/p1-pipeline-bench`, tạo từ `origin/feat/m2-generate-script` (#92, đã chứa #90).
- **PR:** draft vào `dev`, ghi "chồng lên #92".
- **Mục tiêu tuần (02–08/11):** tối ưu tốc độ + nâng chất lượng video (lead #94, 31/10). Lượt này **chỉ đo**, chưa tối ưu.

Bạn là coding agent của repo `AI-review-BE`, chạy trên máy Windows (worker: i7-12700H, RTX 4050 6GB, 16GB RAM, FFmpeg 8.0, Node 24). Làm việc bằng tiếng Việt, giải thích ngắn.

## Việc cần làm
1. Script `spikes/p1-pipeline-bench/bench.py` đo từng bước của luồng **PDFCraft** (dùng dữ liệu đã có, không crawl lại site thật nếu đã có output; ghi rõ bước nào chạy thật, bước nào đọc output cũ):
   | Bước | Cách đo |
   |---|---|
   | Crawl | đọc `crawl.json` của lần crawl PDFCraft gần nhất (`crawl_seconds`, số trang, giây/trang); nếu không có thì chạy lại 1 lần |
   | Extract (#90) | đọc `cost`/thời gian các lần chạy thật đã lưu; nếu không có số thời gian thì ghi "chưa đo", không gọi LLM chỉ để đo |
   | generate_script (#92) | tương tự, từ output run3/run4 |
   | TTS VieNeu (#73) | sinh lại 16 câu của plan `spikes/p1-render-v2/plans/pdfcraft-40-45s.json` (#88): ONNX CPU và PyTorch CUDA; đo tổng giây, RTF, RAM/VRAM; thêm thử **cache theo hash văn bản** (lần 2 phải ~0 s) |
   | Render FFmpeg (#77) | plan 40–45 s có sẵn, 16:9 và 9:16, **1080p và 720p** |
   | Render HyperFrames (#88) | cùng plan, 16:9 và 9:16, **1080p và 720p**; thử dựng **2 tỉ lệ song song** |
   Mỗi phép đo chạy 2 lần, ghi trung vị; máy không chạy việc nặng khác.
2. Bảng kết quả `docs/report/pipeline-timing-2026-11.md`: thời gian từng bước, tổng 1 video (16:9 trước), tổng 2 tỉ lệ, **bước nào chiếm nhiều nhất**, và danh sách cách tối ưu xếp theo **giây tiết kiệm / công sức**:
   - preview 720p cho vòng review, 1080p khi xuất bản cuối;
   - dựng 2 tỉ lệ song song hoặc dùng chung khung hình;
   - cache TTS theo `segment_id` + hash lời;
   - crawl: giảm `render_delay_s` cho trang tĩnh, giới hạn trang cho site một trang;
   - các ý khác bạn thấy khi đo.
   Ghi rõ chất lượng ảnh hưởng thế nào (vd 720p chữ có còn đọc được, chụp 2 khung hình để so).
3. Không đổi code sản phẩm ở lượt này (chỉ thêm script đo). Không commit media, wav, MP4.

## Khi xong
Dừng, báo bảng số đo + 3 đề xuất tối ưu đáng làm nhất để người dùng duyệt. Chưa push.
