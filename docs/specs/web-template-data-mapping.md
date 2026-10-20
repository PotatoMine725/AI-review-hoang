# P1 — Dữ liệu cho template FE (bản nháp)

Ngày: 20/10/2026. **Đang chờ team review**, chưa phải API/render contract đã chốt.

Liên quan: [FE #15](https://github.com/PotatoMine725/AI-review-FE/issues/15), [BE #80](https://github.com/PotatoMine725/AI-review-BE/issues/80), [M2 #83](https://github.com/PotatoMine725/AI-review-BE/pull/83), [demo #78](https://github.com/PotatoMine725/AI-review-BE/pull/78).

## 1. Phạm vi

FE làm bố cục, chuyển động và preview cho ba preset: **hoạt hình đồ họa, điện ảnh tối giản, cổ điển**. Dùng chung thư viện tám layout, hỗ trợ 16:9 và 9:16; không bắt buộc mỗi video dùng đủ tám layout. MP4 P1 hoàn chỉnh cần dài **40–45 giây**.

Giữ nguyên payload M2; preset, tỷ lệ và lựa chọn layout đặt trong file cấu hình riêng để review. Trường nội dung còn thiếu sẽ trao đổi tại #83. Cách đóng gói và renderer cần team chốt, chưa mặc định dùng HyperFrames.

Preview template bổ sung riêng. Các lựa chọn style, thời lượng và video mẫu trong Studio hiện tại vẫn là mock, chưa dùng làm cấu hình P1. Phần nối vào ứng dụng xử lý theo [#61](https://github.com/PotatoMine725/AI-review-BE/issues/61).

## 2. Dữ liệu đầu vào

| Phần | Nội dung | Bên cung cấp |
|---|---|---|
| Kịch bản | Sản phẩm/PKB version, cảnh, lời thoại, chữ, claim/fact refs, CTA | M2 |
| Cấu hình trình bày | Preset, tỷ lệ, layout theo scene ID, chữ được chọn làm tiêu đề | FE đề xuất, thống nhất với BE |
| Media | Asset ID và ảnh/clip/audio dùng được, kích thước, thời lượng | AI–BE |
| Timeline | Audio theo segment ID, thời điểm cảnh và phụ đề | TTS + BE/renderer |

| Trường M2 | FE sử dụng |
|---|---|
| `schema_version` | Đọc đúng cấu trúc; mẫu hiện tại là `p1-ac-03.v1-draft` |
| `product_id`, `pkb_schema_version`, `knowledge_version` | Giữ đúng sản phẩm và phiên bản nguồn; BE xác nhận quyền và PKB |
| `language`, `concept.title` | Ngôn ngữ và tên preview/video |
| `scenes[].scene_id`, `.role` | Giữ ID, thứ tự và vai trò cảnh; không dùng vị trí mảng làm ID |
| `narration_segments[].segment_id`, `.text` | Ghép đúng lời thoại với audio; text chuẩn hóa cho TTS lưu riêng |
| `subtitle_text` | Nội dung phụ đề, chưa có timing từng từ |
| `visual_plan.kind`, `.source_type`, `.asset_id` | Xác định loại tư liệu; BE cung cấp file từ asset ID |
| `visual_plan.text`, `.purpose` | Text card và ghi chú; hiển thị text thuần, không chạy HTML/JS đầu vào |
| `claims[].text`, `.fact_refs`, `.segment_ids` | Giữ tham chiếu về claim và nguồn; không tự thêm số liệu hoặc claim |
| `hook.text`, `cta.text`, `cta.destination` | Nội dung mở đầu và CTA; đích null vẫn dùng được CTA dạng chữ |
| `target_duration_s` | Mục tiêu thời lượng; thời lượng cuối lấy từ MP4, không chia đều cho các cảnh |

Layout khác với vai trò cảnh: một cảnh `demo` có thể dùng `feature_clip` hoặc `highlight_zoom`. `generated_text` không cần asset; `ai_generation` là yêu cầu sinh ảnh, chưa phải ảnh đã có.

README M2 có nhắc `min_duration_s` nhưng schema tại commit bên dưới chưa khai báo, nên chưa dùng trường này.

## 3. Dữ liệu cho tám layout

Đây là nhu cầu để team đối chiếu, chưa phải các trường mới của M2.

| Layout | Dữ liệu cần | Phần cần bổ sung/chốt |
|---|---|---|
| `hook` | Chữ mở đầu, ảnh/icon nếu có | Chọn chữ làm tiêu đề; có thể thử bố cục chỉ có chữ |
| `problem` | Tiêu đề, các ý vấn đề | Nếu dùng danh sách ý, cần mapping rõ về nội dung gốc |
| `feature_clip` | Tiêu đề, clip | File clip, đoạn cắt và cách fit/crop |
| `stat` | Giá trị, nhãn, đơn vị/phạm vi nếu có, fact refs | M2 hiện chỉ có claim dạng text; cần dữ liệu số rõ ràng, không tự tách số rồi đoán nghĩa |
| `steps` | Các bước có thứ tự và tham chiếu nội dung | Không mặc định mỗi đoạn thoại là một bước |
| `before_after` | Hai ảnh/clip, nhãn trước/sau, căn cứ so sánh | M2 hiện có một asset mỗi scene; cần cặp tư liệu phù hợp |
| `highlight_zoom` | Clip/ảnh, vùng focus, thời điểm zoom | Chốt tọa độ, mốc thời gian và bên thực hiện zoom/con trỏ |
| `cta` | Nội dung và đích CTA | Dùng đúng dữ liệu đã xác nhận |

Quy tắc hiển thị:

- Preset thay cách trình bày, giữ nguyên nội dung và references.
- Thử title khoảng 80 ký tự, body khoảng 200 ký tự, 2–4 ý hoặc 2–5 bước. Kiểm số dòng và vùng phụ đề ở cả hai tỷ lệ rồi điều chỉnh.
- Chữ quá dài hoặc thiếu dữ liệu thì báo để sửa; không tự cắt ý hay thu chữ đến mức khó đọc.
- Preview có thể dùng placeholder ghi rõ thiếu media. Layout thiếu đầu vào chưa được tính là render hoàn chỉnh.

## 4. Media và timeline

AI–BE cần gửi file mẫu dùng được và cách truy cập theo asset ID, kèm loại file, kích thước, thời lượng và quyền sử dụng. Ảnh AI cần là ảnh đã sinh, có thông tin lần sinh.

Đề xuất dùng giây cho đoạn cắt clip và tọa độ `[0,1]` cho vùng focus trên ảnh/clip gốc. Team cần chốt mốc thời gian thuộc clip nguồn hay scene, và bên nào xử lý crop, zoom, con trỏ, chuyển cảnh.

Timeline lấy theo audio thật của từng `segment_id`. BE/renderer tính cả khoảng nghỉ và chuyển cảnh; FE dùng lại timeline đó. Phụ đề cần text và mốc bắt đầu/kết thúc rõ ràng; chỉ làm karaoke khi có timing từng từ phù hợp.

## 5. Mẫu dữ liệu kèm theo

| File | Nội dung |
|---|---|
| [m2-script.fixture.json](examples/web-template-data/m2-script.fixture.json) | Giữ nguyên ví dụ ElevenLabs từ M2 [182ea93](https://github.com/PotatoMine725/AI-review-BE/tree/182ea93a09380bc2af04e655bc4a0a7d62444a96/docs/specs/m2); dùng kiểm cấu trúc, chưa có media/timeline thật |
| [template-selection.proposal.json](examples/web-template-data/template-selection.proposal.json) | Cấu hình FE đề xuất: một preset, hai tỷ lệ, bốn layout; `stat` đang thiếu dữ liệu |
| [pdfcraft-source-manifest.json](examples/web-template-data/pdfcraft-source-manifest.json) | Danh sách file/hash và mapping đề xuất từ demo [f293230](https://github.com/PotatoMine725/AI-review-BE/tree/f293230f10535a3435ce78237ba43f2c7470eafb/spikes/p1-demo-pdfcraft); không phải output M2 |

`title_ref` chọn chữ từ script hoặc scene bằng JSON Pointer. Ví dụ `/claims/0/text` chỉ đúng với bản script đang dùng. Mẫu đã gắn hash của script; khi script được sửa hoặc sinh lại, cần kiểm lại lựa chọn chữ/layout. Khi tích hợp, đề xuất gắn cấu hình với revision hoặc hash của script để tránh trỏ nhầm nội dung.

Lưu ý với PDFCraft:

- Kịch bản viết tay; scene/segment ID trong manifest mới là đề xuất. Cần AI–BE xác nhận Product/PKB version và mapping `Fxx` sang fact refs M2.
- `F04`/`F05` mâu thuẫn số công cụ, chưa dùng làm stat. Fact trích tay không tự coi là fact do chủ sản phẩm xác nhận.
- Clip, ảnh AI và audio không nằm trong Git, cần nhóm gửi riêng. Frames không thay được clip nguồn.
- Timeline mẫu đo **22 giây**, giữ làm kết quả cũ; chưa đạt mục tiêu mới 40–45 giây.
- Clip xuất Word đi qua menu Studio, còn F07 nói PDF to Word; cần kiểm lại trước khi dùng làm claim hoặc so sánh trước/sau.

## 6. Việc tiếp theo

| Bước | Việc cần làm |
|---|---|
| FE làm trước | Vũ–Hưng thống nhất màu/font, dùng một preset làm preview tối thiểu. Review 16:9 trước, sau đó kiểm 9:16 |
| Chốt với AI–BE | Cách gửi cấu hình layout; dữ liệu còn thiếu; bộ clip/audio mẫu; timeline và cách renderer nhận template |
| Thử một cảnh | Dùng một scene `feature_clip` có JSON, clip và audio mẫu. FE chuẩn bị template; phối hợp BE/AI nạp font/media và điều khiển theo timeline để xuất cảnh thử |
| Mở rộng | Sau khi cảnh thử chạy được, làm `hook`, `feature_clip`, `stat`, `cta`; ghép video 40–45 giây ở hai tỷ lệ rồi mở rộng tám layout/ba preset |

Cảnh thử đạt khi thay được nội dung từ JSON, chữ tiếng Việt hiển thị đúng, clip không méo/che nội dung chính và preview khớp đầu ra về bố cục, thời điểm hiển thị. Ghi lại JSON, media và kết quả dùng để đối chiếu.

`stat` cần Định/AI–BE cung cấp giá trị, nhãn và fact refs trước khi hoàn thành bản thử bốn layout. Nếu chưa có, báo thiếu và thống nhất với Vũ trước khi đổi layout.

Hưng phụ trách cấu trúc dữ liệu, preview và `feature_clip`, `steps`, `before_after`, `highlight_zoom`; Vũ phụ trách hướng thiết kế và bốn layout còn lại theo #15. Lịch bàn giao chốt sau khi rõ đầu vào; chưa xác nhận mốc 28/10.

## 7. Kiểm tra mẫu

Chạy ở root repo BE, cần Git và Python/uv:

```powershell
python -m uv run --no-project --with jsonschema==4.26.0 python docs/specs/examples/web-template-data/validate.py
```

Script kiểm schema M2, hash nguồn, scene/segment mapping và title binding. Cần có Git object của hai commit đã ghim; nếu thiếu, fetch nhánh PR #83/#78. Kiểm tra này xác nhận dữ liệu mẫu nhất quán, chưa kiểm chất lượng template hay render tích hợp.
