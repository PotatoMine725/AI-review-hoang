# Test Case Specification — Module 1 (Product Intelligence)

| Thuộc tính | Chi tiết |
|---|---|
| **Module / Use Case** | Module 1 - Frontend Merchant — Trải nghiệm Web, Onboarding, xử lý URL và duyệt PKB (AI-review-FE) |
| **Yêu cầu kiểm thử** | Merchant nạp URL ElevenLabs, theo dõi Crawl → Extract → Hoàn tất, dùng upload fallback, review PKB/Evidence và xung đột, Submit/Approve khóa version, điều hướng các màn Merchant; UI responsive desktop/mobile |
| **Tài liệu đối chiếu** | Task Lead Tester ngày 12/10/2026 · T07 · T09 · T10 v2.2 · T12b Golden Facts ElevenLabs · AI-review-FE `onboarding.tsx`, `product-detail.tsx`, `model.ts`, `tests/m1.browser.cjs` |
| **Môi trường & Công cụ** | AI-review-FE · trình duyệt Chromium/Chrome · viewport desktop, 390px, 320px · DevTools Console/Network · ảnh/video bằng chứng · dữ liệu ElevenLabs theo T12b |
| **Tác giả (Tester)** | **Trương Thị Kiều Nhi (@TruongThiKieuNhi245)** — Frontend & Trải nghiệm Merchant |
| **Người rà soát (Reviewer)** | **Võ Đức Phú (@VD-PHU)** — Lead Tester |
| **Ngày cập nhật** | 12/10/2026 |
| **Phiên bản (Version)** | v1.0 (Test Design — chưa chạy) |

## 1. Điều kiện và cách ghi nhận

- Chạy trên AI-review-FE ở môi trường do nhóm cấp; dùng workspace/data test riêng để case duplicate lặp lại được. Tạo project kiểm thử bằng onboarding, không dựa vào các product seed Gamma/Notion/Linear để giả làm ElevenLabs.
- Dùng `https://elevenlabs.io` và affiliate URL chính thức trong T12b. Với case conflict, nhập giá/tính năng Merchant khác dữ liệu crawl trước khi hoàn tất job để tạo tình huống đối chiếu.
- Ghi rõ build/commit, URL môi trường, trình duyệt, viewport và vai trò Merchant cho mỗi lần chạy.
- UI hiện có banner **Mock local**: không gọi website ElevenLabs, crawler hoặc AI thật; thao tác job là thủ công và dữ liệu lưu cục bộ. Vì vậy kết quả hiện chỉ xác nhận trải nghiệm mock UI, không xác nhận tích hợp FE-BE hay tính đúng đắn của dữ liệu ElevenLabs.
- Các case có trạng thái **Draft / Chưa chạy**. Điền Actual Result, Pass/Fail/Blocked và bằng chứng sau khi thực thi; không coi “Ready for Test” là Pass.
- Dùng mẫu bug T09 nếu Actual khác Expected. Đính kèm bước tái hiện, ảnh/video, console và Network log nếu có; không đưa secrets vào bằng chứng.

## 2. Onboarding và nạp URL

| ID | Test Case / Priority | Tiền điều kiện & dữ liệu | Các bước thực hiện | Kết quả mong đợi | Actual / Status |
|---|---|---|---|---|---|
| **TC_FE_MERCHANT_001** | Website URL bắt buộc · P0 | Merchant ở `/merchant/onboarding`; URL để trống | Bấm **Bắt đầu phân tích** | Không tạo sản phẩm/job; hiện lỗi rõ rằng Website URL bắt buộc; focus/label giúp nhận diện trường lỗi | Chưa chạy · Draft |
| **TC_FE_MERCHANT_002** | Affiliate URL bắt buộc và định dạng · P0 | Website `https://elevenlabs.io`; affiliate trống hoặc `javascript:alert(1)` | Thử bắt đầu với từng giá trị | Không tạo sản phẩm/job; báo lỗi rõ ở affiliate URL; không thực thi URL nguy hiểm | Chưa chạy · Draft |
| **TC_FE_MERCHANT_003** | Nạp ElevenLabs với affiliate URL hợp lệ · P0 | Website `https://elevenlabs.io`; affiliate URL hợp lệ theo T12b | Nhập hai URL, bấm **Bắt đầu phân tích** | Chấp nhận dữ liệu; tạo một project/job mock; URL và affiliate hiển thị đúng, không bị cắt hoặc đổi nhầm. Ghi rõ đây là tạo mock, không phải crawl thật | Chưa chạy · Draft |
| **TC_FE_MERCHANT_004** | Trường bổ sung tùy chọn · P1 | Onboarding mới | Để trống tên, tagline, giá/tính năng bổ sung, forbidden claims, logo; điền hai URL bắt buộc và bắt đầu | Không chặn luồng vì các trường tùy chọn trống; không hiện lỗi bắt buộc sai | Chưa chạy · Draft |
| **TC_FE_MERCHANT_005** | URL sai protocol/format · P1 | Website lần lượt `ftp://elevenlabs.io`, `javascript:...`; affiliate hợp lệ | Nhập từng giá trị và bấm **Bắt đầu phân tích** | Từ chối URL, hiển thị lỗi có thể hiểu được, không tạo project/job. Ghi riêng validation browser và validation ứng dụng | Chưa chạy · Draft |
| **TC_FE_MERCHANT_006** | URL trùng dạng có slash cuối · P0 | Workspace đã có `https://elevenlabs.io` | Nhập `https://elevenlabs.io/` và affiliate hợp lệ; bắt đầu | Nhận diện cùng website sau canonicalization; báo trùng rõ ràng, không tạo bản ghi thứ hai | Chưa chạy · Draft |
| **TC_FE_MERCHANT_007** | URL trùng dạng domain trần · P0 | Workspace đã có `https://elevenlabs.io` | Nhập `elevenlabs.io` cùng affiliate hợp lệ; bắt đầu | Chuẩn hóa về cùng URL đã lưu và hiện thông báo rõ website đã tồn tại; không tạo bản ghi duplicate. Nếu báo sai định dạng thay vì nhận diện trùng thì ghi Fail/bug theo yêu cầu lead | Chưa chạy · Draft |
| **TC_FE_MERCHANT_008** | URL khác path trên cùng host · P2 | Có URL gốc ElevenLabs trong workspace | Nhập URL cùng host nhưng path khác nếu sản phẩm cho phép | Xác nhận quy tắc duplicate theo URL chuẩn: không gộp nhầm URL sản phẩm có path khác nếu path là một phần identity. Chốt expected với lead nếu business rule chỉ cho phép một product/domain | Chưa chạy · Draft |

## 3. Trạng thái xử lý và fallback upload

| ID | Test Case / Priority | Tiền điều kiện & dữ liệu | Các bước thực hiện | Kết quả mong đợi | Actual / Status |
|---|---|---|---|---|---|
| **TC_FE_MERCHANT_009** | Status Polling 3 bước Crawl → Extract → Hoàn tất · P0 | Onboarding ElevenLabs đã tạo job; môi trường tích hợp có API status polling | 1. Bắt đầu xử lý URL.<br>2. Không bấm điều khiển tiến trình thủ công; quan sát UI và Network trong suốt job.<br>3. Đối chiếu các status/response backend với nhãn, thứ tự bước và trạng thái kết thúc trên UI.<br>4. Kiểm tra poll dừng khi job hoàn tất. | UI tự cập nhật đúng ba bước **Crawl → Extract → Hoàn tất** từ status thực; không cần Merchant refresh/bấm “Bước tiếp theo”; không báo hoàn tất sớm và dừng polling sau terminal status. Nếu chỉ chạy mock không có API thì đánh dấu Blocked cho polling tích hợp, không Pass theo thao tác demo | Chưa chạy · Draft |
| **TC_FE_MERCHANT_010** | Fallback upload khi crawl bị chặn · P1 | Onboarding đã nhập ElevenLabs; có PDF và ảnh hợp lệ | 1. Mô phỏng/nhận trạng thái WAF hoặc trang yêu cầu đăng nhập.<br>2. Chọn PDF/ảnh thủ công trong vùng upload.<br>3. Bấm hành động tiếp tục/phân tích tài liệu.<br>4. Đóng/mở lại màn hình nếu luồng hỗ trợ; kiểm tra file và dữ liệu form còn đó. | Có thông báo lý do fallback; chọn được file, file được liệt kê và có thể mở/gỡ; tiếp tục được luồng tài liệu; UI không nói crawl website thành công. Ghi rõ upload local hay server | Chưa chạy · Draft |
| **TC_FE_MERCHANT_011** | Upload PDF và ảnh hợp lệ · P1 | File PDF, PNG/JPEG/WebP hợp lệ, mỗi file ≤ 5 MB | Upload từng loại bằng picker; thử thêm file bằng drag/drop nếu UI hỗ trợ | File được liệt kê đúng tên/dung lượng, có thể mở hoặc gỡ; tiếp tục onboarding được. Ghi rõ file lưu local hay server | Chưa chạy · Draft |
| **TC_FE_MERCHANT_012** | Upload vượt số lượng/dung lượng/định dạng · P1 | 6 file; file >5 MB; file không thuộc PDF/PNG/JPEG/WebP | Thử từng trường hợp upload | Từ chối đúng trường hợp vi phạm, báo giới hạn dễ hiểu, giữ các file hợp lệ đã chọn và không làm treo form | Chưa chạy · Draft |

## 4. Review PKB ElevenLabs

| ID | Test Case / Priority | Tiền điều kiện & dữ liệu | Các bước thực hiện | Kết quả mong đợi | Actual / Status |
|---|---|---|---|---|---|
| **TC_FE_MERCHANT_013** | Mở PKB đúng sản phẩm · P0 | Job đã hoàn tất; có product ID ElevenLabs | Mở `/merchant/products/[id]` | Trang hiển thị đúng tên/website ElevenLabs, trạng thái job và version PKB; không mở nhầm sản phẩm | Chưa chạy · Draft |
| **TC_FE_MERCHANT_014** | Hiển thị bốn nhóm thông tin Merchant yêu cầu · P0 | PKB có overview, pricing, features, audience | Mở từng tab/nhóm thông tin | Merchant xem đủ **Tổng quan, Bảng giá, Tính năng, Khách hàng mục tiêu**; nội dung và trạng thái active tab khớp. Ghi bug nếu nhãn/cấu trúc hiện tại không đáp ứng yêu cầu | Chưa chạy · Draft |
| **TC_FE_MERCHANT_015** | Evidence giới hạn 200 ký tự · P0 | PKB có facts/pricing kèm evidence | Mở Evidence popover; kiểm tra độ dài và thao tác mở source | Evidence không quá 200 ký tự; popover đọc được; source link trỏ đúng trang ElevenLabs có liên quan (pricing fact → pricing page; feature → trang chứng minh tính năng) | Chưa chạy · Draft |
| **TC_FE_MERCHANT_016** | Evidence/source không có hoặc sai nguồn · P1 | Fact không có source hoặc dùng URL ngoài ElevenLabs | Mở popover và bấm source | Thiếu/sai nguồn được nhận diện, không gây crash hoặc dẫn đến URL giả/sai; không trình bày nội dung mock như bằng chứng đã xác minh | Chưa chạy · Draft |
| **TC_FE_MERCHANT_017** | Giải quyết xung đột giá Merchant và bản crawl · P0 | Khi onboarding, nhập giá Merchant khác giá do job trả về; mở PKB draft | Mở xung đột giá; so sánh hai giá trị; lần lượt chọn Merchant và Website/crawl; lưu draft; tải lại | Giá trị hai nguồn và lựa chọn được trình bày rõ; unresolved phải còn trước khi chọn; lựa chọn đã lưu được giữ sau reload; giá Merchant phải được xác nhận theo UI rule | Chưa chạy · Draft |
| **TC_FE_MERCHANT_018** | Giải quyết xung đột tính năng Merchant và bản crawl · P0 | Khi onboarding nhập ít nhất một tính năng khác bản crawl/mock; mở PKB draft | Mở conflict tính năng; chọn Merchant rồi Website/crawl; lưu và tải lại | Hai giá trị phân biệt; phải chọn nguồn trước Submit; lựa chọn đã lưu được giữ sau reload và không âm thầm ghi đè dữ liệu đối chiếu | Chưa chạy · Draft |
| **TC_FE_MERCHANT_019** | Chặn Submit khi còn conflict/validation error · P0 | Draft có conflict chưa resolve; lặp lại với thiếu mô tả/tính năng bắt buộc | Kiểm tra trạng thái nút **Gửi review**; thử kích hoạt nếu khả dụng; đọc thông báo | Submit không chuyển PKB sang `in_review`; nút bị disable hoặc có validation rõ; chỉ ra field/conflict cần xử lý | Chưa chạy · Draft |
| **TC_FE_MERCHANT_020** | Gửi duyệt (Submit) · P0 | Draft hợp lệ, conflict đã giải quyết, giá đã xác nhận | Lưu thay đổi; xác nhận không còn unsaved/validation error; bấm **Gửi review** (nút Submit theo UI hiện tại); kiểm tra status/version | PKB chuyển `draft → in_review`; dữ liệu đã lưu được giữ; submit không tạo version hoặc bản ghi trùng ngoài quy tắc đã chốt; UI cập nhật trạng thái và hành động tiếp theo | Chưa chạy · Draft |
| **TC_FE_MERCHANT_021** | Merchant duyệt và khóa version · P0 | PKB `in_review`; vai trò Merchant; nội dung đã kiểm tra | Bấm **Merchant duyệt PKB** (Approve theo UI hiện tại); xác nhận dialog; thử chỉnh sửa trường, lưu hoặc tạo thay đổi trên version đã duyệt | PKB chuyển `approved`; version được đánh dấu hiện hành; nội dung/version đã duyệt chỉ đọc và không thể bị ghi đè. Muốn sửa phải tạo draft/version mới | Chưa chạy · Draft |
| **TC_FE_MERCHANT_022** | Lịch sử/version sau approve · P1 | Đã approve một version; tạo draft mới nếu luồng cho phép | Mở lịch sử, đối chiếu version cũ và mới | Version đã duyệt trước đó còn nguyên; version mới không ghi đè snapshot cũ; version đang xem được nhận diện rõ | Chưa chạy · Draft |

## 5. UI/UX và responsive

| ID | Test Case / Priority | Tiền điều kiện & dữ liệu | Các bước thực hiện | Kết quả mong đợi | Actual / Status |
|---|---|---|---|---|---|
| **TC_FE_MERCHANT_023** | Desktop layout · P1 | Viewport desktop, ví dụ 1440×900 | Kiểm tra onboarding, modal trạng thái, tabs, conflict controls, evidence popover và actions | Không chồng lấn/cắt chữ; vùng thao tác và trạng thái dễ nhận biết; nội dung bảng có thể đọc và thao tác được | Chưa chạy · Draft |
| **TC_FE_MERCHANT_024** | Mobile 390 px · P1 | Viewport rộng 390 px | Đi qua onboarding, upload, PKB tabs, conflicts và submit/approve | Không tràn ngang trang; controls dễ bấm; nội dung không bị che; table/sections có cách cuộn phù hợp | Chưa chạy · Draft |
| **TC_FE_MERCHANT_025** | Mobile 320 px · P1 | Viewport rộng 320 px | Lặp luồng chính ở 320 px; kiểm tra thông báo lỗi và popover | Không mất chức năng hoặc nội dung quan trọng; không có horizontal overflow ngoài vùng bảng có chủ đích; popover/dialog nằm trong viewport hoặc cuộn được | Chưa chạy · Draft |

## 6. Merchant shell, dashboard và điều hướng

| ID | Test Case / Priority | Tiền điều kiện & dữ liệu | Các bước thực hiện | Kết quả mong đợi | Actual / Status |
|---|---|---|---|---|---|
| **TC_FE_MERCHANT_026** | Merchant shell và điều hướng chính · P1 | Mở AI-review-FE ở vai trò demo Merchant | Kiểm tra header/sidebar, nav active và lần lượt mở Dashboard, Onboarding, Sản phẩm & PKB, Thư viện nội dung, Biên tập nội dung | Vai trò và vị trí hiện tại nhận diện được; các route mở đúng màn, không 404/crash; link không lạc sang Admin/Creator ngoài ý muốn | Chưa chạy · Draft |
| **TC_FE_MERCHANT_027** | Dashboard Merchant và danh sách sản phẩm · P1 | Workspace test riêng; đã tạo product ElevenLabs qua onboarding | Mở `/merchant`; theo link Sản phẩm; tìm ElevenLabs; mở Review PKB rồi quay lại danh sách | Dashboard/list render không lỗi; product hiển thị đúng tên, URL, job và PKB state; link mở đúng ID; empty/filter state không che product đã tạo | Chưa chạy · Draft |
| **TC_FE_MERCHANT_028** | Smoke các màn Merchant còn lại · P2 | Vai trò Merchant; nếu có item thì dùng item demo hiện hữu | Mở `/merchant/campaigns`, `/merchant/library`, `/merchant/library/[id]` của item hiện có và `/merchant/content`; kiểm tra heading, navigation và console | Mỗi route render ổn định, có nội dung hoặc empty state phù hợp, điều hướng quay lại được. Chỉ smoke UI/navigation; không thay phạm vi QC video/Admin của Duyên | Chưa chạy · Draft |

## 7. Ghi chú đối chiếu implementation hiện tại

Các ghi chú dưới đây là đối chiếu source để định hướng xác minh, không phải kết quả chạy test:

1. `onboarding.tsx` và `product-detail.tsx` hiển thị rõ đây là **mock local**. Job không polling backend; Merchant bấm điều khiển các bước mock bằng tay.
2. Stepper onboarding hiện có ba nhãn **Kết nối website → Tìm sitemap/trang sản phẩm → Trích xuất thông tin thành PKB**, không trùng wording lead yêu cầu **Crawl → Extract → Hoàn tất**. Xác minh AC/nhãn trước khi kết luận bug.
3. Product detail hiện có các tab **Giá & Gói, Tính năng, Đối tượng / JTBD, Thương hiệu & USP**; mô tả sản phẩm nằm ngoài tabs. So với yêu cầu **Tổng quan, Bảng giá, Tính năng, Khách hàng mục tiêu**, cần ghi nhận chênh lệch labels/IA.
4. Source/evidence hiện được tạo từ dữ liệu mẫu; trang có banner nói rõ nguồn/giá chưa xác minh. Không dùng demo data làm bằng chứng sự thật về ElevenLabs.
5. `model.ts` canonicalize URL bằng cách chuẩn hóa scheme, `www`, hash và slash cuối nhưng giữ query string; duplicate hiện tra trong workspace local. Source hiện dùng `new URL(value)` nên domain trần `elevenlabs.io` có thể bị từ chối thay vì được chuẩn hóa; kiểm tra case 007 sát yêu cầu lead và ghi bug nếu tái hiện.
6. Upload được lưu bytes trong IndexedDB local, tối đa 5 file × 5 MB; picker nhận PDF/PNG/JPEG/WebP.
7. Bốn tab trong yêu cầu có thể khác cấu trúc hiện tại. Giữ Expected theo task lead; nếu team xác nhận các nhãn hiện tại là thiết kế được chấp thuận, cập nhật test basis trước khi đóng bug.

## 8. Tổng kết

### Ma trận đối chiếu task Lead Tester

| Yêu cầu LeadTester | Case bao phủ | Đánh giá coverage |
|---|---|---|
| Toàn bộ trải nghiệm Web Merchant trên AI-review-FE | TC_FE_MERCHANT_001–028; Onboarding, PKB, shell/dashboard, products list và các route Merchant | Đủ task chi tiết và bổ sung smoke coverage cho màn Merchant; không nhận deep test Admin/API/NFR/video QC của nhóm khác |
| Nạp `https://elevenlabs.io` và affiliate URL | TC_FE_MERCHANT_003; dữ liệu T12b | Có happy path; affiliate required/invalid được tách ở TC_FE_MERCHANT_002 |
| Validation trường bắt buộc/tùy chọn | TC_FE_MERCHANT_001–005 | Có website/affiliate required, optional fields, protocol/format |
| Duplicate `https://elevenlabs.io/` và domain trần `elevenlabs.io` | TC_FE_MERCHANT_006–008 | Có hai dạng bắt buộc; thêm path khác host làm boundary. Case domain trần phải bắt lỗi nếu không nhận diện trùng |
| Status Polling Crawl → Extract → Hoàn tất | TC_FE_MERCHANT_009 | Đủ yêu cầu, nhưng chỉ có thể Pass khi có API polling thật; mock hiện chỉ có bước thủ công |
| Upload fallback file ảnh/PDF | TC_FE_MERCHANT_010–012 | Có luồng sau WAF/login, ảnh/PDF hợp lệ và validation loại/kích thước/số file |
| PKB có Tổng quan, Bảng giá, Tính năng, Khách hàng mục tiêu | TC_FE_MERCHANT_014 | Đủ; expected giữ nguyên nhãn lead giao, ghi bug nếu UI khác |
| Evidence popover ≤200 ký tự, nguồn đúng trang ElevenLabs | TC_FE_MERCHANT_015–016 | Đủ giới hạn, popover, URL nguồn và tình huống nguồn thiếu/sai |
| Conflict giá và tính năng Merchant vs bản crawl | TC_FE_MERCHANT_017–019 | Đủ hai loại conflict, chọn/lưu nguồn và chặn Submit khi chưa xử lý |
| Submit, Approve và khóa version | TC_FE_MERCHANT_020–022 | Đủ transition, read-only và snapshot/version lịch sử |
| Desktop, mobile 390px và 320px | TC_FE_MERCHANT_023–025 | Đủ ba kích thước bắt buộc |
| Ghi nhận bug theo T09 | Mục 1 (cách ghi nhận) và Actual/Status của mỗi case | Đủ quy trình; điền evidence, môi trường và severity khi thực thi |
| Merchant shell/dashboard/product list và các route Merchant còn lại | TC_FE_MERCHANT_026–028 | Bổ sung smoke coverage cho trọng tâm toàn giao diện Merchant; không nhận deep test Admin/video của Duyên |

**Kết luận coverage:** Không thấy đầu việc nào trong danh sách Phú giao bị bỏ sót ở mức test design. “Đủ case” không đồng nghĩa “đã chạy/Pass”. TC_FE_MERCHANT_009 cần môi trường tích hợp; TC_FE_MERCHANT_007 có nguy cơ Fail theo code mock; chênh lệch stepper/tabs phải được ghi nhận theo expected của lead.

| Nhóm | Số case |
|---|---:|
| Onboarding / URL | 8 |
| Job progress / upload fallback | 4 |
| PKB review / Evidence / conflict / version | 10 |
| Responsive / UI | 3 |
| Merchant shell / dashboard / navigation smoke | 3 |
| **Tổng** | **28** |

**Tiêu chí hoàn tất:** chạy các case trong môi trường đã chỉ định; ghi Actual, Pass/Fail/Blocked và evidence; lập bug theo T09 cho sai khác. Báo cáo riêng kết quả mock UI và kết quả tích hợp API. Phạm vi này là Frontend Merchant do Nhi phụ trách.