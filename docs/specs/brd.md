<!--
Bản nháp BRD (Business Requirements Document) v0.1 do BA (@khanhphi27) soạn, được @PotatoMine725 đưa vào repo ngày 2026-10-07 để cả team dẫn link.
Nội dung giữ nguyên văn bản BA gửi. Góp ý và câu hỏi mở: xem issue góp ý BRD/SRS và docs/logs/qa-log.md.
Khi mâu thuẫn với decision-log / đặc tả module đã chốt, các tài liệu đó được ưu tiên cho tới khi BA cập nhật bản này.
-->

**BUSINESS REQUIREMENTS DOCUMENT**

**Project:** AI Review Content Factory & Affiliate Network
**Document Type:** Business Requirements Document — BRD
**Version:** 0.1
**Status:** Draft for Stakeholder Review
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
- Revenue / 1,000 Views

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
- Nhận affiliate link.

- Đăng content.
- Theo dõi clicks, conversions và earnings.

**5.3 Platform Admin**

Admin chịu trách nhiệm quản lý hoạt động của platform.

Phạm vi quản lý bao gồm:

- Products
- Campaigns

- Creators
- Videos

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

- Affiliate information

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

- Affiliate Link

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
→ sử dụng affiliate link
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

**Merchant creates Campaign**

↓

**Creators join Campaign**

↓

**Creator selects Content**

↓

**Creator downloads and publishes Content**

↓

**Creator uses unique Affiliate Link**

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

Creator workflow cốt lõi của PRD là Join Campaign → Choose Product → Select AI-generated Video → Download → Copy Caption → Post → Attach Affiliate Link → Track Traffic → Conversion → Commission.

**10. Business Requirements**

**BR-01 — Product Onboarding**

Platform phải cho phép Merchant đưa một AI Product vào hệ thống.

Merchant có thể cung cấp các thông tin như:

- Product Name
- Website

- Product URL
- Description

- Target Audience
- Pricing

- Main Features
- Use Cases

- Competitors
- Affiliate Program

- Commission
- USP

- Limitations
- Brand Guidelines

- Forbidden Claims

PRD cũng đề xuất luồng đơn giản hơn là Merchant chỉ paste URL và AI tự xây dựng Product Knowledge Base.

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

PRD đặc biệt ưu tiên Screen Recording vì AI Product review cần evidence và product demonstration.

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

- Language
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
- Affiliate Link.

**BR-11 — Creator Content Library**

Creator phải có khả năng truy cập các content asset liên quan đến campaign, bao gồm:

- Video
- Caption

- Hashtags
- CTA

- Affiliate Link
- Posting Instructions.

**BR-12 — Content Distribution**

Trong MVP, quá trình publish được thực hiện theo mô hình **semi-automatic**.

Creator:

- Download video.
- Copy content/caption.

- Publish trên social platform.
- Attach affiliate link.

Platform không tự động đăng nhập và publish trên hàng nghìn social accounts trong MVP.

**BR-13 — Affiliate Link Generation**

Platform phải tạo unique tracking link có thể xác định tối thiểu:

- Creator
- Campaign

- Product.

PRD mô tả tracking flow:

**Impression → Click → Landing → Signup → Trial → Purchase → Revenue.**

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
- Content

- Conversion
- Revenue.

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

**13. Assumptions**

Các giả định dưới đây cần được stakeholder xác nhận trước khi chuyển sang SRS.

**A-01**

Merchant chịu trách nhiệm cung cấp thông tin sản phẩm chính xác hoặc xác nhận Product Knowledge được AI thu thập.

**A-02**

Creator chịu trách nhiệm thực hiện việc publish content lên tài khoản social của họ trong MVP.

**A-03**

Merchant có affiliate program hoặc có cơ chế xác định commission cho campaign.

**A-04**

Platform có thể nhận hoặc thu thập dữ liệu cần thiết để xác định clicks, signups, conversions và revenue.

**A-05**

Creator và Merchant sử dụng web platform trong MVP vì Mobile App nằm ngoài phạm vi MVP.

**14. Risks**

**R-01 — Content Accuracy Risk**

AI có thể tạo thông tin sai về:

- Pricing
- Features

- Limitations
- Product Capability.

**Mitigation:** Quality Control + Merchant confirmation.

**R-02 — Misleading Content Risk**

AI-generated content có thể tạo claim quá mức hoặc fake experience.

**Mitigation:** Approved Claims, Forbidden Claims, Evidence và AI Quality Control.

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

Các nội dung dưới đây chưa được PRD mô tả đủ chi tiết và cần làm rõ trước khi hoàn thành SRS.

| **ID** | **Question** |
| --- | --- |
| Q-01 | Merchant registration và approval process như thế nào? |
| Q-02 | Creator có cần Admin approve trước khi tham gia network không? |
| Q-03 | Creator có tự do join campaign hay Merchant phải approve? |
| Q-04 | Merchant có thể giới hạn số Creator trong một Campaign không? |
| Q-05 | Commission được tính theo signup, purchase hay recurring revenue? |
| Q-06 | Platform nhận dữ liệu conversion từ Merchant bằng API, webhook hay tracking pixel? |
| Q-07 | Khi nào commission được xác nhận là payable? |
| Q-08 | MVP có xử lý payout thật cho Creator hay chỉ hiển thị commission? |
| Q-09 | Merchant có phải approve video trước khi Creator download/publish không? |
| Q-10 | AI-generated video có cần manual QA không? |
| Q-11 | Creator có được chỉnh sửa video/caption do AI tạo không? |
| Q-12 | Nếu Product Knowledge do crawler thu thập sai thì ai chịu trách nhiệm xác nhận? |
| Q-13 | Merchant có thể pause hoặc terminate campaign không? |
| Q-14 | Creator có thể tham gia nhiều campaign cùng lúc không? |
| Q-15 | Một Product có thể thuộc nhiều Campaign không? |
| Q-16 | MVP hỗ trợ những social platform nào đầu tiên? |
| Q-17 | Analytics lấy Views và Engagement trực tiếp từ social platform hay Creator nhập thủ công? |
| Q-18 | Có yêu cầu fraud detection nào bắt buộc trong MVP không? |
| Q-19 | Có cơ chế dispute commission giữa Merchant và Creator không? |
| Q-20 | Data retention và privacy requirements của hệ thống là gì? |

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