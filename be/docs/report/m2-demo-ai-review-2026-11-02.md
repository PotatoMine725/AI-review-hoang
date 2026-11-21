# Review AI repo demo cho M2 — issue #94

Ngày: 02/11/2026. Phạm vi của Định (@VoHoangDinh): review contract, provenance và ánh xạ kịch bản; đề xuất phần AI có thể tận dụng. Đây là kết quả đọc mã nguồn, chưa phải kiểm tích hợp hoặc nghiệm thu video.

## Nguồn đối chiếu

- [Phân công của lead trong #94](https://github.com/PotatoMine725/AI-review-BE/issues/94#issuecomment-6558975675) và [đề xuất phối hợp của Hoàng](https://github.com/PotatoMine725/AI-review-BE/issues/94#issuecomment-6565991551).
- Repo demo ghim tại `97290bd7650478a3897706354094b700c08b7cb3` (29/10), không kết luận về các commit sau snapshot này.
- Contract M2 [PR #83](https://github.com/PotatoMine725/AI-review-BE/pull/83), head đọc qua GitHub API: `609d93de0e0b1a1c595b9116000648506e443322`.
- Đọc trực tiếp input/output schema, README M2 và `validate_p1_vi_script_content` trong `spikes/m1-crawl-extract/validate_contracts.py` ở commit trên.

## Kết luận để chọn phần làm trước

Tận dụng ý tưởng proof bank để bổ sung kiểm tra số theo từng fact được tham chiếu; tận dụng phần chấm điểm của Copy Critic làm báo cáo tư vấn sau sinh kịch bản. Giữ contract M2 làm nguồn chuẩn. Brief/outline dùng để định hướng nội dung từ mô tả người dùng, với bước xác nhận riêng cho thông tin sản phẩm mới.

Chưa có căn cứ nói proof bank demo chứng minh đúng nghĩa một claim chỉ vì số xuất hiện trong tập nguồn. Không đưa nguyên cơ chế tự sửa cảnh hoặc ngưỡng điểm 7 của critic thành điều kiện chặn P1. Các phần dưới là đề xuất review để Định–Hoàng thống nhất trước khi sửa contract/worker.

## 1. Proof bank: dùng được ý tưởng, cần thu hẹp phạm vi kiểm tra

Nguồn: [script/proof.py](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/services/api/app/script/proof.py).

`build_proof_bank(profile, pages, inventory, brief)` thu số, quote, offer từ profile, trang, frame và brief. `unsupported_numbers(text, proof, inventory, extra, benefit_only)` trả danh sách số không nằm trong tập cho phép. Mã có chuẩn hóa số dạng `1,000`/`1.000`, phân loại `benefit`/`identifier`/`other`.

Các giới hạn đọc được từ code:

- `supported_values` trả tập **giá trị số**; `unsupported_numbers` bỏ qua đơn vị khi so khớp. Một số đúng giá trị nhưng sai nhãn/đơn vị/phạm vi vẫn có thể được chấp nhận. Ví dụ suy luận từ code: nguồn có `40% reduction in hiring time`, câu viết `40 giờ` vẫn có cùng khóa số `40`.
- Tập nguồn được gộp toàn cục, chưa buộc số của câu phải thuộc đúng fact mà câu tham chiếu. Số ở frame hoặc trang khác không tự chứng minh claim đang dùng.
- `proof_used` có thể trả đúng chỉ vì trùng một số hoặc một cụm bốn từ; không đủ làm bằng chứng về nghĩa.
- `_add_user_facts` nhận proof points, main benefit và offer từ brief thành proof. Với P1, mong muốn trình bày của người dùng phải tách khỏi fact đã xác nhận.
- `strip_numbers` sửa trực tiếp văn bản. Không dùng cơ chế này để sửa âm thầm output rồi báo LLM sinh đạt.

Đề xuất cho M2: kiểm từng hook/claim/CTA có số với đúng tập `fact_refs` của nó trong PKB đã xác nhận, giữ `source_id`, `field_path`, `knowledge_version`, đơn vị, nhãn và điều kiện áp dụng. Scan cả narration, subtitle, text trên hình và `stat_display`; phần chưa gắn được claim cần review. Không dùng regex làm kết luận đúng nghĩa cho mọi cách viết số tiếng Việt, số viết bằng chữ hoặc diễn đạt như `2.58M+`.

Validator hiện có của #83 kiểm đường dẫn fact, nguồn, conflict cha/con, segment liên quan và asset allowlist. Những kiểm tra này không chứng minh toàn bộ lời thoại đúng nghĩa. Bước bổ sung nên báo vị trí và lý do cần review trước; hard gate mới cần thống nhất với Hoàng/QA. Không mở rộng PKB v0.3 chỉ để copy `ProofBank`.

## 2. Copy Critic: lấy bước chấm điểm, giữ revision đã duyệt

Nguồn: [script/critic.py](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/services/api/app/script/critic.py), [prompt](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/services/api/app/llm/prompts/copy_critic.md).

`score(caller, ctx, script)` chấm năm tiêu chí: hook, lợi ích, dùng bằng chứng, CTA và mạch kể; trả scores/reasons, weak scenes, issues, summary. `proof_usage` thành null khi proof rỗng. `compact_script` gửi lời thoại, chữ trên hình, stat và chapter cho model; không phải cấu trúc M2 có fact refs hiện tại.

`critique_and_repair` còn chọn hook và viết lại tối đa hai vòng, tối đa ba cảnh mỗi vòng; có thể giữ bản sửa dựa trên tổng điểm. Không port luồng này trong lượt đầu. Model `Score` của demo khai báo int nullable, chưa có ràng buộc 0–10 bằng Pydantic dù prompt yêu cầu thang đó.

Đề xuất tích hợp cho Hoàng ở #92:

1. Chạy validator hiện tại trước; critic chỉ nhận script hợp lệ về cấu trúc và đúng snapshot PKB/asset.
2. Gọi một lượt chấm qua adapter Gemini hiện có; gửi mô tả người dùng đã xác nhận, script, claim/fact refs và bằng chứng tương ứng. Nội dung nguồn là dữ liệu; không thực thi chỉ dẫn trong đó.
3. Lưu báo cáo phụ gắn với script revision và product/knowledge version; không chèn field ngoài schema vào JSON M2. Kiểm điểm trong 0–10, scene IDs có thật, dữ liệu trả về hợp lệ.
4. Ghi usage/cost và trạng thái lỗi. Critic lỗi hoặc điểm thấp trả trạng thái review, không tự xác nhận hoặc tự sửa kịch bản. Mọi sửa được chấp nhận tạo revision mới và chạy lại validator.

Điểm critic là nhận xét của model, không thay thế QA về fact, quyền tư liệu, chất lượng audio hoặc thời lượng MP4.

## 3. Brief và outline: phần hợp đồng thuộc Định

Nguồn: [marketing_brief schema](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/packages/script-schema/schemas/marketing_brief.json), [brief_suggest.py](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/services/api/app/proposal/brief_suggest.py), [flow_outline.py](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/services/api/app/proposal/flow_outline.py).

Demo có audience, lợi ích chính/phụ, proof points, offer, CTA, tone, avoid. Gợi ý brief lỗi có fallback chung như “Dùng thử miễn phí”; không thể coi gợi ý đó là fact của AISoEasy. `flow_outline` dựng hook → chapter beats → CTA từ flow đã duyệt, có thể dùng lại ý tưởng tổ chức nội dung. Ước tính 30/45/60 giây và số cảnh của demo không thay mục tiêu P1 40–45 giây và 1–12 cảnh.

| Ý định đầu vào | Contract #83 hiện có | Đề xuất cần thống nhất |
| --- | --- | --- |
| Đối tượng xem | `content_context.audience` | Dùng trường sẵn có, giữ mô tả gốc để truy vết |
| Mục tiêu truyền thông | `content_context.intent` | Chỉ ánh xạ khi người dùng xác nhận; không tự đoán thành fact |
| Điều tránh nói | `forbidden_claims` | Giữ yêu cầu người dùng và các giới hạn nguồn |
| CTA text/destination | `content_context.cta` | Không tự bổ sung URL; giữ luật fact refs của CTA |
| Mô tả tự do, tone, lợi ích muốn nhấn mạnh | Chưa có trường tương ứng đầy đủ | Đề xuất một trường mô tả gốc trong content context; độ dài/tên field và prompt chờ đồng thuận #83/#92 |
| Số liệu hoặc ưu đãi mới người dùng nhập | Không phải fact chỉ nhờ có `approved_claims` | Đối chiếu và xác nhận vào PKB trước; chỉ dùng loại fact mà schema hiện hành hỗ trợ |
| Chọn hướng/dàn ý | Output hiện có `concept`; chưa có contract outline riêng | Trước hết trình bày hướng/beat để review; giữ tham chiếu fact, chưa tạo contract demo thứ hai |

Schema input hiện có `additionalProperties: false`; không thể gửi thêm raw description/tone bằng cách tự ý thêm field. Báo cáo này chưa sửa schema hoặc worker. Điểm trên là đề xuất bàn giao contract của Định để Hoàng đối chiếu trước khi cập nhật đồng bộ.

## 4. Ánh xạ script demo sang M2

Nguồn: [script.json](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/packages/script-schema/schemas/script.json), [scene.json](https://github.com/tranquangthong03/ai-video-content/blob/97290bd7650478a3897706354094b700c08b7cb3/packages/script-schema/schemas/scene.json) và schema M2 ở commit đã ghim.

| Demo | Đích M2 | Điều kiện / khoảng trống |
| --- | --- | --- |
| `title`, headline | `concept.title`, hook hoặc chữ hiển thị | Chọn theo nghĩa, không copy cả headline thành claim chưa có fact |
| `goal: tutorial` | Có thể là `intent: education`, angle tutorial | Ánh xạ đề xuất; awareness/conversion tương ứng trực tiếp, recruitment cần người dùng chọn intent phù hợp |
| `scenes[].id` | `scene_id` dạng `s01` | Lập bảng ID cũ→mới ổn định; giữ thứ tự và cập nhật mọi liên kết |
| `type: hook / feature_demo / cta` | `role: hook / demo / cta` | Vai trò nội dung; không đem layout demo vào role |
| `type: before_after` | Có thể tách problem/result hoặc scene result | Contract hiện tại không có payload before/after; cần review hai trạng thái và fact, không chỉ đổi enum |
| `voiceover` | `narration_segments[].text` | Chia câu với ID `s01-u01`; giữ lời, kiểm claim cho từng segment |
| `on_screen_text` | Subtitle hoặc `visual_plan.text` khi text card | Subtitle theo lời; không gộp hai mục đích thành một trường. Claim trên hình cũng phải có căn cứ |
| `stat.value/label` | `claims[].stat_display` | Bổ sung unit/scope và fact refs đã kiểm; không thể chuyển hợp lệ chỉ bằng đổi tên key |
| `visual.mode: recording / screenshot` | `visual_plan.kind`, `existing_asset`, `asset_id` | Chỉ sau khi có file, quyền sử dụng, đúng Product và allowlist. Actions/page chưa phải asset |
| `visual.mode: template` | Có thể text_card/generated_text | Chỉ khi nội dung phù hợp; layout/zoom do renderer phụ trách |
| `chapter_id`, feature | Metadata truy vết chapter/clip bên ngoài script M2 | Không có field chapter_id trong output M2; không coi chapter ID là field_path PKB |
| `duration_ms` | Số đo/ước tính phụ trợ | Không đổi thành duration nghiệm thu. Ghép TTS theo segment_id, timeline dùng audio đo thật |
| aspect_ratio, template, capture, theme | Cấu hình downstream | M2 hiện không chứa chúng; kiểm cả 16:9 và 9:16 theo phạm vi P1 |

Demo schema scene không có `footage` top-level; phải phân biệt trường `visual` của scene với kết quả recorder/producer. Định có thể chuẩn bị bảng ánh xạ này ngay; Thông xác nhận artifact thực tế ở bước bàn giao. Không gắn source_id hoặc fact_refs giả khi scene demo chưa có provenance tương ứng.

## 5. Bàn giao và phần còn phụ thuộc

| Người/phần | Đầu ra đề xuất | Phụ thuộc |
| --- | --- | --- |
| Định — review M2 (#83) | Báo cáo này; thống nhất mapping và đề xuất trường mô tả với Hoàng | Phản hồi contract trước khi cập nhật worker |
| Hoàng — AI worker (#90/#92) | Đánh giá kiểm số theo fact; đề xuất critic một lượt và báo cáo phụ có version | Contract thống nhất, PKB đã kiểm/xác nhận |
| Thông — repo demo/automation | Clip + focus log + steps, thành công/thất bại; định dạng và điều kiện chạy thực tế | Phạm vi public/login và quyền tài khoản được cấp |
| BE/FE/QA | Asset IDs/quyền, lưu revision, UI review, kiểm nội dung và video | Bàn giao clip, contract và script revision đã xác nhận |

Danh sách tối thiểu cần nhận từ Thông: commit/run ID, product URL, bước đã quay, clip time range, chapter/scene liên quan, kích thước khung, đơn vị thời gian/toạ độ focus, điều kiện login, quyền sử dụng và lỗi còn lại. Đây là yêu cầu dữ liệu phục vụ review, chưa phải xác nhận định dạng focus log hiện có. Không lưu credential/session trong báo cáo hoặc Git.

Lượt đầu kiểm trên một video AISoEasy: input và PKB version đã xác nhận → script có fact/asset refs → critic advisory → người duyệt chốt revision → VieNeu đã bàn giao (#73) → audio theo segment_id → template/timeline → MP4 đo thật 40–45 giây, review ngang trước rồi dọc. Giữ output LLM thô, báo cáo lỗi và bản chỉnh tay riêng. Chưa có số đo hoặc video mới từ review này; không dùng benchmark PDFCraft #95 làm bằng chứng AISoEasy đã đạt.

## Kiểm tra báo cáo

Đã đối chiếu code nguồn ghim và contract head qua GitHub API; các ví dụ giới hạn proof bank là suy luận từ nhánh so sánh giá trị trong code, chưa chạy demo. Không gọi LLM, không chạy automation/recorder, không thay contract/worker/BE/FE. Edit Planner/EditOp để lượt sau theo đề xuất đã ghi ở #94. Review này hoàn tất phần phân tích và bảng ánh xạ; việc trao đổi chốt với Hoàng/Thông và tích hợp/video vẫn còn phụ thuộc bàn giao.
