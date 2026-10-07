# Golden set T10 v2.0 (bản lưu tham khảo)

- **Nguồn:** file `T10-danh-sach-san-pham-demo.md` do team lead gửi, người lập: Phú (Test Lead), cập nhật 07/10/2026.
- **Lưu vào repo:** 07/10/2026 bởi @PotatoMine725. **Tài liệu tham khảo, không phải nguồn sự thật**; thay đổi đi qua `logs/qa-log.md` / `logs/decision-log.md`.
- **Ghi chú kiểm chứng của AI-1** (07/10/2026, chưa phải kết luận, cần Test Lead xác nhận):
  - Codeium đã đổi tên thành **Windsurf** (04/2025); URL `codeium.com` có thể chuyển hướng.
  - GitHub: chưa tìm thấy chương trình affiliate chính thức cho Copilot; `github.com/affiliates` cần kiểm tra.
  - Gamma: ngoài trang Referral (tặng credit) còn có affiliate program qua PartnerStack (help.gamma.app).
  - Runway: trang affiliate hiện ở `runway.com/affiliate-program` (domain `runway.com`).
  - File Golden Facts (`T12*.md`, thư mục `QA/QC/`) chưa có trong repo.

---

# DANH SÁCH 10 SẢN PHẨM GOLDEN SET (TASK T10 — v2.0)

- **Dự án:** AI Review Content Factory & Affiliate Network
- **Mã công việc:** `T10` (Sprint 0)
- **Phiên bản:** 2.0 (cập nhật 07/10/2026 — bổ sung đủ 10 sản phẩm, 3 nhóm)
- **Người thực hiện:** Phú (Test Lead)
- **Đối tượng thụ hưởng:** AI-1 (Crawl), AI-2 (Script), Video-1 (Demo), QA (Golden Facts)

---

## 1. BẢNG TỔNG HỢP 10 SẢN PHẨM (GOLDEN SET)

| STT | Tên sản phẩm | Nhóm | Website | Trang Pricing | Link Affiliate Program | Ghi chú |
|-----|---|---|---|---|---|---|
| 1 | **Gamma App** ⭐ | Productivity | [gamma.app](https://gamma.app) | [/pricing](https://gamma.app/pricing) | [Referral Program](https://gamma.app/referral) | **SẢN PHẨM CHÍNH** — Golden Facts ✅ DONE |
| 2 | **ElevenLabs** | Productivity | [elevenlabs.io](https://elevenlabs.io) | [/pricing](https://elevenlabs.io/pricing) | [Affiliate (22–30%)](https://elevenlabs.io/affiliates) | Golden Facts ✅ DONE |
| 3 | **Otter.ai** | Productivity | [otter.ai](https://otter.ai) | [/pricing](https://otter.ai/pricing) | [ShareASale Program](https://www.shareasale.com/info/otter) | Golden Facts 🔲 TODO |
| 4 | **Opus Clip** | Video | [opus.pro](https://www.opus.pro) | [/pricing](https://www.opus.pro/pricing) | [Affiliate (20%)](https://www.opus.pro/affiliate) | Golden Facts ✅ DONE |
| 5 | **Runway** | Video | [runwayml.com](https://runwayml.com) | [/pricing](https://runwayml.com/pricing) | [Affiliate Program](https://runwayml.com/affiliate) | Golden Facts ✅ DONE |
| 6 | **Synthesia** | Video | [synthesia.io](https://www.synthesia.io) | [/pricing](https://www.synthesia.io/pricing) | [Partner Program](https://www.synthesia.io/partners) | Dự phòng nhóm Video |
| 7 | **GitHub Copilot** | Coding | [github.com/copilot](https://github.com/features/copilot) | [github.com/features/copilot](https://github.com/features/copilot) | [GitHub Affiliate](https://github.com/affiliates) | Golden Facts ✅ DONE |
| 8 | **Cursor** | Coding | [cursor.com](https://www.cursor.com) | [/pricing](https://www.cursor.com/pricing) | Chưa có affiliate chính thức — kiểm tra lại | Dự phòng nhóm Coding |
| 9 | **Codeium** | Coding | [codeium.com](https://codeium.com) | [/pricing](https://codeium.com/pricing) | [Affiliate via Rewardful](https://codeium.com/affiliate) | Dự phòng nhóm Coding |
| 10 | **Notion AI** | Productivity | [notion.so](https://www.notion.so) | [/pricing](https://www.notion.so/pricing) | [Affiliate (50%)](https://www.notion.so/affiliate) | Dự phòng nhóm Productivity |

---

## 2. PHÂN LOẠI THEO NHÓM

### 🎬 Nhóm 1 — VIDEO AI (3 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 4 | Opus Clip | Tự động cắt video dài → clip TikTok/Reels | Trực tiếp phục vụ pipeline video ngắn của hệ thống; demo bấm 1 nút ra clip |
| 5 | Runway | Gen video từ text/ảnh, hiệu ứng AI | Thương hiệu mạnh, viral cao, demo ảo hóa video cực ấn tượng |
| 6 | Synthesia | Tạo video avatar nói chuyện từ text | Demo không cần quay người, ứng dụng cao cho Creator không lộ mặt |

### 📋 Nhóm 2 — PRODUCTIVITY AI (4 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 1 | Gamma App ⭐ | AI tạo slide/thuyết trình | **Sản phẩm chính**, visual proof rõ ràng trong 15 giây |
| 2 | ElevenLabs | AI giọng đọc text-to-speech | Affiliate rate cao (30%), nhận diện thương hiệu toàn cầu |
| 3 | Otter.ai | AI ghi chép cuộc họp tự động | Use-case rõ ràng, pain point được nhắc trong PRD |
| 10 | Notion AI | AI viết nội dung trong workspace | Affiliate rate cực cao (50%), base user khổng lồ |

### 💻 Nhóm 3 — CODING AI (3 sản phẩm)

| STT | Sản phẩm | Use-case chính | Vì sao chọn |
|---|---|---|---|
| 7 | GitHub Copilot | AI gợi ý code trong IDE | Thương hiệu số 1, owned by Microsoft, base developer rộng |
| 8 | Cursor | AI code editor toàn phần | Viral cực mạnh trong cộng đồng dev 2026, chuyển đổi cao |
| 9 | Codeium | AI code completion miễn phí | Gói Free mạnh, dễ demo, tệp sinh viên/junior dev lớn |

---

## 3. ƯU TIÊN LÀM GOLDEN FACTS (TOP 5)

| Thứ tự | Sản phẩm | File | Deadline | Trạng thái |
|---|---|---|---|---|
| 1 | Gamma App | `T12-golden-facts-san-pham-demo.md` | 05/10/2026 | ✅ DONE |
| 2 | ElevenLabs | `T12b-golden-facts-elevenlabs.md` | 07/10/2026 | ✅ DONE |
| 3 | Opus Clip | `T12c-golden-facts-opus-clip.md` | 07/10/2026 | ✅ DONE |
| 4 | Runway | `T12d-golden-facts-runway.md` | 07/10/2026 | ✅ DONE |
| 5 | GitHub Copilot | `T12e-golden-facts-github-copilot.md` | 09/10/2026 | ✅ DONE |

---

## 4. KẾT LUẬN & BÀN GIAO

- **Sản phẩm chính thức cho Sprint 1:** **Gamma App** (`https://gamma.app`)
- **Bộ golden set đầy đủ:** 10 sản phẩm, 3 nhóm, đã xác minh affiliate program
- **Bàn giao Nhóm AI-1:** Danh sách URL crawl ưu tiên theo thứ tự cột STT
- **Bàn giao Nhóm QA:** 5 file Golden Facts trong thư mục `QA/QC/`
