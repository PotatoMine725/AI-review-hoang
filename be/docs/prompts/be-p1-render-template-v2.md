# Prompt: P1-06 spike — renderer v2 (template HTML/CSS + Playwright + FFmpeg)

- **Repo / cwd:** `AI-review-BE`
- **Branch:** `spike/p1-render-v2`, tạo từ `origin/spike/p1-render` (#77 chưa merge)
- **PR:** draft vào `dev`
- **Đặc tả:** issue **#80**, đọc kỹ trước khi làm, gồm cả comment của lead (18/10) và đánh giá HyperFrames (19/10). Mốc spike: **21/10**.

---

Bạn là coding agent của repo `AI-review-BE`, chạy trên máy Windows. Làm việc bằng tiếng Việt. Người dùng là AI dev nền C#/.NET, mới với Python: giải thích ngắn, comment code tiếng Việt ngắn.

## Vì sao làm
Quản lý (16/10) nhận xét template video còn đơn giản: đơn sắc, thiếu họa tiết, ít điểm nhấn. Mức cần đạt là video slide của NotebookLM / Gemini Notebook. Renderer FFmpeg hiện tại (#77) khó làm bố cục phong phú. Spike này chứng minh hướng dựng hình bằng HTML/CSS, chụp khung hình bằng Playwright, rồi ghép bằng FFmpeg.

## Đọc trước
- Issue #80: đặc tả, hợp đồng cảnh, 8 bố cục, tiêu chí nghiệm thu.
- `spikes/p1-render/` (#77): plan JSON, preset, cách ghép audio và phụ đề ASS, số đo hiện tại.
- `docs/adr/0003-render-engine.md`: lý do loại Remotion và Revideo.
- Video NotebookLM mẫu, nếu đã có trong `D:\Code\AI-Content-Review\_refs\videos\` (tên có `notebooklm`). Nếu có thì cắt khung hình để rút ra bố cục, họa tiết, nhịp chuyển cảnh, rồi ghi tóm tắt vào README.
- Clip thật: `D:\Code\AI-Content-Review\_refs\assets\pdfcraft\*.mp4`. Ảnh AI: dùng output của #71. **Không commit** clip hay ảnh.

## Cập nhật 19/10: ưu tiên HyperFrames
BE đã gửi bản mẫu làm bằng **HyperFrames** (`heygen-com/hyperframes`, Apache-2.0, cần Node 22+ và FFmpeg). Bản mẫu nằm ở `D:\Code\AI-Content-Review\_refs\incoming\Notion_Pages_Preview.html`. Máy worker có Node 24.14.1 và FFmpeg 8.0.

HyperFrames làm đúng điều #80 cần (HTML/CSS → headless Chrome tua từng khung → FFmpeg), nên:

- **Bước 0, khoảng 1 giờ:** cài HyperFrames bản CLI, ghim phiên bản trong `package.json` và lockfile của thư mục spike.
  - Render thử 1 composition đơn giản rồi render thử bản mẫu của BE trên máy worker.
  - Đo thời gian và RAM.
  - Ghi lại có lỗi crash Chrome không. Revideo từng crash Chrome trên máy này (ADR-0003).
- **Nếu chạy được:** dùng HyperFrames làm lớp dựng hình cho mọi mục bên dưới.
  - Python gọi CLI qua `subprocess`, giống cách gọi FFmpeg.
  - Template là composition HTML có `data-*` cho timing và track.
  - Animation ưu tiên CSS / WAAPI. Không phụ thuộc GSAP; nếu bắt buộc dùng GSAP thì ghi rõ license.
- **Nếu crash hoặc không đáp ứng được:** quay về phương án Playwright tự chụp ở mục 1 bên dưới, ghi lý do vào README.
- **Đầu vào thật** (theo lead, chạy trọn một luồng): kịch bản và audio VieNeu của demo PDFCraft (branch `spike/p1-demo-pdfcraft`, #78), clip thật, 1 ảnh AI. Không dùng fixture cho video chính.
- 8 bố cục và ngưỡng ≤ 2 phút chỉ là đề xuất. Spike chỉ cần 1 preset × 4 bố cục và có số đo.

## Nhiệm vụ (spike: 1 preset × 4 bố cục)
1. **Pipeline chụp khung hình** (`spikes/p1-render-v2/`):
   - Playwright Python sync API, Chromium. Dùng bản đã cài cùng Crawl4AI; nếu trình duyệt thiếu thì `uv run playwright install chromium`.
   - Mỗi cảnh: mở template HTML (file local, không gọi mạng), đổ `props` vào, dừng mọi animation (`document.getAnimations()`), tua `currentTime` theo từng khung 30 fps rồi chụp.
   - Đẩy khung hình thẳng vào FFmpeg qua `image2pipe`, không ghi hàng nghìn file PNG.
   - Đọc vị trí ô clip từ `data-slot` (`getBoundingClientRect`). FFmpeg chèn clip vào ô đó, có bo góc và đổ bóng.
   - Phần ghép audio VieNeu và phụ đề ASS: dùng lại cách làm của #77.
2. **Template HTML/CSS** cho preset **"điện ảnh tối giản"**, 4 bố cục: `hook`, `feature_clip`, `stat`, `cta`.
   - Có họa tiết nền (gradient, chấm hoặc sóng SVG), ≥ 3 màu + 1 màu nhấn, thẻ bo góc, icon Lucide (ISC, đặt file SVG local, ghi license).
   - Animation: chữ hoặc thẻ xuất hiện lần lượt, nhấn mạnh từ khoá, zoom vào `clip_focus`.
   - CSS chuyển bố cục theo 2 tỉ lệ 9:16 và 16:9, có vùng an toàn cho phụ đề.
   - Không dùng CDN; CSS và font nằm local (Be Vietnam Pro OFL lấy từ #77).
   - Viết template sao cho FE sửa giao diện được mà không phải đụng vào Python.
3. **Video mẫu PDFCraft, 2 tỉ lệ:**
   - 4 cảnh trên, dùng clip `pdfcraft-pagenum.mp4` và 1 ảnh AI.
   - Lấy câu thoại và audio từ spike demo PDFCraft nếu đã có. Nếu chưa, dùng 4 câu ngắn có `fact_ref` lấy từ dữ liệu crawl.
   - Ghi output vào `D:\Code\AI-Content-Review\demo-out\v2\`.
4. **Đo trên máy worker:**
   - thời gian chụp khung hình và thời gian encode cho mỗi tỉ lệ, RAM;
   - so với #77;
   - mục tiêu ≤ 2 phút mỗi tỉ lệ cho video 25 s.
5. **README:**
   - lệnh chạy lại;
   - 1 khung hình của mỗi bố cục × tỉ lệ (PNG nhỏ);
   - so sánh với khung NotebookLM nếu có;
   - hướng dẫn FE thêm bố cục hoặc preset mới.

## Phạm vi
- **Làm:** `spikes/p1-render-v2/**` và file prompt này.
- **Không làm:** sửa `spikes/p1-render`, `services/worker`, DB, API, FE repo.
- **Không commit:** video, clip, ảnh AI, key.
- **Thư viện:** HyperFrames (npm, ghim phiên bản) nếu bước 0 đạt; nếu không thì `playwright` (đã có qua Crawl4AI). Cùng với `pydantic`. Cần thêm gì thì hỏi trước.

## Tiêu chí hoàn thành
- [ ] 4 cảnh × 2 tỉ lệ render được; mỗi cảnh có họa tiết hoặc minh họa và ≥ 1 điểm nhấn chuyển động.
- [ ] Clip thật nằm đúng ô, có khung; zoom vào vùng quan trọng hoạt động.
- [ ] Không tràn chữ ở cả 2 tỉ lệ; tiếng Việt đúng dấu.
- [ ] Chạy 2 lần cùng đầu vào cho ra cùng khung hình (so hash của vài khung).
- [ ] Có số đo thời gian và RAM; ruff, pyright sạch; có test cho phần đọc slot và tính khung.

### Thước đo theo benchmark NotebookLM (19/10, xem comment #80)
- [ ] Mỗi cảnh có ≥ 1 họa tiết minh họa theo ngữ nghĩa (icon/hình), không chỉ chữ trên nền.
- [ ] Mỗi cảnh có ≥ 2 lớp hiện dần (vd khung → nội dung → điểm nhấn), mỗi lớp cách nhau 0,2–0,5s.
- [ ] Con số / từ khoá chính trong `fact_refs` hiện thành thẻ có màu nhấn (≥ 1 màu nhấn ngoài màu chính của preset).
- [ ] Nền có chiều sâu (gradient / hoa văn / mờ có màu); độ tương phản chữ ≥ 4.5:1.
- [ ] Clip thao tác thật đặt trong khung thiết bị/trình duyệt, có zoom vào vùng thao tác.
- [ ] Hook 0–2s có tên sản phẩm hoặc vấn đề, kèm chuyển động mạnh.
- [ ] Phụ đề 2–4 chữ mỗi lần, khớp `timings` của TTS.
- [ ] Tổng thời lượng 15–25s; khoảng nghỉ giữa các segment ≤ 0,15s.
- [ ] Không có chữ trên hình mà không có `fact_refs` (trừ CTA/URL).

## Khi xong
Commit kèm file prompt này, push, mở **draft PR** vào `dev`. Body PR có:
- `Refs #80, #67`;
- khung hình của từng cảnh;
- bảng số đo;
- `cc @VV6505 @tranquangthong03 @tua0201n @NguyenHuuHung-Dev`.

Trả về: link PR, đường dẫn video, các khó khăn gặp phải.
