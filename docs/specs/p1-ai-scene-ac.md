# P1 — AC-P1-05: cảnh minh họa AI và ba preset

**Trạng thái:** phạm vi được team lead xác nhận tại [#67](https://github.com/PotatoMine725/AI-review-BE/issues/67#issuecomment-6159883438), ngày 14/10/2026. Đây là nội dung cập nhật cho AC-P1-05 của P1; đưa nguyên tắc và tiêu chí bên dưới vào bản kế hoạch P1 v1.2 khi `p1-yeu-cau-va-ke-hoach.md` được thêm vào repo. Tài liệu này không thay thế toàn bộ kế hoạch P1.

## Quyết định phạm vi

- P1 chấp nhận **ảnh do hệ thống sinh thật qua adapter AI**, sau đó dùng FFmpeg tạo chuyển động, làm cảnh minh họa AI. Clip chuyển động do model video sinh là phần mở rộng khi có nguồn lực phù hợp.
- Bộ demo P1 có ít nhất **một video cho mỗi sản phẩm** kết hợp tư liệu sản phẩm thật có quyền sử dụng với ít nhất một cảnh minh họa AI. Zoom/pan ảnh sản phẩm có sẵn chỉ là hiệu ứng dựng, không được tính là cảnh AI.
- Ba preset dùng tên: **hoạt hình đồ họa**, **điện ảnh tối giản**, **cổ điển**.
- Không tự bật dịch vụ trả phí khi chưa được cấp ngân sách hoặc credit.
- Mỗi video MP4 P1 hoàn chỉnh dài **40–45 giây**, thay mốc 15–25 giây trước đây. Đo trên MP4 cuối, gồm hook, nội dung, CTA, khoảng nghỉ và chuyển cảnh; không chỉ tính audio TTS. Ghi nhận tại [#67](https://github.com/PotatoMine725/AI-review-BE/issues/67), đồng bộ từ #80.

## Nội dung AC-P1-05 cập nhật cho P1 v1.2

1. **Cảnh AI và tư liệu sản phẩm:** Given sản phẩm có tư liệu thật đã xác nhận quyền sử dụng, when tạo bộ video demo P1, then mỗi sản phẩm có ít nhất một video chứa cả tư liệu thật đúng sản phẩm và ít nhất một ảnh minh họa do hệ thống sinh qua adapter AI, được đưa vào video với chuyển động FFmpeg. Ảnh giả/fixture dùng cho spike không được tính là tư liệu sản phẩm thật.
2. **Bằng chứng lần sinh:** Given một cảnh được tính là cảnh AI, when QA kiểm tra, then có thể truy từ cảnh trong video tới ảnh đầu ra và dấu vết lần sinh thật (adapter, provider/model, cấu hình, thời điểm và mã lần gọi hoặc log tương đương). Ghi usage/chi phí nếu provider trả về; nếu không, ghi cách ước tính và `cost_status: estimated` trong `cost-breakdown.v1`. Contract v1 hiện chưa có trường riêng cho đơn vị sinh ảnh; AI–BE bổ sung contract nếu cần đo số ảnh/đơn vị tính. Ước tính usage không thay cho bằng chứng lần sinh. Cache hit chỉ được tính khi truy được về lần sinh gốc.
3. **Tính xác thực:** Given ảnh AI được dùng trong video, when kiểm tra nội dung, then ảnh được nhận diện là minh họa bối cảnh/chuyển cảnh; không thay screenshot thật và không làm bằng chứng giả cho hình dáng, tính năng hoặc kết quả sản phẩm. Zoom/pan trên ảnh có sẵn, không có ảnh AI được sinh thật, không đạt tiêu chí cảnh AI.
4. **Ba preset:** Given cùng dữ liệu sản phẩm, when render từng preset, then tạo được đầu ra được gắn đúng một trong ba tên đã thống nhất, có cấu hình và mẫu video để QA đối chiếu sự khác biệt về cách trình bày; thông tin và tư liệu sản phẩm vẫn chính xác ở cả ba. Khả năng render 9:16/16:9 được kiểm tra theo spike renderer của #67.
5. **Thiếu nguồn lực hoặc asset hợp lệ:** Given chưa có quyền dùng tư liệu thật, chưa có lượt sinh AI được chứng minh, hoặc chưa có quota/ngân sách cho provider cần thiết, when đánh giá AC-P1-05, then ghi rõ phần thiếu/Blocked. Không thay bằng fixture hay chỉ hiệu ứng FFmpeg rồi báo đạt.

## Mốc 18/10 và P1 nghiệm thu

Spike 18/10 có thể dùng fixture được ghi rõ để chứng minh renderer, TTS và adapter. Báo cáo tách kết quả kỹ thuật khỏi kết quả trên sản phẩm thật; fixture không chứng minh AC-P1-05 đã đạt. Bộ demo P1 nghiệm thu vẫn theo phạm vi đã nêu ở #67: tối thiểu hai sản phẩm, mỗi sản phẩm ba video khác nội dung, tiếng Việt, dài 40–45 giây. AC-P1-05 quy định mức tối thiểu về cảnh AI **trên mỗi sản phẩm**, không yêu cầu cả ba video của sản phẩm đều có cảnh AI.
