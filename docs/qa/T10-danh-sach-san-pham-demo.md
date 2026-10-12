# DANH SÁCH 10 SẢN PHẨM GOLDEN SET (TASK T10 — v2.2)

- **Dự án:** AI Review Content Factory & Affiliate Network
- **Mã công việc:** `T10` (Sprint 0 / Sprint 1)
- **Phiên bản:** 2.2 (cập nhật 08/10/2026 — Chốt đổi sản phẩm chính sang **ElevenLabs** do Gamma bị Cloudflare WAF chặn crawler; Opus Clip làm dự phòng)
- **Đối tượng thụ hưởng:** AI-1 (Crawl), AI-2 (Script), Video-1 (Demo), QA (Golden Facts)

---

## 1. BẢNG TỔNG HỢP 10 SẢN PHẨM (GOLDEN SET)

| STT | Tên sản phẩm | Nhóm | Website | Trang Pricing | Link Affiliate Program | Ghi chú & Kết quả Crawl Check |
|-----|---|---|---|---|---|---|
| 1 | **ElevenLabs** ⭐ | Productivity | [elevenlabs.io](https://elevenlabs.io) | [/pricing](https://elevenlabs.io/pricing) | [Affiliate (22–30%)](https://elevenlabs.io/affiliates) | **SẢN PHẨM CHÍNH SPRINT 1** (thay Gamma). Test crawl 08/10: `robots.txt` (200), `/pricing` (200) ✅ PASS, không bị chặn. Golden Facts ✅ DONE |
| 2 | **Gamma App** ⚠️ | Productivity | [gamma.app](https://gamma.app) | [/pricing](https://gamma.app/pricing) | [PartnerStack Affiliate](https://gamma.partnerstack.com) | ⚠️ **BỊ CLOUDFLARE WAF CHẶN CRAWLER** — Chuyển thành case test đối soát thủ công. Golden Facts ✅ DONE |
| 3 | **Otter.ai** | Productivity | [otter.ai](https://otter.ai) | [/pricing](https://otter.ai/pricing) | [Impact Affiliate (15–60%)](https://app.impact.com) | Golden Facts ✅ DONE ⚠️ Fix: affiliate qua Impact, KHÔNG phải ShareASale |
| 4 | **Opus Clip** 🛡️ | Video | [opus.pro](https://www.opus.pro) | [/pricing](https://www.opus.pro/pricing) | [Affiliate (20%)](https://www.opus.pro/affiliate) | **SẢN PHẨM DỰ PHÒNG** (Nhóm Video). Test crawl 08/10: `robots.txt` (200), `/pricing` (200) ✅ PASS, không bị chặn. Golden Facts ✅ DONE |
| 5 | **Runway** | Video | [runway.com](https://runway.com) | [/pricing](https://runway.com/pricing) | [Affiliate Program](https://runway.com/affiliate-program) | Golden Facts ✅ DONE ⚠️ Fix: domain đổi thành runway.com, link affiliate mới |
| 6 | **Synthesia** | Video | [synthesia.io](https://synthesia.io) | [/pricing](https://synthesia.io/pricing) | [Affiliate 25% / 12 tháng](https://www.synthesia.io/affiliates) | Golden Facts ✅ DONE ⚠️ Fix: 25% recurring 12 tháng, qua Rewardful |
| 7 | **GitHub Copilot** | Coding | [github.com/copilot](https://github.com/features/copilot) | [github.com/features/copilot](https://github.com/features/copilot) | ❌ **Không tìm thấy affiliate công khai** — github.com/affiliates không tồn tại | Golden Facts ✅ DONE ⚠️ Không đạt tiêu chí affiliate — giữ làm dự phòng, cân nhắc Tabnine |
| 8 | **Cursor** | Coding | [cursor.com](https://www.cursor.com) | [/pricing](https://www.cursor.com/pricing) | ❌ Chưa có affiliate chính thức | Golden Facts ✅ DONE ⚠️ Không đạt tiêu chí affiliate — giữ làm sản phẩm dự phòng |
| 9 | **Windsurf** (ex-Codeium) | Coding | [windsurf.com](https://windsurf.com) | [/pricing](https://windsurf.com/pricing) | ⚠️ Cần verify — trang windsurf.com chính thức, affiliate cần confirm | Golden Facts ✅ DONE ⚠️ Affiliate chưa xác nhận sau khi đổi tên từ Codeium |
| 10 | **Notion AI** | Productivity | [notion.so](https://www.notion.so) | [/pricing](https://notion.so/pricing) | [Affiliate (50%)](https://www.notion.so/affiliate) | Golden Facts ✅ DONE ⚠️ Fix: AI không còn bán add-on $8 riêng — bundle trong gói Business $20/member |

---

## 2. KẾT QUẢ KIỂM TRA SƠ BỘ TRÌNH THU THẬP THÔNG TIN (08/10/2026)

| Ứng viên kiểm tra | `robots.txt` | `/pricing` | Kết luận Crawler | Quyết định Sprint 1 |
|---|:---:|:---:|---|---|
| **ElevenLabs** | `200` | `200` | ✅ Không bị chặn, phản hồi tốt | **CHỌN LÀM SẢN PHẨM CHÍNH** (Cùng nhóm Productivity, Golden Facts hoàn tất) |
| **Opus Clip** | `200` | `200` | ✅ Không bị chặn, phản hồi tốt | **PHƯƠNG ÁN DỰ PHÒNG** (Nhóm Video AI) |
| **Catwalk / Kling** | `308` | `308` | ⏳ Chuyển hướng redirect | Chưa có kết luận, cần theo redirect |

> **Lưu ý kiểm thử tiếp theo:** Lần thu thập dữ liệu đầy đủ (< 30 trang) sẽ xác nhận `robots.txt` được phép từng trang và trang có giá hiển thị không bị chặn/disallow. Golden Facts được sync vào repo PR `qa-log #11` để đối chiếu giá M1 (AC-04).

---

## 3. PHÂN LOẠI THEO NHÓM

### 🎬 Nhóm 1 — VIDEO AI (3 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 4 | Opus Clip 🛡️ | Tự động cắt video dài → clip TikTok/Reels | **Sản phẩm dự phòng Sprint 1**; trực tiếp phục vụ pipeline video ngắn; crawl mượt (200) |
| 5 | Runway | Gen video từ text/ảnh, hiệu ứng AI | Thương hiệu mạnh, viral cao, demo ảo hóa video cực ấn tượng |
| 6 | Synthesia | Tạo video avatar nói chuyện từ text | Demo không cần quay người, ứng dụng cao cho Creator không lộ mặt |

### 📋 Nhóm 2 — PRODUCTIVITY AI (4 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 1 | ElevenLabs ⭐ | AI giọng đọc text-to-speech / Voice AI | **Sản phẩm chính Sprint 1**; crawler pass 200; Affiliate 22–30%; Golden Facts hoàn chỉnh |
| 2 | Gamma App ⚠️ | AI tạo slide/thuyết trình | Bị Cloudflare WAF chặn crawler tự động; giữ làm testcase so khớp thủ công |
| 3 | Otter.ai | AI ghi chép cuộc họp tự động | Use-case rõ ràng, pain point được nhắc trong PRD, affiliate qua Impact |
| 10 | Notion AI | AI viết nội dung trong workspace | Affiliate rate cực cao (50%), base user khổng lồ |

### 💻 Nhóm 3 — CODING AI (3 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 7 | GitHub Copilot | AI gợi ý code trong IDE | ⚠️ Không có affiliate công khai — cần thay hoặc tìm chương trình khác |
| 8 | Cursor | AI code editor toàn phần | Viral cực mạnh trong cộng đồng dev 2026, chuyển đổi cao |
| 9 | Windsurf (ex-Codeium) | AI code editor từ nhóm Codeium | ⚠️ Đã đổi tên 04/2025 — verify lại URL chính thức và affiliate trước khi crawl |

---

## 4. DANH SÁCH FILE GOLDEN FACTS (FULL 10 SẢN PHẨM)

| Thứ tự | Sản phẩm | File | Vai trò Sprint 1 | Trạng thái |
|---|---|---|---|---|
| 1 | **ElevenLabs** | `T12b-golden-facts-elevenlabs.md` | ⭐ **SẢN PHẨM CHÍNH** | ✅ DONE (Đã đối soát giá) |
| 2 | **Opus Clip** | `T12c-golden-facts-opus-clip.md` | 🛡️ **DỰ PHÒNG** | ✅ DONE |
| 3 | **Gamma App** | `T12-golden-facts-san-pham-demo.md` | ⚠️ Testcase WAF | ✅ DONE |
| 4 | **Runway** | `T12d-golden-facts-runway.md` | Nhóm Video | ✅ DONE |
| 5 | **Synthesia** | `T12g-golden-facts-synthesia.md` | Nhóm Video | ✅ DONE |
| 6 | **Otter.ai** | `T12f-golden-facts-otter-ai.md` | Nhóm Productivity | ✅ DONE |
| 7 | **Notion AI** | `T12j-golden-facts-notion-ai.md` | Nhóm Productivity | ✅ DONE |
| 8 | **GitHub Copilot** | `T12e-golden-facts-github-copilot.md` | Nhóm Coding | ✅ DONE (Không affiliate) |
| 9 | **Cursor** | `T12h-golden-facts-cursor.md` | Nhóm Coding | ✅ DONE (Không affiliate) |
| 10 | **Windsurf** | `T12i-golden-facts-windsurf.md` | Nhóm Coding | ✅ DONE (Affiliate cần verify) |

---

## 5. KẾT LUẬN & BÀN GIAO

- **Sản phẩm chính thức cho Sprint 1:** **ElevenLabs** (`https://elevenlabs.io`) — Thay thế Gamma App.
- **Sản phẩm dự phòng:** **Opus Clip** (`https://www.opus.pro`).
- **Đồng bộ mã nguồn:** Toàn bộ 10 file Golden Facts sẵn sàng nộp vào repo PR [#11 (qa-log)](https://github.com/PotatoMine725/AI-review-BE/pull/11) để đối chiếu giá M1 (AC-04).
