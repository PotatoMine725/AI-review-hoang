<!--
SRS (Software Requirements Specification) v0.2 ("Updated from Feedback"), do team lead (@VV6505) gửi ngày 2026-10-07 (file gốc: tempsrs.md), dựa trên bản của BA (@khanhphi27). Được @PotatoMine725 đưa vào repo ngày 2026-10-07.
Nội dung giữ nguyên văn. Góp ý và câu hỏi mở: xem issue #28, #23 và docs/logs/qa-log.md. Từ bản này, mọi thay đổi đi qua PR vào docs/specs/.
Khi mâu thuẫn với decision-log / đặc tả module / ERD đã chốt, các tài liệu đó được ưu tiên cho tới khi bản này được cập nhật.
-->

**SOFTWARE REQUIREMENTS SPECIFICATION**

**Project:** AI Review Content Factory & Affiliate Network\
**Document Type:** Software Requirements Specification — SRS\
**Version:** 0.2\
**Status:** Draft for Review (Updated from Feedback)\
**Product Stage:** MVP\
**Based on:** PRD v1.0 + BRD Draft

-----
**1. Introduction**

**1.1 Purpose**

Tài liệu SRS này mô tả chi tiết các yêu cầu phần mềm của hệ thống **AI Review Content Factory & Affiliate Network**.

Tài liệu được sử dụng làm cơ sở cho:

- System Design
- UI/UX Design
- Database Design
- API Design
- Development
- Testing
- User Story refinement
- Acceptance Criteria
- Sprint Planning

SRS tập trung trả lời câu hỏi:

**Phần mềm phải làm gì để đáp ứng các Business Requirements đã được xác định trong BRD?**

-----
**1.2 Product Scope**

AI Review Content Factory & Affiliate Network là nền tảng hỗ trợ:

**AI Product**

→ Product Intelligence\
→ Content Generation\
→ AI Video Generation\
→ Campaign\
→ Creator Distribution\
→ Affiliate Tracking\
→ Conversion\
→ Revenue Attribution\
→ Performance Analysis.

Mục tiêu của hệ thống không chỉ là tạo video mà là tạo và phân phối content có khả năng tạo ra measurable traffic, signup, conversion và revenue.

-----
**1.3 Product Objective**

Hệ thống MVP phải hỗ trợ ba nhóm người dùng chính:

1. Merchant
1. Creator
1. Platform Admin

Hệ thống phải giúp Merchant đưa AI Product vào platform, tạo campaign và content; Creator lựa chọn campaign và content để quảng bá; platform theo dõi clicks, signups, conversions và revenue.

-----
**1.4 Definitions and Acronyms**

|**Term**|**Definition**|
| :-: | :-: |
|AI Product|Sản phẩm AI/SaaS được quảng bá trên hệ thống|
|Merchant|Doanh nghiệp/chủ sở hữu AI Product|
|Creator|Người phân phối content để quảng bá AI Product|
|Admin|Người quản trị platform|
|Campaign|Chiến dịch quảng bá một AI Product|
|Content Idea|Ý tưởng nội dung được tạo cho Product|
|Hook|Phần mở đầu nhằm thu hút người xem|
|Script|Kịch bản video|
|CTA|Call to Action|
|Product Knowledge Base|Tập thông tin hệ thống biết về một Product|
|Tracking Link|Unique link do Platform tạo cho Creator trong Campaign để ghi nhận click, conversion và attribution.|
|Attribution|Quá trình xác định nguồn tạo ra conversion/revenue|
|Conversion|Hành động như signup, trial hoặc purchase|
|Commission|Hoa hồng Creator nhận được|
|Content Variation|Phiên bản khác nhau của một content/video|
|MVP|Minimum Viable Product|
|CTR|Click Through Rate|
|RPM|Revenue per 1,000 Views|
|QA|Quality Assurance|
|PRD|Product Requirements Document|
|BRD|Business Requirements Document|
|SRS|Software Requirements Specification|

-----
**2. Overall System Description**

**2.1 Product Perspective**

Hệ thống đóng vai trò trung tâm kết nối ba thành phần:

**Merchant**

Cung cấp AI Product và tạo campaign.

**Creator**

Lấy content để phân phối và tạo traffic.

**Platform**

Tạo content, quản lý campaign, tracking conversion và tính toán performance.

PRD xác định product architecture theo luồng Product Intelligence → Content Strategy → AI Video Factory → Creator Network → Traffic → Trial/Purchase → Affiliate Engine → Revenue Data → Performance AI.

-----
**3. User Classes and Actors**

**3.1 Merchant**

Merchant có thể:

- Đăng ký và đăng nhập.
- Quản lý profile.
- Tạo Product.
- Import Product từ URL.
- Xem Product Knowledge.
- Chỉnh sửa/xác nhận Product Knowledge.
- Tạo Campaign.
- Generate content.
- Generate video.
- Quản lý content.
- Xem Creator participating.
- Xem Analytics.
- Xem Revenue.
-----
**3.2 Creator**

Creator có thể:

- Đăng ký và đăng nhập.
- Tạo Creator Profile.
- Xem Campaign.
- Tham gia Campaign.
- Xem Content Library.
- Download video.
- Copy caption / hashtag / CTA.
- Lấy Tracking Link.
- Theo dõi clicks.
- Theo dõi conversions.
- Theo dõi earnings.

PRD mô tả Creator flow từ Join Campaign đến Commission.

-----
**3.3 Platform Admin**

Admin có quyền quản lý:

- Products
- Merchants
- Creators
- Campaigns
- Videos
- Content
- Conversion
- Revenue
- Fraud-related records
- Platform configuration.

Phạm vi quản lý Product, Campaign, Creator, Video, Affiliate, Traffic, Conversion, Commission, Fraud và Revenue được PRD xác định.

-----
**4. System Modules**

MVP được chia thành các module chính:

|**Module ID**|**Module**|
| :-: | :-: |
|MOD-01|Authentication & User Management|
|MOD-02|Product Management|
|MOD-03|Product Intelligence|
|MOD-04|Content Factory|
|MOD-05|AI Video Factory|
|MOD-06|Campaign Management|
|MOD-07|Creator Network|
|MOD-08|Content Library|
|MOD-09|Affiliate Tracking|
|MOD-10|Conversion & Attribution|
|MOD-11|Analytics & Dashboard|
|MOD-12|AI Quality Control|
|MOD-13|Admin Management|

-----
**5. Functional Requirements**

**5.1 Authentication & User Management**

**FR-AUTH-01 — User Registration**

Hệ thống phải cho phép người dùng đăng ký tài khoản.

Role được hỗ trợ trong MVP:

- Merchant
- Creator
- Admin

Admin account có thể được tạo theo cơ chế quản trị nội bộ.

-----
**FR-AUTH-02 — User Login**

Hệ thống phải cho phép người dùng đăng nhập bằng thông tin xác thực hợp lệ.

-----
**FR-AUTH-03 — Logout**

Hệ thống phải cho phép người dùng đăng xuất khỏi phiên hiện tại.

-----
**FR-AUTH-04 — Role-based Access Control**

Hệ thống phải giới hạn chức năng dựa trên role.

Ví dụ:

- Creator không được quản lý Product của Merchant.
- Merchant không được truy cập Admin Management.
- Admin có quyền quản lý dữ liệu toàn platform theo permission được cấp.
-----
**FR-AUTH-05 — User Profile**

Hệ thống phải cho phép người dùng xem và cập nhật profile của mình.

-----
**5.2 Product Management**

**FR-PROD-01 — Create Product**

Merchant phải có khả năng tạo AI Product mới.

Trong phạm vi MVP, Merchant phải cung cấp tối thiểu:

- Website URL
- Merchant Affiliate URL

Các thông tin còn lại có thể do Merchant cung cấp hoặc được Platform thu thập/suy luận từ Product source, bao gồm:

- Product Name
- Description
- Target Audience
- Pricing
- Main Features
- Use Cases
- Competitors
- Commission
- USP
- Limitations
- Brand Guidelines
- Forbidden Claims.

-----
**FR-PROD-02 — Product Source Input**

Merchant phải nhập **Website URL** và **Merchant Affiliate URL** hợp lệ khi onboard Product.

-----
**FR-PROD-03 — Crawl Product URL**

Hệ thống phải có khả năng crawl các trang public thuộc Product Website để thu thập dữ liệu phục vụ xây dựng Product Knowledge.

Trong MVP:

- Crawl tối đa **30 public pages / Product**.
- Crawler phải tôn trọng robots.txt.
- Chỉ thu thập các nguồn public được phép truy cập.
- Không tự động đăng nhập vào Product Website.
- Nội dung chỉ có sau đăng nhập không được crawler tự truy cập.
- Merchant có thể cung cấp screenshot/PDF hoặc tài liệu bổ sung đối với nội dung không public.

-----
**FR-PROD-04 — Review Product Information**

Merchant phải có khả năng review thông tin Product do hệ thống thu thập/generate.

-----
**FR-PROD-05 — Edit Product**

Merchant phải có khả năng chỉnh sửa Product do mình quản lý.

-----
**FR-PROD-06 — Product Status**

Hệ thống phải lưu trạng thái của Product.

Minimum status:

- Draft
- Active
- Inactive

**Note:** Product Status và Product Knowledge Status là hai lifecycle độc lập.

Product Status mô tả trạng thái sử dụng của Product (Draft / Active / Inactive).

Product Knowledge Status mô tả trạng thái review/approval của từng PKB version (draft / in\_review / approved).

-----
**5.3 Product Intelligence**

**FR-PI-01 — Generate Product Knowledge**

Hệ thống phải có khả năng tạo Product Knowledge dựa trên Product Data.

Product Knowledge có thể bao gồm:

- Features
- Pricing
- Target Users
- Use Cases
- USP
- Limitations
- Competitors
- Positioning
- Differentiators
- Audience
- Jobs-to-be-done.

Các nhóm thông tin này được định nghĩa trong Product Intelligence Engine.

-----
**FR-PI-02 — Store Product Knowledge with Evidence Traceability**

Product Knowledge phải được lưu và liên kết với Product tương ứng. 

Mọi fact/tính năng (features, pricing plans, limitations) bóc tách từ website phải lưu kèm:
- `source_id`: Tham chiếu đến ID/URL của trang nguồn cụ thể.
- `evidence`: Đoạn trích dẫn nguyên văn bằng chứng ($\le 200$ ký tự) từ nội dung trang nguồn.

Mọi fact do AI tự suy luận mà không có nguồn trực tiếp từ trang web phải gắn nhãn `origin: inferred`.

-----
**FR-PI-03 — Review and Approve Product Knowledge**

Merchant phải có khả năng review, chỉnh sửa và approve Product Knowledge của Product.

Product Knowledge phải trải qua các trạng thái:

- draft
- in\_review
- approved

Trong phạm vi MVP, **Merchant là actor chịu trách nhiệm approve Product Knowledge**. Platform Admin không tham gia từng lần approve.

-----
**FR-PI-04 — Product Knowledge Versioning**

Hệ thống phải hỗ trợ versioning cho Product Knowledge.

Mỗi lần Merchant approve một Product Knowledge đã được cập nhật, hệ thống phải tạo một version mới.

Version trước đó phải được giữ lại và có khả năng truy xuất ở chế độ read-only.

Mỗi version tối thiểu phải xác định được:

- Version number
- Status
- Approval time
- Approved by
- Product tương ứng.

-----
**FR-PI-05 — Conflict Detection & Resolution**

Hệ thống phải tự động phát hiện và đánh dấu các điểm xung đột dữ liệu giữa thông tin Merchant nhập thủ công và dữ liệu do crawler thu thập (ví dụ: chênh lệch giá tiền giữa form và trang pricing).

Giao diện phải highlight rõ điểm xung đột và cho phép Merchant lựa chọn giá trị ưu tiên trước khi bấm Approve (mặc định ưu tiên: Merchant nhập > Web crawl > AI suy luận).

**Note về RAG trong MVP:** Để tối ưu chi phí (zero-budget), hệ thống sử dụng Full PKB Prompt Injection (đưa toàn bộ PKB làm context cho LLM) thay vì bắt buộc dùng pgvector embedding, giữ chi phí xử lý $\le \$0.05$/sản phẩm.

-----
**5.4 Content Factory**

**FR-CONT-01 — Generate Content Ideas**

Hệ thống phải có khả năng tạo Content Ideas từ Product Knowledge.

Content Ideas có thể thuộc các nhóm:

- Problem
- Demo
- Comparison
- Tutorial
- Before/After
- Mistake
- Listicle
- Reaction
- Challenge
- Hidden Feature
- Cost Saving
- Workflow.
-----
**FR-CONT-02 — Content Intent**

Mỗi content phải có thể gắn với một intent.

Minimum intents:

- Awareness
- Education
- Consideration
- Conversion.

PRD phân chia content thành bốn nhóm này.

-----
**FR-CONT-03 — Generate Hooks**

Hệ thống phải có khả năng tạo nhiều Hook cho một Product hoặc Content Idea.

-----
**FR-CONT-04 — Generate Script**

Hệ thống phải có khả năng tạo Script.

Input có thể bao gồm:

- Product
- Audience
- Hook
- Content Intent
- Platform
- Video Length
- Creator Persona
- CTA.

Script output có thể bao gồm:

**Hook → Problem → Demo → Result → Proof → CTA.**

-----
**FR-CONT-05 — Generate Caption**

Hệ thống phải có khả năng generate caption cho content.

-----
**FR-CONT-06 — Generate Hashtag**

Hệ thống phải có khả năng cung cấp hashtag recommendation cho content.

-----
**FR-CONT-07 — Content Status**

Content phải có trạng thái.

Minimum đề xuất:

- Draft
- Generated
- Under Review
- Approved
- Rejected

**TBD:** Workflow approval cần stakeholder xác nhận.

-----
**FR-CONT-08 — Edit Generated Content**

Người dùng có quyền phù hợp phải có khả năng chỉnh sửa:

- Hook
- Script
- Caption
- CTA.
-----
**5.5 AI Video Factory**

**FR-VID-01 — Generate Video**

Hệ thống phải có khả năng tạo video từ Script được chọn.

-----
**FR-VID-02 — Video Format & Specifications**

Hệ thống phải hỗ trợ một hoặc nhiều format:

- Screen Recording (Ưu tiên số 1 trong MVP)
- AI Avatar (Optional / sau MVP)
- Faceless
- Hybrid.

**Quy chuẩn kỹ thuật video bắt buộc:**
- **Tỉ lệ khung hình:** Video dạng đứng 9:16 (độ phân giải chuẩn 1080 × 1920 px cho TikTok, Reels, Shorts).
- **Thời lượng:** 15 – 60 giây (tối ưu cho retention và completion rate).
- **Vùng an toàn (Safe Zone):** Phụ đề, văn bản và các yếu tố hình ảnh quan trọng phải nằm trong vùng an toàn ở giữa màn hình (tránh bị che khuất bởi thanh công cụ, icon Like/Share/Comment và caption của TikTok/Shorts).

-----
**FR-VID-03 — Screen Recording Workflow**

Hệ thống phải hỗ trợ Screen Recording như một video workflow cốt lõi trong MVP.

Screen Recording phải sử dụng giao diện hoặc output thực tế của Product (chụp ảnh màn hình các section tính năng, workflow thực thi) làm evidence cho nội dung review.

Định dạng này vừa tạo độ tin cậy tối đa cho người mua (thấy tool chạy thật), vừa giúp hệ thống tiết kiệm 100% chi phí thuê API avatar đắt tiền trong giai đoạn zero-budget.

Khi applicable, Screen Recording phải được liên kết với Product/Product Knowledge và evidence tương ứng.

-----
**FR-VID-04 — AI Voice (Text-to-Speech)**

Hệ thống phải có khả năng chuyển đổi Script thành giọng đọc AI (Text-to-Speech) để lồng tiếng cho video review.

Yêu cầu chi tiết:
- Hỗ trợ giọng đọc tiếng Anh tự nhiên (English US/UK theo phạm vi MVP tiếng Anh).
- Tự động căn chỉnh timing khớp với từng phân đoạn kịch bản (Hook, Problem, Demo, Result, CTA) và Screen Recording visuals.
- Sử dụng giải pháp TTS chi phí thấp / open-source (Edge-TTS hoặc Web Speech API / free-tier) nhằm tuân thủ nguyên tắc zero-budget.

-----
**FR-VID-05 — Subtitle**

Hệ thống phải hỗ trợ subtitle/caption tự động hiển thị trong video đồng bộ với voice track, đảm bảo đặt trong Safe Zone 9:16.

-----
**FR-VID-06 — Video Variation**

Hệ thống phải có khả năng tạo nhiều variation từ cùng content.

Variation có thể thay đổi:

- Hook
- Persona / Voice
- Format
- Length.

PRD mô tả một script có thể tạo nhiều variation dựa trên các dimension này.

-----
**FR-VID-07 — Video Preview**

Người dùng phải có khả năng preview video trước khi sử dụng.

-----
**FR-VID-08 — Video Download**

Video được approve phải có thể download theo quyền của user (kèm theo asset package sẵn sàng 1-click cho Creator).

**FR-VID-09 — AI Avatar Disclosure**

Khi video sử dụng AI Avatar, hệ thống phải hỗ trợ áp dụng disclosure phù hợp theo platform policy hoặc campaign requirement trước khi content được sử dụng/publish.

-----

**5.6 Campaign Management**

**FR-CAMP-01 — Create Campaign**

Merchant phải có khả năng tạo Campaign.

Campaign có thể chứa:

- Campaign Name
- Product
- Start Date
- End Date
- Target Audience
- Target Country
- Languages: English trong phạm vi MVP
- Commission
- Content Requirements
- Approved Claims
- Forbidden Claims
- CTA.

Các trường này được PRD mô tả trong Campaign System.

-----
**FR-CAMP-02 — Link Product to Campaign**

Mỗi Campaign phải được liên kết với ít nhất một Product.

**TBD:** Một Campaign có được liên kết nhiều Product hay không.

-----
**FR-CAMP-03 — Campaign Status**

Campaign phải có trạng thái.

Minimum đề xuất:

- Draft
- Active
- Paused
- Ended
-----
**FR-CAMP-04 — Edit Campaign**

Merchant phải có khả năng chỉnh sửa Campaign chưa bị khóa bởi business rule.

-----
**FR-CAMP-05 — Campaign Listing**

Creator phải có khả năng xem danh sách Campaign có thể tham gia.

-----
**FR-CAMP-06 — Campaign Detail**

Creator phải có khả năng xem thông tin Campaign.

Thông tin tối thiểu:

- Product
- Campaign description
- Target Audience
- Commission
- Content Requirements
- Posting Guidance.
-----
**FR-CAMP-07 — Join Campaign**

Creator phải có khả năng gửi yêu cầu hoặc thực hiện hành động tham gia Campaign.

**TBD:** Auto-join hay Merchant approval.

-----
**FR-CAMP-08 — Leave Campaign**

**TBD:** Creator có được tự leave Campaign sau khi đã join hay không.

-----
**5.7 Creator Network**

**FR-CRE-01 — Creator Registration**

Hệ thống phải cho phép Creator đăng ký Creator Account.

-----
**FR-CRE-02 — Creator Profile**

Creator Profile có thể chứa:

- Creator ID
- Niche
- Language
- Country
- Platform
- Audience
- Follower Count
- Average Views
- Engagement Rate.

Các thuộc tính Creator Profile được PRD định nghĩa rộng hơn trong Creator Persona Engine.

-----
**FR-CRE-03 — Creator Campaign List**

Creator phải có khả năng xem:

- Available Campaigns
- My Campaigns.
-----
-----
**FR-CRE-04 — Creator Performance**

Creator phải xem được performance dữ liệu thuộc về mình.

-----
**FR-CRE-05 — Submit Proof of Publishing**

Sau khi tải video và đăng lên mạng xã hội (TikTok, Instagram Reels, YouTube Shorts), Creator phải có khả năng nộp lại bằng chứng đã đăng (Proof of Publishing):
- Dán URL bài đăng thực tế (`post_url`).
- Chọn nền tảng đã đăng (`platform`: tiktok, reels, shorts).
- Hệ thống lưu trạng thái bài đăng và hiển thị xác nhận đã nộp thành công, cho phép chỉnh sửa nếu nhập sai link mà không tạo bản ghi trùng lặp.

-----
**5.8 Content Library**

**FR-LIB-01 — Campaign Content Library**

Mỗi Campaign phải có Content Library chứa content đã được duyệt và cho phép sử dụng. Giao diện thiết kế theo triết lý "1-Click Ready" để Creator thao tác trong dưới 1 phút.

-----
**FR-LIB-02 — View Content**

Creator tham gia Campaign phải có thể xem content tương ứng.

-----
**FR-LIB-03 — Download Content**

Creator phải có thể download video được phép sử dụng (định dạng MP4 chuẩn 9:16).

-----
**FR-LIB-04 — Copy Caption**

Creator phải có nút 1-click để copy caption chuẩn bị sẵn.

-----
**FR-LIB-05 — Copy Hashtag**

Creator phải có nút 1-click để copy danh sách hashtag đề xuất.

-----
**FR-LIB-06 — Copy CTA**

Creator phải có thể xem/copy CTA.

-----
**FR-LIB-07 — Posting Instruction**

Creator phải có khả năng xem hướng dẫn publish ngắn gọn, dễ hiểu.

PRD định nghĩa Creator được cung cấp Video, Caption, Hashtags, CTA, Tracking Link và Posting Instructions.

-----
**5.9 Affiliate Tracking**

**FR-AFF-01 — Generate Tracking Link**

Hệ thống phải có khả năng generate unique tracking link.

Link phải có khả năng xác định ít nhất:

- Creator
- Campaign
- Product.
-----
**FR-AFF-02 — Track Click**

Hệ thống phải ghi nhận click từ Tracking Link.

-----
**FR-AFF-03 — Click Identifier**

Mỗi tracked click nên có unique identifier.

-----
**FR-AFF-04 — Track Landing**

Nếu technical architecture cho phép, hệ thống phải xác định click đã dẫn người dùng đến landing destination.

-----
**FR-AFF-05 — Tracking Link Access**

Creator phải có thể lấy Tracking Link tương ứng với Campaign của mình.

PRD xác định flow từ tracking link qua Impression, Click, Landing, Signup, Trial, Paid Conversion và Revenue.

-----
**5.10 Conversion & Attribution**

**FR-ATTR-01 — Track Signup**

Hệ thống phải có khả năng nhận hoặc ghi nhận Signup Event.

-----
**FR-ATTR-02 — Track Trial**

Nếu Merchant sử dụng trial, hệ thống phải có khả năng nhận hoặc ghi nhận Trial Event.

-----
**FR-ATTR-03 — Track Paid Conversion**

Hệ thống phải có khả năng nhận Paid Conversion Event (`event_type = 'paid'`).

-----
**FR-ATTR-04 — Track Revenue**

Conversion record phải có khả năng chứa Revenue Amount nếu Merchant cung cấp.

-----
**FR-ATTR-05 — Attribute Conversion**

Hệ thống phải có khả năng liên kết conversion với:

- Product
- Campaign
- Creator
- Video
- Click

khi đủ dữ liệu.

PRD yêu cầu hệ thống biết “Video nào → Creator nào → Campaign nào → User nào → Revenue nào”.

-----
**FR-ATTR-06 — Commission Record**

Hệ thống phải có khả năng tạo Commission Record dựa trên conversion và Campaign Commission Rule.

**TBD:** Công thức tính commission cuối cùng.

-----
**FR-ATTR-07 — Conversion Data Input**

Trong phạm vi MVP, hệ thống phải hỗ trợ nhập dữ liệu conversion và revenue thông qua **CSV file upload**. 

Merchant hoặc người dùng có quyền phù hợp có thể upload file CSV chứa dữ liệu conversion để hệ thống thực hiện đối soát và attribution. 

Cấu trúc các cột chuẩn của file CSV:

| Tên cột | Bắt buộc | Kiểu dữ liệu | Mô tả |
|---|---|---|---|
| `click_id` | Có | String | Mã click identifier gắn với Tracking Link của Creator |
| `external_user_id` | Có | String | Mã định danh khách hàng trên hệ thống Merchant (bắt buộc để kiểm tra `commission_eligibility`, chỉ trả hoa hồng cho first-time purchase của user) |
| `order_id` | Có | String | Mã đơn hàng / giao dịch phía Merchant |
| `event_type` | Có | Enum | Loại sự kiện: `signup`, `trial`, hoặc `paid` (khớp với enum `paid` trong ERD) |
| `event_time` | Có | ISO 8601 | Thời gian phát sinh sự kiện |
| `revenue_amount` | Có | Decimal | Giá trị doanh thu của đơn hàng |
| `currency` | Không | String | Đơn vị tiền tệ (mặc định: `USD`) |

Hệ thống phải tự động kiểm tra trùng lặp `order_id`, bỏ qua bản ghi lỗi, sử dụng `click_id` để map ngược về **Creator, Campaign và Product** tương ứng để ghi nhận attributed revenue, đồng thời đối soát `external_user_id` để xác định điều kiện hưởng hoa hồng (`commission_eligibility`).

-----
**5.11 Merchant Analytics**

**FR-MAN-01 — Merchant Dashboard**

Merchant phải có Dashboard tổng quan.

-----
**FR-MAN-02 — Content Metrics**

Merchant phải có thể xem:

- Videos Created
- Videos Published
- Content Volume.
-----
**FR-MAN-03 — Creator Metrics**

Merchant phải có thể xem số Creator liên quan đến Campaign/Product.

-----
**FR-MAN-04 — Distribution Metrics**

Merchant phải có thể xem dữ liệu được hỗ trợ như:

- Views
- Reach
- Engagement
- Clicks.
-----
**FR-MAN-05 — Business Metrics (RPM & ROI)**

Merchant phải có thể xem:

- Signups
- Trials
- Paid Users
- Attributed Revenue
- Affiliate Commission
- **RPM (Revenue per 1,000 Views):** Tính theo công thức $\text{RPM} = \left(\frac{\text{Attributed Revenue}}{\text{Total Video Views}}\right) \times 1000$, phản ánh giá trị doanh thu thực tế trên mỗi 1,000 lượt xem review (high-intent traffic).
- **ROI (Return on Investment):** Tính theo công thức $\text{ROI} = \frac{\text{Attributed Revenue}}{\text{Affiliate Commission Paid}}$, phản ánh hiệu quả doanh thu thu về trên mỗi đồng hoa hồng chi trả cho Creator.

PRD định nghĩa Merchant Dashboard với cả Content, Distribution và Business metrics (bao gồm ROI và RPM).

-----
**5.12 Creator Analytics**

**FR-CAN-01 — Creator Dashboard**

Creator phải có Dashboard cá nhân.

-----
**FR-CAN-02 — Creator Revenue**

Creator phải có thể xem:

- Total Revenue / Earnings
- Pending Commission
- Paid Commission

nếu dữ liệu tương ứng được hỗ trợ.

-----
**FR-CAN-03 — Creator Conversion Performance**

Creator phải có thể xem:

- Clicks
- Signups
- Conversions (`paid`)
- Conversion Rate
- **EPC (Earnings per Click)** và **Estimated RPM (Earnings / 1,000 Views)** để đánh giá hiệu quả sinh lời của từng video/sản phẩm đã quảng bá.
-----
**FR-CAN-04 — Best Performance**

Creator có thể xem:

- Best Videos
- Best Products.

PRD mô tả các chỉ số này trong Creator Dashboard.

-----
**5.13 AI Quality Control**

**FR-QA-01 — Product Fact Check**

Hệ thống phải kiểm tra AI-generated content dựa trên Product Knowledge hiện có.

-----
**FR-QA-02 — Pricing Check**

Hệ thống phải hạn chế publish content có thông tin pricing không phù hợp với dữ liệu Product hiện tại.

-----
**FR-QA-03 — Feature Check**

Hệ thống phải kiểm tra Product Feature được nhắc tới có tồn tại trong Product Knowledge.

-----
**FR-QA-04 — Forbidden Claim Detection**

Hệ thống phải phát hiện content chứa Forbidden Claims được Merchant cấu hình.

-----
**FR-QA-05 — Approved Claim Validation**

Hệ thống nên ưu tiên claim nằm trong Approved Claims.

-----
**FR-QA-06 — Fake Review Prevention**

Hệ thống không được chủ động tạo fake review, fake testimonial hoặc fake result.

-----
**FR-QA-07 — Unsupported Experience Prevention**

Hệ thống không được sử dụng câu khẳng định như:

“I tested this…”

nếu hệ thống không có evidence phù hợp.

Các constraint này được PRD định nghĩa trong AI Quality Control.

-----
**FR-QA-08 — Content Duplicate Check**

Hệ thống nên có khả năng phát hiện mức độ trùng lặp đối với:

- Hook
- Script
- CTA
- Visual
- Voice.

PRD yêu cầu giảm duplicate content để tránh việc nhiều creator đăng cùng một nội dung.

-----
**5.14 Admin Management**

**FR-ADM-01 — Admin Dashboard**

Admin phải có dashboard tổng quan hệ thống.

-----
**FR-ADM-02 — Manage Products**

Admin phải có khả năng xem và quản lý Product.

-----
**FR-ADM-03 — Manage Creators**

Admin phải có khả năng xem và quản lý Creator.

-----
**FR-ADM-04 — Manage Campaigns**

Admin phải có khả năng xem và quản lý Campaign.

-----
**FR-ADM-05 — Manage Content**

Admin phải có khả năng xem Content/Video.

-----
**FR-ADM-06 — Manage Conversion**

Admin phải có khả năng xem Conversion records.

-----
**FR-ADM-07 — Manage Revenue**

Admin phải có khả năng xem Revenue records.

-----
**FR-ADM-08 — Disable Content**

Admin phải có khả năng disable content vi phạm policy hoặc requirement.

-----
**6. Core Use Cases**

**UC-01 — Merchant Onboards Product**

**Primary Actor:** Merchant

**Preconditions:**

- Merchant đã đăng nhập.

**Main Flow:**

1. Merchant chọn Add Product.
1. Merchant nhập Product URL và/hoặc thông tin Product.
1. Merchant submit.
1. System lưu Product.
1. System thu thập/phân tích Product information.
1. System tạo Product Knowledge.
1. Merchant review Product Knowledge.
1. Merchant xác nhận hoặc chỉnh sửa.
1. Product được lưu.

**Postcondition:**

Product sẵn sàng để sử dụng cho content generation.

-----
**UC-02 — Merchant Generates Content**

**Primary Actor:** Merchant

**Preconditions:**

- Product tồn tại.
- Product Knowledge đã có.

**Main Flow:**

1. Merchant chọn Product.
1. Merchant chọn Generate Content.
1. System tạo Content Ideas.
1. Merchant chọn Content Idea.
1. System tạo Hooks.
1. Merchant chọn Hook.
1. System tạo Script.
1. System tạo Caption/CTA.
1. Merchant review.
1. Merchant approve hoặc chỉnh sửa.
-----
**UC-03 — Merchant Generates Video**

**Primary Actor:** Merchant

**Preconditions:**

- Approved Script tồn tại.

**Main Flow:**

1. Merchant chọn Script.
1. Merchant chọn video format.
1. Merchant yêu cầu Generate Video.
1. System tạo video.
1. System chạy Quality Control.
1. Merchant preview video.
1. Merchant approve hoặc reject video.
-----
**UC-04 — Merchant Creates Campaign**

**Primary Actor:** Merchant

**Main Flow:**

1. Merchant chọn Create Campaign.
1. Merchant chọn Product.
1. Merchant nhập Campaign information.
1. Merchant cấu hình commission.
1. Merchant cấu hình content requirements.
1. Merchant cấu hình Approved/Forbidden Claims.
1. Merchant submit.
1. System tạo Campaign.
1. Merchant activate Campaign.
-----
**UC-05 — Creator Joins Campaign**

**Primary Actor:** Creator

**Main Flow:**

1. Creator mở Discover Campaigns.
1. System hiển thị Campaign.
1. Creator chọn Campaign.
1. System hiển thị Campaign Detail.
1. Creator chọn Join Campaign.
1. System xử lý joining logic.
1. Creator được thêm vào Campaign nếu đủ điều kiện.

**TBD:** Merchant approval.

-----
**UC-06 — Creator Publishes Content**

**Primary Actor:** Creator

**Main Flow:**

1. Creator vào My Campaigns.
1. Creator chọn Campaign.
1. Creator mở Content Library.
1. Creator preview video.
1. Creator download video.
1. Creator copy caption/hashtags/CTA.
1. Creator lấy Tracking Link.
1. Creator publish bên ngoài platform.
1. Creator gắn Tracking Link.

MVP sử dụng semi-automatic distribution; platform không tự login và mass-post lên các social account.

-----
**UC-07 — Tracking Click and Conversion via CSV**

**Primary Actor:** System, Merchant

**Trigger:** Visitor click Tracking Link, hoặc Merchant upload file CSV đối soát conversion.

**Main Flow:**

*Phase 1: Realtime Click Tracking*
1. Visitor click Tracking Link của Creator.
2. System ghi nhận click event và sinh unique `click_id`.
3. System lưu metadata gắn với `click_id`: Creator, Campaign, Product, Timestamp.
4. System redirect Visitor đến Merchant landing page kèm tham số truy vấn `?ref={click_id}`.

*Phase 2: Conversion Ingestion & Attribution (CSV Batch)*
5. Khi khách hàng phát sinh hành vi chuyển đổi trên Merchant website, hệ thống Merchant lưu lại `click_id` và mã khách hàng `external_user_id`.
6. Merchant định kỳ export file CSV chứa các giao dịch và upload lên Platform (FR-ATTR-07).
7. System parse file CSV, validate schema (bắt buộc có `click_id`, `external_user_id`, `order_id`, `event_type`: `signup` / `trial` / `paid`, `event_time`, `revenue_amount`).
8. System đối soát `click_id` với bảng `clicks` để xác định Creator, Campaign, Product và Video tương ứng.
9. System kiểm tra `external_user_id` để đánh giá điều kiện hưởng hoa hồng (`commission_eligibility`) nhằm ngăn chặn fraud/trùng lặp.
10. System tạo bản ghi Conversion (`paid` / `signup` / `trial`).
11. System tính toán Commission cho Creator dựa trên Campaign commission rule.
12. System cập nhật doanh thu và các chỉ số hiệu suất (RPM, ROI, Conversion Rate) trên Merchant và Creator Dashboard.
-----
**7. Data Requirements**

**7.1 Core Entities**

Dựa trên PRD, các entity chính bao gồm:

- users
- merchants
- products
- product\_knowledge
- campaigns
- creators
- creator\_accounts
- creator\_campaigns
- content\_ideas
- content\_scripts
- videos
- video\_variants
- tracking\_links
- tracking\_events
- clicks
- signups
- conversions
- orders
- commissions
- analytics.

PRD cung cấp core database ở mức định hướng với các entity này (lưu ý: `features` và `pricing` được lưu cấu trúc trong `product_knowledge.data` JSONB thay vì tách bảng độc lập).

-----
**7.2 Merchant Entity**

Bảng `merchants` đại diện cho hồ sơ doanh nghiệp sở hữu sản phẩm, quan hệ 1–1 với người dùng qua `user_id → auth.users.id`:

|**Field**|**Description**|
| :-: | :-: |
|merchant\_id|Unique Merchant ID (UUID)|
|user\_id|Tài khoản đăng nhập (`auth.users.id`)|
|company\_name|Tên công ty / Brand|
|website\_url|Website chính thức|
|contact\_email|Email liên hệ|
|status|Trạng thái (active, pending, suspended)|
|created\_at|Thời gian tạo|

-----
**7.3 Product Entity**

Minimum fields đề xuất (với `merchant_id` là khóa ngoại trỏ tới `merchants.merchant_id`):

|**Field**|**Description**|
| :-: | :-: |
|product\_id|Unique Product ID|
|merchant\_id|Product Owner (`merchants.merchant_id`)|
|name|Product Name|
|website\_url|Website chính thức của sản phẩm|
|description|Product Description|
|target\_audience|Target Audience|
|status|Product Status|
|created\_at|Creation Time|
|updated\_at|Last Update|

-----
**7.4 Campaign Entity**

|**Field**|**Description**|
| :-: | :-: |
|campaign\_id|Unique ID|
|merchant\_id|Campaign Owner|
|product\_id|Product|
|campaign\_name|Campaign Name|
|start\_date|Start Date|
|end\_date|End Date|
|target\_audience|Target Audience|
|country|Target Country|
|language|Language|
|commission\_rule|Commission|
|content\_requirement|Content Requirement|
|approved\_claims|Approved Claims|
|forbidden\_claims|Forbidden Claims|
|status|Campaign Status|

-----
**7.5 Creator Entity**

|**Field**|**Description**|
| :-: | :-: |
|creator\_id|Unique Creator ID|
|user\_id|User Account|
|niche|Creator Niche|
|country|Country|
|language|Language|
|primary\_platform|Social Platform|
|follower\_count|Followers|
|avg\_views|Average Views|
|engagement\_rate|Engagement Rate|
|status|Creator Status|

-----
**7.6 Tracking Entity**

Minimum attribution data:

- video\_id
- creator\_id
- campaign\_id
- product\_id
- click\_id
- visitor\_id
- signup\_id
- order\_id
- revenue
- commission.
-----
**8. External Interface Requirements**

**8.1 User Interface**

MVP là Web Application.

PRD định nghĩa Merchant screens:

- Dashboard
- Products
- Campaigns
- Content
- Creators
- Analytics
- Revenue
- Settings.

Creator screens:

- Dashboard
- Discover Campaigns
- My Campaigns
- Content Library
- Tracking Links
- Performance
- Earnings
- Profile.

Admin screens:

- Overview
- Products
- Campaigns
- Creators
- Content Factory
- Conversions
- Revenue
- Analytics
- Settings.
-----
**8.2 AI Provider Interface**

Hệ thống có thể cần tích hợp:

- LLM
- Text-to-Speech
- Image generation
- Video generation
- Vision service.

Provider cụ thể không được cố định trong SRS.

Architecture nên cho phép thay provider, phù hợp với định hướng Video Provider Adapter trong PRD.

-----
**8.3 Merchant Conversion Interface**

Trong phạm vi MVP, hệ thống sử dụng **CSV Import** để nhận dữ liệu conversion từ Merchant.

Hệ thống phải cho phép upload CSV chứa các loại dữ liệu:

- Signup
- Trial
- Purchase
- Revenue

Sau khi file được upload, hệ thống phải:

1. Validate cấu trúc và dữ liệu CSV.
1. Xác định tracking identifier/click tương ứng.
1. Liên kết conversion với Creator, Campaign và Product.
1. Tạo hoặc cập nhật Conversion Record.
1. Ghi nhận Revenue nếu có.
1. Cập nhật dữ liệu Analytics/Attribution liên quan.
-----
**8.4 Social Platform Interface**

Trong MVP, hệ thống không bắt buộc phải tự động publish lên social network.

Social API integrations có thể được xem xét sau MVP.

-----
**9. Non-Functional Requirements**

**NFR-01 — Security**

Hệ thống phải:

- Bảo vệ authentication credential.
- Áp dụng authorization theo role.
- Ngăn user truy cập dữ liệu không thuộc quyền.
- Bảo vệ tracking và revenue data khỏi unauthorized modification.
-----
**NFR-02 — Privacy**

Thông tin Creator, Merchant và tracking visitor phải được xử lý theo privacy policy và pháp luật áp dụng.

**TBD:** Region/legal requirements.

-----
**NFR-03 — Performance**

Các thao tác thông thường như:

- Login
- Product listing
- Campaign listing
- Content library
- Dashboard loading

nên phản hồi trong khoảng thời gian phù hợp với web application.

**TBD:** Numeric SLA cần stakeholder/technical team xác nhận.

AI generation có thể chạy lâu hơn các CRUD operation.

-----
**NFR-04 — Scalability**

Architecture phải có khả năng mở rộng cho:

- Product count tăng.
- Creator count tăng.
- Video count tăng.
- Tracking event volume tăng.
-----
**NFR-05 — Reliability**

Tracking click và conversion không được phụ thuộc hoàn toàn vào frontend session.

Critical tracking events phải được lưu bền vững khi nhận thành công.

-----
**NFR-06 — Auditability**

Các thay đổi quan trọng nên có khả năng xác định:

- Người thực hiện.
- Thời điểm thực hiện.
- Entity bị thay đổi.

Đặc biệt đối với:

- Campaign
- Product
- Revenue
- Commission
- Admin action.
-----
**NFR-07 — AI Explainability**

Đối với AI-generated Product Knowledge hoặc Content, hệ thống nên có khả năng phân biệt:

- Data Merchant cung cấp.
- Data AI/crawler thu thập.
- Content AI generate.
-----
**NFR-08 — Content Safety**

AI generation phải áp dụng Quality Control trước khi content được sử dụng trong Campaign khi flow yêu cầu.

-----
**NFR-09 — Maintainability**

AI provider, video provider và tracking integration nên được thiết kế ở mức có thể thay thế mà không cần thay đổi toàn bộ system.

-----
**NFR-10 — Compatibility**

MVP phải hoạt động trên các desktop browser hiện đại.

**TBD:** Mobile responsive web requirements.

-----
**10. Business Rules**

**RULE-01**

Views cao không đồng nghĩa content thành công.

-----
**RULE-02**

Commercial performance phải được ưu tiên hơn vanity metrics.

-----
**RULE-03**

Mỗi affiliate traffic source phải có khả năng trace về Creator và Campaign.

-----
**RULE-04**

Content không được sử dụng Forbidden Claims.

-----
**RULE-05**

AI không được fabricate Product Feature.

-----
**RULE-06**

AI không được fabricate Product Pricing.

-----
**RULE-07**

AI không được tạo Fake Review hoặc Fake Testimonial.

-----
**RULE-08**

Câu khẳng định trải nghiệm thực tế phải có evidence phù hợp.

-----
**RULE-09**

MVP sử dụng semi-automatic social distribution.

-----
**RULE-10**

Mobile Application không thuộc MVP.

-----
**11. Validation Rules**

**Product**

- Website URL là bắt buộc.
- Merchant Affiliate URL là bắt buộc.
- Website URL phải đúng URL format.
- Merchant Affiliate URL phải đúng URL format.
- Product Name có thể được Platform thu thập từ Product Website và không bắt buộc Merchant nhập khi onboarding.

**Campaign**

- Campaign Name bắt buộc.
- Campaign phải có Product.
- Start Date không được sau End Date.
- Commission configuration phải hợp lệ.
- Forbidden Claims phải được lưu cùng Campaign nếu Merchant nhập.

**Creator**

- Creator phải có active account để tham gia Campaign.
- Creator chỉ xem private data thuộc chính Creator.

**Tracking**

- Tracking Link phải map đến valid Campaign.
- Tracking Link phải map đến valid Creator.
- Tracking Link phải map đến valid Product.
-----
**12. Error Handling**

Hệ thống phải cung cấp error response/message phù hợp khi:

- Authentication thất bại.
- User không có permission.
- Product không tồn tại.
- Campaign không tồn tại.
- Content không tồn tại.
- AI generation thất bại.
- Video generation thất bại.
- Tracking Link không hợp lệ.
- Conversion event không hợp lệ.
- External service unavailable.

System không được silently discard critical tracking event mà không có error-handling strategy.

-----
**13. MVP Exclusions**

Các capability sau không được xem là requirement bắt buộc của SRS MVP:

- AI Livestream
- 24/7 AI Avatar
- Mobile App
- Automated mass social login
- Full Social Posting Automation
- Complex CRM
- Payment Wallet
- AI Marketplace
- Multi-country Payment
- Sophisticated Recommendation Engine
- Full SEO Platform
- Enterprise Integrations.
-----
**14. Assumptions and Dependencies**

**AS-01**

Merchant cung cấp hoặc xác nhận Product Information.

**AS-02**

Merchant có cơ chế Affiliate/Commission phù hợp.

**AS-03**

Creator tự publish content trong MVP.

**AS-04**

Trong MVP, Merchant cung cấp conversion/revenue data cho Platform thông qua CSV file theo format được hệ thống quy định. Realtime integration thông qua API/Webhook/Pixel không thuộc MVP.

**AS-05**

AI/video generation phụ thuộc external service hoặc internal AI infrastructure.

**AS-06**

Social analytics như Views/Engagement có thể cần external API hoặc manual/import mechanism.

**TBD:** Data acquisition method.

-----
**15. Requirement Traceability**

|**BRD Requirement**|**SRS Requirements**|
| :-: | :-: |
|BR-01 Product Onboarding|FR-PROD-01 → FR-PROD-06|
|BR-02 Product Intelligence|FR-PI-01 → FR-PI-05 (kèm Evidence Traceability và Conflict Detection)|
|BR-03 Content Opportunity|FR-CONT-01, FR-CONT-02|
|BR-04 Hook Generation|FR-CONT-03|
|BR-05 Script Generation|FR-CONT-04|
|BR-06 AI Video|FR-VID-01 → FR-VID-09 (Screen Recording, AI Voice, Subtitles, Disclosure)|
|BR-07 Video Variations|FR-VID-06|
|BR-08 Campaign Management|FR-CAMP-01 → FR-CAMP-08|
|BR-09 Creator Registration|FR-CRE-01 → FR-CRE-05 (kèm Submit Proof of Publishing)|
|BR-10 Campaign Discovery|FR-CAMP-05 → FR-CAMP-07|
|BR-11 Content Library|FR-LIB-01 → FR-LIB-07|
|BR-12 Content Distribution|UC-06, FR-CRE-05|
|BR-13 Tracking Link|FR-AFF-01 → FR-AFF-05|
|BR-14 Conversion Attribution|FR-ATTR-01 → FR-ATTR-07 (kèm CSV batch và external_user_id)|
|BR-15 Merchant Dashboard|FR-MAN-01 → FR-MAN-05 (kèm RPM và ROI)|
|BR-16 Creator Dashboard|FR-CAN-01 → FR-CAN-04 (kèm EPC và RPM)|
|BR-17 Admin Management|FR-ADM-01 → FR-ADM-08|
|BR-18 AI Quality Control|FR-QA-01 → FR-QA-07|
|BR-19 Authenticity|FR-QA-06, FR-QA-07|
|BR-20 Content Diversity|FR-QA-08|










**16. Open Requirements / TBD**

Các requirement sau chưa đủ thông tin trong PRD và cần stakeholder xác nhận trước khi SRS chuyển sang Approved:

|**ID**|**Open Requirement**|
| :-: | :-: |
|TBD-01|Merchant registration có cần approval không?|
|TBD-02|Creator registration có cần Admin approval không?|
|TBD-03|Creator join Campaign tự động hay cần Merchant approve?|
|TBD-04|Một Campaign có hỗ trợ nhiều Product không?|
|TBD-05|Một Creator có thể tham gia bao nhiêu Campaign cùng lúc?|
|TBD-06|Campaign pause/terminate behaviour như thế nào?|
|TBD-07|Commission calculation chính xác như thế nào?|
|TBD-08|Commission có recurring không?|
|TBD-09|Commission confirmation period bao lâu?|
|TBD-10|MVP có thực hiện payout thật không?|
|TBD-11|Merchant có cần approve từng video trước khi Creator publish không?|
|TBD-12|Creator có được chỉnh sửa video không?|
|TBD-13|Creator có được chỉnh sửa caption/script không?|
|TBD-14|**ĐÃ CHỐT (Resolved):** Trong MVP dùng **CSV Batch Upload** do Merchant cung cấp (FR-ATTR-07). Webhook, Realtime API hoặc Pixel chuyển sang giai đoạn post-MVP.|
|TBD-15|Views/engagement được lấy từ social platform bằng cách nào?|
|TBD-16|Social platform ưu tiên MVP là TikTok, Shorts, Reels hay tất cả?|
|TBD-17|Fraud detection tối thiểu của MVP là gì?|
|TBD-18|Merchant/Creator dispute flow có tồn tại không?|
|TBD-19|Data retention period là bao lâu?|
|TBD-20|Numeric performance SLA là bao nhiêu?|

-----
**17. MVP System Workflow**

Luồng nghiệp vụ hệ thống MVP:

**Merchant Login**

↓

**Create / Import Product**

↓

**Build Product Knowledge**

↓

**Generate Content Ideas**

↓

**Generate Hooks**

↓

**Generate Scripts**

↓

**Generate Videos**

↓

**Quality Check**

↓

**Create Campaign**

↓

**Publish Content to Campaign Library**

↓

**Creator Joins Campaign**

↓

**Creator Downloads Content**

↓

**Creator Receives Tracking Link**

↓

**Creator Publishes Content**

↓

**User Clicks Tracking Link**

↓

**System Tracks Click**

↓

**Signup / Trial / Purchase**

↓

**Conversion Attribution**

↓

**Revenue / Commission**

↓

**Merchant & Creator Analytics**

MVP vision trong PRD được thu gọn thành Product → Content → Videos → Creators → Published Posts → Clicks → Signups → Revenue.

-----
**18. System Acceptance at SRS Level**

Hệ thống MVP được xem là đáp ứng SRS ở mức tổng thể khi có thể thực hiện end-to-end scenario sau:

1. Merchant đăng nhập.
1. Merchant onboard một AI Product.
1. Platform tạo Product Knowledge.
1. Merchant tạo Content Idea.
1. Platform tạo Hook.
1. Platform tạo Script.
1. Platform tạo Video.
1. Merchant tạo Campaign.
1. Creator tham gia Campaign.
1. Creator xem và download Content.
1. Creator lấy Tracking Link.
1. Creator publish content bên ngoài platform.
1. Visitor click Tracking Link.
1. Platform ghi nhận Click (`click_id`).
1. Merchant upload CSV chứa Conversion event (`paid` / `signup` / `trial`) kèm `click_id` và `external_user_id`.
1. Platform xác định Creator/Campaign/Product attribution và kiểm tra `commission_eligibility`.
1. Platform ghi nhận Revenue.
1. Merchant xem Performance (bao gồm RPM, ROI).
1. Creator xem Performance/Commission (bao gồm EPC, RPM).

Nếu core flow trên không thể hoàn thành từ đầu tới cuối, MVP chưa đáp ứng mục tiêu chính của SRS.

-----
**19. SRS Approval**

SRS được xem là ready for development khi:

- Functional Requirements được stakeholder/Product approve.
- Các TBD ảnh hưởng Sprint 1 được giải quyết.
- MVP Scope được khóa.
- Data Model sơ bộ được approve.
- Main User Flow được approve.
- API dependencies được xác định.
- AI provider constraints được xác định.
- User Stories và Acceptance Criteria cho Sprint 1 được mapping với Requirement ID.

Sau approval:

**SRS**

→ **Epic**

→ **User Story**

→ **Acceptance Criteria**

→ **Technical Task**

→ **Test Case**

→ **Development**

→ **UAT**

-----
**20. Final System Definition**

Ở mức Software Requirement, MVP được định nghĩa là:

Một web platform cho phép Merchant onboard AI Product, sử dụng AI để tạo product knowledge, content và video review, xây dựng Campaign cho Creator, cung cấp Content và Tracking Link cho Creator, theo dõi traffic/conversion qua CSV và hiển thị attributed revenue/performance (RPM, ROI) cho Merchant, Creator và Admin.

Core success flow:

**Product → AI Content → Video → Campaign → Creator → Click → Conversion → Revenue**

