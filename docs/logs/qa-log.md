# Q&A log

Ghi mọi câu hỏi nghiệp vụ hoặc kỹ thuật vào đây, không để trôi trong chat. BA điều phối việc trả lời.

- **Blocking**: chặn công việc, phải trả lời trước khi tiếp tục.
- **Trạng thái**: Mở / Đã trả lời / Chuyển thành ADR hoặc Decision.

| # | Ngày | Người hỏi | Câu hỏi | Liên quan (PRD §, module) | Blocking | Trả lời | Người trả lời | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-05 | | Ai approve PKB: merchant, admin, hay cả hai? | Module 1, PotatoMine725/AI-review-BE#15 | | | @khanhphi27 | Mở |
| 2 | 2026-10-05 | | Merchant pilot có cung cấp ảnh/tài liệu phần sau login không? | Module 1, PotatoMine725/AI-review-BE#15 | | | @khanhphi27 | Mở |
| 3 | 2026-10-05 | | Site của merchant có ngôn ngữ nào ngoài tiếng Anh? | Module 1, PotatoMine725/AI-review-BE#15 | | | @khanhphi27 | Mở |
| 4 | 2026-10-05 | @PotatoMine725 | Ai làm 1.4–1.6 (extraction, merge, enrichment)? Đặc tả M1 giao "AI dev 2", nhưng kế hoạch tuần 1 giao AI-2 làm Module 2, 4. Tạm thời AI-1 làm trong spike | Module 1, `plan/week-1.md`, PotatoMine725/AI-review-BE#14 | Có (trước 06/10) | | @khanhphi27 | Mở |
| 5 | 2026-10-05 | @PotatoMine725 | Phạm vi RAG của 1.8: dùng full-text search của Postgres trước, hay embedding + pgvector ngay? PKB 1 product chỉ vài KB, M2 có thể dùng nguyên PKB làm context | Module 1 (1.8), M2, M4 | | | BE + AI-1 | Mở |
| 6 | 2026-10-05 | @PotatoMine725 | NFR-02 (≤ $0.05/product) còn khả thi không? Gemini 2.5 Flash-Lite không mở cho dự án mới; Flash-Lite 3.x đắt hơn 2,5–4 lần. Spike #6 sẽ đo | Module 1 (NFR-02), ADR-002 | | | AI-1 | Mở |
| 7 | 2026-10-05 | @PotatoMine725 | Chọn 2 product nào cho spike #6? Lấy từ golden set, ưu tiên 1 site tĩnh + 1 site SPA | Module 1, spike #6 | Có (trước 07/10) | Tạm dùng Claude (`claude.com`, pricing nhiều plan) và Dreamina (`dreamina.capcut.com`, SPA). Lấy từ video tham khảo (`references/ref-videos-2026-10-06.md`). Đổi khi có golden set | @PotatoMine725 | Đã trả lời (tạm) |
| 8 | 2026-10-06 | @PotatoMine725 | MVP làm video và PKB bằng ngôn ngữ nào: tiếng Việt, tiếng Anh hay cả hai? Video tham khảo của tech lead đều tiếng Việt, PRD nhắm thị trường global | PRD §39, Module 1 (1.4), M2, PotatoMine725/AI-review-BE#15 | | | @khanhphi27 + tech lead | Mở |
