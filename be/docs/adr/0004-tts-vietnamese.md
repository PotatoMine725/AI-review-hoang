# ADR-0004: TTS tiếng Việt cho video P1

- **Trạng thái:** Đề xuất (**Proposed**). QA (@VD-PHU) đã chấm bộ nghe v2 (21/10) và lead đã xác nhận hướng cho bước tích hợp (25/10); license/nguồn giọng, review mã remote và tích hợp worker vẫn chưa xác minh nên chưa chốt. Gemini là khảo sát thêm (chưa gọi thật), không chặn P1
- **Ngày:** 2026-10-14 (cập nhật 2026-10-19 theo review của lead ngày 18/10; 2026-10-28 theo QA 21/10 và lead 25/10)
- **Người đề xuất:** @PotatoMine725 (spike P1-02b)
- **Người quyết định:** team lead @VV6505 (kỹ thuật); license/dữ liệu do chủ dự án quyết
- **Liên quan:** issue #67 · [spike](../../spikes/p1-tts-vi/README.md) · [ADR-0002](0002-llm-provider.md) (cách ghi quota, điều khoản dữ liệu) · [ADR-0005](0005-repo-structure-and-extensibility.md) (provider sau adapter) · `docs/specs/contracts/cost-breakdown.v1.schema.json` · ADR-0003 (renderer, số dành riêng)

> Tra nguồn ngày 14/10/2026. Số đo trên máy dev (i7-12700H, RTX 4050 6 GB), **chưa đo trên máy worker thật**. RTF/RAM chỉ nói về tốc độ và tài nguyên, **không suy ra chất lượng**. Hai phần khác nhau:
> - **(a) Chất lượng giọng: đã có kết quả QA** (@VD-PHU, bộ nghe mù v2, 65 clip, thang 1–5, comment #73 ngày 21/10): VieNeu tự nhiên 4,00–4,23, đúng dấu 4,77–4,92, đọc số 4,90, tên riêng 3,50–3,75 (trước khi chỉnh bảng phát âm); Piper `vais1000` tự nhiên 2,85, Piper `25hours_single` 1,38. Lead (25/10): VieNeu đạt cho P1, Mai Anh ONNX CPU là phương án đã có kết quả cho máy không GPU; Piper không ưu tiên cho luồng chính, giữ số đo làm tài liệu so sánh. **Kết quả này xác nhận hướng cho bước tích hợp, chưa thay thế kiểm tra audio và video hoàn chỉnh trên sản phẩm thật.**
> - **(b) Vẫn chưa xác minh:** nguồn gốc/license giọng và dữ liệu huấn luyện, review `trust_remote_code` bởi BE, revision codec ONNX, tích hợp worker, đo trên máy worker thật.

## Bối cảnh
Video tiếng Việt 15–25 s (khoảng 50–70 từ voice) cần TTS trong worker Windows, sau **TTS adapter**. Ràng buộc:
- Không tự bật dịch vụ trả phí; chỉ gọi thật trong quota/free tier đã xác minh (có ảnh quota). Không gửi upload của merchant hay dữ liệu nhạy cảm lên free tier.
- Tiêu chí chính: giọng tiếng Việt rõ, **đọc đúng tên sản phẩm và số liệu** (sai giá là lỗi nặng nhất, như ADR-0002), căn phụ đề được.
- TTS có thể local hoặc cloud; chưa chốt local làm dependency bắt buộc trước khi đo trên máy worker thật (#67).
- Usage ghi theo đơn vị của provider (ký tự, giây, token âm thanh), không quy đổi sang token LLM. Pilot hiện đo chi phí từng lời gọi bằng USD theo `cost-breakdown.v1` (decision-log #22). **Cấu trúc ghi usage thống nhất ở #74**, ADR này không đề xuất schema.

Sự kiện về Gemini TTS lấy từ HTML gốc của `ai.google.dev` (tải 14/10/2026): model ID `gemini-3.8-flash-tts` / `gemini-3.8-flash-lite-tts`; WAV 24 kHz; tiếng Việt có hỗ trợ; trang giá ghi free tier "Free of charge" và **"Used to improve our products: Yes"** (free) / "No" (trả phí); khối TTS **không ghi RPM/RPD** và trang ghi "Rate limits are subject to change", nên quota thật phải lấy từ ảnh AI Studio.

## Các lựa chọn (đã chạy trong spike)
| Lựa chọn | Ưu | Nhược | Chi phí / License |
|---|---|---|---|
| A. **VieNeu-TTS v3 Turbo** (local, SDK `vieneu` 3.8.3; weight `@61b85e3d`, codec `@6aa02b01`) | Model tiếng Việt (theo model card); 25 giọng có sẵn nam/nữ Bắc/Trung/Nam; tự xử lý số qua `sea-g2p`; chạy offline (đã thử `HF_HUB_OFFLINE=1`); tốc độ GPU RTF 0,13, CPU ONNX RTF 0,83 (máy dev); QA: giọng đạt cho P1 (số, ngày, giá đọc đúng ~5/5) | RAM ~2,4 GB; CPU PyTorch chậm (RTF 2,0); không tham số tốc độ; lấy mẫu ngẫu nhiên (mỗi lần khác); backend PyTorch tải **và chạy mã** từ HF (`trust_remote_code`, 2 file `.py` đã ghim sha256; backend ONNX không có); nguồn gốc dữ liệu huấn luyện/giọng mẫu **chưa xác minh**; tên riêng tiếng Anh là điểm yếu duy nhất theo QA (3,50–3,75), và lỗi nằm ở bảng phát âm chứ không ở model | 0. Code Apache-2.0; weight `pnnbao-ump/VieNeu-TTS-v3-Turbo` Apache-2.0; tokenizer MOSS-Nano Apache-2.0 |
| B. **Gemini TTS** (`gemini-3.8-flash-tts`, `-flash-lite-tts`) | 30 giọng + thư viện giọng; hỗ trợ tiếng Việt; không cần GPU/RAM; có thể điều khiển phong cách bằng prompt | Cần mạng; **free tier dùng nội dung cải thiện sản phẩm**; quota chưa biết (trang giá không ghi); không timestamp; giá trả phí tăng gấp đôi từ 01/01/2027 | Free tier "Free of charge"; trả phí audio $9 hoặc $6/1M token đến 31/12/2026. **Khảo sát thêm, không chặn P1; chưa gọi thật (chưa có ảnh quota)** |
| C. **Piper `vi_VN`** (local) | Rất nhanh và nhẹ (CPU RTF 0,04–0,05, RAM ~300 MB); offline; mô hình nhỏ ~60 MB; không remote code | **Engine GPL-3.0**; mỗi giọng 1 người nói, license dataset khác nhau (`vais1000` CC BY 4.0; `25hours_single` "Unknown" = chưa xác minh; `vivos` NC); QA: sai dấu, đọc sai giá/đơn vị (tự nhiên 2,85 / 1,38) | 0. Giọng dùng được: `vais1000-medium` (CC BY 4.0, cần ghi nguồn) |
| D. F5-TTS tiếng Việt / MMS-TTS | — | Weight **non-commercial** (CC-BY-NC-SA 4.0 / CC-BY-NC 4.0); chỉ làm nếu A–C trượt | Không chạy, chỉ gắn cờ |
| Loại | viXTTS/XTTS (CPML non-commercial), `edge-tts` (endpoint không chính thức), Google Cloud/Azure TTS (cần billing) | | |

## Quyết định (đề xuất)
**Chính (đề xuất): A — VieNeu-TTS v3 Turbo, chạy local**, vì P1 cần một TTS tiếng Việt chạy được để ghép luồng và A đã chạy offline với adapter + CLI theo đoạn. QA (21/10) và lead (25/10) xác nhận hướng này cho bước tích hợp; đây **chưa phải nghiệm thu audio và video hoàn chỉnh**. **Dự phòng (đề xuất): B — Gemini TTS**, chỉ là khảo sát thêm: cần ảnh quota đủ và chủ dự án chấp nhận điều khoản dữ liệu free tier. Piper (C) không đề xuất làm chính hay dự phòng: kết quả nghe không đạt (xem trên), lead (25/10) không ưu tiên cho luồng chính và giữ số đo làm tài liệu so sánh; thêm cờ GPL của engine. Giữ làm phương án offline nhẹ cho CI/dev nếu cần.

Giọng cụ thể (hiện dùng `Mai Anh` cho demo) **chưa được chọn**: nguồn gốc/license 25 giọng VieNeu chưa xác minh.

Điều kiện để xác nhận (kiểm bằng điểm nghe và số đo; ngưỡng là đề xuất, lead chỉnh):
1. **Điểm nghe**: trung bình ≥ 4,0 cho "tự nhiên" và ≥ 4,0 cho "đọc số"; không có clip nào bị đánh dấu "SAI GIÁ" ở bộ câu giá/ngày; "đọc tên riêng" ≥ 3,5 sau khi chỉnh bảng phát âm. Nếu A không đạt mà B đạt → đổi vai (B chính, A dự phòng).
   *Hiện trạng (QA 21/10, 1 người chấm, A = VieNeu):* tự nhiên 4,00–4,23 và đọc số 4,90 trên cả 3 cấu hình VieNeu; QA ghi VieNeu đọc đúng số, ngày, giá, đơn vị (~5/5, cả bản raw và bản chuẩn hoá); tên riêng 3,50–3,75 **trước khi** chỉnh bảng phát âm. Bảng phát âm đã tách theo provider (VieNeu để nguyên `ElevenLabs`, `&` → "en") nhưng **chưa nghe lại** toàn bộ, và `PDFCraft` / `Word` / `PDF` / `Starter` đang chờ nghe đối chiếu; vì vậy ngưỡng "đọc tên riêng sau khi chỉnh" chưa kiểm xong.
2. **Hiệu năng trên máy worker thật**: RTF ≤ 1 cho 1 video (≤ 25 s audio, gồm cả khởi động model); nếu máy worker không có GPU, A chạy bằng backend ONNX (RTF 0,89 trên máy dev: sát ngưỡng, cần đo lại) và B trở nên hấp dẫn hơn.
3. **License/dữ liệu** (cần chủ dự án quyết; đều **chưa xác minh**): nguồn gốc dữ liệu huấn luyện và 25 giọng mẫu của A; BE review 2 file mã remote của `MOSS-Audio-Tokenizer-Nano` @ `6aa02b01…` (đã ghim revision + sha256 trong `spikes/p1-tts-vi/vieneu/pins.py`; chi tiết ở README spike, mục `trust_remote_code`) trước khi đưa backend PyTorch vào worker (backend ONNX không chạy mã remote); với B, văn bản kịch bản gửi lên free tier có bị xem là dữ liệu merchant không.
4. **Phụ đề**: mức câu. Worker sinh audio từng câu (`synthesize_script`), cộng dồn độ dài và khoảng nghỉ để có mốc `start/end` từng câu. Cả 3 provider đều không có timestamp theo từ, nên không thêm thư viện alignment.

Đặt tên và cấu hình: chọn provider/giọng bằng config (ví dụ `TTS_PROVIDER=vieneu`, `TTS_VOICE=Mai Anh`), theo ADR-0005. Văn bản qua `normalize_vi` trước khi vào provider; bảng phát âm tên tiếng Anh là dữ liệu chỉnh được, **tách theo provider** (Piper cần phiên âm, VieNeu giữ nguyên tên và chỉ đổi ký hiệu như `&` → "en", số, đơn vị), không nằm trong code provider. Đã nghe kiểm một phần (QA 21/10); phần còn lại là đoán ban đầu.

**Xem lại khi:** điểm nghe không đạt ngưỡng; máy worker không đủ RAM/GPU; quota Gemini không đủ cho số video dự kiến; Google đổi giá/điều khoản; phát hiện vấn đề license với dữ liệu hoặc giọng của VieNeu; cần giọng riêng của merchant (clone, ngoài phạm vi MVP).

## Hệ quả
- **Dễ hơn:** audio không tốn tiền ở cả 2 hướng trong phạm vi demo; `FakeTTS` giúp CI không phụ thuộc model; phụ đề mức câu không cần thư viện thêm.
- **Khó hơn / nợ kỹ thuật:**
  - Worker local cần ~2,3 GB RAM + (tuỳ chọn) GPU, thêm bước tải model lần đầu và ghim phiên bản; torch CUDA ~3 GB đĩa nếu dùng backend PyTorch.
  - Interface adapter mới rút ra từ spike (3 provider), cần rà lại khi viết vào `services/worker` (ADR-0005 nguyên tắc 3).
  - **Usage của TTS** (ký tự/giây/token) chưa có chỗ ghi trong `cost-breakdown.v1` hiện tại: **theo #74**. ADR này không đề xuất cấu trúc; adapter chỉ giữ `TTSCost.unit/quantity` như số liệu nội bộ spike.
- **Việc cần làm tiếp:**
  - ~~QA chấm bộ nghe v2~~ — đã xong (21/10); bảng điểm ở README spike, mục "Bộ nghe và phiếu chấm".
  - QA nghe `pron-ab` (đối chiếu để nguyên vs phiên âm cho `PDFCraft`, `PDF`, `Word`, `Starter`; đã sinh, chưa upload), rồi mới đổi bảng phát âm của 4 từ này.
  - BE review mã remote (README spike, mục `trust_remote_code`).
  - (Khảo sát thêm, không chặn) khi có ảnh quota AI Studio: chạy ứng viên Gemini (tối đa ~15 lần gọi) rồi cập nhật ADR.
  - Chỉnh phần bảng phát âm còn lại sau khi nghe; thêm test cho lỗi phát hiện.
  - Đo RTF/RAM trên máy worker thật; cập nhật mục "Xem lại khi".
  - Sau khi chốt: đổi trạng thái thành "Đã chốt", thêm 1 dòng vào `docs/logs/decision-log.md`, tạo issue port adapter vào `services/worker`.
