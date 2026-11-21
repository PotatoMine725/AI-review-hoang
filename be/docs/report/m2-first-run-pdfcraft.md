# M2 P1-AC-03 — chạy LLM thật với PDFCraft

Sáu lượt chạy: **12/11** (contract `8008cbf`, mục E ngay dưới; chuẩn bị `kind` + một lượt sửa), **11/11** (contract `29f868a`, mục D ngay dưới; yêu cầu giao ngày 10/11, chạy 11/11), **09/11** (contract `4c5b72b`, mục C; yêu cầu giao ngày 05/11, chạy 09/11), **04/11** (contract `73f4df9`, mục B), **30/10** (contract `609d93d`, mục A) và **29/10** (contract `8f86523`, lịch sử). Các lượt cũ giữ nguyên bên dưới; mỗi lượt đánh số riêng.

## Lần chạy 12/11/2026 (contract 8008cbf, chuẩn bị `kind` + một lượt sửa)

- **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định, Khánh; cần xác nhận của các bạn.
- **Code:** PR #92 (`feat/m2-generate-script`). Đồng bộ #83 `8008cbf` ở commit `c8fc3b6`: prompt sinh (blob `2487354` → `f222ad1`, thêm luật 12) và template sửa mới `p1-ac-03-script-vi-repair.prompt.md` (blob `a2f073d`), chép nguyên byte; SHA pin và `SOURCE.md` cập nhật. Schema, ví dụ, PKB và `validate_contracts.py` (`638f499`) giữ nguyên blob nên `validate.py` và parity không đổi (tôi không chạy lại script của Định vì blob không đổi). Orchestration ở `2ee3b48`: `kind.py` (chỉ điền/thay `visual_plan.kind` từ allowlist của đúng Product và `asset_id`; audit cũ → mới và hash allowlist; ID lạ, sai Product, thiếu `asset_id` thì ghi `error:*`, giữ nguyên cảnh và để validator báo; allowlist trùng ID hoặc kind ngoài enum là lỗi input, không gọi LLM), `repair.py` (feedback có nguồn, render template sửa), `generate_script` (sinh → chuẩn bị kind → validator → **tối đa 1 lời gọi sửa** → chuẩn bị kind → validator; không có vòng thứ hai). Không đổi luật validator. ruff, format, pyright xanh; 308 test pass.
- **Khi nào gọi lượt sửa:** còn lỗi schema/content, có `qa_feedback` do người/QA đưa vào, hoặc âm tiết ngoài 150–170 (khuyến nghị). Nếu lượt sửa chỉ do khuyến nghị âm tiết mà bản sửa hỏng thì giữ bản đầu đã qua kiểm và ghi cảnh báo. Lần này **không** đưa `qa_feedback` (worker không tự gán nhãn QA): feedback chỉ gồm lỗi validator và khuyến nghị âm tiết.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier, cùng `input.json` với run3–run10 (không `video_description`, CTA `destination: null`). Tổng $ giá niêm yết 0,013435 + 0,014363 = 0,027798 (trả thật $0).
- **Dữ liệu:** `run11-2026-11-12/`, `run12-2026-11-12/`: `initial.raw.json` (thô), `initial.prepared.json` (sau chuẩn bị kind), `initial.kind_audit.json`, `feedback.json`, `repair.raw.json`, `repair.prepared.json`, `repair.kind_audit.json`, `script.json` (kịch bản cuối; run12 là output thô của lượt sửa vì fail), `stages.json`, `validation.json`, `cost.json`. Run11 còn `produce/` (`render_report.json`, báo cáo của lần fail đầu, `assets.widened.json`).
- **PDFCraft vẫn là dữ liệu thử.** 2 mẫu, chưa kết luận chất lượng prompt.

> **Kết luận ngắn.**
> - **Qua validator: 1/2.** Run11 qua (bản thô đã qua, bản sau lượt sửa cũng qua). Run12 **không qua sau lượt sửa**: còn 1 lỗi `claim 'Xem thêm thông tin.' thiếu fact_refs` (cảnh CTA có claim không ref); lượt sửa lặp lại đúng lỗi này và không có lượt thứ hai.
> - **Chuẩn bị `kind` có tác dụng ở run12, là no-op ở run11.** Run12 thô khai `product_asset` cho `pdfcraft-merge` ở s01 (allowlist: `screen_recording`): worker thay và ghi audit, lỗi này biến mất. Run11 thô đã khai đúng cả 4 `kind` (`unchanged`). Lỗi `kind` của `pdfcraft-word-result` ở run9/run10 không lặp lại.
> - **Lượt sửa của run11 chỉ do khuyến nghị âm tiết** (111 < 150), không có lỗi validator. Kết quả: 111 → **133** âm tiết (vẫn dưới 150); bỏ “nhanh chóng” khỏi hook, thêm segment `s01-u03` và claim “Hoàn toàn Miễn phí” (có evidence). Lượt sửa của run12 chỉ khôi phục `kind` s01, nội dung còn nguyên, vẫn 100 âm tiết.
> - **Word có clip riêng, clip Word không ở CTA:** run11 có clip riêng (s03 + `pdfcraft-word-export`) nhưng clip `pdfcraft-word-result` **vẫn ở cảnh CTA** (s04). Run12 **không có clip Word**: ý Word đọc ở `s03-u02` trên clip đánh số trang (lời–hình lệch); CTA là `text_card`.
> - **`claims[].text` tiếng Việt: đạt 2/2, cả hai tầng** (giới hạn 100 tệp/500 MB đã bằng tiếng Việt).
> - **CTA đọc nguyên văn `cta.text`: đạt 2/2, cả hai tầng.**
> - **Từ đánh giá thiếu fact:** run11 thô có “nhanh chóng” (hook, `s01-u01`), “dễ dàng” (subtitle s02), “theo ý muốn” (`s02-u02`); sau sửa còn “dễ dàng”, “theo ý muốn”. Run12: không có trong danh sách kiểm. “mạnh mẽ”, “riêng tư” (claim s04 của run11) là chép từ `identity.tagline`; “hoàn toàn miễn phí” có evidence.
> - **MP4 run11 (16:9, preview): 36,433 s, `out_of_range` (`too_short`)**, `predicted_s` 36,433. Cần nới đoạn clip Word mới dựng được (xem E3). Run12 không dựng vì không qua validator.

### E1. Từng tầng

Tầng: **thô** → **sau chuẩn bị kind** → **feedback** → **bản sửa (thô)** → **bản sửa sau chuẩn bị kind** → **kết quả kiểm**. Đã chạy lại `schema_errors` + `content_errors` trên từng file để kiểm.

| | Run11 | Run12 |
|---|---|---|
| Thô: validator (chưa chuẩn bị) | **qua** | fail: `s01` kind phải là `screen_recording`; `claim 'Xem thêm thông tin.' thiếu fact_refs` |
| Audit kind (thô) | s01–s04 `unchanged` (4 cảnh `existing_asset`) | s01 `replaced` (`product_asset` → `screen_recording`); s02, s03 `unchanged` |
| Sau chuẩn bị kind: validator | qua | fail: còn `claim 'Xem thêm thông tin.' thiếu fact_refs` |
| Âm tiết (thô = sau chuẩn bị) | 111 | 100 |
| Feedback gửi lượt sửa | 1 mục `syllable_advisory` (111, ngoài 150–170) | 2 mục: `content_validator` (claim CTA thiếu fact_refs), `syllable_advisory` (100) |
| Bản sửa (thô) | qua; 133 âm tiết | fail: **cùng lỗi** claim CTA; 100 âm tiết; `kind` s01 về `screen_recording` |
| Bản sửa sau chuẩn bị kind | qua; audit đều `unchanged` | fail như trên |
| Kết quả cuối | `completed`, `estimated_duration_s` 35,5 | `failed` (`llm_invalid_output`) |
| Lời gọi, token, $ (giá niêm yết) | sinh: vào 5 349, ra 1 973, 0,006537; sửa attempt 1: lỗi provider, 0 token; sửa attempt 2: vào 10 051, ra 1 553, 0,006898 | sinh: vào 5 349, ra 1 944, 0,006465; sửa: vào 10 078, ra 1 950, 0,007898 |
| Cảnh / segment / claim (thô → sửa) | 4/7/7 → 4/8/8 | 4/7/7 → 4/7/7 |

Ghi chú: (1) “attempt 1 lỗi provider” ở run11 là retry của lớp LLM (#90), vẫn là **một** lời gọi sửa về mặt orchestration; `cost.json` chưa ghi mã lỗi gốc nên tôi chưa biết là 429 hay 503. (2) Prompt sửa nhúng prompt sinh, schema, candidate và feedback nên vào ~10 000 token, gấp ~2 lần lượt sinh (~5 350).

### E2. Sáu mục theo từng run và từng tầng

| Mục | Run11 thô | Run11 sau sửa | Run12 thô | Run12 sau sửa |
|---|---|---|---|---|
| Qua validator | qua | qua | fail (kind, claim CTA); sau chuẩn bị kind vẫn fail | fail (claim CTA) |
| Âm tiết | 111 | 133 | 100 | 100 |
| Word có clip riêng; clip Word không ở CTA | có clip riêng (s03); **clip Word còn ở CTA** (`pdfcraft-word-result`, s04) | như thô | **không có clip Word**; CTA là `text_card` | như thô |
| `claims[].text` tiếng Việt | có | có | có | có |
| CTA đọc nguyên văn `cta.text` | có | có | có | có |
| Từ đánh giá thiếu fact | “nhanh chóng”, “dễ dàng”, “theo ý muốn” | “dễ dàng”, “theo ý muốn” | không | không |

Cách kiểm: đọc nội dung từng tầng, cộng thêm quét chuỗi (từ đánh giá: nhanh chóng, nhanh, dễ dàng, đơn giản, hữu ích, tùy ý, mạnh mẽ, theo ý muốn, tiện lợi, tuyệt vời, hiệu quả…; từ tiếng Anh thông dụng cho `claims[].text`) rồi đối chiếu với PKB. Danh sách từ không đầy đủ.

### E3. Đo MP4 run11 (`worker.produce` #97, head `c3e6898`, preview 16:9)

Thư mục làm việc `D:/tmp/m2-run11-2026-11-12`. Template #88: `feat/render-v2-claim-layout` (`a7dc4f0`) qua `PRODUCE_RENDER_V2`. Chạy CPU, một tiến trình render, không có render khác chạy cùng. Kịch bản là `run11-2026-11-12/script.json` (bản sau sửa), không sửa tay.

- **Lần 1, `assets.json` cũ (đoạn theo kịch bản Khánh): không dựng được.** `s03: [clip_too_short] clip chỉ có 3.90 s cho cảnh 10.97 s (tốc độ 0.36 < 0.6)`: đoạn đã chọn cho `pdfcraft-word-export` (1,3–4,4 s và 11,45–12,25 s) chỉ có 3,9 s trong khi lời s03 dài 10,72 s. Đây là cấu hình đoạn clip, không phải lỗi M2. Báo cáo: `produce/render_report.as-is-failed.json`.
- **Lần 2, chỉ nới `parts` của `pdfcraft-word-export` thành cả clip 0–12,25 s** (`produce/assets.widened.json`; lời, claim và asset khác giữ nguyên). Đây là chỉnh media ngoài M2, nên cảnh s03 không còn dùng đúng đoạn Khánh chọn.

| | Giá trị |
|---|---|
| `status` | `out_of_range` (`too_short`) |
| `predicted_s` / MP4 | **36,433 s / 36,433 s** (1920×1080) |
| `estimated_duration_s` của M2 | 35,5 s (133 âm tiết ÷ 3,75) |
| Audio VieNeu | 8 segment, tổng 34,88 s; lần 2 cache hit 8/8 (tổng hợp ở lần 1) |
| Cảnh | s01 `feature_clip` 14,17 s (clip tua 0,85×); s02 `feature_clip` 9,43 s (0,81×); s03 `feature_clip` 10,97 s; s04 `cta` 1,87 s, **không có footage** (layout CTA không dùng clip `pdfcraft-word-result`) |
| Cảnh báo | `predicted_too_short: timeline 36.43 s ngoài 40–45 s`; `subtitle_split[16:9]: s03-u01 chia 2 cue`; `title_duplicates_subtitle` ở s02 (83%) và s03 (100%) |
| Render (CPU) | 142,6 s; RAM đỉnh HyperFrames ≈ 4,5 GB |

Chưa xem khung hình hay chuyển động của MP4; chỉ có số đo. Chưa chạy 9:16 (yêu cầu chỉ 16:9).

### E4. Nhận xét

- **Chuẩn bị `kind` làm đúng việc của nó và chỉ việc đó:** ở run12 thay một `kind` sai, có audit và hash allowlist (`010406b1…`), giữ thô riêng. Nó không làm run12 đúng nội dung; lỗi còn lại không liên quan `kind`.
- **Lượt sửa hiệu quả khác nhau theo loại feedback.** Với khuyến nghị âm tiết (run11), model bổ sung nội dung và tăng 22 âm tiết nhưng chưa tới 150. Với lỗi cấu trúc (run12), model **lặp lại lỗi** dù feedback nêu đúng claim: cảnh CTA vẫn có claim “Xem thêm thông tin.” không ref. Theo quyết định của #83 thì dừng, cần chỉnh ngoài payload script.
- **Lỗi claim CTA không ref:** run11 gắn claim CTA vào `identity.tagline.value`, run12 để `fact_refs: []`. Validator chặn đúng. Có nên ghi rõ trong prompt “cảnh CTA có thể không có claim” là câu hỏi hợp đồng cho Định, không đổi ở đây.
- **Thời lượng:** 133 âm tiết cho MP4 36,43 s. Audio đo 34,88 s (≈3,8 âm tiết/s), MP4 dài hơn audio 1,55 s. Nếu giữ tỉ lệ này, 150–170 âm tiết ứng với audio ~39,3–44,6 s và MP4 ~40,9–46,2 s. Đây là nội suy, chưa có mẫu nào ở mốc đó, nên chưa xác nhận mốc 150–170 vào được 40–45 s.
- **Cải thiện so với run9/run10:** không còn `kind` sai ở `pdfcraft-word-result`; `claims[].text` giới hạn đã tiếng Việt ở cả hai run. **Còn lại:** clip Word ở cảnh CTA (run11), run12 không có clip Word, “dễ dàng”/“theo ý muốn” ở run11.
- **Không vá, không sửa tay kịch bản.** `run11/script.json` là output của lượt sửa sau chuẩn bị kind; `run12/script.json` là output thô của lượt sửa (không hợp lệ). Không chạy `produce` cho run12.
- **Giới hạn:** 2 mẫu, một input, `temperature=0` nhưng LLM vẫn không lặp lại hoàn toàn (hai run khác nhau ngay ở cảnh đầu); `produce` chỉ 1 tỉ lệ; lần đo thành công phải nới đoạn clip.

## Lần chạy 11/11/2026 (contract 29f868a)

- **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định, Khánh; cần xác nhận của các bạn.
- **Code:** PR #92 (`feat/m2-generate-script`), đồng bộ từ #83 `29f868a` ở commit `b12d896`. So với `4c5b72b` đổi 4 file ở #83: prompt (150–170 âm tiết, claim hiển thị bằng tiếng Việt, quy nguồn trong câu đọc, `kind` chép từ allowlist, một thao tác chính mỗi cảnh quay), README, test-cases và `validate_contracts.py` (blob `09224cf` → `638f499`: luật `visual_plan.kind` phải khớp `kind` của asset khi `existing_asset`). Schema, ví dụ, PKB giữ nguyên blob. Worker chép prompt nguyên byte (blob `2487354`), port luật `kind` vào `validate.py` (lỗi đầu tiên trùng bản của Định), ghi lại parity từ `29f868a` (`parity-29f868a.json`, thêm ca `screen-recording-cannot-be-used-as-logo`). Bộ kiểm của Định chạy lại ở `29f868a`: **99/99 đạt**. ruff, format, pyright xanh; 292 test pass.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier, 2 lời gọi, $0 trả thật. Cùng `input.json` với run3–run8 (không `video_description`, CTA mặc định `destination: null`). Không thử lại.
- **Dữ liệu:** `run9-2026-11-11/`, `run10-2026-11-11/` (`script.json` là output thô vì không qua validator, `validation.json`, `cost.json`). Validator mới trên run7/run8: `run7-2026-11-09/validation-29f868a.json`, `run8-2026-11-09/validation-29f868a.json`. File cũ giữ nguyên.
- **Âm tiết** đếm bằng `narration_syllables` của worker. Run9/run10 không có `estimated_duration_s` vì không `completed`.
- **PDFCraft vẫn là dữ liệu thử.** Chưa dùng làm bằng chứng chất lượng. 2 mẫu.

> **Kết luận ngắn.**
> - **Qua validator: 0/2.** Run9: 2 lỗi. Run10: 1 lỗi. Cả hai đều dính luật `kind` mới ở `pdfcraft-word-result` (allowlist ghi `screen_recording`, model khai `screenshot`).
> - **Run7/run8 bị từ chối đúng như dự kiến**, ở `s01`: `asset_id 'pdfcraft-merge' phải dùng visual_plan.kind 'screen_recording'`.
> - **Âm tiết:** 145 (run9) và 133 (run10), tăng so với 127/126 nhưng **chưa vào mốc thử 150–170**.
> - **Word có clip riêng:** run10 có (s04 dùng `pdfcraft-word-export`), run9 không (ý Word nằm ở s03 trên clip đánh số trang, `pdfcraft-word-export` không dùng). **Cả hai vẫn đặt thêm `pdfcraft-word-result` ở cảnh CTA.**
> - **Claim tiếng Việt: chưa đạt 2/2.** Câu giới hạn 100 tệp/500MB vẫn là chuỗi tiếng Anh nguyên văn ở `claims[].text`.
> - **Quy nguồn “PDFCraft công bố” trong câu đọc: có ở cả hai** (`s01-u02`).
> - **Từ đánh giá thiếu fact:** run10 có “dễ dàng” (subtitle s03) và “nhanh chóng” (`meta.title`); run9 không có “dễ dàng/đơn giản/hữu ích/tùy ý”.
> - **Chưa dựng MP4:** không run nào qua validator nên không chạy `worker.produce` (bước 5 không áp dụng). Chưa có phép đo audio/MP4 cho lượt này.

### D1. Validator mới trên output cũ và mới

| Output | Kết quả | Lỗi |
|---|---|---|
| run7 (`script.json` thô) | fail | `cảnh 's01': asset_id 'pdfcraft-merge' phải dùng visual_plan.kind 'screen_recording'` |
| run8 (`script.json` thô) | fail | như run7 |
| run9 | fail (`llm_invalid_output`) | `s04`: `pdfcraft-word-result` phải dùng `screen_recording`; cảnh cta phải kết bằng lời đọc `cta.text` (model đọc “Xem thêm thông tin chi tiết.”, `cta.text` là “Xem thêm thông tin.”) |
| run10 | fail (`llm_invalid_output`) | `s05`: `pdfcraft-word-result` phải dùng `screen_recording` |

Validator của worker trả mọi lỗi (không chỉ lỗi đầu), nên run7/run8 chỉ có đúng một lỗi này. Token vào 5 204 (prompt dài hơn, 4 913 trước đó), ra 2 000 và 2 089. $ giá niêm yết 0,006561 + 0,006784 = 0,013345 (trả thật $0).

### D2. Từng run

| | Run9 | Run10 |
|---|---|---|
| Cảnh / segment / claim | 4 / 8 / 7 | 5 / 8 / 6 |
| Âm tiết lời thoại | 145 | 133 |
| Hook đọc ở `s01-u01` | đúng | đúng |
| CTA kết bằng `cta.text` | **sai** (“…thông tin chi tiết.”) | đúng |
| Word có clip riêng | không: Word ở s03 trên clip đánh số trang | có: s04 + `pdfcraft-word-export` |
| Clip Word còn ở CTA | có (`pdfcraft-word-result`, s04) | có (`pdfcraft-word-result`, s05) |
| Kind khai cho `pdfcraft-word-result` | `screenshot` (sai) | `screenshot` (sai) |
| `claims[].text` giới hạn 100 tệp | tiếng Anh nguyên văn | tiếng Anh nguyên văn |
| `stat_display` giới hạn | có, nhãn tiếng Việt | có, nhãn tiếng Việt |
| “Theo PDFCraft công bố” trong lời đọc | có (`s01-u02`) | có (`s01-u02`) |
| Quy nguồn trên chữ hiển thị | claim s01 và text card **không** có “công bố” | claim s01 có “PDFCraft công bố:”; text card chỉ nêu tên PDFCraft |
| Từ đánh giá không có fact | “lo lắng về chi phí ẩn” (lời thêm, nghĩa không có trong fact) | “dễ dàng” (subtitle s03), “nhanh chóng” (`meta.title`) |
| “Hoàn toàn miễn phí” | có, evidence có “Hoàn toàn Miễn phí” | có, như run9 |

### D3. Nhận xét

- **Prompt mới có tác dụng ở một vế.** Run10 tách Word thành cảnh riêng với clip Word; hai run đều đưa quy nguồn vào câu đọc; không run nào dùng `kind: logo` cho clip ghép PDF nữa (run7/run8 đều sai chỗ này). Cả hai có hook đọc đúng.
- **Chưa tác dụng:** (1) `kind` của `pdfcraft-word-result` vẫn sai, dù prompt bảo chép `kind` từ allowlist; (2) claim giới hạn vẫn tiếng Anh dù prompt có đúng ví dụ này; (3) clip Word còn lại bị đưa vào cảnh CTA thay vì bỏ; (4) run9 sửa `cta.text` trong lời đọc.
- **Âm tiết:** 145 gần mốc dưới 150 nhưng chưa tới; chưa có audio/MP4 nên không kết luận thời lượng. Với 3,75 âm tiết/s (hệ số mặc định) 145 và 133 tương ứng 38,7 s và 35,5 s, vẫn dưới 40–45 s.
- **Hook không có `fact_refs` ở run9** (claim ở s01 gắn `s01-u01`, `s01-u02`): validator của Định chấp nhận. Việc có buộc `hook.fact_refs` hay không là câu hỏi hợp đồng của #97, không đổi ở đây.
- **Không vá, không sửa tay:** output run9/run10 giữ nguyên bản thô; không chạy `produce`; không đụng `pricing.free_plan.value` của #97.
- **Giới hạn:** 2 mẫu, một input, `temperature=0` nhưng LLM vẫn không bảo đảm lặp lại. Chưa đủ để kết luận prompt tốt hay xấu; cần Định/Khánh quyết hướng (nới schema/prompt, hay thêm cơ chế sinh lại có phản hồi lỗi, ngoài phạm vi #92).

## Lần chạy 09/11/2026 (contract 4c5b72b)

- **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định, Khánh. Tôi chỉ là một người rà, cần xác nhận.
- **Code:** PR #92 (`feat/m2-generate-script`), commit `6e02382` (đồng bộ prompt `4c5b72b`, **chưa push**). #83 head vẫn là `4c5b72b`, không có commit contract mới hơn. So với `73f4df9` chỉ prompt (+5 dòng) và README/báo cáo của #83 đổi; schema, ví dụ, `validate_contracts.py` (blob `09224cf`) giữ nguyên nên parity `parity-73f4df9.json` giữ nguyên. Worker chép prompt, cập nhật `SOURCE.md`, SHA pin (`test_contract.py`) và README worker. README của #83 không nằm trong `contract/` nên không chép. ruff, pyright xanh; 291 test pass.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier. **2 lời gọi**, $0 trả thật. Cùng `input.json` với run3–run6, không `video_description`, CTA mặc định (`destination: null`).
- **Dữ liệu** (`run7-2026-11-09/`, `run8-2026-11-09/`): `script.json`, `validation.json`, `cost.json`. Run7 thêm `render_report.json` và `script.s01-edited.json`, xem C6.
- **PDFCraft vẫn là dữ liệu thử** (duyệt mô phỏng). Chỉ để hồi quy kỹ thuật, chưa dùng làm bằng chứng chất lượng.

> **Kết luận ngắn.**
> - **Qua validator: 2/2**, 0 lỗi (run5/run6 trước đó: 1/2). Cả hai ghi đúng `pricing.free_plan.value` và `limitations[0].text`; Word → `features[4].description` **đúng ở cả hai** (run5 thiếu).
> - **Hook/CTA được đọc: đạt 2/2.** `hook.text` nguyên văn ở `s01-u01`; cảnh cuối `role: cta` kết bằng "Xem thêm thông tin."; không có `cta_narration_derived`; không có URL trong lời/phụ đề CTA.
> - **Thời lượng: tăng nhưng chưa đạt.** 127 và 126 âm tiết (33,9 s / 33,6 s ước tính), 4 cảnh, 8 và 7 segment. Còn dưới mốc tham khảo 130–150 âm tiết và dưới 40–45 s. MP4 thật (run7) 34,733 s, `too_short`.
> - **Lời–hình vẫn lệch (rule 11 chưa có hiệu lực):** cả hai gộp "đánh số trang" và "Word" vào một cảnh s03 với clip đánh số trang; clip Word nằm ở cảnh CTA nói về miễn phí/không đăng ký. Cả hai dùng `kind: logo` cho clip quay màn hình ở s01.
> - **Từ đánh giá:** run8 có "dễ dàng", "một cách đơn giản" (không có fact). Run7 có "hữu ích". "Hoàn toàn miễn phí" ở cả hai (evidence có "Hoàn toàn Miễn phí").
> - **Quyền riêng tư:** run8 nói "giữ tệp không rời khỏi thiết bị" trong hook **không có "PDFCraft công bố"**, trái `forbidden_claims`.
> - **Chữ tiếng Anh lên hình:** cả hai chép nguyên câu giới hạn tiếng Anh vào `claims[].text`; MP4 hiện câu đó trong video tiếng Việt (C6).
> - **Chặn ở #97, không phải M2:** `produce` không dựng được cả hai script nguyên bản (C6).
> - **Chưa dùng làm bằng chứng đạt.** 2 mẫu.

### C1. Cấu trúc JSON và validator

| | Run7 | Run8 |
|---|---|---|
| Kết quả | `completed`, 0 lỗi | `completed`, 0 lỗi |
| Cảnh báo | `estimated_duration_s_is_estimate`, `estimate_outside_target:33.9s` | tương tự, 33.6 s |
| Cảnh / segment / claim | 4 / 8 / 7 | 4 / 7 / 7 |
| Âm tiết lời thoại | 127 (33,9 s) | 126 (33,6 s) |
| Token vào / ra | 4 913 / 2 033 | 4 913 / 2 007 |
| $ giá niêm yết (trả thật $0) | 0,006556 | 0,006491 |

Token vào tăng 4 340 → 4 913 do prompt dài hơn. Tổng 2 lần: $0,013047 giá niêm yết. Run5 trước đó: 97 âm tiết, 3 cảnh.

### C2. Hook và CTA có thực sự được đọc

| | Run7 | Run8 |
|---|---|---|
| `hook.text` nguyên văn ở segment đầu cảnh đầu | có (`s01-u01`) | có (`s01-u01`) |
| Cảnh cuối `role: cta`, lời kết bằng `cta.text` | có (`s04-u02`) | có (`s04-u02`) |
| `cta.destination` | `null` | `null` |
| URL/domain trong script (lời, phụ đề, purpose) | không | không |
| `cta_narration_derived` | không | không |

Đúng luật. CTA vẫn là câu mặc định nên chưa chứng minh model theo CTA do người dùng đưa. Trên MP4 run7, cảnh CTA chỉ có nút "Xem thêm thông tin." và phụ đề, **không có URL**: lượt 4 của #97 đã bỏ việc lấy `identity.website`.

### C3. Claim, fact_refs (nghĩa, không chỉ path)

Run7:

| Segment | Lời đọc (rút gọn) | Ref | Đánh giá |
|---|---|---|---|
| s01-u01 (hook) | công cụ xử lý PDF miễn phí và mạnh mẽ ngay trong trình duyệt | tagline, `free_plan.value` | Đúng. "mạnh mẽ" là chữ của tagline, đọc như sự thật không quy nguồn |
| s01-u02 | "khám phá PDFCraft với các tính năng **hữu ích**" | tagline | "hữu ích" không có fact |
| s02-u01 | kết hợp nhiều tệp PDF thành một | `features[0]` | Đúng |
| s02-u02 | gộp đến 100 tệp, tối đa 500MB | `limitations[0].text` | Đúng. `claims[].text` là câu **tiếng Anh** |
| s03-u01 | thêm số trang, chỉnh vị trí "tùy ý" | `features[3]` | Đúng ý; "tùy ý" mạnh hơn fact (vị trí, định dạng, số bắt đầu) |
| s03-u02 | chuyển PDF sang Word để chỉnh sửa | `features[4]` | **Đúng**, claim và ref riêng |
| s04-u01 | hoàn toàn miễn phí, không đăng ký, "mọi thao tác đều diễn ra trong trình duyệt" | `free_plan.value`, `features[1]` | Mệnh đề **trình duyệt không có ref** (`features[2]`) và không "PDFCraft công bố" |

Run8:

| Segment | Lời đọc (rút gọn) | Ref | Đánh giá |
|---|---|---|---|
| s01-u01 (hook) | công cụ xử lý PDF miễn phí và **giữ tệp không rời khỏi thiết bị** | tagline, `free_plan.value`, `features[2]` | Ref đủ. Nhưng đọc như sự thật, **thiếu "PDFCraft công bố"**: trái `forbidden_claims` |
| s02-u01 | kết hợp nhiều tệp PDF "một cách **đơn giản**" | `features[0]` | "đơn giản" không có fact |
| s02-u02 | ghép tối đa 100 tệp, 500MB | `limitations[0].text` | Đúng. `claims[].text` tiếng Anh |
| s03-u01 | "**dễ dàng** thêm số trang… theo ý muốn" | `features[3]` | "dễ dàng" lặp lỗi run6; "theo ý muốn" mạnh hơn fact |
| s03-u02 | chuyển sang Word (DOCX) | `features[4]` | **Đúng** |
| s04-u01 | mọi xử lý trong trình duyệt, hoàn toàn miễn phí, không cần đăng ký | `features[2]`, `free_plan.value` | Ref đủ cho trình duyệt và miễn phí; "không cần đăng ký" **không có ref** `features[1]`; thiếu "PDFCraft công bố" trong lời |

- **Ý trình duyệt/thiết bị:** run7 không nói "thiết bị", chỉ nói trình duyệt (s04-u01 thiếu ref). Run8 nói "thiết bị" ở hook (có ref, thiếu quy nguồn). Lỗi "trong thiết bị" gắn nhầm tagline của run5 **không lặp lại**.
- **Từ đánh giá/tuyệt đối:** không có "nhanh nhất", "không giới hạn". "Hoàn toàn miễn phí" ở cả hai có evidence ("Hoàn toàn Miễn phí") và `free_plan.value`: chấp nhận theo prompt mới; chưa nói mọi usage đều miễn phí. Còn "hữu ích" (run7), "đơn giản", "dễ dàng" (run8).
- **`stat_display`:** không claim nào trình bày số liệu theo layout `stat`. Câu 100 tệp/500MB là claim trong cảnh demo, không có `stat_display`. Chưa chứng minh model làm đúng `stat_display`.

### C4. Khớp lời–hình

| Cảnh | Lời đọc | Run7: hình | Run8: hình | Khớp |
|---|---|---|---|---|
| s01 | hook | `kind: logo` + `pdfcraft-merge` | `kind: logo` + `pdfcraft-merge` | **kind sai** (logo nhưng asset là clip quay màn hình) |
| s02 | ghép file, 100 tệp | `pdfcraft-merge` | `pdfcraft-merge` | đúng |
| s03 | u01 số trang, u02 **Word** | `pdfcraft-pagenum` | `pdfcraft-pagenum` | **lệch ở u02**: không có hình Word |
| s04 | miễn phí / không đăng ký / CTA | `pdfcraft-word-result` | `pdfcraft-word-export` | **lệch**: clip Word dưới lời không nói Word. Layout `cta` không hiện clip nên không lộ trong MP4 |

Prompt rule 11 ("không đặt câu xuất Word lên clip chỉ quay đánh số trang"; phân cảnh theo thao tác) **không được theo** ở cả hai lần. Hai clip Word có sẵn trong allowlist nhưng bị đặt vào cảnh CTA. Vẫn không có cảnh riêng cho Word.

### C5. `estimated_duration_s`

127 âm tiết ÷ 3,75 = 33,9 s (run7); 126 → 33,6 s (run8). Audio VieNeu thật của run7: **33,20 s** (8 segment: 4,48 + 3,52 + 4,32 + 5,28 + 4,88 + 4,40 + 4,96 + 1,36). Ước tính cao hơn audio thật 0,7 s (+2%); 127 ÷ 33,20 = 3,83 âm tiết/s. Prompt đã nhắc "rà độ đầy đủ", model dùng thêm giới hạn 100 tệp/500MB nhưng không dùng bước ghép (`features[5]`). Vẫn thiếu khoảng 6–11 s lời đọc có căn cứ cho 40–45 s.

### C6. Đo thật qua `worker.produce` (#97), preview, 1 mẫu (run7)

`#97` ở `81f5108` (lượt 4 xong, đã kiểm: không còn tiến trình render nào chạy). Chạy trên máy dev, CPU, `--mode preview`, 2 tỉ lệ song song. Template #88: `feat/render-v2-claim-layout` (`a7dc4f0`), đặt bằng `PRODUCE_RENDER_V2` (mặc định trỏ `p1-render-v2` cũ, thiếu `crop_by_ratio` nên lỗi `RenderPlan`).

**`produce` không dựng được script nguyên bản của cả hai run.** Hai lỗi, thuộc #97/mapping, không thuộc M2:

1. `s01: [asset_kind] hook cần asset kind=image (pdfcraft-merge)`. Cảnh hook có `visual_plan.kind: logo`, `asset_id: pdfcraft-merge` (clip). `scene_assets` của manifest chỉ áp khi M2 **không** nêu `asset_id`, nên manifest không sửa được. Run7 và run8 cùng dạng này (run8 thử với 1 tỉ lệ, cùng lỗi).
2. `s04: [fact_ref_invalid] fact 'pricing.free_plan.value' không có chữ để trích`. `FactBook.add` gọi `resolve_field_path` ra giá trị bool `true`; `_quote` chỉ đọc chuỗi/dict nên lỗi, và `_source_id` cũng không đọc được `source_id` (id thành `pkb:...` thay vì `src_01:...`). Prompt `4c5b72b` nêu ví dụ `pricing.free_plan.value` kiểu boolean, nên model sẽ ghi path này thường xuyên. Cần sửa trong `produce/facts.py` (lùi về nút cha lấy `evidence`). Tôi **chưa sửa** (worktree #97 của job khác).

Để vẫn có số đo, chỉ cho lần đo này tôi dùng: (a) `run7-2026-11-09/script.s01-edited.json`: **chỉ `visual_plan` của s01 đổi sang `text_card`** (lời, claim, các cảnh khác giữ nguyên); (b) một wrapper tạm ngoài repo lùi `free_plan.value` về nút cha. Hai thay đổi này **không** thuộc kết quả của M2. Assets: `assets.pdfcraft-khanh.json` (crop/đoạn theo kịch bản Khánh, chưa chỉnh theo run7), s01 → `ai-paperwork`.

| | Giá trị |
|---|---|
| `status` | `out_of_range` (`too_short`) |
| Audio VieNeu (tổng 8 segment) | **33,20 s** (cache hit 8/8: đã tổng hợp ở lần chạy lỗi trước đó trong cùng phiên) |
| MP4 16:9 (1920×1080) | **34,733 s** |
| MP4 9:16 (1080×1920) | **34,733 s** (khớp `predicted_s`) |
| Layout dựng | s01 `hook` (ảnh AI, 8,27 s), s02 `feature_clip` (9,87 s), s03 `feature_clip` (clip tua 0,80×, 9,50 s), s04 `cta` (7,10 s) |
| Render (CPU) | 16:9 336,7 s, 9:16 393,9 s, tổng 398,0 s; RAM đỉnh ≈ 5,8 GB. Không có render khác chạy cùng, nhưng có các tiến trình node/MCP nền |
| Phụ đề 9:16 | cả 8 segment chia 2 cue (`subtitle_split`) |

Đã xem 3 khung 16:9 (10 s, 20 s, 33 s), chưa xem chuyển động:
- **10 s (s02):** panel hiện claim tiếng Việt "Kết hợp nhiều tệp PDF…", bên dưới là **câu tiếng Anh** "You can merge up to 100 files at once, with a total combined size of up to 500MB." (`claims[].text` chép từ nguồn). Lời đọc tiếng Việt. Cần M2 viết `claims[].text` bằng tiếng Việt khi `language: vi`, hoặc mapping không hiện claim khác ngôn ngữ video. Quyết định thuộc Định/lead.
- **20 s (s03):** clip đánh số trang; panel nêu claim đánh số trang kèm chip "Chuyển PDF sang tài liệu Word chỉnh sửa được." Lời đang đọc ý số trang; chip Word hiện khi chưa có hình Word.
- **33 s (s04):** cảnh CTA chỉ có logo, nút "Xem thêm thông tin." và phụ đề, **không URL**.

### C7. So với lần chạy 04/11 và việc còn lại

| | 04/11 (`73f4df9`) | 09/11 (`4c5b72b`) |
|---|---|---|
| Qua validator | 1/2 | 2/2 |
| Âm tiết / ước tính | 97 / 25,9 s | 127 và 126 / 33,9 và 33,6 s |
| Word → `features[4]` | thiếu | có |
| "trong thiết bị" gắn nhầm tagline | có | không |
| "dễ dàng" | có (run6) | có (run8) |
| Clip Word dưới lời Word | không | không |
| MP4 thật | 27,933 s | 34,733 s (có sửa s01, xem C6) |

- **Chưa đạt, cần Định xem prompt hoặc validator:** rule 11 (lời–hình theo thao tác), quy nguồn "PDFCraft công bố" khi nói về trình duyệt/thiết bị, từ đánh giá "dễ dàng/đơn giản/hữu ích", `claims[].text` tiếng Anh, `kind` của cảnh hook.
- **Cần lead/Hoàng sửa ở #97:** hai lỗi ở C6 trước khi chạy tự động bản qua validator.
- **Giới hạn:** 2 mẫu, free tier, `temperature=0`; PKB duyệt mô phỏng; chưa `video_description`, chưa CTA do người dùng đưa; chỉ render run7 (1 mẫu, 1 người rà); số đo render có thể nhiễu bởi tiến trình nền.

## Lần chạy 04/11/2026 (contract 73f4df9)

- **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định (contract M2, #83), Khánh (input, QA).
- **Code:** PR #92 (`feat/m2-generate-script`), commit `5dbdcfc` (đồng bộ contract `73f4df9`, chưa push lúc ghi báo cáo). Phần ghép MP4 chạy bằng `worker.produce` của #97 (`feat/p1-script-to-mp4`, `fccb6b6`) và template #88 có layout `claim` (`feat/render-v2-claim-layout`, `4e9f04f`).
- **Contract:** prompt và output schema của Định ở **`73f4df9`** (#83). Input schema, examples và PKB không đổi so với `fb4f0ed`.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier. **2 lời gọi**, $0 trả thật.
- **Dữ liệu thử:** input PDFCraft `input.json` (cùng file với run3/run4 ngày 30/10, để so sánh được). `approved_pkb.status = "approved"`, người duyệt và thời điểm duyệt là **mô phỏng**, chưa có BA/khách hàng/merchant xác nhận. Lần chạy này **chỉ để hồi quy kỹ thuật**; chưa dùng làm bằng chứng chất lượng nội dung. PKB AISoEasy chưa được xác nhận nên chưa chạy.
- **`video_description`:** **không dùng** trong 2 lần chạy. Câu mẫu của lead (#94, 31/10) nói về "học AI để ứng dụng trong công việc", không khớp sản phẩm PDFCraft. Đưa vào sẽ trộn phép thử hồi quy với phép thử hai yêu cầu mâu thuẫn. Câu mẫu đã có ở `tests/m2/parity_cases.py` (`LEAD_VIDEO_DESCRIPTION`) và test `generate_script`. Nên chạy thật với AISoEasy khi PKB được xác nhận.
- **Dữ liệu** (`docs/report/m2-first-run-pdfcraft/`):

  | File | Nội dung |
  |---|---|
  | `run5-2026-11-04/` | `script.json` qua validator (output LLM sau bước worker: đã thêm `estimated_duration_s`), `validation.json`, `cost.json`, `render_report.json` (từ `worker.produce`) |
  | `run6-2026-11-04/` | **output thô**, bị validator từ chối (`script.json` là output thô, `validation.json` có lỗi), `cost.json` |
  | không có `script.edited.json` | **không có bản chỉnh tay** lần này. `produce` chạy trên `run5/script.json` nguyên bản |
  | `D:\tmp\m2-run5-2026-11-04\produce\` (không commit) | `script-preview-16x9.mp4`, `script-preview-9x16.mp4`, `script-preview.json` (plan), `render_report.json` |
  | `D:\tmp\m2-run5-2026-11-04\frames\` (không commit) | 10 khung (5 mốc × 2 tỉ lệ). Mới xem bằng mắt 2 khung 16:9 (14 s, 26 s) |

> **Kết luận ngắn.**
> - **Qua validator: 1/2.** Run5 `completed`; run6 `llm_invalid_output` (1 lỗi: `fact_ref 'free_plan.value'` không tồn tại, model tự bịa đường dẫn). Chỉ 2 lần, chưa kết luận được độ ổn định.
> - **Hook và CTA được đọc: đạt cả 2 lần.** `hook.text` nguyên văn ở `s01-u01`; cảnh cuối `role: cta` kết bằng `Xem thêm thông tin.` Cả hai do LLM sinh: không có warning `cta_narration_derived`.
> - **Thời lượng vẫn thiếu.** Run5: 97 âm tiết, ước tính 25,9 s. Audio VieNeu thật 26,64 s. MP4 thật **27,933 s** (cả 2 tỉ lệ), `too_short` so với 40–45 s. Run6 (thô): 63 âm tiết ≈ 16,8 s. Prompt `73f4df9` đã nhắc 130–150 âm tiết và "rà độ đầy đủ", nhưng model chỉ viết 3 cảnh / 6 segment (run5) và 3 cảnh / 6 segment (run6). Tăng so với 18,9–19,2 s của 30/10 nhưng chưa tới mục tiêu.
> - **Nghĩa claim còn lỗi dù path đúng (run5):** xem A4. Validator không bắt được các lỗi này.
> - **Lời–hình lệch ở run5:** cảnh `s02` đọc về ghép file nhưng gắn clip đánh số trang; clip Word gắn vào cảnh CTA nói về quyền riêng tư (A6).
> - **Chưa dùng làm bằng chứng đạt** cho thời lượng, nghĩa claim hay lời–hình. Còn thiếu: chạy lặp, PKB AISoEasy đã xác nhận, mô tả video của người dùng.

### B1. Cấu trúc JSON và validator

| | Run5 | Run6 (thô) |
|---|---|---|
| Kết quả | `completed`, 0 lỗi | `llm_invalid_output`, 1 lỗi |
| Lỗi | — | `claim: fact_ref 'free_plan.value' không tồn tại: 'free_plan'` (s03) |
| Cảnh báo | `estimated_duration_s_is_estimate`, `estimate_outside_target:25.9s` | — |
| Cảnh / segment / claim | 3 / 6 / 5 | 3 / 6 / 3 |
| Token vào / ra | 4 340 / 1 523 | 4 340 / 1 387 |
| $ giá niêm yết (trả thật $0) | 0,005110 | 0,004770 |
| Âm tiết lời thoại | 97 (25,9 s) | 63 (16,8 s, tính tay từ output thô) |

Token vào tăng 3 549 → 4 340 so với run3/run4 (30/10) do prompt dài hơn. Tổng 2 lần: $0,009880 giá niêm yết.

Ví dụ `field_path` từ gốc trong prompt `73f4df9` giúp run5 (mọi path đúng, kể cả `identity.tagline.value`), nhưng run6 vẫn bịa `free_plan.value`. Lỗi kiểu "thiếu `identity.`" của run3 không lặp lại.

### B2. Hook và CTA có thực sự được đọc

| | Run5 | Run6 |
|---|---|---|
| `hook.text` ở segment đầu cảnh đầu | có, nguyên văn (`s01-u01`) | có, nguyên văn (`s01-u01`) |
| Cảnh cuối `role: cta` | có (`s03`) | có (`s03`) |
| Lời đọc kết bằng `cta.text` | `s03-u02` = "Xem thêm thông tin." | `s03-u02` = "Xem thêm thông tin." |
| `cta.destination` | `null`, không có `cta.fact_refs` | `null`, không có `cta.fact_refs` |
| Fallback `cta_narration_derived` | không | không |

Đúng luật mới. Cần lưu ý: CTA là câu mặc định của contract nên chưa chứng minh model theo CTA do người dùng đưa.

**Phát hiện cho #97 (không thuộc output M2):** MP4 hiện URL `pdfcraft.devtoolcafe.com` trên cảnh CTA dù `cta.destination = null`. `produce/mapping.py:416` lấy `identity.website` khi không có destination. Contract M2 cấm lấy URL từ PKB để điền destination; ở đây là bước render, nhưng người xem vẫn thấy URL mà người dùng chưa đưa. Cần lead/Định quyết định có chấp nhận hay không. Tôi chưa sửa.

### B3. Claim, fact_refs (nghĩa, không chỉ path), `stat_display`

Fact PDFCraft trong input: F0 (hợp nhất), F1 (không đăng ký, không chi phí ẩn), F2 (PDFCraft **tự công bố** xử lý trong trình duyệt, tệp không rời thiết bị), F3 (đánh số trang), F4 (PDF → Word chỉnh sửa được), F5 (cách ghép), giới hạn 100 tệp / 500MB.

Run5, từng segment so với fact:

| Segment | Lời đọc | Ref | Đánh giá |
|---|---|---|---|
| s01-u01 (hook) | "…xử lý file PDF trực tiếp trên trình duyệt mà không cần đăng ký?" | `features[1]` (F1) | Phần "không cần đăng ký" đúng F1. "Trực tiếp trên trình duyệt" thuộc F2/tagline nhưng không có trong ref. Claim còn ghi "không có chi phí ẩn" mà lời đọc không nhắc |
| s01-u02 | "…công cụ xử lý file tài liệu **ngay trong thiết bị của bạn**" | `identity.tagline.value` | **Sai nghĩa ref:** tagline không nói về thiết bị. Ý "trong thiết bị" thuộc F2 và mất cụm "PDFCraft công bố" |
| s02-u01 | "kết hợp nhiều tệp PDF… kéo và thả để sắp xếp" | `features[0]` | Đúng F0 |
| s02-u02 | "thêm số trang hoặc chuyển PDF sang tài liệu Word chỉnh sửa được" | `features[3]` (F3) | Một nửa đúng. **Phần Word (F4) không có ref** |
| s03-u01 | "PDFCraft công bố mọi xử lý diễn ra trong trình duyệt, tệp của bạn không rời khỏi thiết bị." | `features[2]` (F2) | Đúng, giữ được "PDFCraft công bố" |

- **Từ đánh giá / tuyệt đối (rule mới của prompt):** lời đọc run5 sạch ("nhanh chóng", "dễ dàng", "nhanh nhất", "không giới hạn" đều không có). Chữ "mạnh mẽ" chỉ nằm trong `claims[].text` (chép nguyên từ tagline, tự công bố), không đọc ra. **Run6 vi phạm:** "dễ dàng" (s02-u02) và "hoàn toàn miễn phí" (s03-u01); lỗi path của run6 chặn nó trước khi có kết quả cuối.
- **Quyền riêng tư:** run5 giữ cách nói "PDFCraft công bố" ở s03 nhưng mất ở s01-u02.
- **`stat_display`:** không claim nào trình bày số liệu, nên không cần và model không thêm. Model không dùng giới hạn 100 tệp / 500MB. Không có gì để kiểm đơn vị/nhãn/phạm vi. Ca này **chưa chứng minh** model làm đúng `stat_display` khi có số liệu.

### B4. Khớp lời–hình

Cả 3 cảnh dùng `screen_recording` + `existing_asset`.

| Cảnh | Lời đọc | Hình (`asset_id`) | Khớp |
|---|---|---|---|
| s01 | giới thiệu xử lý PDF trong trình duyệt | `pdfcraft-merge` (clip ghép) | chấp nhận được |
| s02 | u01 nói **ghép file**, u02 nói số trang + Word | `pdfcraft-pagenum` (clip đánh số trang) | **lệch:** clip ghép nằm ở s01, s02 u01 không có hình tương ứng |
| s03 | quyền riêng tư + CTA | `pdfcraft-word-export` (clip xuất Word) | **lệch:** lời không nói về Word. Khi dựng, cảnh CTA dùng layout `cta` nên clip này không xuất hiện |

Xem MP4 (2 khung 16:9): ở s02 panel chữ hiện nguyên claim "Kết hợp nhiều tệp PDF…" kèm chip "Thêm số trang…", nghĩa là chữ trên hình khớp lời đọc của u01 nhưng clip nền là clip đánh số trang. Clip Word (F4) không xuất hiện trong video dù lời đọc có nhắc Word.

**Mô tả người dùng:** không có `video_description` trong 2 lần chạy (xem trên). Chưa đánh giá được việc model theo giọng/góc kể do người dùng yêu cầu.

### B5. Phần cần sửa tay để bàn giao (chưa sửa, `run5/script.json` giữ nguyên)

1. Thời lượng: kịch bản cần dài hơn ≈ 13–18 s lời đọc nữa (cần thêm nội dung có căn cứ: cách dùng F5, giới hạn 100 tệp / 500MB, Word F4). Không thể kéo bằng cách thêm claim không có fact.
2. s01-u02: đổi ref sang `features[2].description` và giữ "PDFCraft công bố…", hoặc bỏ ý "trong thiết bị".
3. s02-u02: thêm claim + ref `features[4]` cho phần Word, hoặc tách segment.
4. Hình: gán `pdfcraft-merge` cho s02-u01 (hoặc đổi thứ tự), gán `pdfcraft-word-export` / `pdfcraft-word-result` cho đoạn nói về Word.
5. `cta`: quyết định có hiện URL hay không (mục B2).

### B6. Đo thật qua `worker.produce` (#97), preview, 1 mẫu

Chạy trên `run5/script.json`, `--mode preview`, 2 tỉ lệ song song, 1 mẫu, máy dev (CPU, VieNeu `onnx/cpu`).

| | Giá trị |
|---|---|
| `status` | `out_of_range` (`too_short`, 27,933 s ngoài 40–45 s) |
| Audio VieNeu (tổng 6 segment) | **26,64 s** (4,56 + 5,12 + 4,96 + 5,12 + 5,52 + 1,36) |
| MP4 16:9 (1920×1080) | **27,933 s** |
| MP4 9:16 (1080×1920) | **27,933 s** (khớp `predicted_s`) |
| Ước tính worker | 25,9 s (97 âm tiết ÷ 3,75). Thực tế 97 ÷ 26,64 = 3,64 âm tiết/s; ước tính thấp hơn audio thật 0,74 s (−2,8%) |
| Layout dựng | s01 `feature_clip` (clip chậm 0,78×), s02 `feature_clip` (0,63×), s03 `cta`. Không dùng `claim`/`stat` |
| Thời gian | TTS 41,1 s (tải model 14,1 s), render 325,5 s, tổng 370,0 s |
| Phụ đề 9:16 | 5/6 segment bị chia 2 cue theo số ký tự (cảnh báo `subtitle_split`) |

Đường dẫn MP4 (không commit):
- `D:\tmp\m2-run5-2026-11-04\produce\script-preview-16x9.mp4`
- `D:\tmp\m2-run5-2026-11-04\produce\script-preview-9x16.mp4`

Clip bị tua chậm (0,78× và 0,63×) vì lời đọc dài hơn đoạn clip có sẵn; sau khi thêm lời cho đủ 40 s cần xem lại tỉ lệ này. Chưa xem chuyển động toàn video.

### B7. Giới hạn của lần chạy 04/11

- 2 mẫu, `temperature=0`, free tier. Không đủ để nói về độ ổn định.
- PKB PDFCraft là dữ liệu thử, duyệt mô phỏng. Không đại diện PKB đã xác nhận.
- Chưa chạy với `video_description`, chưa chạy với CTA do người dùng đưa, chưa có ca `stat_display` thật.
- Số đo audio/MP4 là 1 mẫu CPU, không kiểm soát tải máy lúc đo; render chạy bằng #97 chưa merge và template #88 có patch `claim`.
- Chưa có người rà ngữ nghĩa khác ngoài tôi. Phần B3/B4 là đánh giá của một người, cần Định/Khánh xác nhận.
- Không dùng fallback `cta_narration_derived` làm bằng chứng; lần này không có.

## Lần chạy 30/10/2026 (contract 609d93d)

- **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định (contract M2, #83), Khánh (input, QA).
- **Code:** `services/worker/src/worker/m2/`, PR #92 (`feat/m2-generate-script`, head `c32e068`), chồng lên #90.
- **Contract:** prompt / schema / validator của Định ở **`609d93d`** (#83), đã đồng bộ ở `c32e068`.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier. **2 lời gọi**, $0 trả thật.
- **Dữ liệu** (`docs/report/m2-first-run-pdfcraft/`):

  | File | Nội dung |
  |---|---|
  | `input.json`, `build_input.py` | input đã sửa theo QA 29/10 (dùng cho cả 2 lần) |
  | `input-2026-10-29.json` | input cũ (lịch sử, dùng cho `run1/`, `run2/`) |
  | `run3-2026-10-30/` | **output thô**, bị validator từ chối (`script.json` là output thô, `validation.json` có lỗi) |
  | `run4-2026-10-30/` | output qua validator (`script.json` là output LLM sau bước worker: đã thêm `estimated_duration_s`, bỏ trường worker) |
  | `run3-2026-10-30/script.edited.json` | **bản chỉnh tay duy nhất**: chỉ sửa 2 `field_path` của lần 3 để kiểm offline (A2). Không sửa ngầm `script.json` nào |

> **Kết luận ngắn.**
> - **Qua validator: 1/2.** Lần 3 bị `llm_invalid_output` (2 lỗi `field_path` thiếu `identity.`); lần 4 qua. Chỉ 2 lần, chưa kết luận được độ ổn định.
> - **CTA: đạt cả 2 lần.** `destination: null`, không có `cta.fact_refs`. Lỗi tự điền URL của 29/10 không lặp lại sau khi đồng bộ contract.
> - **Hook và claim còn lỗi về nghĩa dù path đúng:** hook lần 4 nói "không muốn cài phần mềm phức tạp" nhưng ref `identity.tagline` không nói vậy; s04 thêm "nhanh chóng" không có trong fact. Validator không bắt được các lỗi này.
> - **Lời thoại ước tính ~19 s** (lần 3: 72 âm tiết = 19,2 s; lần 4: 71 âm tiết = 18,9 s), chưa bằng một nửa mục tiêu 40–45 s. Prompt 609d93d **đã có** chỉ dẫn 130–150 âm tiết nhưng model không theo.
> - **Chưa bàn giao được cho TTS/renderer** nếu không sửa tay (mục A7). Lead ưu tiên một kịch bản bàn giao từ PKB đã xác nhận; PKB PDFCraft vẫn là bản mô phỏng.

### A0. Fixture và LLM thật

| Loại | Kết quả | Chứng minh được gì |
|---|---|---|
| **Test fixture** (`uv run pytest`, 0 mạng) | 69 test trong `tests/m2` xanh | contract trùng byte 609d93d; validator port khớp parity; luồng `generate_script` |
| **LLM thật** (2 lần, mục A2–A7) | 1 qua, 1 `llm_invalid_output` | chất lượng output thật của prompt 609d93d trên PDFCraft |

Kết quả fixture **không** chứng minh chất lượng output LLM, thời lượng TTS hay thời lượng MP4.

### A1. Input đã sửa theo QA (Khánh, 29/10 17:50) và lead

| # | Việc | Cách xử lý |
|---|---|---|
| 1 | F7, F9: evidence khớp `/ro/tools/merge-pdf` còn `src_10` là `/en/...` | **Không tái hiện được trên dữ liệu Hoàng giữ** (chưa đọc được biên bản QA `docs/qa/review-pdfcraft-input-m2-first-run.md`: không có trên `dev`, trong PR #92 hay nhánh nào đã push). Crawl 21/10 không có trang `/ro` nào (0 chuỗi `/ro/` trong `crawl.json` và `pages/*`). `src_10` = `https://pdfcraft.devtoolcafe.com/en/tools/merge-pdf` (`fetched_at` 21/10 01:02Z, `http_status` 301, `final_url` giữ nguyên `/en`). Câu F9 có **nguyên văn** trong markdown trang `/en` (`EvidenceIndex`, theo từng `source_id`). Không cần crawl lại. `build_input.py` nay in URL của từng nguồn khi kiểm và loại fact nếu URL chứa `/ro/`. Nhờ Khánh chỉ ra file hoặc lệnh nếu vẫn thấy `/ro` |
| 2 | F3 và F7 gần trùng ý | Gộp thành 1 fact (`features[2]`), giữ evidence F3 ("Mọi xử lý diễn ra trong trình duyệt. Tệp của bạn không bao giờ rời khỏi thiết bị.", `src_01`) vì ngắn, tiếng Việt, nói thẳng "không rời khỏi thiết bị". Evidence F7 (tiếng Anh, "complete privacy") không dùng |
| 3 | Fact quyền riêng tư | Tên và mô tả ghi "PDFCraft tự công bố / PDFCraft công bố: …"; thêm vào `forbidden_claims`: không khẳng định tuyệt đối về bảo mật/riêng tư như sự thật đã kiểm chứng. Fact PDF→Word (F5) vẫn "chỉnh sửa được", không nói giữ nguyên định dạng; `forbidden_claims` vẫn cấm |
| 4 | Conflict 67+/132+ | `_note` ghi: **chưa giải quyết**, số công cụ chưa dùng, conflict `features` vẫn mở. `quality.conflicts: []` chỉ vì đây là input test đã lọc, **không đại diện PKB chuẩn**. `forbidden_claims` ghi "chưa thống nhất, conflict đang để mở" |
| 5 | `approved_pkb.status = "approved"` | `_note` đầu tiên ghi: status, reviewer và thời điểm duyệt là **mô phỏng để chạy thử**, chưa có BA, khách hàng hay merchant xác nhận |

Kết quả dựng: 5 fact bổ sung (F2, F3+F7, F4, F5, F9), 0 fact thiếu. `features`: F6, F2, F3+F7, F4, F5, F9. `limitations`: F8.

**Rủi ro nhỏ chưa xử lý:** evidence gốc của F2 là "Không đăng ký, **không giới hạn**, không chi phí ẩn." Lần 3 đã đưa "không giới hạn" lên chữ trên hình (s05) trong khi F8 ghi giới hạn 100 tệp / 500MB khi ghép. Mô tả F2 đã bỏ "không giới hạn", nhưng evidence thì phải nguyên văn. Nên cân nhắc cấm trong `forbidden_claims` hoặc chọn câu evidence ngắn hơn khi BA chốt PKB.

### A2. Cấu trúc JSON và validator

| | Lần 3 (thô) | Lần 4 |
|---|---|---|
| Kết quả | `llm_invalid_output`, 2 lỗi | `completed`, 0 lỗi |
| Lỗi | `hook` và `claim` s01: `fact_ref 'tagline.value' không tồn tại: 'tagline'`. Model ghi `field_path: tagline.value`, thiếu `identity.` | — |
| Cảnh báo | — | `estimated_duration_s_is_estimate`, `estimate_outside_target:18.9s` |
| Cảnh / segment / claim | 5 / 5 / 5 | 5 / 5 / 6 |
| Token vào / ra | 3 549 / 1 677 | 3 549 / 1 833 |
| $ giá niêm yết (trả thật $0) | 0,005257 | 0,005647 |

`field_path` ở prompt 609d93d chỉ nói "cú pháp `key.key[index].key` chính xác", không có ví dụ từ gốc `data`. Lần 4 ghi `identity.tagline` (đúng). Kiểm offline (không gọi LLM): sửa đúng 2 chỗ `tagline.value` → `identity.tagline.value` trong lần 3 (`run3-2026-10-30/script.edited.json`, **bản chỉnh tay, không phải output LLM**) thì qua validator, không còn lỗi nào khác. Chỉ dùng để biết lỗi nằm ở đâu, không tính là LLM sinh đạt.

### A3. CTA

Cả 2 lần: `cta = {text: "Xem thêm thông tin", destination: null}`, không có `cta.fact_refs`. Đúng luật 6: không lấy URL từ `identity.website`. Khác 29/10 (2/2 lần tự điền `https://pdfcraft.devtoolcafe.com`).

**Còn thiếu:** không cảnh nào có `role: cta` (cả 2 lần), nên chữ CTA không nằm trong cảnh nào. Renderer cần quyết định hiển thị CTA ở cuối video khi `destination = null`.

### A4. Hook và claim so với fact (nghĩa, không chỉ path)

**Lần 4 (qua validator)**

| Cảnh | Lời thoại | Claim → fact_ref | Đánh giá |
|---|---|---|---|
| hook (trường `hook`) | "Bạn có cần xử lý file PDF mà không muốn cài phần mềm phức tạp?" | `identity.tagline` | Path đúng, **nghĩa không đỡ**: tagline chỉ nói "ngay trong trình duyệt", không nói "không cài phần mềm phức tạp". Hơn nữa câu hook **không được đọc ở cảnh nào** (s01 đọc tagline) |
| s01 | Tagline nguyên văn | `identity.tagline` | Đúng nguyên văn. "riêng tư" là lời tagline của PDFCraft; lời thoại không ghi "PDFCraft nói" |
| s02 | "Kết hợp nhiều tệp PDF thành một tài liệu một cách dễ dàng." | `features[0]` (F6) | Claim đúng. "một cách dễ dàng" không có trong fact |
| s03 | "Bạn có thể đánh số trang tùy chỉnh vị trí và định dạng dễ dàng." | `features[3]` (F4) | Đúng F4. "dễ dàng" thêm, phụ đề "theo ý muốn" mềm hơn nguồn |
| s04 | "Chuyển đổi PDF sang tài liệu Word chỉnh sửa được một cách nhanh chóng." | `features[4]` (F5) | Claim đúng, **"nhanh chóng" không có căn cứ** (claim tốc độ). Không nói giữ định dạng (đúng forbidden claim) |
| s05 | "Mọi xử lý diễn ra trực tiếp trong trình duyệt và hoàn toàn miễn phí." | `pricing.free_plan`; `features[2]` (F3+F7) | Hai ref đúng. Lời không nói "tệp không rời thiết bị" (claim text có) và không ghi "PDFCraft công bố". Phụ đề "Dùng không cần đăng ký" và chữ trên hình "Không đăng ký - Không chi phí ẩn" thuộc F2 nhưng **không có claim / ref F2** |

**Lần 3 (thô, không qua validator)**

| Cảnh | Đánh giá |
|---|---|
| hook | "Bạn có biết PDFCraft giúp xử lý tài liệu hoàn toàn miễn phí ngay trong trình duyệt?" ref `tagline.value` (sai path). Nghĩa gần tagline hơn lần 4, cũng không được đọc ở cảnh nào |
| s01 | Tagline nguyên văn. Phụ đề bỏ "riêng tư" |
| s02–s04 | Claim đúng F6, F4, F5. "một cách dễ dàng" (s02), "linh hoạt" (s03) là từ thêm |
| s05 | Lời "Mọi xử lý diễn ra trực tiếp trong trình duyệt mà không cần đăng ký" chỉ ref `features[1]` (F2): phần "trong trình duyệt" không có ref. Chữ trên hình: "Không đăng ký, không giới hạn, không chi phí ẩn" (xem rủi ro "không giới hạn" ở A1) |

Không lần nào bịa giá, số liệu, so sánh, lời chứng thực hay số công cụ. Cả 2 lần tuân forbidden claims (không nêu số công cụ, không nói giữ định dạng).

### A5. Lời thoại có nội dung không có fact

Có, ở cả 2 lần (validator không kiểm phần này):
- Từ đánh giá/tốc độ thêm vào: "một cách dễ dàng" (s02), "dễ dàng" (s03), "nhanh chóng" (s04) lần 4; "một cách dễ dàng", "linh hoạt" lần 3.
- Hook lần 4: "không muốn cài phần mềm phức tạp".
- Chữ hiển thị (phụ đề, `text_card`) chứa nội dung F2 không có claim: s05 lần 4.

### A6. Kế hoạch hình ảnh

| | Lần 3 | Lần 4 |
|---|---|---|
| Asset dùng | `pdfcraft-merge`, `pdfcraft-pagenum`, `pdfcraft-word-export` | như lần 3 |
| Asset không dùng | `pdfcraft-word-result` | như lần 3 |
| `text_card` | s01 (hook), s05 | s01 (hook), s05 |
| `stat_display`, `ai_generation` | 0 | 0 |
| Fact không dùng | F9 (cách ghép), F8 (100 tệp / 500MB), F3+F7 | F9, F8 |

- Hình **khớp lời** ở cả 3 cảnh có clip (lần 4: s02 merge, s03 pagenum, s04 word-export, đều trùng claim). Lỗi lệch hình–lời của 29/10 (lời quyền riêng tư trên clip khác) không lặp lại.
- s05 (`proof`) lần 4: lời nói "trong trình duyệt + miễn phí", chữ trên hình nói "không đăng ký + không chi phí ẩn + trong trình duyệt". Lệch một phần.
- 3/4 clip được dùng; F8 (con số rõ ràng) và F9 không được dùng.
- **Template chưa hỗ trợ / thiếu:** cảnh `proof` không có layout riêng trong #88 (tạm map `feature_clip`); không có cảnh `stat` vì output không có `stat_display`; không có cảnh `cta` (A3); `steps`, `before_after`, `highlight_zoom` của FE#16 chưa có field trong contract M2 v1.

### A7. Phần cần sửa tay (lần 4, để bàn giao được)

Việc 1 bắt buộc; việc 2–6 là chất lượng nội dung:
1. **Kéo dài lời thoại** từ 71 lên 130–150 âm tiết bằng nội dung có căn cứ: F9 (cách ghép), F8 (100 tệp / 500MB, dạng stat), clip `word-result`, F2 có claim. Gần như viết lại phần thân.
2. Bỏ "nhanh chóng" (s04) và các "dễ dàng" nếu muốn bám sát fact.
3. Hook: sửa nội dung hoặc ref cho khớp nghĩa; quyết hook được đọc ở cảnh nào.
4. s05: thêm claim/ref F2 hoặc bỏ "Không đăng ký - Không chi phí ẩn" khỏi chữ hiển thị.
5. Nếu nói quyền riêng tư: ghi là PDFCraft công bố.
6. Quyết cách hiển thị CTA (không có cảnh `cta`, `destination` null).

Lần 3 muốn qua validator chỉ cần sửa 2 `field_path` (thêm `identity.`, đã kiểm offline ở A2); các việc 1–6 trên vẫn áp dụng tương tự.

### A8. `estimated_duration_s` so với 40–45 s

| | Âm tiết | `estimated_duration_s` (÷ 3,75) | `target_duration_s` model ghi | MP4 đo |
|---|---|---|---|---|
| Lần 3 | 72 | 19,2 | 42 | — |
| Lần 4 | 71 | **18,9** | 42 | — |
| 29/10, lần 1 / lần 2 | 78 / 73 | 20,8 / 19,5 | 42 | — |
| #88 viết tay | 132 | 35,2 | — | **42,1 s** (16:9, VieNeu + khoảng nghỉ + clip) |

- Đây **không** phải số đo TTS hay MP4 (cách đếm bỏ sót số, đơn vị, từ tiếng Anh như "PDF").
- Prompt 609d93d luật 1 đã ghi "tổng lời thoại khoảng 130–150 âm tiết làm mốc khởi đầu". Model **không theo** (71–72 âm tiết, 4/4 lần chạy gần 20 s), nên chỉ dẫn mềm là chưa đủ.
- **Không sửa prompt của Định ở đây.** Đề xuất cụ thể cho Định, dự kiến đăng ở comment #83:
  1. Đổi "mốc khởi đầu" thành yêu cầu: mỗi cảnh `demo` 2–3 segment, mỗi segment 10–16 âm tiết; tự đếm tổng trước khi trả; thiếu thì thêm segment về cách dùng / giới hạn **có fact** (F9, F8), không thêm tính từ quảng cáo.
  2. Thêm ví dụ `field_path` tính từ gốc `data`: `identity.tagline.value`, `features[0].description`; nhắc không bỏ `identity.`.
  3. Cấm tính từ đánh giá/tốc độ ("dễ dàng", "nhanh chóng", "mạnh mẽ") trừ khi có trong evidence; chữ trên hình và phụ đề không chứa thông tin ngoài claim.
  4. Làm rõ `hook.text` có phải được đọc ở cảnh đầu không.
  5. Tuỳ chọn: schema `minItems: 2` cho `narration_segments` của cảnh `demo`. Chỉ ép số câu; Gemini có thể bỏ qua.

  Sau khi Định sửa, đồng bộ lại worker và chạy lại.

### A9. Giới hạn của lần chạy 30/10

- 2 lần, 1 sản phẩm, 1 input. Input **chưa phải PKB đã xác nhận**: fact bổ sung, status `approved`, reviewer và thời điểm đều mô phỏng; `product_id` giả lập.
- **AISoEasy chưa chạy M2.** Chờ Khánh xác nhận PKB AISoEasy (đang sửa ở #90).
- Chưa làm: `llm_revise`, retry khi `llm_invalid_output`, lưu DB / API / queue, TTS / render. Chưa đo audio / MP4.
- Bảng đánh giá ở A4–A6 là rà tay của Hoàng; Định và Khánh rà lại.

### A10. Tình trạng các đề xuất của 29/10

Đã được xử lý trong 609d93d (theo prompt và validator trong repo): CTA không lấy URL từ PKB, kiểm `cta.fact_refs`, placeholder `product_id` / `knowledge_version`, chỉ dẫn 130–150 âm tiết (nhưng chưa đủ, A8). Còn mở: kiểm nghĩa giữa lời và fact, lời/chữ hiển thị ngoài claim, hình khớp lời (có thể là việc của QA), cách đánh dấu fact do người duyệt bổ sung ở `features[]`.

---

## Lịch sử: lần chạy 29/10/2026 (contract 8f86523)

Giữ nguyên để so sánh. Chưa dùng để kết luận bản mới đã đạt.

- **Ngày:** 29/10/2026. **Người chạy:** Hoàng (AI). **Rà soát nội dung:** Định (contract M2, #83).
- **Code:** `services/worker/src/worker/m2/`, PR `feat/m2-generate-script` (chồng lên #90).
- **Contract:** prompt / schema / validator của Định ở commit **`8f86523`** (#83), chép nguyên byte.
- **Model:** `gemini-3.5-flash-lite`, `temperature=0`, free tier. **2 lời gọi** (2/500 RPD), 0 lần 429, $0 trả thật.
- **Dữ liệu:** `docs/report/m2-first-run-pdfcraft/` gồm `input-2026-10-29.json` (input lúc đó, nay `input.json` là bản 30/10), `build_input.py`, `run1/`, `run2/`.

> **Kết luận ngắn.**
> - Cả 2 lần đều **chưa qua validator** (`llm_invalid_output`), nên **chưa có kịch bản bàn giao được** cho TTS/renderer.
> - Lỗi còn lại sau lần 2 chỉ có 1: `cta.destination` model tự điền URL website. Đặt trường này về null thì cả 2 output qua validator.
> - Lời thoại chỉ ước tính khoảng **20 s**, xa mức 40–45 s.
> - Fact ref của hook và claim (12/12) đều trỏ tới fact có thật, có evidence. Nhưng 2 hook trỏ nhầm fact về nghĩa (đúng ra phải là F7).
> - Ref của CTA (`website`) không tồn tại, và validator không kiểm ref này.
> - Lỗi còn lại nằm ở phần lời thoại vượt quá claim và ở chỗ hình không khớp lời.

### 0. Tách kết quả fixture và kết quả LLM thật

| Loại | Kết quả | Chứng minh được gì |
|---|---|---|
| **Test fixture** (`uv run pytest`, 0 mạng) | 60 test M2 xanh (tổng worker 260) | contract trùng byte 8f86523; validator cho cùng lỗi đầu tiên với script của Định trên 24 ca; `generate_script` xử lý đúng các ca thành công, sai schema, sai fact_ref, 429 RPD, input sai, JSON hỏng |
| **LLM thật** (2 lần, mục 2–7) | 2/2 `llm_invalid_output` | chất lượng output thật của prompt v8f86523 trên PDFCraft |

Kết quả fixture **không** chứng minh chất lượng output LLM, thời lượng TTS hay thời lượng MP4.

### 1. Input: PKB nào, chọn fact thế nào

`input.json` ghi rõ: *"PKB lang-p4 + fact bổ sung mô phỏng bước xác nhận PKB, evidence nguyên văn, chờ BA xác nhận"*.
Dựng lại bằng `build_input.py`.

- **PKB gốc:** `D:\tmp\extract-pdfcraft-lang-p4` (#90; extract 21/10 trên crawl 21/10 `en,vi`). Trong 10 lần extract
  PDFCraft, mỗi lần chỉ có 4–5 trong 9 fact của BA. Chọn lang-p4 vì `identity.name` có evidence hợp lệ, không có warning.
- **Giữ** (đã có trong PKB, khớp bộ BA, không warning):
  - `identity.name`;
  - `identity.tagline` (F1);
  - `pricing.free_plan`;
  - `features[0]` "Hợp nhất PDF" (F6);
  - `limitations[0]` "100 tệp / 500MB" (F8).
- **Bỏ:**
  - `identity.description` ("Hơn 67 công cụ…", liên quan conflict);
  - `identity.category` (evidence yếu, không thuộc bộ BA);
  - `pricing.plans[0]` (plan Free có `price_unit: month` chỉ là giữ chỗ, warning `free_only_placeholder_period`);
  - `features[1..7]`, `use_cases` (không thuộc bộ BA, BA chưa kiểm).
- **Conflict `features`** (số công cụ 67 / 132+): bỏ khỏi `quality.conflicts`. Đây là **giải quyết thủ công, chờ BA**.
  BA đã ghi không dùng con số này, và các fact có con số đã bị bỏ.
- **Fact bổ sung mô phỏng bước xác nhận PKB:**
  - Nguồn: F2, F3, F4, F5, F7, F9 trong `_refs/notebooklm/pdfcraft-thong-tin-san-pham.md`.
  - Điều kiện: chỉ thêm khi câu trích có **nguyên văn** trong trang đã crawl. Kiểm bằng `EvidenceIndex` của M1 (chuẩn hoá NFC + khoảng trắng).
  - Kết quả: **6/6 tìm thấy**, ở `src_01` (trang chủ), `src_02` (/en/tools), `src_10` (/en/tools/merge-pdf). Không có fact nào phải bỏ vì thiếu trang.
  - Ghi vào `features[1..6]` với `origin: crawled`, `source_id`, evidence nguyên văn tiếng Anh/Việt, `name`/`description` tiếng Việt theo BA.
  - **Giới hạn schema:** PKB v0.3 không cho `origin: owner` / `edited_by` ở `features[]`. `Fact.origin` cố định là `crawled`, `previous` chỉ có ở `identity`. Người duyệt mô phỏng (`00000000-0000-4000-8000-0000000000b1`, 29/10 08:30Z) chỉ được ghi trong `_note`. **Đề xuất M1/Định:** cần cách đánh dấu fact do người duyệt bổ sung trong `features`.
- **Asset:**
  - 4 clip tự quay: `pdfcraft-pagenum`, `pdfcraft-word-export`, `pdfcraft-word-result`, `pdfcraft-merge`. Mỗi clip có `screen_recording`, `internal_demo`, chỉ tham chiếu ID, không commit media.
  - Ảnh AI **không** đưa vào allowlist: enum `kind` không có giá trị phù hợp. Để LLM tự sinh `generation_request` nếu cần.
- **`content_context`:** chỉ có `forbidden_claims`, gồm:
  - số công cụ;
  - giá / đánh giá / số người dùng / so sánh;
  - "PDF→Word giữ nguyên định dạng".

  Platform, intent, audience và CTA để mặc định.

#### Phát hiện cho M1 (#90)

- **Extract bỏ sót 5/9 fact cốt lõi:** F3 (trang chủ), F4, F5 (/en/tools), F7, F9 (/en/tools/merge-pdf). F2 chỉ nằm trong evidence của plan Free giữ chỗ.
- **Không phải lỗi chọn trang:** `src_01`, `src_02`, `src_10` đều nằm trong 10 trang đã gửi LLM (lang-p4 `sources`). LLM nhận trang nhưng không trích ra.
  - Follow-up cần xem lại **prompt / giới hạn số fact mỗi trang**. Trang /en/tools liệt kê hơn 100 công cụ, LLM chọn các công cụ khác.
  - Thêm trang /tools/* vào prompt sẽ không giúp, vì các trang này đã có sẵn.
- **Conflict do LLM ghi ở mức cả mảng `features` là quá rộng.**
  - Theo luật cha/con đề xuất ở #83, conflict này sẽ chặn mọi `features[i]`, dù nó chỉ nói về số công cụ.
  - M1 sẽ chuẩn hoá `field` về trường cụ thể (việc của #90).

### 2. Cấu trúc JSON (validator)

| | Lần 1 | Lần 2 |
|---|---|---|
| Code | schema gửi Gemini giữ `const` | `const` → `enum: [giá trị]` (sửa sau lần 1) |
| Kết quả | `llm_invalid_output`, lỗi schema đầu tiên: `schema_version: 'p1-ac-03.v1-draft' was expected` (model ghi `"0.3"`) | `llm_invalid_output`, 1 lỗi: `cta.destination phải null khi người dùng không cung cấp đích` |
| Lỗi khác (kiểm offline, không gọi thêm) | sửa `schema_version` thì còn đúng lỗi `cta.destination` | — |
| Nếu `cta.destination = null` | qua validator | qua validator |
| Token vào / ra | 3 411 / 1 732 | 3 411 / 1 796 |
| $ giá niêm yết (trả thật $0) | 0.005353 | 0.005513 |

**Lỗi 1: Gemini nhận `const` nhưng không tuân.**
- Prompt của Định không nêu giá trị `schema_version` của output, nên model chép `schema_version` của PKB (0.3).
- Worker sửa ở lớp chuyển schema (`const` → `enum`), có test. Lần 2 đúng.
- Ở #90, `const` chỉ có ở `origin: "crawled"`; model ghi đúng nhờ description, nên trước đó chưa lộ.
- **Đề xuất Định:** thêm vào prompt luật 10 câu "`schema_version` = `p1-ac-03.v1-draft`".

**Lỗi 2: CTA destination tự điền, lặp lại cả 2 lần.**
- Cả 2 lần đều ghi `destination: "https://pdfcraft.devtoolcafe.com"` kèm `cta.fact_refs: [{source_id: "src_01", field_path: "website"}]`.
- Model lấy URL từ `identity.website` của PKB, trái luật 6 ("CTA vắng mặt … destination là null").
- Ref này **không trỏ tới fact nào**:
  - `website` không có ở cấp gốc của `data` (`resolve_field_path` → KeyError);
  - `identity.website` là chuỗi do code M1 điền từ URL gốc, không có `origin` / `source_id` / `evidence`.
- **Lỗ hổng validator:** `content_errors`, và cả bản gốc của Định, không kiểm `cta.fact_refs`. Ref sai này lọt qua mà không có lỗi. Lỗi duy nhất được báo là `destination` khác null.
- Worker không sửa hộ. **Đề xuất Định:**
  - (a) prompt nói rõ "destination null kể cả khi PKB có `identity.website`";
  - (c) hoặc BE bỏ `identity.website` khỏi PKB gửi M2.

  Theo ý mình, **(a)** là cách ít thay đổi nhất. Muốn CTA có URL thì người dùng nhập ở `content_context.cta`, như luật 6 đang cho phép.
- Validator nên kiểm `cta.fact_refs` (và `hook.fact_refs`) cùng luật với claim.

### 3. Độ đúng claim so với nguồn

Mỗi claim → `fact_ref` → fact → evidence (câu nguồn). Cả 2 lần, mọi fact_ref của hook / claim đều **trỏ tới fact có
thật, có evidence**. Không có fact inferred, conflict hay asset ngoài allowlist. Một số ref **trỏ nhầm về nghĩa** (cột Đánh giá). Lỗi nằm ở phần lời thoại **vượt quá** claim, nhưng validator không
kiểm phần này.

**Lần 1**

| Cảnh | Lời thoại (tóm tắt) | Claim → fact_ref | Câu nguồn | Đánh giá |
|---|---|---|---|---|
| hook | "Bạn có biết xử lý PDF… mà không cần tải lên máy chủ?" | `features[2].description` (F3) | "Mọi xử lý diễn ra trong trình duyệt. Tệp của bạn không bao giờ rời khỏi thiết bị." | Gần đúng. "không tải lên máy chủ" là ý của F7 (`features[5]`), trỏ nhầm fact |
| s01 | tagline | `identity.tagline.value` (F1) | "Xử lý PDF miễn phí, riêng tư và mạnh mẽ ngay trong trình duyệt" | Đúng nguyên văn |
| s02 | "Công cụ hợp nhất PDF… kéo và thả để sắp xếp lại" | `features[0].description` (F6) | "Kết hợp nhiều tệp PDF thành một tài liệu. Công cụ hợp nhất PDF trực tuyến miễn phí với kéo và thả…" | Đúng. Text claim chép dính tiêu đề ("Hợp nhất PDF Kết hợp…"), cần sửa chữ |
| s03 | "thêm số trang … **và dễ dàng chuyển đổi sang Word**" | `features[3]` (F4) | "Add page numbers to PDF documents…" | Nửa sau (Word) **không có claim / fact_ref** trong cảnh |
| s04 | "Mọi xử lý diễn ra trong trình duyệt, tệp hoàn toàn riêng tư" | `features[2]` (F3) | (như hook) | Đúng; "hoàn toàn riêng tư" hơi mạnh hơn nguồn |
| s05 | "Dùng không cần đăng ký, không có chi phí ẩn." | `features[1]` (F2) | "Không đăng ký, không giới hạn, không chi phí ẩn." | Đúng |

**Lần 2**

| Cảnh | Lời thoại (tóm tắt) | Claim → fact_ref | Câu nguồn | Đánh giá |
|---|---|---|---|---|
| hook | "…hoàn toàn riêng tư mà không cần tải lên máy chủ không?" | `identity.tagline.value` (F1) | "…miễn phí, riêng tư…" | "không tải lên máy chủ" **không có trong F1**, đúng ra phải là F7 |
| s01 | tagline | `identity.tagline.value` (F1) | như trên | Đúng nguyên văn |
| s02 | "…tệp của bạn không bao giờ rời khỏi thiết bị" | `features[2]` (F3) | "Mọi xử lý… không bao giờ rời khỏi thiết bị." | Đúng |
| s03 | "thêm số trang hoặc chuyển đổi tài liệu" | `features[3]` (F4) | "Add page numbers…" | "chuyển đổi tài liệu" mơ hồ, không có claim |
| s04 | "xuất tệp sang định dạng Word để chỉnh sửa" | `features[4]` (F5) | "Convert PDF to editable Word (DOCX) documents." | Đúng; **không** khẳng định giữ định dạng (tuân forbidden claim) |
| s05 | "Dùng ngay hoàn toàn miễn phí không cần đăng ký." | `features[1]` (F2), type `pricing` | "Không đăng ký, không giới hạn, không chi phí ẩn." | Đúng ý; "hoàn toàn miễn phí" có căn cứ ở F1 / `free_plan` nhưng không được trỏ |

Không lần nào bịa giá, số liệu, so sánh hay lời chứng thực. Cả 2 lần đều tuân forbidden claims (không nêu số công cụ).

### 4. Mapping fact / segment / asset

| | Lần 1 | Lần 2 | #88 viết tay (tham khảo) |
|---|---|---|---|
| Cảnh / segment / claim | 5 / 5 / 5 | 5 / 5 / 5 | 7 / 16 / — |
| Fact dùng | F1, F2, F3, F4, F6 | F1, F2, F3, F4, F5 | F1–F9 |
| Fact không dùng | F5, F7, F8, F9 | F6, F7, F8, F9 | — |
| Asset dùng | merge, pagenum, word-export | merge, pagenum, word-export | 4 clip + ảnh AI |
| Asset không dùng | word-result | word-result | — |
| `ai_generation` | 0 | 0 | 1 (hook) |
| `stat_display` | 0 | 0 | 2 cảnh stat (F1–F3, F8) |

**Hình không khớp lời:**
- Lần 1, s04: lời nói về quyền riêng tư nhưng hình là clip xuất Word.
- Lần 2, s02: lời về quyền riêng tư (F3) trên clip ghép PDF. `purpose` ghi "ghép PDF chạy cục bộ" nhưng claim không trỏ F7.

Validator chỉ kiểm asset có trong allowlist, không kiểm hình có khớp lời không.

### 5. Cảnh template chưa hỗ trợ

Vai trò cảnh output: `hook`, `demo`, `proof`, `cta`. `visual_plan.kind`: `text_card` (hook, cta), `screen_recording`.

- **#88 HyperFrames** (hook, stat, feature_clip, cta):
  - `screen_recording` → `feature_clip`: được.
  - `text_card` ở hook / cta → layout `hook` / `cta`, nhưng hook của #88 dùng ảnh nền AI và output không có `generation_request`. Cần quy ước hook không ảnh hoặc ảnh mặc định.
  - `role: proof` không có layout riêng, nên tạm map sang `feature_clip`.
  - **Layout `stat` không được dùng**, vì output không có `stat_display`, dù F8 (100 tệp / 500MB) là ứng viên rõ ràng.
- **FE#16** (feature_clip, steps, before_after, highlight_zoom): `steps`, `before_after`, `highlight_zoom` chưa có field trong contract M2 v1 (README của Định). Output không sinh, và cũng không thể sinh.
- Không có cảnh nào ngoài 4 layout của #88. Phần thiếu là ở chiều ngược lại: output dùng quá ít loại cảnh (không có stat, mỗi cảnh chỉ 1 câu).

### 6. `estimated_duration_s` so với 40–45 s

| | Âm tiết | `estimated_duration_s` (÷ 3.75) | `target_duration_s` model ghi | MP4 đo |
|---|---|---|---|---|
| Lần 1 | 78 | **20.8** | 42 | — |
| Lần 2 | 73 | **19.5** | 42 | — |
| #88 viết tay | 132 | 35.2 | — | **42.1 s** (16:9, TTS VieNeu + khoảng nghỉ + clip) |

- Model ghi `target_duration_s: 42` nhưng chỉ viết đủ lời cho khoảng một nửa. Prompt không có chỉ dẫn về độ dài lời thoại (số câu, số âm tiết).
- #88 cho thấy 132 âm tiết ≈ 42 s MP4. Vậy để đạt 40–45 s cần khoảng **130–150 âm tiết**.
  - Ở mức 3.75 âm tiết/s, ước tính hụt khoảng 7 s so với MP4, vì MP4 còn có khoảng nghỉ, chuyển cảnh, đuôi.
  - Đây là ước tính, cần hiệu chỉnh bằng TTS thật.
- Cách đếm âm tiết đếm thiếu số, đơn vị và từ tiếng Anh ("PDF" = 1, đọc là 3; "500MB" = 1).
- Đây **không** phải số đo TTS hay MP4.
- **Đề xuất Định:** thêm vào luật 1 "lời thoại khoảng 130–150 âm tiết, 10–16 câu" và gợi ý dùng `stat_display` cho fact có số.

### 7. Mức sửa tay cần thiết

Để bàn giao được, mỗi lần chạy cần khoảng 7 việc sửa. Việc 1 và 2 bắt buộc; việc 3–7 là chất lượng nội dung:

1. `cta.destination` → null, hoặc chốt hướng (b) ở mục 2 (cả 2 lần).
2. **Kéo dài lời thoại khoảng gấp đôi** (73–78 → khoảng 130–150 âm tiết). Thêm F7 / F9 (cách ghép, chạy cục bộ), cảnh stat F8, clip `word-result`. Đây là việc lớn nhất, gần như viết lại phần thân.
3. Hook trỏ đúng F7 (cả 2 lần).
4. Lần 1 s03: bỏ "chuyển đổi sang Word" hoặc thêm claim F5. Lần 2 s03: bỏ "chuyển đổi tài liệu".
5. Đổi hình cho khớp lời: lần 1 s04, lần 2 s02.
6. Lần 1 s02: sửa chữ trong claim text.
7. Lần 2 s05: trỏ thêm F1 / `free_plan` cho "hoàn toàn miễn phí".

So với #88 (tham khảo, không phải đáp án): #88 có nhịp "giá trị → 3 demo từng bước → con số → CTA" và mỗi demo có 3 câu theo clip. Output LLM là danh sách 5 câu tagline/tính năng. Đủ đúng nhưng chưa thành video demo.

### 8. Đề xuất cho Định (#83). Worker không tự sửa contract

1. Prompt nêu hằng `schema_version` của output (luật 10). Worker đã đổi `const` → `enum` ở schema gửi Gemini.
2. CTA destination khi PKB có `identity.website`: (a) sửa prompt, hoặc (c) BE bỏ trường này (mục 2). `identity.website` không có provenance nên không làm căn cứ được.
3. Prompt thêm chỉ dẫn độ dài (130–150 âm tiết) và gợi ý `stat_display` cho fact có số.
4. Placeholder cho `product_id` và `knowledge_version`. Hiện worker gửi ở tin nhắn user vì prompt không có chỗ.
5. Ảnh AI đã sinh (vd. `paperwork-s1.jpg` của #88): enum `kind` của `permitted_assets` không có loại phù hợp.
6. Validator chưa kiểm:
   - **`cta.fact_refs`**: cả 2 lần trỏ `website`, không tồn tại, nhưng không bị bắt;
   - lời thoại có ý không nằm trong claim nào (lần 1 s03);
   - hình có khớp lời không.

   Hai ý sau có thể là việc của bước QA / người duyệt chứ không phải validator.
7. Đã biết từ #83: `identity.category.value` lọt conflict. Test worker ghi lại hành vi hiện tại và chờ Định sửa.
8. PKB v0.3: chưa có cách đánh dấu fact do người duyệt bổ sung ở `features[]` (mục 1).

### 9. Giới hạn

- Chỉ 2 lần chạy, 1 sản phẩm, 1 bộ input. Lần 1 và lần 2 khác code ở bước chuyển `const` → `enum`, nên **không** dùng để đo độ dao động. Ở các phần giống nhau (5 cảnh, CTA destination, khoảng 75 âm tiết), hai lần nhất quán.
- Input là bản chọn tay, có fact bổ sung mô phỏng, **chờ BA xác nhận**. `product_id` là UUID giả lập.
- Chưa làm: `llm_revise`, retry khi `llm_invalid_output`, lưu DB / API / queue, TTS / render.
- Bảng "Đánh giá" ở mục 3–4 là rà tay của Hoàng; Định rà lại theo contract.
