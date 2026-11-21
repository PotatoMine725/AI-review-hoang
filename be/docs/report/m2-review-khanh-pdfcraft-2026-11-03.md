# Review M2: bản PDFCraft Khánh chỉnh tay — 03/11/2026

Người review: Định (@VoHoangDinh), phạm vi contract/nội dung M2. Kết quả: **chưa qua validator nội dung của contract 73f4df9**. Không thay đổi file gốc, không xác nhận thời lượng hoặc chất lượng clip.

## Snapshot và cách kiểm

- [Bàn giao của Khánh trong #92](https://github.com/PotatoMine725/AI-review-BE/pull/92#issuecomment-6596681163).
- Script: [script.khanh-edited.json tại cd87819](https://github.com/PotatoMine725/AI-review-BE/blob/cd87819/docs/report/m2-first-run-pdfcraft/run3-2026-10-30/script.khanh-edited.json).
- SHA256 byte file script: `12bfb905ac9433e3b735e8090f3da19d9bd9e257b0461bb048986f956537c036`.
- Input đối chiếu: [input.json tại 398d5ae](https://github.com/PotatoMine725/AI-review-BE/blob/398d5ae/docs/report/m2-first-run-pdfcraft/input.json). Đây là snapshot input worker, có trạng thái approved mô phỏng, không phải PKB khách hàng xác nhận.
- Contract/validator: [73f4df9, PR #83](https://github.com/PotatoMine725/AI-review-BE/commit/73f4df9cebc9e8ce74d6b25b79c6af182b92d3dd). Dùng output JSON Schema và `validate_p1_vi_script_content(script, context)` với approved_pkb/product/version/permitted_assets từ input trên. Validator fixture hiện yêu cầu pkb_file; khi gọi trực tiếp đã cung cấp file fixture sẵn có chỉ để đáp ứng thao tác load ban đầu, còn approved_pkb truyền tường minh là PDFCraft, không lấy fact ElevenLabs làm căn cứ.

## Kết quả thực thi

| Kiểm tra | Kết quả |
| --- | --- |
| JSON Schema output | Không có lỗi |
| Validator nội dung, script gốc | `hook.text phải được đọc trong segment đầu` |
| Chẩn đoán trong bộ nhớ: chỉ gán hook.text bằng nguyên câu s01-u01 | Không còn lỗi validator nội dung |
| Lời thoại | 150 token tách bằng khoảng trắng, không phải 150 từ ngôn ngữ học hoặc số âm tiết TTS đã đo |
| Target | 42 giây theo metadata; chưa đo audio/MP4 |

Bản chẩn đoán chỉ dùng xác định lỗi tiếp theo; không ghi thành script chỉnh sửa, không tính script gốc là đã đạt. Không gọi LLM, TTS, recorder hoặc renderer trong lượt review.

## Điểm cần tác giả bản chỉnh tay xem lại

1. **Hook lệch lời đọc.** Metadata: “Bạn đang cần gộp PDF, đánh số trang hay xuất sang Word?”; s01-u01: “Bạn cần gộp PDF, đánh số trang hay xuất sang Word? Cùng xem ba thao tác PDFCraft.”. Theo mapping mới, thống nhất hook với segment mở đầu. Có thể giữ hook hiện tại làm câu đầu và chuyển phần dẫn sang segment kế tiếp, hoặc cập nhật metadata theo câu thực sự đọc; tác giả chọn và cập nhật liên kết claim/segment nếu chia segment. Không nới validator chỉ để chấp nhận snapshot cũ.
2. **Stat hai đại lượng nhưng unit null.** s02 claim giới hạn có `value: "100 tệp / 500 MB"`, `unit: null`. Nguồn limitations[0] nêu rõ hai đại lượng `100 files` và `500MB`; null theo contract chỉ dùng khi fact không có đơn vị. Đề xuất hai claim/stat trỏ cùng fact: `value: "100", unit: "tệp", label: "Số tệp tối đa", scope: "Mỗi lượt ghép"` và `value: "500", unit: "MB", label: "Tổng dung lượng tối đa", scope: "Tổng các tệp trong một lượt ghép"`. Đây là đề xuất diễn giải để tác giả/QA chốt; schema hiện tại không tự kiểm được nghĩa của unit null.
3. **Đối chiếu UI/clip còn phụ thuộc tư liệu.** s03 nói clip chọn vị trí, bấm Apply rồi xem kết quả; s04 nêu Save & Export → Export as Word. Các fact features[3]/[4] chứng minh tính năng, chưa chứng minh tên nút/thao tác cụ thể. s05 nói “Đây là tệp Word sau khi xuất” và dùng word-result. Chưa xem các clip trong lượt review nên chưa xác nhận các mô tả đó đúng với hình. Hoàng/QA kiểm clip thật và quyền sử dụng trước ghép; không tự thêm source/fact mới từ mô tả asset.

## Các điểm đã đối chiếu được

- F8: s02 giữ tối đa 100 tệp và tổng 500 MB mỗi lượt, phù hợp limitations[0]. Câu “kiểm tra số lượng/dung lượng” là chỉ dẫn, không hứa kết quả mới.
- F9: s02 có bước Merge/tải kết quả, tham chiếu features[5]/src_10. Sắp xếp thứ tự được features[0] hỗ trợ.
- F2: s06 chỉ dùng “không cần đăng ký, không có phí ẩn”, có quy nguồn trang chủ; không đưa “không giới hạn” lên lời hoặc chữ. Input snapshot vẫn có cụm cũ trong evidence; đây là giới hạn input đã được nhóm thảo luận, không kết luận conflict đã giải quyết.
- Xuất Word: nội dung không hứa giữ nguyên định dạng. Hook và chữ mở đầu nêu ba tính năng, có ba claim tương ứng ở s01.
- Có bảy cảnh, cảnh s07 role cta đọc đúng `cta.text`, destination null. Không cần worker suy lời đọc CTA từ metadata cho snapshot này. Cấu trúc một scene nhiều segment ở s02 hợp lệ.
- Có đủ bốn asset IDs trong allowlist snapshot PDFCraft; điều này chỉ kiểm ID/Product trong dữ liệu thử, không xác nhận quyền hoặc file tồn tại trên máy chạy.
- Các fact refs hiện có qua kiểm đường dẫn, source và conflict trong input thử đã lọc. Không dùng kết quả này làm bằng chứng mọi câu diễn giải đúng nghĩa hoặc PKB chuẩn đã hết conflict.

## Bàn giao tiếp theo

Khánh là tác giả bản chỉnh tay: thống nhất lại hook và biểu diễn stat rồi cung cấp revision mới nếu đồng ý. Hoàng tiếp tục đồng bộ worker theo commit contract #83 mới và kiểm snapshot đã chỉnh trước TTS/render; kiểm rõ nội dung UI/clip và báo duration audio/MP4 thực tế. Định review lại contract và kết quả sau sửa. Không sửa nhánh Khánh, worker, timeline hoặc template trong lượt này; báo cáo này phục vụ review, không thay phần duyệt của QA và không phải output LLM sinh đạt.
