# ADR-0003: Render engine cho video review (FFmpeg thuần hay Revideo)

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-10-15
- **Người đề xuất:** @PotatoMine725 (spike P1-02a, issue #67)
- **Người quyết định:** team lead @VV6505 (decision-log #12). BE chưa nhận renderer (15/10); BE review sau.

## Bối cảnh
Cần dựng video review **40–45 s** (lead đổi từ 15–25 s ngày 19/10; mốc là cấu hình `spikes/p1-render/config.py`, renderer v2 #80 đọc chung), H.264 + AAC, 30 fps, **9:16 (1080×1920) và 16:9 (1920×1080) từ cùng một plan**, có phụ đề tiếng Việt đốt cứng, 3 preset (hoạt hình đồ họa, điện ảnh tối giản, cổ điển), giọng đọc VieNeu-TTS (ADR-0004) và 1 cảnh AI (ADR-0006). Ràng buộc: không dùng Remotion (vướng license), không thêm thư viện ngoài stack khi chưa hỏi, đường CPU là bắt buộc (GPU chỉ là tối ưu tuỳ chọn), team 7 dev và stack BE hiện là Python.

Spike dựng thử bằng FFmpeg thuần, code ở `spikes/p1-render/` (README có lệnh chạy lại, khung hình và bảng số đo). **Revideo không được đo**: không chạy được trên máy dev và team (15/10) quyết định không đo thêm (xem dưới). So sánh Revideo vì vậy dựa trên tài liệu và kiểm tra cài đặt, không dựa trên số đo.

## Các lựa chọn
| Lựa chọn | Ưu | Nhược | Chi phí / License |
|---|---|---|---|
| A. FFmpeg thuần (Python sinh filter graph + ASS, gọi `ffmpeg`) | Đã chạy được cả 3 preset × 2 tỉ lệ; chỉ thêm `pydantic` + binary ffmpeg; cùng ngôn ngữ với worker (không cần service thứ hai, hợp ADR-0005); đo được RAM/thời gian; phụ đề ASS đủ dấu tiếng Việt | Hoạt ảnh phức tạp (chữ nảy, chuyển động theo phần tử) phải viết bằng biểu thức filter, khó đọc/khó test hình; mỗi preset mới là tinh chỉnh filter bằng tay; libass chỉ tạo hiệu ứng chữ giới hạn | FFmpeg gọi qua `subprocess`, **không phân phối binary** cùng sản phẩm (xem §Giấy phép FFmpeg). Be Vietnam Pro: OFL. Không phí |
| B. Revideo (TypeScript, render qua Chromium/Puppeteer + ffmpeg) | Mô tả cảnh bằng code TS/JSX, hoạt ảnh và bố cục linh hoạt hơn, preview trong trình duyệt | Cần **service Node thứ hai, khác ngôn ngữ** (ADR-0005); phụ thuộc Chromium (nặng, dễ vỡ theo phiên bản/hệ điều hành/driver, khó chạy trong container không GUI); **không chạy được trên máy dev** (crash Chrome, xem §Revideo); RAM/thời gian không đo | MIT (theo repo); bản 0.11.0, cập nhật gần nhất 2026-07-10 (kiểm trên npm) |
| C. Remotion | — | Vướng license | **Loại** |
| D. HyperFrames, MoviePy | Có nêu trong ADR-0005 | **Không nằm trong phạm vi spike này**, chưa đánh giá | — |

## Đo đạc (FFmpeg thuần, máy dev)
Máy: Windows 11, i7-12700H (14 nhân/20 luồng), 15,6 GB RAM, RTX 4050 Laptop + Iris Xe, FFmpeg 8.0 (Gyan full build). Bộ đầu vào thật: giọng VieNeu (PR #73) + ảnh FLUX (PR #71). Trung vị 3 lần chạy sau 1 lần khởi động bị bỏ; RAM = `maxrss` của `ffmpeg -benchmark`.

### Mốc 40–45 s (hiện hành, đo 20/10, chỉ CPU)
Plan 10 cảnh (8 ảnh + 2 thẻ chữ), giọng VieNeu thật 41,08 s, video 43,0–43,3 s. Dựng bằng libx264, một video một lần: **hoạt hình 33–34 s, điện ảnh 48–49 s, cổ điển 58–60 s** (chậm nhất 59,8 s, ~1,4× thời gian thực), RAM đỉnh **~1,9–2,0 GB**, file 3,5–4,4 MB. Còn dư ~5 lần so với timeout 300 s trên máy đo; trên máy khác hoặc khi chạy song song thì chưa đo. Không có cấu hình lỗi; NVENC/QSV chưa đo ở mốc này. Ngưỡng 2 phút không phải tiêu chí đã chốt. Bảng và so sánh với mốc cũ: `spikes/p1-render/README.md`.

### Mốc cũ 15–25 s (lịch sử, đo 15/10; không dùng cho video 40–45 s)
Video ~23 s, plan 5 cảnh. Bảng đầy đủ 18 cấu hình: `spikes/p1-render/README.md`.

| Preset | Tỉ lệ | Encoder | Dựng (s) | CPU-s | RAM đỉnh (MB) | MB |
|---|---|---|---|---|---|---|
| hoạt hình đồ họa | 9:16 | CPU (libx264) | 11.9 | 47.4 | 1561 | 2.66 |
| hoạt hình đồ họa | 16:9 | CPU | 11.6 | 49.1 | 1505 | 2.85 |
| điện ảnh tối giản | 9:16 | CPU | 19.9 | 63.0 | 1553 | 1.98 |
| điện ảnh tối giản | 16:9 | CPU | 17.7 | 56.6 | 1499 | 1.83 |
| cổ điển | 9:16 | CPU | 24.0 | 70.5 | 1545 | 1.92 |
| cổ điển | 16:9 | CPU | 23.7 | 72.5 | 1491 | 1.91 |
| hoạt hình đồ họa | 9:16 | NVENC | 12.4 | 29.7 | 1201 | 4.86 |
| điện ảnh tối giản | 9:16 | NVENC | 20.1 | 45.4 | 1167 | 4.13 |
| cổ điển | 9:16 | NVENC | 26.0 | 55.7 | 1160 | 4.00 |
| hoạt hình đồ họa | 9:16 | QSV | 19.6 | 42.4 | 858 | 2.93 |
| điện ảnh tối giản | 9:16 | QSV | 25.8 | 52.7 | 847 | 2.49 |
| cổ điển | 9:16 | QSV | 32.1 | 64.8 | 836 | 2.33 |

- **CPU đủ dùng** (mốc cũ; mốc 40–45 s xem trên): 12–24 s cho video 23 s, RAM ~1,5 GB, file 1,8–2,9 MB. Cả 18 cấu hình và 6 video fixture qua kiểm ffprobe (độ phân giải, 30 fps, `h264`/`aac`, `yuv420p`, thời lượng).
- **NVENC không giảm thời gian tường** (phần lọc hình chạy CPU): chỉ giảm CPU-s ~21–40% và RAM ~23–30%, file lớn gấp ~2×. **QSV chậm hơn** CPU nhưng RAM thấp nhất (~0,8 GB). Vì vậy GPU chỉ là tối ưu tuỳ chọn, không cần cho MVP. NVENC từng treo một lần sau lỗi mã hoá (known issue, README mục 6); đường CPU không bị.
- **Preset điện ảnh từng chậm bất thường (35–38 s) và đã sửa**: nguyên nhân là filter `vignette` của FFmpeg chạy một luồng (~19 s riêng nó). Thay bằng mặt nạ vignette dựng một lần + `lut2` thì còn ~18–20 s, hình giống bản cũ. Script thăm dò rời trước đây chỉ ~23–25 s vì chuỗi filter của nó thiếu `vignette`. Chi tiết và cách đo: README của spike.
- Số đo chỉ trên 1 máy Windows; chưa thử Linux/CI/máy chủ không GPU. Preset cổ điển (~24 s) là preset chậm nhất hiện nay, chưa tách xem filter nào tốn nhất.

## Revideo: không đo
`@revideo/renderer` 0.11.0 cài được, nhưng Chromium do Puppeteer mở bị crash (mã `0x80000003`) ở mọi biến thể thử, kể cả `--single-process`, trên máy dev này. **Team chốt 15/10: không đo Revideo nữa.** Lý do ghi lại để người sau không phải thử lại:
- Không có số thời gian/RAM/chất lượng nào cho Revideo; đây là khoảng trống của ADR, **không** phải kết luận rằng Revideo kém.
- **Rủi ro vận hành mà lần thử này đã lộ ra**: Revideo kéo theo cả Node và một trình duyệt Chromium để dựng từng khung. Chromium crash trên một máy Windows bình thường, nghĩa là mỗi môi trường chạy renderer (máy dev 7 người, CI, máy chủ/container không GUI) đều phải tự chứng minh Chromium chạy ổn, thêm một bề mặt lỗi mà FFmpeg thuần không có (FFmpeg là một binary tĩnh).
- Chi phí đo thêm (sửa môi trường Chromium, dựng lại 3 preset bằng TS) lớn hơn giá trị thông tin khi đường FFmpeg đã đạt yêu cầu MVP.

## Quyết định
**Đề xuất chọn A (FFmpeg thuần) cho MVP**, vì: đã chứng minh được đủ 3 preset × 2 tỉ lệ có giọng VieNeu, phụ đề tiếng Việt và cảnh AI thật; đường CPU đủ nhanh; không thêm service/ngôn ngữ thứ hai. Preset là dữ liệu (`presets.py`), thêm preset không sửa engine.

Xem xét lại (chuyển sang hoặc bổ sung Revideo) nếu: (1) cần hoạt ảnh chữ/đồ hoạ mà filter ASS/FFmpeg không làm được; (2) đội Video muốn dựng cảnh bằng TS và chấp nhận service Node; (3) có người chứng minh Chromium/Revideo chạy ổn ở môi trường triển khai (kèm số đo). Điều kiện chốt: BE/AI review code spike.

## Giấy phép FFmpeg
- FFmpeg được gọi **qua `subprocess`** như một chương trình riêng (không link thư viện, không nhúng) và **không được phân phối** cùng sản phẩm: môi trường chạy tự cài `ffmpeg`.
- **Nếu sau này đóng gói** (image Docker, bộ cài) cùng binary ffmpeg thì phải dùng **build LGPL** (cấu hình không có `--enable-gpl` và `--enable-nonfree`) và tuân thủ LGPL.
- Spike đo bằng Gyan full build (GPL, có libx264) chỉ để nghiên cứu nội bộ, không phân phối.
- **Chưa kiểm, cần làm trước khi đóng gói**: build LGPL không có libx264 (GPL), nên đường CPU mặc định `libx264` của spike sẽ không dùng được; phải chọn encoder H.264 khác có trong build LGPL (vd. libopenh264, hoặc encoder phần cứng) và đo lại chất lượng/tốc độ. Cũng cần xác nhận các filter spike dùng (libass, xfade, zoompan, lut2, sidechaincompress, loudnorm, gradients) có đủ trong build đó. Ý kiến pháp lý chưa có; đây là định hướng kỹ thuật.

## Hệ quả
- Dễ hơn: một ngôn ngữ, một binary ngoài; test được phần dựng lệnh không cần ffmpeg; chạy lại bằng một lệnh cho QA.
- Khó hơn / nợ kỹ thuật: tinh chỉnh hình ảnh bằng filter; phụ đề chia thời gian theo số ký tự trong câu vì TTS chỉ cho mốc theo câu (ADR-0004), nên cụm có thể lệch vài trăm ms; chưa có lớp adapter theo ADR-0005; chưa rõ ai nhận renderer.
- Việc cần làm tiếp: BE review spike và chọn người nhận; chọn encoder H.264 cho build LGPL nếu đóng gói (§Giấy phép FFmpeg); contract kịch bản P1 (v1) làm sau, ở M2 (không ép theo `script.v0`; bảng đối chiếu plan ↔ `script.v0` ở README của spike); xin quyền tư liệu sản phẩm thật (BA #67, #52).
- Decision log: **chưa thêm** dòng vào `docs/logs/decision-log.md` (quyết định 15/10); thêm khi ADR chuyển sang Accepted.

---
Liên quan: [spike README](../../spikes/p1-render/README.md), ADR-0004 (TTS, PR #73), ADR-0006 (cảnh AI, PR #71), [ADR-0005](0005-repo-structure-and-extensibility.md).
