# Video tham khảo từ tech lead — phân tích format (20 giây đầu)

- **Ngày:** 2026-10-06 · **Người phân tích:** @PotatoMine725 (coordinator hỗ trợ)
- **Nguồn:** 2 video TikTok do tech lead gửi. File gốc **không** lưu trong repo (bản quyền, hình người thật).
- **Trạng thái:** Tham khảo. Không phải nguồn sự thật; đề xuất thay đổi đi qua issue #5 và `logs/qa-log.md`.
- **Phạm vi:** chỉ 20 giây đầu, xem khung hình mỗi 1 giây. Chưa chép lời thoại đầy đủ.

## Thông số

| | Video 1 | Video 2 |
|---|---|---|
| Độ phân giải | 720×1280 (9:16) | 1080×1920 (9:16) |
| Thời lượng | 215 giây | 79 giây |
| Product | Claude (dùng để tự động edit video) | Dreamina Seedance 2.5 (model tạo video) |
| Ngôn ngữ | Tiếng Việt | Tiếng Việt |

GHI CHÚ: Cả 2 video dài hơn giới hạn ≤ 60 giây của PRD và checklist QC.

## Format

### Video 1 — Talking head
- Bố cục: người nói giữa khung, nền lưới đen–vàng (ghép nền), logo product nhỏ góc trên phải ở giây 0.
- Hook (0–3 giây): câu hỏi cộng đồng — "Có rất nhiều anh em hỏi mình cách sử dụng Claude để tự động edit video…".
- 10–20 giây: đặt kỳ vọng — "Claude không phải là một trình editor…".
- Caption: 1 dòng, 3–4 từ, hiện theo từng từ, từ khóa tô vàng, ở khoảng 37% chiều cao tính từ dưới.
- 20 giây đầu không có demo product.

### Video 2 — Hybrid (PRD §15.4)
- 0–10 giây, 3 tầng:
  1. Tiêu đề product + 3 ảnh đầu vào (tham chiếu).
  2. Trình phát video kết quả, có thanh tiến độ.
  3. Người nói trong khung bo góc.
- Hook: cho xem kết quả trước, giải thích sau.
- 10–20 giây: người nói toàn màn hình → thẻ thương hiệu ("Dreamina AI WEB") → B-roll kết quả toàn màn hình → người nói.
- Caption: chữ nghiêng trắng, theo cụm từ, giữa màn hình.

## So sánh nhanh (cho M2 hook/script, M3 render)

| | Hook | Bố cục | Caption | Bằng chứng |
|---|---|---|---|---|
| Video 1 | Câu hỏi cộng đồng | Người nói + logo | Theo từ, tô màu từ khóa | Chưa có trong 20 giây đầu |
| Video 2 | Cho xem kết quả | Tiêu đề + đầu vào + kết quả + người nói | Theo cụm | Kết quả product + cặp đầu vào → đầu ra |

## Ảnh hưởng tới Module 1 (đề xuất cho đặc tả v0.2, issue #5)

1. **Asset `media_sample`:** với product tạo ảnh/video, bằng chứng chính là kết quả product tạo ra (gallery/showcase công khai), không chỉ screenshot website. Ưu tiên: Could.
2. **`identity.version` / `models[]`:** phiên bản model là fact quan trọng ("Seedance 2.5"); cần `source_id` như fact khác.
3. **Logo chất lượng cao:** video dùng logo + wordmark làm thẻ thương hiệu riêng; 1.3 nên ưu tiên SVG.
4. **Ngôn ngữ video:** cả 2 video tham khảo là tiếng Việt, PRD nhắm global → qa-log #8.
