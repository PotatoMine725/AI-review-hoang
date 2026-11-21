# Đo thời gian toàn luồng PDFCraft (P1-07, baseline trước khi tối ưu)

Ngày đo: 02/11/2026. Branch `spike/p1-pipeline-bench` (từ `feat/m2-generate-script`, chồng lên #92). Script đo: `spikes/p1-pipeline-bench/bench.py`.
Máy: i7-12700H, RTX 4050 6 GB, 16 GB RAM (trống khoảng 5,8–8 GB lúc đo, vì còn ứng dụng nền; CPU nhàn rỗi 0–4%), FFmpeg 8.0, Node 24, HyperFrames 0.8.173.
Chỉ đo, không đổi code sản phẩm. Số thô ở `D:\tmp\p1-pipeline-bench\results.json` (ngoài git), khung hình so sánh ở `D:\tmp\p1-pipeline-bench\frames\` và `smoke\`.

## 1. Cách đo (bước nào chạy thật, bước nào đọc output cũ)

| Bước | Nguồn số | Số lần |
|---|---|---|
| Crawl | **Đọc output cũ** `D:\tmp\crawl-pdfcraft-lang\crawl.json` (crawl 21/10, bản #92 dùng). Không crawl lại | 1 (đã có) |
| Extract (#90) | **Chạy thật** `worker.m1.extract` trên crawl trên, Gemini free tier (`gemini-3.5-flash-lite`) | **1 mẫu**, độ trễ LLM dao động |
| generate_script (#92) | **Chạy thật** `worker.m2.generate` với `input.json` đã sửa theo QA, cùng model | **1 mẫu** |
| TTS VieNeu (#73) | **Chạy thật** 16 câu của `pdfcraft-40-45s.json` (#88), 1 câu warm-up không tính | 2, trung vị |
| Render FFmpeg (#77) | **Chạy thật**, 1 lần warm-up không tính | 2, trung vị |
| Render HyperFrames (#88) | **Chạy thật**, 1 lần chạy lạnh đầu (smoke) không tính | 2, trung vị |

Extract và script dùng 2 request Gemini (1 request mỗi bước, không retry). Tổng RPD đã dùng trong ngày không có số liệu, vì các lần chạy trước đó trong ngày không được ghi lại. `wall` gồm khởi động `uv` và import (đo riêng: 1,2 s và 0,7 s).
Với 2 mẫu, "trung vị" là trung bình hai giá trị.

**Hai điều kiện làm số đo không so sánh trực tiếp được:**
- **FFmpeg dựng nội dung khác.** Plan 40–45 s của #77 (`dien-anh-toi-gian`) là nội dung Acme Demo, 10 câu, khác schema với plan PDFCraft của #88 (16 câu, 7 cảnh). Hai renderer không dùng chung plan. So tốc độ chỉ nói được "cùng độ dài video", không nói được "cùng cảnh".
- **HyperFrames 720p không hợp lệ** (mục 4).

## 2. Bảng thời gian từng bước (PDFCraft, video khoảng 42 s)

| Bước | Thời gian | Ghi chú |
|---|---|---|
| Crawl | **183,4 s** | 30 trang, 32 request, 6,1 s/trang, khoảng cách trung vị giữa 2 request 5,8 s (khoảng nghỉ tối thiểu 1,0 s, `render_delay_s` mặc định 3,0 s) |
| Extract | **9,0 s** (7,8 s sau khi trừ khởi động) | 1 lệnh gọi LLM, 8.639 token vào, 2.093 ra |
| generate_script | **5,8 s** (5,1 s) | 1 lệnh gọi LLM, 3.549 token vào, 1.570 ra |
| TTS ONNX CPU | nạp model lạnh **6,7 s** + sinh 16 câu **15,5 s** = **22,2 s** | RTF 0,39; RAM đỉnh 1,36 GB |
| TTS PyTorch CUDA | nạp lạnh **12,6 s** + sinh **4,2 s** = **16,8 s** | RTF 0,11; RAM đỉnh 2,5 GB, VRAM đỉnh 413 MB |
| TTS đọc lại qua cache hash | **0,05–0,07 s** (16 câu) | đổi giọng thì cache miss đúng (đã kiểm) |
| FFmpeg 1080p | 16:9 **15,4 s**; 9:16 **15,5 s** | RAM FFmpeg khoảng 1 GB |
| FFmpeg 720p | 16:9 **9,3 s**; 9:16 **9,3 s** | −40% so với 1080p |
| HyperFrames 1080p (`-q looks`) | 16:9 **171,3 s**; 9:16 **176,1 s** | bước chụp khung hình 155 s; FFmpeg đốt phụ đề và trộn voice 4,9 s; RAM đỉnh 2,6 GB |
| HyperFrames 1080p `-q draft` | 16:9 **152,7 s**; 9:16 **141,9 s** | −11% / −19%; chụp 137 s |
| HyperFrames "720p" | 16:9 **120,1 s**; 9:16 **120,1 s** | **layout vỡ, không dùng được** (mục 4) |
| HyperFrames 2 tỉ lệ song song, `--workers auto` mỗi bên | **188,8 s** cho cả hai | RAM đỉnh khoảng 5,1 GB mỗi tiến trình |
| HyperFrames 2 tỉ lệ song song, `--workers 3` mỗi bên | **146,5 s** cho cả hai | RAM đỉnh khoảng 7,1 GB mỗi tiến trình |

(Chú ý RAM đỉnh: do spike đo theo từng tiến trình dựng nên khi chạy song song có thể tính trùng. Máy vẫn chạy được, không thấy lỗi bộ nhớ.)

### Tổng một video

| Cách tính | Thời gian |
|---|---|
| Một video 16:9 (crawl + extract + script + TTS ONNX + HyperFrames 1080p) | 183,4 + 9,0 + 5,8 + 22,2 + 171,3 = **391,7 s** (khoảng 6,5 phút) |
| Hai tỉ lệ, dựng tuần tự | 391,7 + 176,1 = **567,8 s** (khoảng 9,5 phút) |
| Hai tỉ lệ, dựng song song 3+3 worker | 183,4 + 9,0 + 5,8 + 22,2 + 146,5 = **366,9 s** (khoảng 6,1 phút) |

### Bước chiếm nhiều nhất

- **Cả luồng từ URL:** crawl chiếm 47% và HyperFrames 44% của 391,7 s.
- **Phần lặp lại cho mỗi video** (crawl, extract, script chỉ chạy một lần mỗi sản phẩm): HyperFrames chiếm khoảng **89%** (171,3 / 193,5 s). Trong đó 155 s là bước chụp khung hình bằng Chrome; ghép FFmpeg chỉ 4,9 s.
- **LLM và TTS không phải điểm nghẽn:** gộp lại dưới 40 s.

## 3. Cách tối ưu xếp theo giây tiết kiệm / công sức

Số "tiết kiệm" tính trên số đo ở mục 2. Mục nào chưa kiểm thực nghiệm thì ghi rõ.

| # | Cách | Tiết kiệm | Công sức | Ảnh hưởng chất lượng / rủi ro |
|---|---|---|---|---|
| 1 | **Dựng 2 tỉ lệ song song, `--workers 3` mỗi bên** | **201 s** trên 2 tỉ lệ (347 → 146,5 s, −58%) | Thấp: chạy 2 tiến trình thay vì 2 lần nối tiếp, đặt `--workers 3` | Không đổi hình. Cần RAM: máy 16 GB chạy được nhưng chỉ còn trống rất ít; máy yếu hơn phải giảm worker. `workers auto` song song chỉ tiết kiệm 158 s (188,8 s), tức `3` tốt hơn `auto` (có thể do `auto` chạy quá nhiều Chrome). Chưa đo `--workers 3` cho dựng một tỉ lệ đơn lẻ |
| 2 | **Cache TTS theo `segment_id` + hash** (hash gồm model, backend, giọng, bảng phát âm, văn bản đã chuẩn hoá) | **16,8–22,2 s** mỗi lần dựng lại cả video; lượt cache chỉ 0,06 s | Thấp: đã chạy thử trong `tts_driver.py` | Không đổi âm thanh. Phải đưa bảng phát âm vào khoá để không trả audio cũ (đã kiểm: đổi giọng thì miss). Chỉ lợi khi dựng lại cùng lời. Cũng nên giữ model nạp sẵn trong worker để bỏ 6,7–12,6 s nạp lạnh |
| 3 | **Preview bằng `-q draft` cho vòng review, `looks` khi xuất bản** | 18,6 s (16:9) và 34 s (9:16) mỗi lần preview | Rất thấp: một cờ CLI | Một khung hình 1080p ở 5 s trông còn nét, chữ đọc tốt. Chưa so nén kỹ nhiều cảnh, chưa xem chuyển động. Cần người xem một lượt trước khi chốt |
| 4 | **Preview 720p cho HyperFrames** | khoảng 51 s mỗi lần (171 → 120 s) *nếu layout đúng* | Trung bình–cao: phải sửa template (CSS đang cố định px theo 1920×1080) | Chưa dùng được, xem mục 4 |
| 5 | **Preview 720p bằng FFmpeg (#77)** | 6,1 s mỗi lần (15,4 → 9,3 s) | Thấp, nhưng nhỏ | Chữ phụ đề vẫn đọc được (khung ở `frames\ff720_20s.png`). Số tiết kiệm nhỏ và renderer này chưa phải đường chính |
| 6 | **Crawl: giảm `render_delay_s` với trang tĩnh** | tối đa khoảng 90 s (mặc định 3,0 s × khoảng 30 trang) | Thấp: đổi cấu hình theo loại trang | **Chưa kiểm**: nếu trang SPA cần chờ JS thì mất nội dung. Cần chạy lại crawl với `render_delay_s` nhỏ và so số trang/nội dung trích được. Với site một trang, đặt `max_pages` thấp cũng giúp |

Nhận xét thêm khi đo:
- **Thời gian dựng HyperFrames dao động nhẹ:** 9:16 1080p chạy 169,5 và 182,6 s (chênh 7%).
- **LLM nhanh bất ngờ:** extract 9 s và script 6 s với một request. Điều này đúng khi không bị 429; thời gian xấu nhất theo spec M1 là hàng chục phút.
- **FFmpeg nhanh khoảng 11 lần** so với HyperFrames ở cùng độ dài video, nhưng khác nội dung và khác độ phức tạp hình ảnh (mục 1).

## 4. HyperFrames 720p: chưa dùng được, kèm bằng chứng

`hyperframes render --help` (0.8.173) **không có tuỳ chọn kích thước, scale hay viewport**. Kích thước nằm ở `data-width/data-height` của composition và ở CSS px cố định (`.r169 { width:1920px; height:1080px }`, mọi cỡ chữ `--fs-*` tính bằng px).
Đã thử hai cách đổi trong tiến trình (`hf_driver.py`, không sửa spike):
1. đặt `data-width/height` = 1280×720 và thêm `#root { zoom: 0.667 }`;
2. như trên nhưng dùng `#root { transform: scale(0.667) }` cùng `html, body { width:1280px; height:720px; overflow:hidden }`.

Cả hai cho **cùng một kết quả**: file MP4 đúng 1280×720 nhưng nội dung chỉ chiếm góc trên-trái 853×480 và bị cắt (xem `D:\tmp\p1-pipeline-bench\smoke\hf720_5s.png` và `hf720b_5s.png`), phần còn lại màu đen. HTML sinh ra đúng ý định (đã kiểm), nên có khả năng HyperFrames tự co/cắt composition theo kích thước nó biết trước. Chưa tìm ra nguyên nhân; không sửa spike theo yêu cầu.
Vì vậy con số 120 s chỉ cho biết **thời gian chụp ở viewport nhỏ**, không phải thời gian dựng một video 720p hợp lệ. Không được dùng nó để ước tính tiết kiệm cho tới khi có cách dựng đúng.
Phụ đề (ASS) thì ổn: giữ PlayRes 1080p để libass tự co về 720p, chữ không bị phóng to.

FFmpeg #77: dựng 720p hợp lệ bằng cách đặt lại `FRAME_SIZE` ở `graph` và `renderer`; bố cục giữ đúng, chữ đọc được ở khung 20 s.

## 5. Hạn chế của lần đo này

- **Extract và generate_script chỉ 1 mẫu** mỗi bước; độ trễ LLM dao động. Chưa đo lúc bị giới hạn tốc độ.
- **Crawl không chạy lại**: số liệu là của lần 21/10 (183 s), có thể khác khi mạng hoặc site thay đổi.
- **Code bench không tái lập hoàn toàn sau khi các PR merge**: `bench.py` gọi spike #73, #77, #88 qua đường dẫn worktree trên máy này (cấu hình bằng biến môi trường `P1_TTS_VI`, `P1_RENDER_V2`, `P1_RENDER`). Hai spike #73 và #88 chưa nằm trong nhánh này.
- **Lỗi đã sửa giữa chừng:** lần đo TTS đầu ghi RAM đỉnh bằng 0 do lỗi `ctypes` của driver; đã sửa và đo lại cả 4 lần TTS khi máy rảnh. Số RAM trong báo cáo là của lần đo lại.
- Chưa so ảnh 1080p và 720p của HyperFrames (do mục 4). Mới chụp một khung 1080p `looks` và `draft` ở giây 5, chưa so nén chuyển động.
- Dung lượng file: 1080p `looks` 5,8 MB, `draft` 7,0 MB (draft lớn hơn, bitrate cao hơn), 720p 2,6 MB.
