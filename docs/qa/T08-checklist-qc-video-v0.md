# CHECKLIST QC VIDEO & NỘI DUNG V0 (TASK T08)

- **Dự án:** AI Review Content Factory & Affiliate Network
- **Mã công việc:** `T08` (Sprint 0)
- **Phiên bản:** 1.0
- **Ngày lập:** 05/10/2026

- **Reviewer phối hợp:** AI-2 (Kịch bản) & Video-1 (Render)
- **Mục tiêu:** Cung cấp bảng tiêu chí bắt buộc để Admin kiểm duyệt video demo trước khi chuyển trạng thái sang `Approved` cho Creator tải về.

---

## 1. TIÊU CHUẨN KỸ THUẬT VIDEO (TECHNICAL SPECS)

| STT | Hạng mục kiểm tra | Tiêu chuẩn bắt buộc | Đạt (Pass) | Không đạt (Fail) | Ghi chú |
|:---:|---|---|:---:|:---:|---|
| 1.1 | **Tỷ lệ khung hình (Aspect Ratio)** | Chuẩn dọc **9:16** (1080 x 1920 pixels), không bị méo hình, không bị viền đen thừa | [ ] | [ ] | Phù hợp TikTok, Reels, Shorts |
| 1.2 | **Thời lượng (Duration)** | Từ **15 đến 30 giây** (tối ưu nhất 20–25s) | [ ] | [ ] | Quá 30s dễ giảm tỷ lệ xem hết |
| 1.3 | **Vùng an toàn (Safe Zone)** | Nội dung chính, chữ phụ đề và logo nằm trong vùng an toàn (cách mép trên 150px, mép dưới 250px, mép phải 120px) | [ ] | [ ] | Không bị che bởi icon Like, Share, Avatar hoặc Caption của nền tảng |
| 1.4 | **Định dạng & Dung lượng** | File định dạng `.mp4` (H.264/AAC), dung lượng tối đa $\le 30$ MB | [ ] | [ ] | Load nhanh trên mobile |

---

## 2. CHẤT LƯỢNG ÂM THANH & PHỤ ĐỀ (AUDIO & SUBTITLES)

| STT | Hạng mục kiểm tra | Tiêu chuẩn bắt buộc | Đạt (Pass) | Không đạt (Fail) | Ghi chú |
|:---:|---|---|:---:|:---:|---|
| 2.1 | **Giọng đọc (Voice / TTS)** | Âm thanh to, rõ ràng, không lẫn tạp âm, ngữ điệu tự nhiên, nhịp điệu vừa phải (140–160 từ/phút) | [ ] | [ ] | Tránh giọng đọc robot vô cảm |
| 2.2 | **Khớp âm thanh - hình ảnh** | Lời đọc khớp 100% với thao tác trên màn hình | [ ] | [ ] | |
| 2.3 | **Phụ đề (Captions/Subtitles)** | Phụ đề tự động hiện đúng từng từ (word-by-word hoặc từng cụm ngắn), font chữ dày, dễ đọc, có viền hoặc nền tương phản | [ ] | [ ] | Người xem tắt tiếng vẫn hiểu |
| 2.4 | **Chính tả phụ đề** | Không sai chính tả tiếng Anh/tiếng Việt, viết đúng tên thương hiệu sản phẩm (ví dụ: Gamma, ChatGPT, Claude) | [ ] | [ ] | |

---

## 3. CHẤT LƯỢNG NỘI DUNG & FACT-CHECKING (AUTHENTICITY & TRUTH)

> **Cảnh báo Anti-Slop:** Không duyệt bất kỳ video nào có dấu hiệu bịa đặt thông tin hoặc tâng bốc sai sự thật!

| STT | Hạng mục kiểm tra | Tiêu chuẩn bắt buộc | Đạt (Pass) | Không đạt (Fail) | Ghi chú |
|:---:|---|---|:---:|:---:|---|
| 3.1 | **Bằng chứng thực tế (Proof / Demo)** | Video phải có cảnh quay màn hình (Screen recording) thao tác thật trên sản phẩm; không dùng ảnh chụp màn hình giả mạo | [ ] | [ ] | Cốt lõi của video review |
| 3.2 | **Đúng thông tin sản phẩm (Fact-check)** | Giá cả gói cước, tính năng, giới hạn dùng thử phải khớp 100% với tài liệu **Golden Facts** đã duyệt | [ ] | [ ] | Tuyệt đối không bịa giá |
| 3.3 | **Không giả mạo trải nghiệm** | Nghiêm cấm câu nói bịa đặt: *"Tôi đã dùng công cụ này 6 tháng..."* hoặc lời chứng thực (testimonial) giả nếu không có bằng chứng | [ ] | [ ] | Tuân thủ chính sách quảng cáo |
| 3.4 | **Cấu trúc kịch bản 30s** | Đủ 5 phần: Hook (0-3s) $\to$ Problem (3-8s) $\to$ Demo (8-20s) $\to$ Result (20-26s) $\to$ Call-to-action (26-30s) | [ ] | [ ] | |

---

## 4. TUÂN THỦ CHÍNH SÁCH & THƯƠNG HIỆU (COMPLIANCE & BRANDING)

| STT | Hạng mục kiểm tra | Tiêu chuẩn bắt buộc | Đạt (Pass) | Không đạt (Fail) | Ghi chú |
|:---:|---|---|:---:|:---:|---|
| 4.1 | **Nhãn công bố nội dung AI (AI Disclosure)** | Có gắn nhãn hoặc chú thích nhỏ "AI-assisted content / Generated with AI" nếu sử dụng giọng đọc tổng hợp hoặc avatar | [ ] | [ ] | Tránh vi phạm chính sách TikTok/YouTube |
| 4.2 | **Lời kêu gọi hành động (CTA)** | CTA rõ ràng, điều hướng người xem: *"Link dùng thử ở phần bio/mô tả"* | [ ] | [ ] | Phục vụ kéo click tracking |
| 4.3 | **Quyền sở hữu tài sản (Asset Licensing)** | Logo, icon, font chữ, âm nhạc nền (BGM) phải là tài sản được phép sử dụng thương mại hoặc miễn phí bản quyền | [ ] | [ ] | Tránh gậy bản quyền âm thanh |

---

## 5. KẾT LUẬN KIỂM DUYỆT (QC VERDICT)

* **Tổng số tiêu chí:** 16 tiêu chí
* **Kết quả:**
  * [ ] **APPROVED (Đạt):** Đạt 16/16 tiêu chí $\to$ Cho phép chuyển sang thư viện Creator.
  * [ ] **REJECTED (Từ chối):** Vi phạm bất kỳ tiêu chí nào tại Mục 3 (Fact-check) hoặc Mục 1 (Kỹ thuật méo hình/mất tiếng) $\to$ Trả về hàng đợi sửa kịch bản / render lại.
* **Người kiểm duyệt (QC Inspector):** ...................................
* **Ngày kiểm duyệt:** ...... / ...... / 2026
