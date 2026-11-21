# Prompt: P1 — video demo thật cho PDFCraft (dùng cho báo cáo quản lý)

- **Repo / cwd:** `AI-review-BE`
- **Branch:** `spike/p1-demo-pdfcraft`, tạo từ `origin/spike/p1-render`, vì PR #77 chưa merge
- **PR:** draft vào `dev`, ghi rõ phụ thuộc #71, #73, #77
- **Thời hạn:** trước buổi báo cáo quản lý, khoảng 1–2 giờ làm việc
- **Mục tiêu:** có **1 video hoàn chỉnh về sản phẩm thật PDFCraft**, ghép từ các phần đã chạy thật. Phạm vi mở rộng: 3 video, mỗi video 1 tính năng và 1 preset.

---

Bạn là coding agent của repo `AI-review-BE`, chạy trên máy Windows. Làm việc bằng tiếng Việt. Người dùng là AI dev nền C#/.NET, mới với Python. Giải thích ngắn; comment code bằng tiếng Việt, ngắn.

## Bối cảnh
- Sản phẩm: **PDFCraft** (https://pdfcraft.devtoolcafe.com), bộ công cụ PDF chạy trong trình duyệt, mã nguồn mở `PDFCraftTool/pdfcraft`, AGPL-3.0. Đã đề xuất làm nguồn demo ở #67.
- Kết quả crawl đã có ở `D:\tmp\crawl-pdfcraft\`: `completed`, 30 trang. Nếu thư mục không còn thì crawl lại:
  ```
  cd services\worker
  uv run python -m worker.m1.crawl https://pdfcraft.devtoolcafe.com --out D:\tmp\crawl-pdfcraft
  ```
- **Tư liệu thật, do nhóm tự quay,** nằm ở `D:\Code\AI-Content-Review\_refs\assets\pdfcraft\`. Thư mục nằm ngoài repo, **không commit**.

  | File | Thời lượng | Nội dung |
  |---|---|---|
  | `pdfcraft-pagenum.mp4` | 15 s | Đánh số trang; giây 12–14 có thông báo "Applied Page Numbers" |
  | `pdfcraft-word-export.mp4` | 12 s | Xuất sang Word; khoảng giây 4–10 là đoạn chờ xử lý, nên tua nhanh hoặc cắt |
  | `pdfcraft-word-result.mp4` | 7 s | Mở file Word: giữ được ảnh bìa, biểu đồ và số trang |
  | `pdfcraft-merge.mp4` | 22 s | Ghép 2 PDF; giây 16 có thông báo "Applied", giây 18–20 cuộn tới trang 6/6 |

  File PDF dùng trong clip là dữ liệu giả "Acme Demo" (`samples/`).
- **Code đã có trên các branch chưa merge.** Chỉ chạy bằng CLI của từng branch qua worktree riêng, **không chép code giữa các branch**:
  - TTS: `origin/spike/p1-tts-vi` (#73), dùng VieNeu-TTS, sinh audio theo từng câu, có `normalize_vi`.
  - Cảnh AI: `origin/spike/p1-ai-scene` (#71), dùng Cloudflare `flux-1-schnell`. Key nằm trong `.env` của spike đó, có sẵn trên máy.
  - Renderer: `spikes/p1-render` ngay trên branch này (#77), dùng plan JSON và 3 preset.
- Gemini: key nằm ở `spikes/m1-crawl-extract/.env`.

## Nhiệm vụ

### 1. Fact có nguồn (trích từ crawl)
- Lấy khoảng 8–12 fact về PDFCraft từ markdown đã crawl, ưu tiên:
  - miễn phí;
  - chạy trong trình duyệt, file không tải lên server (nếu trang có ghi);
  - số lượng công cụ;
  - các tính năng đánh số trang, chuyển PDF sang Word, ghép PDF.
- Cách lấy:
  - Ưu tiên chạy `spikes/m1-crawl-extract/extract.py` trên dữ liệu crawl. Nếu định dạng output của crawler worker khác với spike thì viết 1 script chuyển đổi nhỏ.
  - Nếu không chạy được thì trích tay.
- Mỗi fact phải có `source_url` và `evidence` (trích nguyên văn, ≤ 200 ký tự).
- Ghi vào `spikes/p1-demo-pdfcraft/facts.json`.

### 2. Kịch bản tiếng Việt
- **Viết tay**, mỗi video dài 18–25 s, theo cấu trúc Hook → Vấn đề → Demo → Kết quả → CTA.
- Mỗi câu nhắc tới tính năng phải có `fact_ref` trỏ vào `facts.json`.
- **Không nói điều gì clip hay fact không chứng minh được.** Ví dụ:
  - được nói "giữ được hình ảnh khi chuyển sang Word" (clip cho thấy);
  - **không** nói "giữ nguyên định dạng", vì phần nền màu của tiêu đề bị mất;
  - không đưa ra số liệu nếu trang không có.
- CTA: chỉ ghi tên trang "pdfcraft.devtoolcafe.com", không có link theo dõi.
- Ghi rõ trong README: *"Kịch bản viết tay dựa trên fact đã crawl; bước AI tự viết kịch bản chưa làm."*
- File: `spikes/p1-demo-pdfcraft/script-*.json`, theo cấu trúc plan của renderer.

### 3. Giọng đọc
- Dùng VieNeu-TTS, giọng chọn theo bộ nghe thử, sinh theo từng câu.
- Thêm cách đọc tên riêng vào bảng phát âm, chỉ trong spike này: "PDFCraft", "PDF", "Word".
- Tự nghe lại toàn bộ audio. Câu nào đọc sai thì sửa văn bản hoặc bảng phát âm rồi sinh lại.

### 4. Cảnh AI (1 cảnh mỗi video)
- 1 ảnh minh hoạ qua Cloudflare, ví dụ "giấy tờ lộn xộn được sắp xếp gọn gàng".
- Prompt tiếng Anh. Không người, không logo, không chữ.
- Ghi bằng chứng lần sinh: request id, model, neuron.
- Ảnh này dùng ở đoạn Hook hoặc Vấn đề, **không** dùng để thay cảnh thao tác app.

### 5. Dựng video
- Plan dùng clip thật cho đoạn Demo và Kết quả. Cắt đúng đoạn, tua nhanh hoặc bỏ đoạn chờ. Cảnh AI dùng cho Hook.
- Thêm `text_card` cho CTA.
- **Video chính:** tính năng đánh số trang + xuất Word, preset "điện ảnh tối giản", xuất cả 9:16 và 16:9.
- **Nếu còn thời gian:** thêm 2 video:
  - ghép PDF, preset "hoạt hình đồ họa";
  - chuyển sang Word, preset "cổ điển".
- Output ghi ra `D:\Code\AI-Content-Review\demo-out\`, **không commit video**.
- Kiểm tra bằng `ffprobe`. Chụp 1 khung hình mỗi video (PNG nhỏ) để đưa vào README.

## Phạm vi
- **Làm:** `spikes/p1-demo-pdfcraft/**` (facts, script, plan, README, script chuyển đổi nếu cần) và file prompt này.
- **Không làm:** sửa code của #71, #73, #77 (gặp lỗi thì ghi lại, sửa ở PR tương ứng); `services/worker`; DB, API, FE.
- **Không commit:** clip, audio, ảnh AI, video và key.

## Tiêu chí hoàn thành
- [ ] Có ít nhất 1 video PDFCraft (9:16 và 16:9) dài 18–25 s, gồm: giọng VieNeu, phụ đề tiếng Việt đúng dấu, clip thao tác thật, 1 cảnh AI thật.
- [ ] Mọi câu nói về tính năng đều có `fact_ref` và evidence.
- [ ] README có:
  - lệnh chạy lại;
  - nguồn tư liệu (AGPL-3.0, clip do nhóm tự quay, file PDF giả);
  - bằng chứng lần sinh ảnh AI;
  - danh sách phần chạy thật và phần làm tay.
- [ ] Không có tư liệu bên thứ ba ngoài giao diện PDFCraft.

## Khi xong
Commit kèm file prompt này, push, mở **draft PR** vào `dev`. Body PR có:
- `Refs #67`;
- phụ thuộc #71, #73, #77;
- khung hình của từng video;
- `cc @VV6505`.

Trả về: đường dẫn video trong `demo-out`, link PR, và những gì còn làm tay.
