# AISoEasy: PKB nháp 30/10/2026 (chưa xác nhận)

> **PKB nháp, chưa xác nhận.** Đây là output máy (Gemini `gemini-3.5-flash-lite`), chưa ai duyệt. Không dùng làm thông tin đã xác nhận cho kịch bản cho tới khi QA đối chiếu và người dùng xác nhận (xem #67, #83). Mục "Còn sai hoặc thiếu" bên dưới liệt kê những gì đã biết là chưa đúng.

- **Nguồn:** https://aisoeasy.co/ (1 trang, crawl 29/10 07:51 UTC, vùng VN, locale en-US). Không crawl lại; mọi lần chỉ chạy lại extract trên cùng crawl.
- **Code:** PR #90, nhánh `feat/m1-extract-worker`.
- **Bốn lần chạy thật**, mỗi lần 1 lời gọi LLM trong quota miễn phí: ba lần ngày 30/10 và **lần 4 ngày 02/11** (sau góp ý QA, xem mục "Lần 4"). `pkb.json` ở thư mục này là lần 4 (mới nhất); lần 3 nằm ở `run3/`.

## File
| File | Nội dung |
|---|---|
| `pkb.json` | **Lần 4 (02/11, mới nhất).** `data` (PKB v0.3) và `sources[]`, output máy chưa sửa |
| `extract.json` | Số fact, tỉ lệ evidence khớp, warnings của lần 4 |
| `pages/src_01-other-home.raw.md` | Markdown trang chủ, đúng file `sources[0].markdown_path` trỏ tới (dùng chung cho mọi lần). Evidence của mọi fact là đoạn trích nguyên văn từ file này. Là markdown, không có HTML thô. |
| `run1/`, `run2/`, `run3/` | `pkb.json` + `extract.json` của lần 1, 2 và 3, giữ làm lịch sử |
| `pkb.reviewed.json` | **Mô phỏng bước xác nhận (02/11).** `pkb.json` lần 4 cộng 2 audience bị LLM bỏ, `origin: owner`, evidence nguyên văn, `edited_by` / `edited_at` là giá trị mô phỏng. Ghi chú nằm ở khoá `review_note` cạnh `data` / `sources` (PKB v0.3 không có trường ghi chú). Qua `validate_pkb`. Không phải PKB đã được người dùng xác nhận |
| `pkb-content-review-draft.json` | Bản nháp rà nội dung (làm từ output lần 3, `run3/pkb.json`) để QA xem lại; giữ nguyên `pkb.json` là output LLM thô. Chưa phải PKB đã được người dùng/merchant xác nhận. |

## Lần 4 (02/11): sửa theo QA Khánh (#67, mục "Sửa ngay")

Chạy thật **đúng 1 lần** trên crawl 29/10 (không crawl lại): 1 lời gọi, 35 fact, evidence khớp nguồn 100 %, ~$0,0085. Code mới nằm ở `extract/context.py` (không gọi LLM, có test bằng dữ liệu giả). Output máy ở `pkb.json`; bản mô phỏng bước xác nhận ở `pkb.reviewed.json`.

| Mục #67 | Kết quả lần 4 |
|---|---|
| 1. `usp[3..9]` thiếu nền tảng | **Đã sửa bằng code.** Evidence nối heading gần nhất phía trên (`### TikTok\nThe Virality Engine\n2.58M+ Views`), `text` thêm tên khối (`2.58M+ Views (TikTok)`; Facebook Page, YouTube, Facebook Group tương tự). Evidence vẫn nguyên văn và ≤ 200 ký tự |
| 2. `usp[9]` | `self_reported_metric:usp[9]` **đã có** (số có dấu `+` giờ tính là số liệu). Evidence nay là `…1,867+\nelite members, +720 in H1` nên giữ ngữ cảnh "elite members". LLM không tự ghi nhãn vào `text` (`+720 in H1 (Facebook Group)`), phần nhãn do evidence mang |
| 3. `use_cases[0..4]` | **Chưa đạt.** Tên phòng ban nằm ở dòng *trên* heading (`Sales`, rồi `### Close deals…`), giữa heading và dòng kết quả còn Level / Learning path / AI tools, tổng quá 200 ký tự. Giữ evidence cũ, thêm `evidence_context_missing:use_cases[0..4]`, giữ `self_reported_metric`. Muốn đạt cần cho phép nhiều evidence span hoặc nới giới hạn 200 (đã nêu ở bản rà nội dung P1) |
| 4. `audiences` | Lần 4 chỉ trả **2** (Individuals, Employees); **mất Small businesses và AI Brands & Technology Partners** của lần 3. `Employees` có, `jtbd` null, evidence `Role-based learning paths\n## Training built for real jobs\nSales` (dòng đầu do code nối nhãn; từ "Employees" không nằm trong evidence). Code nối nhãn `For AI Brands & Technology Partners` vào evidence của audience đối tác đã chạy được trên output lần 3 nhưng lần 4 LLM không trả audience này. `pkb.reviewed.json` thêm lại cả hai với `origin: owner` (mô phỏng) |
| 5. Challenge | **Vẫn thiếu.** Feature "Become an AI Partner" của lần 3 cũng mất: LLM trả feature tên `For AI Brands & Technology Partners` (lấy nhãn làm tên), nên `section_not_covered:Become an AI Partner` xuất hiện lại. **Không thêm được vào `pkb.reviewed.json`**: `features[]` chỉ nhận `origin: crawled` ở model PKB v0.3 (`Fact.origin`), thêm feature `owner` là đổi contract. **Quyết định 02/11: không mở `owner` cho `features[]` ở v0.3; Challenge để ngoài PKB cho video P1** (ghi ở mục "Đề xuất cho phiên bản schema sau" của spec M1). Evidence nguyên văn để dành cho schema sau: `### Challenges & rewards\nJoin real-world challenges, climb leaderboards, and earn rewards.` và `### Become an AI Partner\nSend us your details and the AI So Easy team will reach out to discuss a distribution partnership.` |

**Không làm (mục "Hoãn" của #67):** `avg 36k views/video`, `~250 videos & posts deployed`, `usp[10]` (evidence dính chữ giữ nguyên; code từ chối nối vì dòng này cách heading `### Facebook Group` quá 3 dòng, `evidence_context_missing:usp[10]`), `usp[11]` giữ nhãn, số liệu thị trường ngoài PKB.

**Cảnh báo mới `evidence_context_missing:<path>` (9 cái):** `use_cases[0..4]` như trên; `usp[10]` như trên; `usp[0..2]` là số liệu ở phần đầu trang, heading gần nhất là H1 cách quá 200 ký tự (không có tên khối nào để thêm, cảnh báo này gần như nhiễu). Mọi số `usp` / `use_cases` vẫn là số website tự công bố; trong video chỉ dùng 1–2 số, ghi "theo AISoEasy".

**Dùng cho QA:** evidence mở rộng chỉ gắn thêm đoạn nguyên văn phía trên, không đổi số hay nhãn. Khi so với `pages/src_01-other-home.raw.md`, evidence khớp sau khi bỏ `*`, `_`, `#` và gộp khoảng trắng như cũ.

## Bản rà nội dung cho video P1 (chưa xác nhận)

Tạo `pkb-content-review-draft.json` từ output lần 3 sau góp ý QA #67. Chỉ cập nhật ngữ cảnh/evidence của các metric AISoEasy mà crawl snapshot chứng minh trực tiếp: Bản nháp này làm trước lần 4 và không được cập nhật theo lần 4; lần 4 và `pkb.reviewed.json` là bản mới hơn.

- Bổ sung nền tảng TikTok, Facebook Page, YouTube và Facebook Group vào các fact tương ứng; phân biệt `+720 members in H1` với tổng 1,867+ thành viên.
- Giữ riêng `5M+ view infrastructure` ở khối đối tác, không nhập nhằng với `5.06M+ AI content views`.
- Chuẩn hóa evidence `87.6% audience in Vietnam` để giữ ranh giới từ; không thay đổi giá trị.
- Bản nháp đưa `usp[9]` vào nhóm warning `self_reported_metric`; `metric_label_mismatch:usp[9]` vẫn được giữ vì nguồn đặt `members` trước `+720`, nên code không thể chứng minh nhãn này theo quy tắc số-đứng-trước-nhãn.

Đối chiếu evidence đã dùng đều khớp nguyên văn snapshot sau khi gộp khoảng trắng và dài không quá giới hạn 200 ký tự của PKB v0.3. Đây là số liệu website tự công bố, chưa xác minh độc lập; không được diễn đạt trong video như số liệu đã kiểm chứng. Output LLM gốc và ba lần chạy vẫn được giữ nguyên.

**Để sau / cần thống nhất:** evidence của 5 use case không thể chứa đồng thời phòng ban, tiêu đề và kết quả trong giới hạn 200 ký tự vì các đoạn đó cách nhau bởi nội dung learning path. Không ghép các đoạn rời thành một quote giả. Cần quyết định cách biểu diễn nhiều evidence span hoặc giới hạn mới trước khi sửa contract; đến lúc đó giữ cảnh báo và không dùng các use-case metric trong video. Challenge, số liệu ~250 videos/posts, audience Employees và market stats không cần cho video P1 hiện tại, nên để ngoài phạm vi bản rà này.

QA cần đối chiếu file nháp này rồi xác nhận phần có thể dùng. Trạng thái dữ liệu vẫn là **draft**.

## Cách đối chiếu
1. Mở `pkb.json`, lấy `source_id` + `evidence` của fact cần kiểm.
2. Tìm `evidence` trong `pages/src_01-other-home.raw.md` (khớp sau khi bỏ dấu `*`, `_`, `#` và gộp khoảng trắng).
3. `sources[0].variant` là `raw`: LLM nhận markdown thô của trang. Lần 29/10 nhận bản `fit` (làm rơi dòng giá).

## So sánh các lần
| | 29/10 | 30/10 lần 1 | 30/10 lần 2 | 30/10 lần 3 | 02/11 lần 4 (mới nhất) |
|---|---|---|---|---|---|
| Thay đổi so với lần trước | | gửi `raw`; tách giá khuyến mãi, tên plan từ heading | thêm `audiences`, `usp`; prompt trích các khối còn thiếu; kiểm độ phủ section | `usp` mỗi số liệu 1 mục; kiểm `metric_label_mismatch`; thêm Challenge / đối tác / nhân viên vào prompt | nối heading khối vào evidence (code), số có dấu `+` tính là số liệu; prompt: Challenge, Employees, nhãn đầy đủ |
| Bản markdown gửi | `fit` | `raw` | `raw` | `raw` | `raw` |
| Tổng fact | 17 | 19 | 28 | **36** | **35** |
| `identity` | 4 | 5 | 5 | 5 | 5 |
| `pricing` | 5 | 5 | 5 | 5 | 5 |
| `features` | 3 | 4 | 5 | **6** | 6 |
| `use_cases` | 5 | 5 | 5 | 5 | 5 |
| `audiences` | | | 3 | 3 | **2** |
| `usp` | | | 5 | **12** | 12 |
| Evidence khớp nguồn | 94,1 % | 100 % | 100 % | 100 % | 100 % |
| Giá Individual Pro | list 9, thiếu promo | list 18 / promo 9 | list 18 / promo 9 | list 18 / promo 9 (`50% off, limited spots`) | list 18 / promo 9 (`50% off, limited spots`) |
| Token vào / ra | 2.668 / 1.447 | 3.543 / 1.706 | 4.005 / 2.636 | 4.179 / 3.027 | 4.407 / 2.862 |
| Chi phí giá niêm yết | ~$0,0044 | ~$0,0053 | ~$0,0078 | ~$0,0088 | ~$0,0085 |
| `section_not_covered` | 11 | 13 | 6 | **5** | **6** |
| `metric_label_mismatch` | | | 1 (`usp[0]`) | **0** | **0** |
| Warning khác | `evidence_not_found:pricing.plans[0]`, `value_not_in_evidence:pricing.plans[1].name` | 0 | 10 `self_reported_metric` | 16 `self_reported_metric` | 17 `self_reported_metric` (có `usp[9]`), 9 `evidence_context_missing` |

Số `section_not_covered` và `metric_label_mismatch` của lần 29/10, 1 và 2 tính bằng cách phát lại output cũ qua luật hiện tại (offline, không gọi LLM); riêng lần 2 lần gọi thật chạy luật cũ hơn nên in ít cảnh báo hơn, `run2/extract.json` đã tính lại. 29/10 dùng bản `fit` nên danh sách section khác các lần sau. Lần 3 dùng đúng luật hiện tại. Phát lại output lần 3 cho cùng `data`, `sources` và 5 cảnh báo section.

### Section của trang chủ qua các lần
| Section (heading) | Lần 1 | Lần 2 | Lần 3 | Lần 4 | Ghi chú |
|---|---|---|---|---|---|
| Vietnam's AI community already trusts AI So Easy. | bỏ | bỏ | **bỏ** | bỏ | Đoạn dẫn của khối traction; số nằm ở các section con |
| TikTok, Facebook Page, YouTube, Facebook Group | bỏ | phủ | phủ | phủ | Traction (b), `usp` |
| Free AI videos? Here's what you're missing. | bỏ | phủ | phủ | phủ | Đối tượng cá nhân (e) |
| Find your next role with AI skills | bỏ | phủ | phủ | phủ | Jobs board (d) |
| Partner with us to bring AI adoption to millions of SMEs | bỏ | phủ | phủ | phủ | Đối tác (e) |
| Become an AI Partner | bỏ | bỏ | phủ (`features[5]`) | **bỏ** (LLM thay bằng feature tên nhãn) | Chương trình đối tác (d) |
| New skills required every year | bỏ | bỏ | **bỏ, dự kiến** | bỏ, dự kiến | Số liệu thị trường (c), xem dưới |
| New AI tools released weekly | bỏ | bỏ | **bỏ, dự kiến** | bỏ, dự kiến | (c) |
| SMEs have no AI training team | bỏ | bỏ | **bỏ, dự kiến** | bỏ, dự kiến | (c) |
| Retail business saves 200 hours/month after 8 weeks | bỏ | bỏ | **bỏ** | bỏ | Câu chuyện thành công trong mục "Content & community", không thuộc brief |

## Các khối (a)–(e) của brief, theo lần 3 (lịch sử; lần 4 xem mục "Lần 4")
| Khối | Kết quả |
|---|---|
| (a) Lộ trình theo phòng ban | `use_cases[0..4]`: Sales, Marketing, Finance, HR và Operations (trang có 5 khối). `title` dạng "Sales: Close deals faster with AI". Evidence là dòng kết quả kèm số (`+35% more opportunities handled per week`, `5x content output`, `Save 12 hours / month`, `40% reduction in hiring time`, `+28% operational productivity`). Tên phòng ban và tiêu đề nằm ở `title`, không nằm trong evidence (cách dòng kết quả quá 200 ký tự) |
| (b) Traction H1 2026 | `usp[0..11]`, mỗi mục 1 số + nhãn, `text` bắt đầu "Theo AI So Easy công bố:". `usp[0..2]` là `5.06M+ AI content views`, `33,973+ new followers`, `1.3M+ unique reach on Facebook`: **đã đúng** (lần 2 ghép lệch một nấc) |
| (c) Số liệu thị trường | Không đưa vào PKB, theo brief. Xem dưới |
| (d) Jobs board, Challenge, đối tác | Có Jobs board (`features[4]`) và chương trình đối tác (`features[5]`, "Become an AI Partner"). **Thiếu Challenge** |
| (e) Đối tượng | `audiences[0..2]`: Small businesses, Individuals, AI Brands & Technology Partners. **Thiếu "nhân viên theo phòng ban"** |

### (c) Số liệu thị trường: chưa có trường phù hợp
Brief nêu "12+ new skills required every year", "50+ new AI tools released weekly", "90% SMEs have no AI training team". **Crawl 29/10 không có các số này**: bộ đếm chạy bằng hiệu ứng nên markdown chỉ có `0+`, `0+`, `0%` (và `0,00M+` / `0,00K+` / `0,00M+` ở khối traction). Prompt bảo bỏ qua bộ đếm toàn số 0 và PKB không có số 0 nào. Ba section thị trường vì vậy còn `section_not_covered`; đó là kết quả dự kiến, không phải sót.

Đây là số liệu về thị trường, không phải fact về sản phẩm, nên v0.3 không có trường phù hợp. **Đề xuất cho v0.3.x:** thêm nhóm `proof` hoặc `market_stat` (text + nguồn + evidence), tách khỏi `usp`. Muốn lấy được số thật thì crawl phải chờ bộ đếm chạy xong (việc của bước crawl, ngoài PR này).

## Còn sai hoặc thiếu (lần 3, lịch sử; lần 4 xem mục "Lần 4")
**Thiếu**
1. **Challenge** ("7-Day AI Builder Challenge …") chưa thành feature. Trên trang nó chỉ là 6 tiêu đề thẻ "Learner Showcase" (tên + điểm từng người học), không có đoạn mô tả; LLM bỏ qua dù prompt đã nhắc.
2. **Nhân viên theo phòng ban** chưa có trong `audiences`.
3. Một số số liệu traction chưa được lấy, ví dụ `~250 videos & posts deployed`.
4. Số liệu thị trường (c): chờ quyết định trường ở v0.3.x.

**Cần QA đối chiếu**
1. `usp[3]`..`usp[6]`: `2.58M+ Views`, `35k+ followers`, `2.3M+ Views`, `18.8k followers` bị tách thành từng số nên **không còn nói rõ nền tảng** (TikTok cho `usp[3]`, `usp[4]`; Facebook Page cho `usp[5]`, `usp[6]`). Nền tảng chỉ có ở heading phía trên trong trang. Khi dùng trong video phải ghi nền tảng.
2. `usp[9]` = `+720 in H1` mất nhãn (trang ghi `1,867+ elite members, +720 in H1` ở Facebook Group, tức +720 thành viên). Không dùng riêng mục này; dùng cùng `usp[8]`. Code không bắt được vì nhãn "in H1" có trong evidence liền sau số.
3. `usp[11]` = `5M+ view infrastructure` (khối đối tác) trùng ý với `usp[0]` (`5.06M+`) nhưng là số khác trên trang: giữ cả hai, QA xem có dùng không.
4. Mọi số trong `usp` và `use_cases` là **số website tự công bố**, chưa ai kiểm. Khi dùng trong video phải nói "theo AISoEasy".
5. `audiences[].jtbd` lấy từ evidence, gần nguyên văn; xem có đúng ý trang không.
6. `identity.company` = "ECOMDY GLOBAL LLC": đối chiếu với nguồn. `pricing.free_plan` = true với evidence là tiêu đề mục "Learn for free — or unlock every opportunity with Pro".

## Điểm khác brief (đã duyệt 30/10; các mục ghi "02/11" chờ duyệt)
- Độ phủ section chỉ kiểm trang `page_type` = `other` (trang chủ, about). Trang features / docs / faq / pricing có hàng chục section lặp dạng mà PKB chỉ lấy vài mục. Đổi được bằng `ExtractSettings.coverage_page_types`.
- `self_reported_metric` chỉ áp cho `usp` và `use_cases`.
- Ngưỡng 15 từ cho "section đáng kể". Evidence chỉ tính ở lần xuất hiện đầu trong trang; evidence vắt qua ranh giới 2 section phải lấn vào section kia ≥ 20 ký tự. Hai luật sau được thêm sau khi đối chiếu output lần 2: luật đầu tiên tính mọi lần xuất hiện nên evidence ngắn như tên sản phẩm phủ cả trang và che mất 3 section bị bỏ (`4e4c379`, `49bf640`).
- `metric_label_mismatch:<path>`: với `usp` / `use_cases` có số liệu, mỗi số trong `text` / `title` phải đứng liền trước nhãn của nó trong evidence (cùng dòng hoặc dòng kế). Nhãn không có trong evidence (LLM dịch nhãn) thì bỏ qua. Test dùng đúng ca `usp[0]` lần 2.
- Định dạng warning `section_not_covered:<heading>` theo brief. Heading có thể chứa dấu `:` và warning không ghi `source_id`; bên nhận không nên tách warning theo `:`.
- **02/11, nối ngữ cảnh khối vào evidence** (`usp`, `use_cases`, `audiences`): evidence không chứa heading thì nối từ heading gần nhất phía trên tới hết evidence cũ, cắt thẳng từ markdown nguồn. Quá 200 ký tự thì giữ evidence cũ và cảnh báo `evidence_context_missing:<path>`. Hai chốt chặn thêm ngoài brief: **tối đa 4 dòng** (`MAX_LINES`: heading + 3 dòng thân; xa hơn thường là dòng thống kê chung của cả trang, ca `87.6%audience in Vietnam` sau `### Facebook Group` suýt bị gán cho nhóm Facebook) và **tên khối chỉ thêm vào `text` của `usp` khi heading ≤ 4 từ** (`NAME_MAX_WORDS`: `TikTok`, `Facebook Group`; heading dạng câu thì chỉ nối evidence, không thêm vào `text`).
- **02/11, dòng nhãn (kicker):** khi evidence chính là dòng heading, nối thêm dòng ngay trên nếu là nhãn: ≤ 6 từ, không chữ số, không kết thúc bằng `.!?`, không phải heading, mục danh sách hay trích dẫn (`For AI Brands & Technology Partners` trên `## Partner with us…`; `+28% operational productivity` trên `## Learner Showcase` bị loại vì có chữ số). Evidence nối nhãn có thể lấn sang section trước ≥ 20 ký tự và tính là phủ section đó (`MIN_OVERLAP`); chấp nhận.
- **02/11, số có dấu `+` đứng trước** (`+720 in H1`) tính là số liệu tự công bố (`self_reported_metric`), nhãn đi sau có thể là chữ bất kỳ. `C++11` không tính. Các ca không phải số liệu (`Pro 10 seats`, `Step 2 of 3`) giữ nguyên.

## Chạy lại offline PDFCraft và ElevenLabs (output LLM 21/10, không gọi LLM)
| | PDFCraft | ElevenLabs |
|---|---|---|
| Fact | 17 | 27 |
| `section_not_covered`, chỉ trang `other` (mặc định) | **1**: `100% Riêng tư` | **8**: `Two platforms built on the same research foundation`, `Image & Video`, `Text to Speech API`, `Speech to Text API`, `Showcasing the global impact of AI audio research`, `Research that redefines human technology interaction`, `Expressive Mode for Agents`, `Safety, built in` |
| `section_not_covered` nếu kiểm mọi loại trang | 37 | 122 |
| Warning khác | `value_not_in_evidence:identity.name`, `free_only_placeholder_period:pricing.plans[0]` | `promo_above_list:pricing.plans[2]` |

Các warning "khác" là luật có từ trước chạy trên dữ liệu 21/10, không phải luật mới. Cảnh báo của ElevenLabs là các khối thật của trang chủ (dòng sản phẩm, nghiên cứu, an toàn) chưa thành fact; không thấy cảnh báo vô lý. 37 và 122 là lý do không kiểm trang features / docs / faq. Hai output 21/10 không có `usp` / `use_cases` có số nên không sinh `self_reported_metric`.
