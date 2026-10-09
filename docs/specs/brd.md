<!--
BRD (Business Requirements Document) v0.2 ("Updated from Feedback"), do team lead (@VV6505) gửi ngày 2026-10-07 (file gốc: tempbrd.md), dựa trên bản của BA (@khanhphi27). Được @PotatoMine725 đưa vào repo ngày 2026-10-07.
Cập nhật 2026-10-07: chuyển phần duyệt video / Manual QA của BA (@khanhphi27, file BRD.md, sửa trên bản cũ) sang bản v0.2 này.
Nội dung giữ nguyên văn. Góp ý và câu hỏi mở: xem issue #28, #23 và docs/logs/qa-log.md. Từ bản này, mọi thay đổi đi qua PR vào docs/specs/.
Khi mâu thuẫn với decision-log / đặc tả module / ERD đã chốt, các tài liệu đó được ưu tiên cho tới khi bản này được cập nhật.
-->

**BUSINESS REQUIREMENTS DOCUMENT**

**Project:** AI Review Content Factory & Affiliate Network
**Document Type:** Business Requirements Document — BRD
**Version:** 0.2
**Status:** Draft for Stakeholder Review (Updated from Feedback)
**Product Stage:** MVP

**1. Introduction**

**1.1 Purpose**

Tài liệu này mô tả các yêu cầu nghiệp vụ cho nền tảng **AI Review Content Factory & Affiliate Network**.

Mục tiêu của BRD là:

- Xác định bài toán kinh doanh cần giải quyết.
- Xác định mục tiêu kinh doanh của sản phẩm.

- Xác định các bên liên quan chính.
- Xác định phạm vi MVP.

- Xác định quy trình nghiệp vụ mong muốn.
- Xác định các Business Requirements và Business Rules.

- Làm cơ sở để xây dựng SRS, Product Backlog, User Stories và Acceptance Criteria.
- Tạo cơ sở thống nhất giữa khách hàng, Product, BA, Development và QA trước khi triển khai.

**1.2 Product Overview**

AI Review Content Factory & Affiliate Network là nền tảng kết hợp:

- AI Content Factory
- AI Video Generation

- Creator Network
- Affiliate Network

- Conversion & Revenue Tracking

Nền tảng hướng tới việc biến một AI Product thành nhiều nội dung review dạng video ngắn, phân phối các nội dung này qua creator/affiliate network và đo lường hiệu quả dựa trên traffic, signup, conversion và revenue.

Sản phẩm không chỉ tập trung vào việc tạo video, mà tập trung vào khả năng:

Content → Distribution → Traffic → Conversion → Revenue.

North Star của sản phẩm là doanh thu được tạo ra từ hoạt động phân phối content bằng AI, thay vì chỉ đo số video, số views hoặc số creator.

**2. Business Context**

**2.1 Current Business Situation**

Các công ty AI/SaaS đang gặp nhiều khó khăn trong việc phân phối sản phẩm tới người dùng.

Các vấn đề được xác định bao gồm:

- Sản phẩm tốt nhưng ít người biết đến.
- Founder không có kỹ năng hoặc nguồn lực để tạo nội dung TikTok/Reels/Shorts.

- Doanh nghiệp không có đội content đủ lớn.
- Paid Ads có chi phí ngày càng cao.

- SEO cần thời gian dài để tạo kết quả.
- Influencer campaign khó mở rộng.

- Một creator chỉ có thể tạo một lượng nội dung giới hạn.
- Doanh nghiệp khó biết nội dung nào thực sự tạo ra doanh thu.

**2.2 Business Opportunity**

Thay vì phụ thuộc vào một số influencer lớn, mô hình kinh doanh hướng tới việc sử dụng nhiều micro-creator hoặc niche account để tạo distribution ở quy mô lớn.

Ý tưởng cốt lõi:

**AI Product**

→ AI hiểu sản phẩm
→ AI tạo content
→ Creator phân phối content
→ Người dùng click
→ Signup / Trial / Purchase
→ Affiliate Revenue
→ Thu thập Performance Data
→ AI tối ưu content tiếp theo.

Mô hình này cho phép doanh nghiệp phát triển khả năng phân phối dựa trên hiệu suất thay vì chỉ dựa vào lượng follower của influencer.

**3. Business Objectives**

**3.1 Primary Business Objective**

Xây dựng một nền tảng có khả năng giúp AI Product Merchant:

Tạo, phân phối và tối ưu nội dung review AI Product nhằm tạo traffic, signup, conversion và attributed revenue.

**3.2 Business Goals**

**BG-01 — Scale Content Production**

Cho phép tạo nhiều nội dung marketing/review từ một AI Product mà không cần mở rộng đội content theo tỷ lệ tương ứng.

**BG-02 — Scale Distribution**

Cho phép nội dung được phân phối thông qua creator và affiliate network thay vì chỉ thông qua tài khoản chính thức của Merchant.

**BG-03 — Improve Attribution**

Cho phép xác định mối quan hệ:

**Video → Creator → Campaign → Product → Click → Signup → Purchase → Revenue.**

PRD xác định attribution là yếu tố quan trọng của nền tảng.

**BG-04 — Optimize for Revenue**

Không chỉ tối ưu:

- Views
- Likes

- Engagement

mà tối ưu:

- CTR
- Signup

- Conversion
- Revenue

- Revenue per 1,000 Views.

PRD xác định Revenue per 1,000 Views là một chỉ số kinh doanh quan trọng.

**BG-05 — Validate Product-Market Fit**

MVP phải giúp trả lời câu hỏi:

Một AI Product có sẵn sàng trả tiền để sử dụng AI-powered Creator Network nhằm quảng bá và bán sản phẩm hay không?

Đây là mục tiêu validation chính của MVP.

**4. Success Metrics**

**4.1 North Star Metric**

**Attributed Affiliate Revenue**

Doanh thu có thể xác định được nguồn đến từ AI-generated content và creator distribution.

**4.2 Secondary Metrics**

Các KPI chính bao gồm:

**Content Metrics**

- Videos Generated
- Videos Published

- Publish Rate
- Video Completion Rate

**Distribution Metrics**

- Views
- Reach

- Engagement
- CTR

**Conversion Metrics**

- Clicks
- Signups

- Trials
- Paid Users

- Conversion Rate

**Revenue Metrics**

- Revenue
- Revenue / Video

- Revenue / Creator
- Revenue / 1,000 Views (RPM)
- ROI (Return on Investment = Revenue Generated / Commission Expense)
- Affiliate Commission

**Network Metrics**

- Active Creators
- Creator Activation Rate

- Creator Retention

Các nhóm KPI này được xác định trong PRD.

**5. Stakeholders**

**5.1 Merchant**

Merchant là doanh nghiệp hoặc chủ sở hữu AI Product muốn sử dụng platform để quảng bá sản phẩm.

Merchant có nhu cầu:

- Onboard AI Product.
- Cung cấp thông tin sản phẩm.

- Tạo campaign.
- Tạo content.

- Phân phối content qua creator.
- Theo dõi performance.

- Theo dõi signup, conversion và revenue.
- Report video có nội dung sai, misleading hoặc không phù hợp để Platform Admin review.

Các loại sản phẩm mục tiêu bao gồm AI writing tools, AI video tools, AI coding agents, AI productivity SaaS và các AI SaaS tương tự.

**5.2 Creator**

Creator là người tham gia campaign và sử dụng content được platform cung cấp để quảng bá sản phẩm.

Creator có thể là:

- TikTok Creator
- YouTube Creator

- Instagram Creator
- Student

- Freelancer
- Developer

- AI Enthusiast
- Tech Reviewer

Creator không bắt buộc phải có lượng follower lớn.

Creator có nhu cầu:

- Tìm campaign.
- Chọn sản phẩm.

- Nhận content.
- Download video.

- Nhận caption và CTA.
- Nhận Tracking link.

- Đăng content.
- Theo dõi clicks, conversions và earnings.

**5.3 Platform Admin**

Admin chịu trách nhiệm quản lý hoạt động của platform.

Phạm vi quản lý bao gồm:

- Products
- Campaigns

- Creators
- Videos
- Manual review, approve/reject video

- Affiliates
- Traffic

- Conversions
- Commission

- Fraud
- Revenue.

**6. Business Scope**

**6.1 In Scope — MVP**

MVP tập trung vào các nhóm chức năng sau.

**Product Management**

- Product onboarding
- Product URL

- URL crawler
- Product Knowledge Base

- Pricing
- Features

- Merchant Affiliate URL

**AI Content Generation**

- Content Idea Generator
- Hook Generator

- Script Generator
- Caption Generator

**AI Video Generation**

- AI Video Generation
- Screen Recording Workflow

- AI Voice
- Subtitle

- Video Variations

**Creator**

- Creator Registration
- Campaign Participation

- Content Library
- Content Download

- Tracking Link

**Campaign**

- Campaign creation and management
- Product selection

- Commission
- Content requirements

- Approved / Forbidden claims

**Performance**

- Views
- Clicks

- Signups
- Revenue

- Creator Attribution
- Analytics

**Administration**

Admin có khả năng quản lý:

- Products
- Creators

- Videos
- Review / approve / reject video
- Campaigns

- Revenue

Đây là phạm vi MVP được xác định trong PRD §50.

**7. Out of Scope — MVP**

Các chức năng sau không thuộc phạm vi MVP:

- AI Livestream
- 24/7 AI Avatar

- Mobile Application
- Automated login vào số lượng lớn social accounts

- Full Social Posting Automation
- Complex CRM

- Payment Wallet
- AI Marketplace

- Multi-country Payment
- Sophisticated Recommendation Engine

- Full SEO Platform
- Enterprise Integrations

Các chức năng này có thể được xem xét cho các phase sau.

**8. Current State — AS-IS**

Hiện tại Merchant thường phải thực hiện nhiều bước thủ công.

Ví dụ:

**Merchant có AI Product**

→ tự nghiên cứu target audience
→ tự nghĩ content idea
→ tự viết hook
→ tự viết script
→ tạo video
→ tìm creator
→ gửi brief
→ creator đăng video
→ sử dụng tracking link
→ Merchant thu thập analytics
→ Merchant cố gắng xác định nội dung nào tạo revenue.

Quy trình này dẫn đến:

- Production capacity thấp.
- Chi phí content cao.

- Khó scale.
- Content quality không nhất quán.

- Khó kiểm soát claims.
- Khó tracking attribution.

- Khó xác định content nào thực sự tạo revenue.

**9. Target State — TO-BE**

Quy trình mong muốn:

**Merchant adds AI Product**

↓

**Platform builds Product Knowledge**

↓

**AI identifies Content Opportunities**

↓

**AI generates Hooks / Scripts / Captions**

↓

**AI generates Video Content**

↓

**Platform Admin performs Manual QA and approves/rejects Video**

↓

**Merchant creates Campaign**

↓

**Creators join Campaign**

↓

**Creator selects Content**

↓

**Creator downloads and publishes Content**

↓

**Creator uses unique Tracking link**

↓

**Platform tracks Click / Signup / Purchase**

↓

**Platform calculates Attribution & Revenue**

↓

**Performance Data is analyzed**

↓

**Winning Content Patterns are identified**

↓

**Future Content is optimized**

Creator workflow cốt lõi của PRD là Join Campaign → Choose Product → Select AI-generated Video → Download → Copy Caption → Post → Attach Tracking Link → Track Traffic → Conversion → Commission.

**10. Business Requirements**

**BR-01 — Product Onboarding**

Platform phải cho phép Merchant đưa một AI Product vào hệ thống.

Trong phạm vi MVP, Merchant phải cung cấp tối thiểu:

- **Website URL**
- **Merchant Affiliate URL**

Website URL được sử dụng làm nguồn đầu vào để Platform thu thập thông tin công khai và xây dựng Product Knowledge Base.

Merchant Affiliate URL là URL do Merchant cung cấp liên quan đến chương trình affiliate hoặc destination của Product và **khác với Tracking Link do Platform tạo cho Creator**.

Các thông tin khác có thể được Merchant cung cấp thủ công hoặc được Platform thu thập/suy luận từ Product source, bao gồm:

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
- Forbidden Claims

Merchant phải có khả năng review và xác nhận Product Knowledge trước khi dữ liệu được sử dụng cho các bước tạo content tiếp theo. Hệ thống phải tự động phát hiện và cảnh báo các xung đột dữ liệu (ví dụ chênh lệch giá giữa form nhập và nội dung cào từ web) để Merchant chủ động lựa chọn.

**BR-02 — Product Intelligence**

Platform phải có khả năng tổng hợp thông tin cần thiết để hiểu AI Product bao gồm:

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

Mọi thông tin/tính năng bóc tách được phải gắn liền với nguồn trích dẫn và bằng chứng xác thực (đoạn trích dẫn nguyên văn từ website sản phẩm) để đảm bảo tính minh bạch, giúp Merchant tuyệt đối tin tưởng và dễ dàng kiểm chứng.

Trong phạm vi MVP, Merchant chịu trách nhiệm review, chỉnh sửa và approve Product Knowledge của Product.

Platform Admin không tham gia vào từng lần approve Product Knowledge.

Product Knowledge chỉ được xem là approved sau khi Merchant xác nhận.

**BR-03 — Content Opportunity Generation**

Platform phải có khả năng biến Product Knowledge thành các Content Opportunities khác nhau.

Ví dụ:

- Problem
- Demo

- Comparison
- Tutorial

- Before / After
- Mistake

- Listicle
- Reaction

- Challenge
- Hidden Feature

- Cost Saving
- Workflow.

**BR-04 — AI Hook Generation**

Platform phải hỗ trợ tạo nhiều hook khác nhau cho cùng một product để phục vụ content experimentation.

**BR-05 — AI Script Generation**

Platform phải tạo script dựa trên các input như:

- Product
- Audience

- Hook
- Content Intent

- Platform
- Video Length

- Creator Persona
- CTA.

Output script có thể gồm:

**Hook → Problem → Demo → Result → Proof → CTA.**

**BR-06 — AI Video Generation**

Platform phải hỗ trợ tạo video review từ các script đã được tạo.

Các format có thể bao gồm:

- Screen Recording
- AI Avatar
- Faceless
- Hybrid.

Trong giai đoạn MVP và mô hình zero-budget, hệ thống ưu tiên tuyệt đối định dạng **Screen Recording (chụp/quay màn hình sản phẩm thực tế kết hợp lồng tiếng và phụ đề)**. Format này vừa đảm bảo bằng chứng xác thực (evidence) cao nhất cho người mua, vừa tiết kiệm 100% chi phí thuê ngoài các dịch vụ avatar AI tốn kém.

**BR-07 — Video Variations**

Một script có thể tạo thành nhiều creative variations dựa trên:

- Hook
- Persona
- Format
- Length.

Platform không bắt buộc publish tất cả variations mà có thể lựa chọn nội dung phù hợp với creator và channel.

**BR-08 — Campaign Management**

Merchant phải có khả năng tạo campaign.

Campaign có thể bao gồm:

- Campaign Name
- Product
- Start Date
- End Date
- Target Audience
- Target Country
- Language – English
- Commission
- Content Requirements
- Approved Claims
- Forbidden Claims
- CTA.

**BR-09 — Creator Registration**

Platform phải cho phép Creator tạo tài khoản và profile để tham gia creator network.

**BR-10 — Campaign Discovery**

Creator phải có khả năng xem và lựa chọn các campaign phù hợp.

Campaign information có thể bao gồm:

- Product
- Commission
- Recommended Content
- Expected Audience
- Video Library
- Tracking Link.

**BR-11 — Creator Content Library**

Creator phải có khả năng truy cập các content asset liên quan đến campaign, bao gồm:

- Video
- Caption
- Hashtags
- CTA
- Tracking Link
- Posting Instructions.

Giao diện thư viện phải thiết kế dạng "1-click" tiện lợi, sẵn sàng để Creator sử dụng ngay mà không đòi hỏi kỹ năng chỉnh sửa video phức tạp.

**BR-12 — Content Distribution**

Trong MVP, quá trình publish được thực hiện theo mô hình **semi-automatic**.

Creator:

- Download video.
- Copy content/caption.
- Publish trên social platform.
- Attach tracking link.
- **Nộp lại Proof of Publishing (link bài đăng thực tế trên TikTok/Reels/Shorts)** qua chức năng "Tôi đã đăng" để hệ thống và Merchant theo dõi được trạng thái chiến dịch.

Platform không tự động đăng nhập và publish trên hàng nghìn social accounts trong MVP.

**BR-13 — Tracking Link Generation**

Platform phải tạo **unique Tracking Link** có thể xác định tối thiểu:

- Creator
- Campaign

- Product

Tracking Link được Platform tạo cho từng hoạt động phân phối và không phải là Merchant Affiliate URL được Merchant cung cấp trong Product Onboarding.

**BR-14 — Conversion Attribution**

Platform phải có khả năng xác định:

Video nào → Creator nào → Campaign nào → Product nào → Revenue nào.

Data attribution dự kiến bao gồm:

- video_id
- creator_id

- campaign_id
- product_id

- click_id
- visitor_id

- signup_id
- order_id

- revenue
- commission.

**BR-15 — Merchant Performance Dashboard**

Merchant phải có khả năng theo dõi các nhóm dữ liệu:

**Content**

- Videos Created
- Videos Published

- Creators Active
- Content Volume

**Distribution**

- Views
- Reach

- Engagement
- Clicks

**Business**

- Signups
- Trials

- Paid Users
- Revenue

- Affiliate Commission
- ROI.

**BR-16 — Creator Performance Dashboard**

Creator phải có khả năng theo dõi:

- Total Revenue
- Pending Commission

- Paid Commission
- Clicks

- Signups
- Conversions

- Best Videos
- Best Products

- Conversion Rate
- Revenue / 1,000 Views.

**BR-17 — Platform Administration**

Admin phải có khả năng quản lý các business entities chính:

- Product
- Campaign

- Creator
- Content / Video

- Conversion
- Revenue.

Đối với video trong MVP, **Platform Admin là actor thực hiện manual review và quyết định approve/reject video trước khi video được phép đưa vào Content Library để Creator sử dụng**.

Merchant không thực hiện approve/reject từng video.

**BR-18 — AI Quality Control**

Platform phải kiểm tra nội dung nhằm giảm nguy cơ tạo thông tin sai hoặc misleading.

Các nhóm kiểm tra bao gồm:

- Factual Accuracy
- Pricing

- Features
- Product Limits

- Availability
- Claims

- Brand
- Compliance.

Platform không được chủ động tạo:

- Fake Reviews
- Fake Testimonials

- Fake Results
- Misleading Claims

- Fabricated Screenshots
- Fabricated Product Features.

Ngoài automated AI Quality Control, **Platform Admin phải đóng vai trò manual reviewer đối với video trong MVP**.

Admin phải có khả năng:

- Review video sau bước AI Quality Control.
- Approve video đạt yêu cầu.
- Reject video không đạt yêu cầu.
- Đảm bảo chỉ video đã được Admin approve mới được đưa vào Content Library cho Creator sử dụng.

Merchant không phải actor approve/reject từng video.

Nếu Merchant phát hiện video sai, misleading hoặc không phù hợp sau khi được tạo/approve, Merchant phải có khả năng **report video** để Platform Admin review và xử lý theo quyền quản trị.

**BR-19 — Content Authenticity**

Review content nên có khả năng gắn với evidence như:

- Screen Recording
- Actual Product Output

- Test Dataset
- Test Date

- Product Version

nhằm tăng mức độ tin cậy của nội dung.

**BR-20 — Content Diversity**

Platform cần hạn chế việc nhiều creator đăng nội dung quá giống nhau.

Content nên được đa dạng hóa theo:

- Audience
- Creator

- Hook
- Content Angle

- CTA
- Visual

- Voice.

PRD xác định hệ thống cần phát hiện duplicate hooks, scripts, visuals, voice và CTA.

**11. Business Rules**

**BRULE-01 — Revenue over Vanity Metrics**

Một video có nhiều views không mặc nhiên được coi là thành công.

Content phải được đánh giá dựa trên commercial performance như:

- CTR
- Signup

- Conversion
- Revenue.

**BRULE-02 — Creator-specific Attribution**

Mỗi creator phải có tracking mechanism riêng để xác định hiệu quả phân phối của creator đó.

**BRULE-03 — Campaign-specific Attribution**

Performance phải được liên kết với campaign tương ứng.

**BRULE-04 — Product-specific Attribution**

Conversion và revenue phải có khả năng liên kết về AI Product tương ứng.

**BRULE-05 — No Unsupported Claims**

Content không được sử dụng claim không được Merchant cho phép hoặc không có evidence.

**BRULE-06 — Forbidden Claims**

Nếu Merchant định nghĩa Forbidden Claims, AI-generated content không được chứa các claim đó.

**BRULE-07 — Authentic Review**

Platform không được tự tạo nội dung theo kiểu:

“I tested this product…”

nếu không có evidence cho việc đã thực hiện test thực tế.

**BRULE-08 — MVP Distribution Model**

MVP sử dụng semi-automatic distribution.

Creator tự publish nội dung lên platform của họ.

**BRULE-09 — Zero Upfront Financial Risk for Merchants**

Merchant tham gia platform với mô hình chia sẻ doanh thu thuần túy (affiliate commission khi có conversion thành công). Không áp dụng phí khởi tạo, phí duy trì hay chi phí tạo video trả trước nhằm tối đa hóa việc thu hút Merchant tham gia hệ thống.

**BRULE-10 — Zero Friction Distribution for Creators**

Nội dung cung cấp trong Content Library phải đạt tiêu chuẩn sẵn sàng đăng ngay (1-click ready). Creator không cần đầu tư thiết bị hay kỹ năng quay dựng chuyên nghiệp để có thể tham gia kiếm tiền từ mạng lưới.

**BRULE-11 — Full Evidence Traceability**

Mọi fact/tính năng trong Product Knowledge Base dùng để tạo kịch bản video review bắt buộc phải có nguồn trích dẫn từ tài liệu công khai của sản phẩm và có đoạn trích chứng minh (evidence), triệt tiêu hoàn toàn rủi ro AI bịa đặt thông tin.

**12. Constraints**

**12.1 MVP Scope Constraint**

MVP phải tập trung vào việc validate business model thay vì xây dựng toàn bộ long-term vision.

**12.2 Social Platform Constraint**

Không thực hiện automated login và mass posting trên social platforms trong MVP do các rủi ro liên quan tới:

- Platform Policy
- Spam
- Duplicate Content
- Account Ban
- Account Safety.

**12.3 Content Compliance Constraint**

AI-generated content phải tuân thủ:

- Merchant Brand Guidelines
- Approved Claims
- Forbidden Claims
- Platform Rules
- Các yêu cầu disclosure phù hợp khi sử dụng AI Avatar.

**12.4 MVP Language Constraint**

Trong phạm vi MVP, ngôn ngữ được hỗ trợ chính là English đối với:

- Product source
- Product Knowledge Base
- AI-generated content
- AI-generated video

Multilingual support và Localization không thuộc phạm vi MVP và được xem xét trong các phase sau.

**13. Assumptions**

Các giả định dưới đây cần được stakeholder xác nhận trước khi chuyển sang SRS.

**A-01**

Merchant chịu trách nhiệm cung cấp thông tin sản phẩm chính xác và review, chỉnh sửa, approve Product Knowledge được Platform thu thập hoặc tạo ra.

**A-02**

Creator chịu trách nhiệm thực hiện việc publish content lên tài khoản social của họ trong MVP.

**A-03**

Merchant có affiliate program hoặc có cơ chế xác định commission cho campaign.

**A-04**

Trong phạm vi MVP, Merchant cung cấp dữ liệu Signup, Trial, Paid Conversion và Revenue cho Platform thông qua CSV file import theo format do Platform quy định (gồm các cột cốt lõi: `click_id`, `external_user_id`, `order_id`, `event_type`: `signup` / `trial` / `paid`, `event_time`, `revenue_amount`, `currency`).

Platform sử dụng dữ liệu trong CSV kết hợp với Tracking Link/Click Identifier và `external_user_id` để thực hiện conversion attribution và kiểm tra điều kiện hoa hồng (`commission_eligibility`).

Realtime integration thông qua API, Webhook, SDK hoặc Pixel không thuộc phạm vi MVP.

**A-05**

Creator và Merchant sử dụng web platform trong MVP vì Mobile App nằm ngoài phạm vi MVP.

**A-06**

Để đảm bảo khả thi cho mô hình bootstrap/zero-budget, hệ thống sử dụng Full PKB Prompt Context thay vì hạ tầng vector database đắt đỏ trong MVP, đảm bảo chi phí LLM trung bình $\le \$0.05$/sản phẩm.

**14. Risks**

**R-01 — Content Accuracy Risk**

AI có thể tạo thông tin sai về:

- Pricing
- Features

- Limitations
- Product Capability.

**Mitigation:** Quality Control + Merchant confirmation + Admin manual review đối với video.

**R-02 — Misleading Content Risk**

AI-generated content có thể tạo claim quá mức hoặc fake experience.

**Mitigation:** Approved Claims, Forbidden Claims, Evidence, AI Quality Control và Admin manual review đối với video.

**R-03 — Social Platform Policy Risk**

Content automation hoặc duplicate content có thể dẫn tới hạn chế hoặc ban tài khoản.

**Mitigation:** Semi-automatic distribution trong MVP và Content Diversity Control.

**R-04 — Attribution Accuracy Risk**

Không đầy đủ dữ liệu conversion có thể khiến hệ thống không xác định chính xác revenue source.

**Mitigation:** Unique tracking links và integration với Merchant conversion data.

**R-05 — Creator Adoption Risk**

Creator có thể không muốn sử dụng hoặc đăng AI-generated content.

Đây cũng là một trong các No-Go criteria của product validation.

**R-06 — Merchant Adoption Risk**

Merchant có thể không sẵn sàng trả phí hoặc commission cho mô hình creator distribution.

Điều này phải được kiểm chứng trong MVP/Pilot.

**15. MVP Validation**

MVP nên được thiết kế đủ nhỏ để kiểm chứng business model.

Recommended workflow:

**1 AI Product**

→ **5 Content Angles**

→ **20 Hooks**

→ **20 Scripts**

→ **50 Videos**

→ **10 Creators**

→ **100 Published Posts**

→ **Track Clicks**

→ **Track Signups**

→ **Track Revenue**.

**16. Pilot Approach**

PRD đề xuất pilot ban đầu với:

- 3 AI Products
- 10 Creators

- 100 Videos
- 30 Days.

Ba nhóm sản phẩm mẫu:

- AI Video
- AI Productivity

- AI Coding.

Các metric cần theo dõi:

- Views
- Clicks

- Signups
- Paid Users

- Revenue.

**17. Go / No-Go Criteria**

**GO**

Tiếp tục phát triển/scale nếu:

- Creator tiếp tục đăng content.
- Content tạo traffic.

- Traffic tạo signup.
- Signup tạo paid users.

- AI Product Merchant muốn tiếp tục.
- Affiliate revenue có xu hướng tăng.

**NO-GO / Re-evaluate**

Cần xem xét lại mô hình nếu:

- Creator không muốn đăng.
- AI-generated content không có engagement.

- Có views nhưng không có clicks.
- Có clicks nhưng không có conversion.

- Merchant không sẵn sàng trả commission.
- Unit economics không phù hợp để scale.

**18. Future Scope**

Các capability sau thuộc định hướng phát triển sau MVP và không phải commitment hiện tại:

- AI Review Agent
- AI Comparison Engine

- AI Trend Engine
- Advanced Content Intelligence

- Automated Optimization Loop
- SEO Content Engine

- AI Landing Pages
- Multi-channel Automation

- Localization
- Advanced Recommendation

- Autonomous Growth Agent.

Long-term direction của sản phẩm là tiến từ:

**AI Review Content Factory**

→ **AI Creator Network**

→ **AI Affiliate Network**

→ **AI Growth Engine**

→ **Autonomous AI Growth Agent.**

**19. Open Questions for Stakeholder Confirmation**

**Decision đã chốt về Video Approval / Manual QA:** Platform Admin thực hiện manual review và approve/reject từng video trong MVP. Merchant không approve/reject từng video. Merchant có thể report video sai/misleading để Admin review.

Các nội dung dưới đây chưa được PRD mô tả đủ chi tiết và cần làm rõ trước khi hoàn thành SRS.

| **ID** | **Question** |
| --- | --- |
| Q-01 | Merchant registration và approval process như thế nào? |
| Q-02 | Creator có cần Admin approve trước khi tham gia network không? |
| Q-03 | Creator có tự do join campaign hay Merchant phải approve? |
| Q-04 | Merchant có thể giới hạn số Creator trong một Campaign không? |
| Q-05 | Commission được tính theo signup, purchase hay recurring revenue? |
| Q-06 | Khi nào commission được xác nhận là payable? |
| Q-07 | MVP có xử lý payout thật cho Creator hay chỉ hiển thị commission? |
| Q-10 | Creator có được chỉnh sửa video/caption do AI tạo không? |
| Q-11 | Merchant có thể pause hoặc terminate campaign không? |
| Q-12 | Creator có thể tham gia nhiều campaign cùng lúc không? |
| Q-13 | Một Product có thể thuộc nhiều Campaign không? |
| Q-14 | MVP hỗ trợ những social platform nào đầu tiên? |
| Q-15 | Analytics lấy Views và Engagement trực tiếp từ social platform hay Creator nhập thủ công? |
| Q-16 | Có yêu cầu fraud detection nào bắt buộc trong MVP không? |
| Q-17 | Có cơ chế dispute commission giữa Merchant và Creator không? |
| Q-18 | Data retention và privacy requirements của hệ thống là gì? |

**20. Requirement Traceability — Business Level**

| **Business Goal** | **Related Business Requirements** |
| --- | --- |
| Scale Content Production | BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07 |
| Scale Distribution | BR-08, BR-09, BR-10, BR-11, BR-12 |
| Affiliate Revenue | BR-13, BR-14 |
| Performance Measurement | BR-14, BR-15, BR-16 |
| Platform Control | BR-17 |
| Content Quality | BR-18, BR-19, BR-20 |
| Revenue Optimization | BR-14, BR-15, BR-16 |

**21. Approval Criteria**

BRD được xem là hoàn tất khi các stakeholder thống nhất tối thiểu các nội dung:

- Business Problem
- Business Objectives

- Stakeholders
- MVP Scope

- Out of Scope
- Business Requirements

- Business Rules
- Main Business Flow

- Success Metrics
- Assumptions

- Open Questions ảnh hưởng trực tiếp đến MVP.

Sau khi BRD được approve, team có thể tiếp tục xây dựng:

**BRD**

→ **SRS**

→ **Process / User Flow**

→ **Epic**

→ **User Story**

→ **Acceptance Criteria**

→ **Sprint Backlog**

→ **Development & Testing**

**22. Business Definition**

Sản phẩm được định nghĩa ở mức business như sau:

**AI Review Content Factory & Affiliate Network là nền tảng giúp AI Product Merchant biến thông tin sản phẩm thành AI-generated review content, phân phối nội dung thông qua Creator/Affiliate Network, theo dõi conversion và liên tục tối ưu content dựa trên attributed revenue.**

Business principle cốt lõi:

**AI Products In → Revenue Out.**