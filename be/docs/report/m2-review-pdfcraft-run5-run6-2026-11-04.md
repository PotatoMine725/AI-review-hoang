# Review M2 PDFCraft run5/run6 — 04/11/2026

Định (@VoHoangDinh) review snapshot [worker 8bab0ed](https://github.com/PotatoMine725/AI-review-BE/commit/8bab0ed), contract sinh kịch bản `73f4df9`. Input là dữ liệu thử PDFCraft, trạng thái approved mô phỏng; không đại diện khách hàng xác nhận hoặc AISoEasy. Đọc JSON script/input qua GitHub API, không sửa output gốc và không chạy lại LLM/audio/render.

Nguồn: [báo cáo Hoàng ở #92](https://github.com/PotatoMine725/AI-review-BE/pull/92#issuecomment-6620274186); [run5](https://github.com/PotatoMine725/AI-review-BE/blob/8bab0ed/docs/report/m2-first-run-pdfcraft/run5-2026-11-04/script.json), [run6](https://github.com/PotatoMine725/AI-review-BE/blob/8bab0ed/docs/report/m2-first-run-pdfcraft/run6-2026-11-04/script.json), [input](https://github.com/PotatoMine725/AI-review-BE/blob/8bab0ed/docs/report/m2-first-run-pdfcraft/input.json).

## Run5: qua validator không đồng nghĩa nội dung đã duyệt

| Vị trí | Kết quả đối chiếu | Cách xử lý đề xuất |
| --- | --- | --- |
| hook + s01-u01 | Câu hỏi có cả xử lý trên trình duyệt và không đăng ký, nhưng hook.fact_refs chỉ có features[1].description về không đăng ký/phí ẩn | Cần thêm fact cho mệnh đề xử lý trong trình duyệt, ví dụ features[2] với cách quy nguồn phù hợp |
| s01-u02 | Lời đọc “ngay trong thiết bị” nhưng claim trỏ tagline chỉ nói miễn phí/riêng tư/trong trình duyệt | Dẫn features[2] và quy nguồn PDFCraft tự công bố; không coi tagline chứng minh tệp không rời thiết bị |
| s02-u01 + visual | Lời ghép tệp/kéo thả có fact features[0], nhưng asset là pdfcraft-pagenum | Phân ý/cảnh với đúng tư liệu; tên ID/purpose gợi ra lệch hình, cần xem clip thật trước kết luận hình đã khớp |
| s02-u02 | Câu có đánh số trang và xuất Word; claim hiện chỉ dẫn features[3] về đánh số trang | Thêm claim/ref features[4] cho Word hoặc bỏ ý Word; dùng clip export phù hợp |
| s03-u01 | Quy nguồn “PDFCraft công bố” và features[2] phù hợp tuyên bố xử lý trong trình duyệt/tệp không rời thiết bị | Có thể giữ nội dung; clip word-export không trực tiếp chứng minh bảo mật/cục bộ, tránh trình bày như một phép chứng minh đã đo |
| Hook và CTA | Hook trùng segment đầu, cuối role cta có lời đọc cta.text, destination null | Phần mapping lời đọc có tiến triển, giữ validator hiện tại |

Input đã có cách ghép ở features[5] và giới hạn 100 tệp/500 MB ở limitations[0], nhưng run5 chưa dùng các ý này. Có thể diễn giải các ý có căn cứ nếu phù hợp hướng kể/tư liệu để bổ sung nội dung. Không bắt buộc dùng mọi fact hoặc nhồi đủ thời lượng.

## Run6: lỗi đường dẫn và thiếu căn cứ theo từng ý

- s03 claim tham chiếu `free_plan.value` không tồn tại; input có `pricing.free_plan.value = true`. Validator từ chối là đúng; không sửa output thô rồi ghi model đã đạt.
- s01 claim dùng features[0] (miễn phí cho công cụ hợp nhất) để diễn đạt miễn phí cho công cụ nói chung. Dùng đúng fact pricing.free_plan và kiểm phạm vi, không tự mở rộng usage.
- s02-u02 vừa có Word vừa có “dễ dàng”, trong khi claim chỉ dẫn hợp nhất và đánh số trang. features[4] hỗ trợ Word chỉnh sửa được, chưa hỗ trợ đánh giá dễ dùng. Bổ sung ref theo nghĩa và bỏ đánh giá nếu thiếu nguồn.
- s03-u01 “hoàn toàn miễn phí” **có trong evidence của pricing.free_plan** (“Hoàn toàn Miễn phí”). Không kết luận riêng từ “hoàn toàn” là bịa; vấn đề là ref sai và cần giữ đúng phạm vi. Các câu “không giới hạn” không được suy ra từ fact free khi vẫn có limitations.
- Hook/CTA được đọc đúng cấu trúc theo JSON, nhưng run6 chưa qua validator và không đủ điều kiện bàn giao dựng như output hợp lệ.

## Thời lượng và dữ liệu số

Theo số đo Hoàng báo: run5 có 97 âm tiết, estimate 25,9 giây; audio 26,64 giây, MP4 27,933 giây ở hai tỷ lệ. Vẫn dưới mục tiêu 40–45 giây. Review này không tái đo các file media. Hai lần chạy là mẫu nhỏ, chưa đủ kết luận tính ổn định hoặc hiệu quả toàn bộ prompt. Không có claim số liệu marketing nên chưa kiểm chứng được stat_display ở hai output này.

## CTA: phản hồi contract cho câu hỏi ở #92

Không chấp thuận tự lấy identity.website làm URL/domain của cảnh CTA khi cta.destination null. Cấu hình nguồn/địa chỉ Product không tự thành lời kêu gọi truy cập được xác nhận. Theo quy tắc M2 hiện có, chỉ cta.text được phản ánh, renderer không tự bổ sung destination/tracking. Đề xuất Hoàng bỏ fallback trình bày URL ở mapping #97 hoặc để lead chốt một yêu cầu hiển thị riêng trước khi bật. Đây là đề xuất của chủ contract M2, không phải thay đổi code renderer hoặc tuyên bố lead đã duyệt.

Phân biệt URL được mapping tự thêm vào CTA với URL tự nhiên nhìn thấy trong footage trang web. Loại sau cần QA kiểm theo ngữ cảnh/clip; không dùng quy tắc metadata để giả định mọi địa chỉ trong hình đều sai.

## Phần Định cập nhật sau review

Prompt bổ sung tự lập/rà ý → fact → asset, kiểm đủ từng mệnh đề, đường dẫn/kiểu fact thực tế và không dùng asset cho thao tác khác chỉ vì cùng Product. Hướng dẫn bổ sung cách dùng/giới hạn có căn cứ để tăng độ đầy đủ, giữ mốc âm tiết tham khảo. README làm rõ CTA null ở cả metadata và trình bày.

Không thêm schema field, luật đếm từ cứng hoặc regex “chặn nghĩa”. Validator hiện vẫn kiểm cấu trúc/refs và hook/CTA; sai nghĩa cần review riêng. Không tự sửa input, worker, script của Khánh hoặc output thô. Hoàng đồng bộ commit prompt mới và chạy lại khi sẵn sàng; ghi riêng validator, review nghĩa, phần chỉnh tay, usage và duration thật. Chưa kiểm tác động của prompt mới bằng lời gọi LLM.
