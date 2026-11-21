# P1-AC-03 — bộ ca kiểm thử đề xuất

**Trạng thái:** kế hoạch kiểm thử. Các ca contract có fixture được chạy bởi `spikes/m1-crawl-extract/validate_contracts.py`; ca LLM/TTS/renderer chờ tích hợp và bàn giao adapter.

| ID | Ca kiểm thử | Kết quả mong đợi | Trạng thái |
|---|---|---|---|
| M2-AC03-01 | Product + PKB approved đúng version, tư liệu trong allowlist, content context hợp lệ nếu có | Input pass; output có concept, hook, cảnh, câu thoại theo segment, phụ đề, visual plan và CTA | Đã có fixture/validator |
| M2-AC03-02 | Lời thoại/phụ đề có tiếng Việt dấu, emoji và dấu câu Unicode | JSON parse/serialize giữ nguyên Unicode; không mất dấu | Chờ implement |
| M2-AC03-03 | Thiếu `product_id`, `knowledge_version`, hoặc PKB chưa approved | Từ chối trước khi gọi LLM; không sinh/lưu script | Chờ input validation |
| M2-AC03-04 | Claim thiếu `fact_refs` | Output không hợp lệ; không persist. Fixture thiếu refs đang được kiểm | Đã có fixture/validator |
| M2-AC03-05 | Fact ref sai `source_id`, cú pháp/đường dẫn không tồn tại, trỏ fact null, `inferred` hoặc conflict chưa xử lý | Fixture validator từ chối đúng bằng lỗi conflict cho đường dẫn trùng/cha/con, hỗ trợ `field_path`/`field`/`path`, so theo ranh giới key/index; sibling, index khác và fact không liên quan vẫn pass. Runtime phải lặp lại kiểm tra trên đúng `schema_version` + `knowledge_version` | Fixture validator; bản runtime ở PR #92 cần đồng bộ sau thay đổi contract |
| M2-AC03-06 | Asset không nằm trong allowlist hoặc thuộc Product khác | Output bị từ chối; BE không resolve/tải/render asset ngoài Product và allowlist | Đã có fixture/validator |
| M2-AC03-07 | PKB mâu thuẫn hoặc thiếu thông tin giá/tính năng | Không tự chọn một giá trị, không tự tính giá, không bịa claim; yêu cầu bỏ claim hoặc cần review | Chờ semantic QA |
| M2-AC03-08 | Nội dung PKB chứa chỉ thị kiểu prompt injection | Chỉ thị trong dữ liệu bị bỏ qua; vẫn tuân system prompt và allowlist | Chờ LLM integration |
| M2-AC03-09 | LLM trả rỗng, JSON hỏng, sai schema hoặc thiếu trường | Fail rõ ràng, không persist; retry có giới hạn nếu chính sách provider cho phép | Chờ quyết định retry |
| M2-AC03-10 | LLM timeout, quota hoặc provider lỗi | Trả lỗi có thể phân loại, không tạo script giả/fixture như kết quả thật; retry/quota behavior cần chốt | Chờ LLM adapter |
| M2-AC03-11 | Script hợp lệ gửi sang TTS | Gửi từng `segment_id` theo thứ tự; giữ riêng lời thoại hiển thị và văn bản normalize; nhận audio + duration đo thật cùng ID | Chờ kiểm thử adapter/integration |
| M2-AC03-12 | Timeline dựng video | Ghép segment theo thứ tự; khoảng nghỉ 0,15 giây chỉ là cấu hình thử, không thêm sau segment cuối; xử lý transition overlap một lần; MP4 cuối không mất câu/lệch phụ đề và đạt 30–40 giây | Chờ kiểm thử BE/TTS/renderer; hai vòng sửa vẫn là đề xuất |
| M2-AC03-13 | Một script được renderer xuất 9:16 và 16:9 | Kịch bản dùng chung; tỉ lệ và layout do renderer quyết định | Chờ tích hợp renderer |
| M2-AC03-14 | Regression các ví dụ `script.v0` hiện có | Ví dụ cũ vẫn pass/fail như trước; contract draft tiếng Việt không đổi hành vi v0 | Đã chạy validator chung |
| M2-AC03-15 | Không có Campaign/Affiliate hoặc không truyền content context | Input vẫn hợp lệ; output ghi rõ mặc định platform/intent/audience/CTA, CTA trung tính và destination null | Đã có validator |
| M2-AC03-16 | Visual là ảnh AI cần sinh | Ghi generation request riêng, không giả thành asset đã lưu/được cấp quyền; provenance được bổ sung sau khi tạo thật | Fixture/schema; adapter chờ tích hợp |
| M2-AC03-17 | User cung cấp CTA text và destination | Output giữ nguyên text và destination; nếu thiếu CTA thì không tự tạo ưu đãi/claim/link | Đã có validator cho CTA được cung cấp |
| M2-AC03-18 | Claim trong cảnh không trỏ tới lời thoại tương ứng | Từ chối claim nếu `segment_ids` rỗng hoặc không thuộc cảnh đó | Đã có validator |
| M2-AC03-19 | Output tham chiếu PKB schema/knowledge version khác input hoặc người dùng xác nhận | Từ chối; không tự nâng PKB 0.2 lên 0.3 | Fixture validator |
| M2-AC03-20 | Fact do owner nhập không có crawl `source_id` | Cho phép tham chiếu bằng `field_path`; không tạo `source_id` giả. Nếu `source_id` được gửi thì phải khớp fact | Fixture validator |
| M2-AC03-21 | `text_card` hiển thị nội dung do renderer dựng | Dùng `kind=text_card`, `source_type=generated_text`, có `text`, không có `asset_id`; claim sản phẩm vẫn cần fact refs | Fixture/schema validator |
| M2-AC03-22 | Một cảnh chứa nhiều narration segments | Contract cho phép; giữ ID/thứ tự. Duration và đồng bộ được xác nhận bằng TTS/renderer thật | Fixture validator; tích hợp chờ |
| M2-AC03-23 | Output chỉ có một cảnh | Schema M2 chấp nhận; không ép thêm cảnh để thỏa giới hạn tạm của renderer | Fixture validator; renderer thử ở #80 |
| M2-AC03-24 | Cảnh dùng claim có fact `origin=inferred` chưa được duyệt hoặc field đang conflict | Không cho dùng làm claim trong kịch bản | Fixture validator; semantic/runtime QA cần thêm |
| M2-AC03-25 | Output có 12 cảnh | Schema và fixture validator chấp nhận giới hạn kỹ thuật; không yêu cầu tạo đủ 12 cảnh | Fixture validator |
| M2-AC03-26 | Output có 13 cảnh | Schema từ chối vượt giới hạn kỹ thuật 12 cảnh | Fixture validator |
| M2-AC03-27 | `target_duration_s` bằng 39 giây | Contract từ chối target dưới 40 giây | Schema/validator contract |
| M2-AC03-28 | `target_duration_s` bằng 40 giây | Contract chấp nhận biên dưới | Schema/validator contract; không đo MP4 |
| M2-AC03-29 | `target_duration_s` bằng 45 giây | Contract chấp nhận biên trên | Schema/validator contract; không đo MP4 |
| M2-AC03-30 | `target_duration_s` bằng 46 giây | Contract từ chối target trên 45 giây | Schema/validator contract |
| M2-AC03-31 | `estimated_duration_s` được worker tính từ tổng âm tiết / tốc độ cấu hình | Ghi nhãn ước tính; không thay `target_duration_s`, duration TTS hoặc thời lượng MP4 | Chờ bước hậu xử lý trong worker |
| M2-AC03-32 | JSON thô từ LLM không có `estimated_duration_s` | Chấp nhận response thô; worker bổ sung estimate trước khi trả `ScriptResult` hoàn chỉnh | Chờ tích hợp `generate_script` |
| M2-AC03-33 | Ước tính lời thoại nằm trong 30–40 giây nhưng MP4 thực tế ngoài khoảng | Không nghiệm thu theo estimate; yêu cầu đánh giá timeline/audio và MP4 đo thật | Chờ tích hợp TTS/renderer |
| M2-AC03-34 | LLM trả `schema_version`, `product_id`, `pkb_schema_version` hoặc `knowledge_version` sai với contract/input | Từ chối output; không tự sửa hoặc suy ra ID/version từ nội dung PKB | Schema/validator fixture |
| M2-AC03-35 | CTA tự lấy URL từ `identity.website`, hoặc `cta.fact_refs` sai đường dẫn/nguồn | Không có destination do người dùng cung cấp thì destination phải null; nếu CTA có fact refs thì từng ref phải hợp lệ như claim ref | Fixture validator; lần chạy #92 đã tái hiện model tự điền destination |
| M2-AC03-36 | Lời thoại ngắn hơn mốc thử 115–150 âm tiết | Bổ sung thao tác/giới hạn có căn cứ khi phù hợp. Đo thời lượng trên audio/MP4 thực tế | Prompt; cần hiệu chỉnh bằng TTS thật |
| M2-AC03-37 | Visual plan yêu cầu ảnh AI mới sinh | Dùng `kind=ai_generated_image`, `source_type=ai_generation`, `generation_request`; không giả `asset_id` đã tồn tại | Schema/fixture validator |
| M2-AC03-38 | Asset clip nằm trong allowlist nhưng `visual_plan.kind` là `logo` | Từ chối sai loại tư liệu và báo cảnh/asset/loại cần dùng | Fixture validator, đối chiếu run7/run8 |

## Điều kiện nghiệm thu đề xuất

- Bổ sung 03/11: hook khác segment đầu bị từ chối; không có role cta cuối hoặc CTA không được đọc bị từ chối; khác biệt khoảng trắng được chấp nhận. Các fixture 1/12 cảnh giữ mapping hook/CTA hợp lệ; 13 cảnh vẫn bị từ chối. Stat đủ bốn trường qua schema, thiếu value/label/unit/scope bị từ chối; đây chỉ là ca cấu trúc tổng hợp, không xác nhận claim fixture có số đó trong nguồn.
- QA sau khi đồng bộ #92: chạy prompt mới, giữ output thô, kiểm hook/CTA được đọc, claim trên hình và các từ đánh giá có nguồn; báo phần chỉnh tay, usage, ước tính âm tiết và audio/MP4 thật nếu đã ghép. Không thêm hard gate về số âm tiết/segment hay ngưỡng footage từ demo. Chưa có lần chạy LLM thật với bản cập nhật này.

- Bổ sung validator fixture theo #94: mô tả video vắng mặt, 1 ký tự và 2000 ký tự hợp lệ; 2001 ký tự, rỗng, toàn khoảng trắng hoặc sai kiểu bị từ chối. Tham chiếu `content_context.video_description` như fact PKB bị từ chối.
- QA tích hợp cần kiểm riêng: mô tả định hướng đúng giọng điệu/trọng tâm; không ghi đè CTA/audience đã xác nhận; chữ như “nhanh nhất” hoặc số mới không thành claim; yêu cầu mâu thuẫn được hỏi lại trước M2. Fixture không chứng minh LLM tuân thủ các quy tắc ngữ nghĩa này.

- Input chỉ nhận Product và PKB đã approved đúng version, cùng allowlist tư liệu thuộc Product. Content context độc lập là tùy chọn; quyền tư liệu do người dùng/nhóm xác nhận, không suy ra từ allowlist schema.
- Mọi claim về sản phẩm trỏ đúng fact trong cặp PKB `schema_version` + `knowledge_version` đã được người dùng xác nhận; `source_id` tùy chọn với fact owner và khi có thì phải khớp fact.
- Kịch bản được sinh bằng LLM thật, bằng tiếng Việt, có `target_duration_s` trong khoảng 30–40 giây. `estimated_duration_s` được tính riêng từ lời thoại và gắn nhãn ước tính; chỉ nghiệm thu thời lượng trên MP4 cuối, gồm hook, nội dung, CTA, khoảng nghỉ và chuyển cảnh.
- TTS/renderer tích hợp bằng contract đã được hai bên thống nhất; renderer chịu trách nhiệm tính timeline audio thật, xuất 9:16 và 16:9, và xác nhận MP4 cuối. Ca contract chỉ kiểm tra giá trị target; không được báo như bằng chứng MP4 đạt thời lượng.
- Kết quả schema/fixture được báo riêng, không đại diện cho kiểm tra ownership/quyền/resolve asset phía BE hoặc tích hợp LLM/TTS/renderer.
- Lỗi provider hoặc validation không lưu kịch bản chưa hợp lệ.
