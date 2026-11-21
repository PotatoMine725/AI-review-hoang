# Spike P1-02b — TTS tiếng Việt (so sánh, chọn, adapter)

Issue: #67 (P1-02). Prompt: `docs/prompts/be-p1-spike-tts-vi.md`. ADR đề xuất: `docs/adr/0004-tts-vietnamese.md` (Proposed).
Ngày tra nguồn: **14/10/2026** (mọi license/giá/free tier bên dưới tra ngày này, từ nguồn chính thức: model card, PyPI, trang giá).

**Phạm vi P1 (theo review của lead, 18/10/2026):** ưu tiên **một TTS tiếng Việt chạy được để ghép luồng P1**. Hiện là **VieNeu-TTS** (đã chạy, đã bàn giao cách chạy, xem mục "Bàn giao cho M2").
Piper là ứng viên so sánh đã chạy. **Gemini TTS là khảo sát thêm, không chặn PR**: đã có adapter + test, **chưa gọi thật** (chưa có ảnh quota; chưa cần gọi chỉ để đủ số ứng viên).
Hai phần khác nhau, đừng gộp:
- **(a) Chất lượng giọng: ĐÃ CÓ kết quả QA** (@VD-PHU chấm mù bộ v2, 65 clip, tổng hợp ở comment #73 ngày 21/10; bảng ở mục "Bộ nghe và phiếu chấm"). Kết luận của lead (25/10): **VieNeu đạt cho P1** (Mai Anh ONNX CPU là phương án đã có kết quả cho máy không GPU); Piper không ưu tiên cho luồng chính, giữ số đo làm tài liệu so sánh. Kết quả này xác nhận hướng cho bước tích hợp, chưa thay thế kiểm tra audio và video hoàn chỉnh trên sản phẩm thật. Các số RTF/RAM chỉ nói về tốc độ và tài nguyên, **không suy ra chất lượng**.
- **(b) Vẫn CHƯA xác minh:** nguồn gốc/license của giọng VieNeu và giọng Piper `25hours_single` (không giọng nào được xem là "đã chọn" cho sản phẩm), revision đầu-cuối của codec ONNX, review mã `trust_remote_code` bởi BE, và tích hợp vào worker.

## Cấu trúc
```
spikes/p1-tts-vi/
  common/        tts_common: normalize_vi, bảng phát âm theo provider, adapter (TTSProvider/TTSResult/TTSCost), FakeTTS, tách câu, đầu vào/log theo đoạn, đo RTF/RAM (chỉ stdlib)
  piper/ vieneu/ gemini/   mỗi ứng viên 1 môi trường uv riêng (adapter.py, run.py)
  vieneu/pins.py           ghim revision HF + sha256 mã remote; vieneu/synth_segments.py = CLI bàn giao theo từng đoạn
  samples/                 segments.sample.json (đầu vào mẫu) + tts-log.sample.json (log từ lần chạy thật)
  sentences.json           bộ 9 câu thử + kịch bản mẫu 5 câu (~60 từ)
  scoring-sheet.md         phiếu chấm
  summarize.py             in bảng số đo từ output/*/results.json
  make_listening_kit.py    tạo bộ nghe mù (mã ngẫu nhiên) + phiếu CSV
```
Audio, model tải về (`output/`, `models/`) nằm trong `.gitignore`.
**Thư mục local giữ audio và kết quả:** `D:\Code\AI-Content-Review\tts-spike-output\` (bản sao ngoài worktree). Bộ nghe: `listening-v2.zip` (không có đáp án); đáp án `answer-key.json` nằm riêng cùng thư mục; bản cũ ở `obsolete\` (xem "Bộ nghe và phiếu chấm").
Người nghe không truy cập được ổ `D:` của máy này: cần gửi `listening-v2.zip` qua Drive/Zalo/… (không commit audio vào Git).

## Bảng ứng viên

| Ứng viên | License code / weight | Chi phí | Free tier (nguồn, ngày tra) | Offline | RTF (CPU / GPU) | Timestamp | Giọng | Kết luận sơ bộ |
|---|---|---|---|---|---|---|---|---|
| **VieNeu-TTS v3 Turbo** (SDK `vieneu` 3.8.3) | Code Apache-2.0 (PyPI); weight `pnnbao-ump/VieNeu-TTS-v3-Turbo` Apache-2.0 (HF card); tokenizer `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` Apache-2.0 | 0 (local) | Không áp dụng | Có (đã thử `HF_HUB_OFFLINE=1`, cả ONNX và PyTorch) | CPU ONNX **0,83**, CPU PyTorch 2,00, GPU **0,13** | Không | 25 giọng có sẵn (nam/nữ; Bắc/Trung/Nam) + clone; nguồn gốc giọng **chưa xác minh** | **Chạy được; ưu tiên P1 để ghép luồng.** QA (21/10): tự nhiên 4,00–4,23, đúng dấu 4,77–4,92, đọc số 4,90; lead (25/10): đạt cho P1. License/nguồn giọng, review mã remote và tích hợp worker: chưa xác minh |
| **Piper `vi_VN`** (`piper-tts` 1.8.0) | **Engine GPL-3.0-or-later** (PyPI); repo giọng `rhasspy/piper-voices` ghi MIT nhưng license theo từng giọng (bảng dưới) | 0 (local) | Không áp dụng | Có | CPU **0,04–0,05** | Không có theo từ (API có `include_alignments`, chưa thử với tiếng Việt) | 3 giọng, mỗi giọng 1 người nói; model card không ghi nam/nữ | **Chạy được**, nhanh, nhẹ; QA (21/10): tự nhiên 1,38–2,85, nhiều clip sai dấu/giá/đơn vị; lead (25/10): không ưu tiên cho luồng chính, giữ số đo làm tài liệu so sánh; cờ GPL; giọng `25hours_single` license chưa xác minh |
| **Gemini TTS** (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`) | Dịch vụ API, SDK `google-genai` | Free tier "Free of charge" (input và output); trả phí: text $0,50/1M token, audio $9/1M (Flash) hoặc $6/1M (Flash-Lite) đến 31/12/2026, **gấp đôi từ 01/01/2027** | Trang giá `ai.google.dev/gemini-api/docs/pricing`, 14/10/2026. **Trang không ghi RPM/RPD** → cần ảnh quota. Free tier: nội dung **được Google dùng cải thiện sản phẩm** ("Yes"), gói trả phí "No" | Không | Chưa đo (có độ trễ mạng) | Không (chỉ trả audio) | 30 giọng có sẵn + thư viện giọng; hỗ trợ tiếng Việt | **Khảo sát thêm, không chặn P1.** Có adapter + test, chưa gọi thật (chưa có ảnh quota) |
| F5-TTS bản tiếng Việt (`hynt/F5-TTS-Vietnamese-ViVoice`) | **CC-BY-NC-SA 4.0** (HF card); weight gốc `SWivid/F5-TTS` **CC-BY-NC 4.0** | 0 (local) | — | Có | Chưa đo | — | — | **Không chạy**: NC, đã có 3 ứng viên chạy được. Chỉ làm nếu cả 3 trượt (hỏi lại) |
| `facebook/mms-tts-vie` | **CC-BY-NC 4.0** (HF card) | 0 | — | Có | Chưa đo | — | 1 giọng | Không chạy: NC |
| viXTTS / XTTS-v2 | Coqui Public Model License (non-commercial) (HF card `capleaf/viXTTS`, `coqui/XTTS-v2`) | — | — | — | — | — | — | **Loại trước**: CPML non-commercial |
| `edge-tts` | Dùng endpoint không chính thức của Edge | — | — | Không | — | — | — | **Loại trước**: không chính thức, có thể bị chặn bất cứ lúc nào |
| Google Cloud TTS / Azure TTS | — | Cần bật billing | — | Không | — | — | — | **Loại trước**: yêu cầu billing, trái ràng buộc lead |

### Nguồn Gemini đã đối chiếu trực tiếp (HTML gốc, tải bằng curl ngày 14/10/2026)
- `ai.google.dev/gemini-api/docs/speech-generation`: model `gemini-3.8-flash-tts` và `gemini-3.8-flash-lite-tts`; mẫu Python dùng `client.interactions.create(model=…, input=[{"type": "user_input", …, "annotations": [{"type": "speech_metadata", "style": …}]}], response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": "Kore"}]})`; trả WAV (`audio/wav`) 24 kHz; tiếng Việt có trong bảng ngôn ngữ; không có chữ "timestamp" nào trong trang.
- `ai.google.dev/gemini-api/docs/pricing`, khối Gemini 3.8 Flash TTS / Flash-Lite TTS: Free Tier "Free of charge"; **"Used to improve our products": Yes (free) / No (paid)**; **không có RPM/RPD** trong khối TTS (các dòng RPD trên trang chỉ thuộc phần grounding); trang ghi "Rate limits are subject to change" và dẫn tới trang Rate limits riêng (giới hạn theo project xem trong AI Studio), nên vẫn cần ảnh quota.

### License từng giọng Piper (model card `rhasspy/piper-voices`)
| Giọng | Dataset | License dataset | Chất lượng / sample rate | Dùng trong spike |
|---|---|---|---|---|
| `vi_VN-vais1000-medium` | VAIS-1000 | **CC BY 4.0** (cần ghi nguồn) | medium, 22,05 kHz | Có |
| `vi_VN-25hours_single-low` | InfoRe Technology 1 | **"Unknown"** (model card không rõ) | low, 16 kHz | Có (gắn cờ license chưa rõ) |
| `vi_VN-vivos-x_low` | VIVOS (InfoRe) | **CC BY-NC-SA 4.0 (NC)** | x_low, 16 kHz, 65 người nói | **Không** (NC) |

### Cờ license / điều khoản cần chủ dự án quyết
1. **Piper engine GPL-3.0-or-later** (copyleft). Dùng như dependency trong worker hoặc nhúng vào sản phẩm phát hành có thể kéo theo nghĩa vụ GPL. Cần quyết nếu chọn Piper.
2. **Piper `25hours_single`: license dataset "Unknown"** → **chưa xác minh**, không dùng khi chưa làm rõ.
3. **Gemini free tier dùng nội dung để cải thiện sản phẩm**. Ràng buộc lead: không gửi upload của merchant hay dữ liệu nhạy cảm lên free tier. Kịch bản TTS sinh từ PKB (thông tin sản phẩm công khai đã crawl, không phải tài liệu merchant upload); tác giả PR đã nêu quan điểm này trong bình luận PR, **chờ lead xác nhận**. Gemini là khảo sát thêm nên chưa chặn P1.
4. **VieNeu tải và chạy mã từ HF** (`trust_remote_code=True`, chỉ ở backend PyTorch). Chi tiết file nào được chạy, revision đã ghim và cách kiểm: mục "trust_remote_code" bên dưới. **BE cần review trước khi đưa vào worker.**
5. **Nguồn gốc dữ liệu huấn luyện và 25 giọng mẫu VieNeu** (như "Adam bựa", "Trúc Ly"…): **chưa xác minh**. Apache-2.0 ở weight không bảo đảm quyền với dữ liệu gốc hay quyền giọng/hình ảnh của người thật. Giọng `Mai Anh` đang dùng cho demo #78 chỉ vì đã chạy được, **không phải quyết định chọn giọng cho sản phẩm**. Cần hỏi tác giả hoặc xem repo trước khi dùng ngoài demo.
6. VieNeu có tuỳ chọn watermark (extra `watermark`, resemble-perth); **không cài**, nên audio đo không có watermark.

## Phiên bản và revision đang dùng
Tra/đo ngày 19/10/2026. Khoá chính xác ở `vieneu/uv.lock`, `piper/uv.lock`.

| Thành phần | Phiên bản / revision | Ghi chú |
|---|---|---|
| Package `vieneu` | **3.8.3** (PyPI, Apache-2.0) | `Vieneu(mode="v3turbo", …)`; deps: `transformers==4.57.6`, `torch==2.8.0+cu128`, `onnxruntime 1.31.0` |
| Model VieNeu | `pnnbao-ump/VieNeu-TTS-v3-Turbo` @ **`61b85e3d937fbbacb387714180e8182823512523`** | PyTorch dùng thư mục con `update/`, ONNX dùng `onnx_update/` (fp32); thêm `speaker_encoder.onnx`, `denoiser.onnx` ở gốc |
| Codec (có mã remote) | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` @ **`6aa02b01e445cc585582cf0ba480bc3ea6c8dd68`** | chỉ backend PyTorch; xem mục `trust_remote_code` |
| Codec ONNX (không có mã) | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` @ **`ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae`** | chỉ file ONNX; SDK tải không kèm `revision` (xem giới hạn bên dưới) |
| Giọng VieNeu đang dùng | **`Mai Anh`** (nữ; dùng cho demo #78 và bộ nghe), **`Hải Đăng`** (nam; chỉ trong bộ nghe) | giọng là preset trong file `vieneu/assets/voices_v3_turbo.json` của package 3.8.3 (sha256 `e1f13cd2c2e0d29fdab5e15bfd7a30f3d7b768e6132bb43dd2b853f8efefdce9`); repo HF không có file giọng, nên "phiên bản giọng" = phiên bản package. Nguồn gốc giọng: **chưa xác minh** |
| Package `piper-tts` | **1.8.0** (PyPI, GPL-3.0-or-later) | |
| Giọng Piper | `vi_VN-vais1000-medium` (sha256 `ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab`, CC BY 4.0); `vi_VN-25hours_single-low` (sha256 `266945c4a80cb3301450c8ba6fcf6ba3542c56cf952a08a8ff3d2d4ff0ab5609`, license **chưa xác minh**) | tải bằng `piper.download_voices` từ `rhasspy/piper-voices` nhánh `main` (không có commit ghim); **hash file `.onnx` là mốc nhận diện bản đã đo** |

Ghim trong code: `vieneu/pins.py` (`REVISIONS`, `REMOTE_CODE_SHA256`). Adapter `VieNeuTTS` tải đúng commit bằng `snapshot_download(revision=…)` rồi đưa **đường dẫn cục bộ** cho SDK (SDK không có tham số `revision`). `TTSResult.model` ghi dạng `pnnbao-ump/VieNeu-TTS-v3-Turbo@61b85e3d[onnx/cpu]`.
Các số đo bên dưới chạy lại ngày 19/10 bằng bản đã ghim (cache HF cục bộ, `HF_HUB_OFFLINE=1`).

## trust_remote_code: mã nào được tải và chạy (cho BE review)
Chỉ rõ để BE review trước khi đưa vào worker.

1. **Chạy mã Python từ Hugging Face: chỉ ở backend PyTorch**, tại `vieneu/_v3_turbo_engine/inference_v3_turbo.py:81`:
   `AutoModel.from_pretrained(moss_tokenizer_path, trust_remote_code=True)` với repo **`OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`** @ `6aa02b01…`. `config.json` của repo khai báo `auto_map` tới 2 file được import và chạy:

   | File (trong repo) | sha256 |
   |---|---|
   | `configuration_moss_audio_tokenizer.py` | `b2d67dc4581e70f4b69b2d7eccefe32581d0c5192fe4d97fe1830e94a255b8aa` |
   | `modeling_moss_audio_tokenizer.py` (~3000 dòng) | `b14af7c188944da5101adbd4aaa9c3617d66b83507f0efbd6eb416381a105930` |

   Import: stdlib, `torch`, `transformers`. Tôi mới **grep nhanh** (không phải review): không thấy lời gọi mạng, `subprocess`, `os.system`, `exec/eval`, `pickle`; chỉ có `importlib.import_module("flash_attn")` (tuỳ chọn). **BE vẫn cần đọc 2 file này.**
2. `AutoTokenizer.from_pretrained(<VieNeu>/update, trust_remote_code=True)` truyền cờ nhưng `tokenizer_config.json` của `update/` **không có `auto_map`** và snapshot không có file `.py`, nên không chạy mã nào từ repo VieNeu (code mô hình nằm trong package `vieneu`, đã khoá bởi `uv.lock`).
3. **Backend ONNX không dùng `trust_remote_code`**: chỉ nạp file `.onnx`, `.npz`, `.json` từ `onnx_update/` và repo `…-Nano-ONNX`. Đây cũng là đường mà demo #78 dùng (Mai Anh, ONNX, CPU).
4. `vieneu/standard.py` cũng có `trust_remote_code` nhưng thuộc `mode="standard"`, spike **không dùng**.

**Cách ghim:** `pins.py` tải đúng commit (`snapshot_download(revision=<sha>)`) rồi truyền `backbone_repo=<thư mục snapshot>`, `moss_tokenizer=<thư mục snapshot>` cho `Vieneu(...)`. Khi nạp từ đường dẫn cục bộ, `transformers` chỉ chạy file `.py` trong snapshot đó. **Đã kiểm:** sau khi khởi tạo adapter PyTorch, 2 module `…moss_audio_tokenizer` trong `sys.modules` nằm ở thư mục `transformers_modules/_6aa02b01…` và có sha256 trùng bảng trên (chạy được với `HF_HUB_OFFLINE=1`).
**Giới hạn đã biết:** `V3TurboVieNeuTTS` không chuyển `codec_dir`/`codec_repo` xuống engine ONNX, nên codec `…-Nano-ONNX` do SDK tự tải **không kèm `revision`** (chỉ là file ONNX, không có mã Python). Muốn ghim chặt trên worker: tải sẵn commit `ceff0d07…` vào cache rồi chạy `HF_HUB_OFFLINE=1`, hoặc nhờ tác giả SDK thêm tham số. Đổi bất kỳ revision nào ở `pins.py` = phải review lại 2 file trên.

## Máy đo và số đo
Máy dev (không phải máy worker thật): Windows 11, Intel Core i7-12700H (20 luồng), RTX 4050 Laptop 6 GB VRAM (driver 617.14), Python 3.12, uv 0.12.
**Chưa đo trên máy worker đại diện**; theo #67 chưa chốt TTS local làm dependency bắt buộc trước khi có số đo đó.

Phương pháp: 9 câu × (bản chuẩn hoá `norm` + bản gốc `raw`), 1 lần warm-up không tính, 1 lượt/câu. RTF = thời gian sinh / độ dài audio
(< 1 nhanh hơn thời gian thực). Bảng dưới tính trên bản `norm`. RAM = working set đỉnh của tiến trình (gồm model); VRAM VieNeu là `torch.cuda.max_memory_allocated`.
Mẫu nhỏ, 1 lượt: coi là thứ tự độ lớn, không phải benchmark chính xác.

| Cấu hình | RTF (tổng) | RTF xấu nhất | RAM đỉnh (MB) | VRAM đỉnh (MB) | Audio 9 câu (s) |
|---|---|---|---|---|---|
| piper `vais1000-medium`, CPU | 0,05 | 0,06 | 310 | - | 34,5 |
| piper `25hours_single-low`, CPU | 0,04 | 0,04 | 302 | - | 44,4 |
| vieneu `Mai Anh` (nữ), ONNX, CPU | 0,83 | 0,87 | 2368 | - | 39,8 |
| vieneu `Mai Anh`, PyTorch, CPU | 2,00 | 2,03 | 2082 | - | 39,6 |
| vieneu `Mai Anh`, PyTorch, GPU (CUDA) | 0,13 | 0,19 | 2379 | 507 | 40,5 |
| vieneu `Hải Đăng` (nam), PyTorch, GPU | 0,14 | 0,20 | 2407 | 483 | 33,4 |
| Gemini TTS | chưa gọi (khảo sát thêm) | | | | |

Các số trên chạy lại ngày 19/10 với bản đã ghim và `normalize_vi` đã sửa lỗi ngày cuối câu (xem mục "Chuẩn hoá"). Lần chạy 14/10 cho số tương đương (VieNeu GPU 0,15–0,16, ONNX-CPU 0,89); chênh lệch nằm trong dao động giữa các lần chạy, không phải cải tiến.
Kịch bản mẫu 5 câu (~60 từ, Hook → … → CTA) cho audio **19,6–26,6 s** tuỳ giọng/lần chạy: gần khoảng 15–25 s, một giọng (Piper `25hours`) dài hơn.
Nhận xét kỹ thuật (không phải đánh giá chất lượng):
- Tất cả sinh ra audio hợp lệ, không có clip im lặng. Một số clip chạm trần biên độ (Piper: 13 mẫu mỗi giọng; `Hải Đăng`: 2 mẫu; trên hàng triệu mẫu; số này đo ở lần chạy 14/10): nếu nghe thấy méo thì ghi vào cột ghi chú. `25hours_single` có cảnh báo `Missing phoneme from id map` (ký tự không có trong bản đồ âm vị, chưa rõ ảnh hưởng thế nào đến âm thanh).
- VieNeu lấy mẫu ngẫu nhiên (temperature 0,8): chạy lại cho audio khác nhau.
- VieNeu không có tham số tốc độ (`supports_speed=False`); Gemini chỉ gợi ý tốc độ qua style ("speaking rapidly/slowly"). Piper có `length_scale`.
- Phụ đề: không provider nào cho timestamp theo từ. Theo yêu cầu, sinh audio **từng câu** (`synthesize_script`) và cộng dồn độ dài + khoảng nghỉ để có mốc `start/end` mức câu (xem `script-timings.json` mỗi lần chạy).

## Chuẩn hoá văn bản (`normalize_vi`)
Theo quy tắc, không dùng LLM. Có test (`common/tests`, 89 test). Xử lý:
- số theo quy ước Việt (`390.000` nghìn, `1,2` thập phân, `2026`, `lẻ`, `mốt/tư/lăm`), tiền (`đ ₫ VND USD $ k`, "1,2 triệu đ"), `%`, đơn vị (`ml l g kg mg mm cm m km m² GB MB W °C`…), khoảng `15-25`, giờ `9h30`, ngày `31/10/2026`, tháng/năm, số điện thoại, phân số;
- ký hiệu: `&` → "en" (quy tắc ở bước chuẩn hoá ký hiệu, **dùng cho mọi provider**; QA: "Lock&Lock" với `&` đọc "và" 3/5, đổi thành "en" 5/5 trên cả 3 cấu hình VieNeu; trước đây code đổi `&` thành "và");
- bảng phát âm tên tiếng Anh/viết tắt, **tách theo provider** (`pronunciations.py`, khoá `piper` / `vieneu`; mở rộng bằng dict hoặc file JSON), **đã nghe kiểm một phần (QA 21/10)**, phần còn lại vẫn là đoán ban đầu; viết tắt toàn chữ hoa đọc từng chữ cái.
Giới hạn đã biết: số kiểu Anh `1,200,000` không hỗ trợ; `3.5` hiểu là thập phân, `1.500` hiểu là một nghìn năm trăm; "5-10" luôn là khoảng, không phải ngày/điểm số; viết tắt chữ hoa 2–4 ký tự không có trong bảng bị đọc từng chữ cái (kể cả từ tiếng Việt viết hoa toàn bộ không dấu).
**Kết quả nghe về chuẩn hoá (QA 21/10, bộ v2 có cả bản `raw` cho 4 câu có số/tên riêng):** số, ngày, giá, đơn vị: VieNeu đọc đúng cả bản `raw` lẫn bản chuẩn hoá (đều ~5/5), nên **vẫn giữ `normalize_vi`** cho số, ngày, giá, đơn vị, ký hiệu để an toàn và để phụ đề thống nhất. Tên tiếng Anh: xem bảng phát âm ở mục "Bàn giao cho M2".

**Lỗi đã sửa ngày 19/10 (phát hiện khi chạy CLI bàn giao):** ngày/tháng/phân số/số điện thoại/viết tắt đứng **cuối câu có dấu chấm** (vd. `…ngày 31/10/2026.`) không được nhận ra vì regex coi dấu `.` cuối câu là phần của số; kết quả bị đọc thành "ba mươi mốt/mười/hai nghìn…". Đã sửa (chỉ chặn `.`/`,` khi sau đó còn chữ số) và thêm 7 test hồi quy, gồm cả kịch bản mẫu. Bản `norm` của câu `s6-date-money` trong bộ nghe **v1** đã nhận văn bản sai này; bộ nghe **v2** đã thay 5 clip đó (xem "Bộ nghe và phiếu chấm"). Bảng phát âm: xem mục "Bàn giao cho M2" (đã nghe kiểm một phần).

## Adapter
`TTSProvider.synthesize(text, voice, speed) -> TTSResult(path, duration_s, timings|None, provider, model, cost)` (`common/src/tts_common/provider.py`).
- `FakeTTS`: wav im lặng đúng độ dài ước tính (từ + dấu câu), dùng cho CI.
- `PiperTTS`, `VieNeuTTS`, `GeminiTTS` ở `<ứng viên>/adapter.py`. Interface rút ra từ 3 provider này, **chưa phải bản chốt cho worker** (ADR-0005).
- `GeminiTTS` từ chối gọi thật nếu không có `live=True`, có trần số lần gọi mỗi phiên (`max_calls`), và test bằng client giả (4 test).
- Usage: **theo #74**; spike không thêm cấu trúc usage nào vào schema. `TTSCost(unit, quantity, cost_usd, cost_status)` là cấu trúc **nội bộ spike** để ghi lại số đo; `to_item()` chỉ xuất các trường `cost-breakdown.v1` hiện cho phép (`category=tts`, `cost_usd`, `cost_status`; có test kiểm bằng schema). `unit`/`quantity` không đi vào item.

## Bàn giao cho M2 (@VoHoangDinh)
Dùng lại adapter và cấu hình đã có; hướng dẫn chạy/kiểm tra, audio từng đoạn và thời lượng đo thật như sau. Chất lượng giọng đã có kết quả QA (mục "Bộ nghe và phiếu chấm") nhưng chưa thay thế kiểm tra audio và video hoàn chỉnh; đây là bàn giao kỹ thuật để ghép luồng.

### 1. Interface
```python
from tts_common.normalize import normalize_vi          # common/src/tts_common/normalize.py
from tts_common.provider import TTSProvider, TTSResult  # common/src/tts_common/provider.py

normalize_vi(text: str, pronunciations: dict[str, str] | None = DEFAULT_PRONUNCIATIONS, *, spell_acronyms: bool = True) -> str
#   pronunciations=None  → không đổi cách đọc tên riêng; dict riêng → thay cho bảng mặc định (xem mục 3)
#   DEFAULT_PRONUNCIATIONS = bảng PIPER (tên cũ, giữ cho mã đã có). Với VieNeu dùng bảng riêng:
normalizer_for("vieneu")(text)   # tts_common.normalize; tương đương normalize_vi(text, pronunciations_for("vieneu"))

TTSProvider.synthesize(text: str, voice: str, speed: float = 1.0) -> TTSResult
TTSResult(path: Path, duration_s: float, timings: list[Timing] | None, provider: str, model: str, cost: TTSCost)
#   timings = None với cả 3 provider (không có mốc theo từ). Phụ đề căn theo câu: tts_common.script.synthesize_script
#   sinh audio từng câu, cộng dồn duration_s + khoảng nghỉ gap_s (0,2 s) → mốc start/end từng câu.
#   VieNeuTTS: supports_speed=False (bỏ qua `speed`). Cần chỉnh tốc độ thì xử lý hậu kỳ (vd. ffmpeg atempo).
```
`VieNeuTTS(out_dir, device="cpu"|"cuda", backend="onnx"|"pytorch")` ở `vieneu/adapter.py`; `FakeTTS` (`tts_common.fake`) cho test/CI không cần model.

### 2. Chạy CLI theo từng đoạn
```bash
cd spikes/p1-tts-vi/vieneu && uv sync
uv run python synth_segments.py ../samples/segments.sample.json --device cpu --backend onnx --voice "Mai Anh"
uv run python synth_segments.py kich-ban.json --pronunciations bang-phat-am.json   # bảng riêng gộp đè bảng mặc định
uv run python synth_segments.py kich-ban.json --only 3 5                            # chỉ sinh lại đoạn 3 và 5
```
- Đầu vào: `{"segments": [{"id": "…", "text": "…"}]}` hoặc `{"scenes": [{"id": "…", "voice_text": "…"}]}` (dạng `script-*.json` của #78). `id` (hoặc `segment_id`; với scenes còn `scene_id`) trở thành `segment_id` trong log; thiếu thì dùng `s01`, `s02`… theo thứ tự; `id` trùng nhau là lỗi.
- Đầu ra trong `--out-dir` (mặc định `output/handoff/`, không commit): `s01.wav`, `s02.wav`… (mono 16-bit, 48 kHz; số theo thứ tự đoạn) và `tts-log.json`.
- Mỗi đoạn trong `tts-log.json` giữ đủ liên kết: `segment_id` ↔ `voice_text` (lời gốc) ↔ `normalized` (văn bản sau chuẩn hoá, đúng thứ đưa vào TTS) ↔ `path` (audio) ↔ `duration_s` (đo từ lần sinh thật), thêm `gen_s`, `voice`.
- **Sửa lời hoặc bảng phát âm thì phải sinh lại audio và cập nhật timing của đoạn đó, không dùng lại thời lượng cũ.** Khi chạy `--only`, CLI so các đoạn còn lại với log cũ (`segment_id`, lời gốc, văn bản chuẩn hoá) và in `CẢNH BÁO` ra stderr nếu có đoạn đã cũ.
- **Thời lượng P1 40–45 s được kiểm trên MP4 cuối** (tính cả khoảng nghỉ và chuyển cảnh), không phải tổng `duration_s` của các đoạn thoại. Usage vẫn theo #74 (spike không thêm cấu trúc usage).
- Mỗi lần sinh đi qua `VieNeuTTS.synthesize()` → `TTSResult`, nên đây chính là adapter được bàn giao.
- Ghim revision tự động qua `pins.py`. Lần đầu cần mạng để tải đúng commit; sau đó chạy được `HF_HUB_OFFLINE=1`. Ghi chú về cache HF: đặt `HF_HUB_CACHE` nếu muốn dùng cache khác.
- **Lưu ý cho #78:** `spikes/p1-demo-pdfcraft/tts.py` hiện gọi `Vieneu(...)` trực tiếp (không qua adapter, không ghim revision, không dùng `pins.py`). Khi ghép vào luồng chính nên chuyển sang `VieNeuTTS`.

### 3. Bảng phát âm (tách theo provider)
`PRONUNCIATIONS_BY_PROVIDER` ở `common/src/tts_common/pronunciations.py`, khoá `piper` và `vieneu` (khoá từ không phân biệt hoa thường, khớp nguyên từ). **Đã nghe kiểm một phần (QA 21/10)**: Piper cần phiên âm, VieNeu đọc tên tiếng Anh để nguyên tốt hơn.
- **`piper`: giữ nguyên bảng cũ** (bảng dưới). `DEFAULT_PRONUNCIATIONS` là tên cũ, bằng bảng Piper, giữ để mã đã có (vd. demo #78) không đổi hành vi.
- **`vieneu`: bảng dưới, bỏ `ElevenLabs` và `Lock&Lock`.** `ElevenLabs` để nguyên (QA: 4–5/5; phiên âm "I lép ven Láp" chỉ 2/5, trên cả 3 cấu hình VieNeu). `Lock&Lock` không cần mục riêng vì quy tắc ký hiệu `&` → "en" (xem "Chuẩn hoá"): "Lock en Lock" 5/5.
- **Chưa đổi (chờ nghe):** `Starter`, `Pro`, `PDFCraft`, `Word`, `PDF` và các mục còn lại của bảng. QA chưa nghe bản để nguyên của các từ này; **không suy rộng từ ElevenLabs sang tên khác**. Bộ đối chiếu có chọn lọc đã sinh xong (mục "Bộ nghe và phiếu chấm"), chưa có kết quả chọn.
- Quy tắc chuẩn hoá số, ngày, giá, đơn vị, ký hiệu **không bỏ**, áp dụng cho cả hai provider.

Mở rộng bằng file JSON `{ "từ": "cách đọc" }` (`--pronunciations` của CLI gộp lên bảng `vieneu`; `load_pronunciations(path, provider)`, `provider` mặc định `piper` để giữ hành vi cũ; demo #78 có `pronunciations.json` gộp đè).

| Nhóm | Mục (từ → cách đọc; `ElevenLabs` và `Lock&Lock` chỉ có ở bảng `piper`) |
|---|---|
| Thương hiệu | ElevenLabs → I lép ven Láp · Lock&Lock → Lốc en Lốc · Claude → Clốt · Gemini → Giê mi nai · Gamma → Ga ma · Dreamina → Đrim mi na · TikTok → Tích Tóc · YouTube → Diu Túp · Facebook → Phây búc · Shopee → Sốp pi · Lazada → La da đa · Tiki → Ti ki · Google → Gu gồ |
| Từ hay gặp | AI → ây ai · Pro → Prô · Plus → Plát · Free → Phri · Max → Mách · Premium → Pri mi âm · Standard → Stan đớt · Starter → Sờ ta tơ · Creator → Cri ây tơ · App → Ép · Online → On lai · Video → Vi đi ô · Review → Ri viu · Sale → Seo · Freeship → Phri síp · Hot → Hót · Deal → Đin |
| Địa danh | TP.HCM, TPHCM → Thành phố Hồ Chí Minh |
| Dự phòng | viết tắt 2–4 chữ hoa chưa có trong bảng → đọc từng chữ cái tiếng Anh (CTA → xi ti ây) |

### 4. Log mẫu (audio từng đoạn + `duration_s` đo thật)
`samples/tts-log.sample.json` là log của **một lần chạy thật bằng CLI hiện tại** (28/10/2026; đầu vào `samples/segments.sample.json`; 5 đoạn, VieNeu `Mai Anh`, ONNX CPU, bản ghim, bảng `vieneu`; không kèm audio). Cùng dạng với `spikes/p1-demo-pdfcraft/runs/*/tts-log.json` (#78): khoá `"1"`, `"2"`… và `_meta`; mỗi đoạn có thêm `segment_id` và `voice`. Có test kiểm log mẫu khớp đầu vào và bảng phát âm (`common/tests/test_segments.py`).

| Đoạn | `segment_id` | `duration_s` | `gen_s` | Văn bản đọc (sau `normalize_vi`) |
|---|---|---|---|---|
| 1 | s01-hook | 3,28 | 3,33 | Bạn còn mất cả buổi chỉ để làm một Vi đi ô Ri viu? |
| 2 | s02-spec | 5,76 | 5,45 | Bình giữ nhiệt Lock en Lock năm trăm mi li lít giữ nóng mười hai giờ, giữ lạnh hai mươi tư giờ. |
| 3 | s03-feature | 3,76 | 3,53 | Nắp khóa kín, không rò nước, nặng chỉ một phẩy hai ki lô gam. |
| 4 | s04-price | 7,20 | 6,98 | Giá chỉ còn ba trăm chín mươi nghìn đồng, giảm hai mươi lăm phần trăm đến hết ngày ba mươi mốt tháng mười năm hai nghìn không trăm hai mươi sáu. |
| 5 | s05-cta | 2,56 | 2,19 | Bấm vào link ngay hôm nay để nhận ưu đãi! |

Tổng thoại 22,56 s. `_meta` ghi `provider`, `model` (có revision), `voice`, `sample_rate`, `revisions`, `remote_code_sha256`, `pronunciations`.
Đoạn 2 khác log 19/10 ("Lốc en Lốc" → "Lock en Lock") vì bảng `vieneu` không còn phiên âm `Lock&Lock`; log được sinh lại bằng lần chạy thật, không sửa tay.
**Renderer phải lấy `duration_s` từ log của lần chạy thật (hoặc đo lại từ file wav), không dùng log mẫu**: VieNeu lấy mẫu ngẫu nhiên (temperature 0,8) nên cùng một câu cho độ dài khác nhau giữa các lần (vd. đoạn 1: 3,04 s ở lần chạy 19/10 và 3,28 s ở lần 28/10, cùng văn bản). `gen_s` là thời gian sinh trên máy dev, không phải số đo trên máy worker.

## Cách chạy
```bash
# chung: test + lint + type check
cd spikes/p1-tts-vi/common && uv sync && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run pyright

# Piper
cd spikes/p1-tts-vi/piper && uv sync
uv run python -m piper.download_voices --download-dir models vi_VN-vais1000-medium vi_VN-25hours_single-low
uv run python run.py --voice vais1000-medium

# VieNeu (torch CUDA cu128 từ download.pytorch.org; --device cpu để đo CPU)
cd spikes/p1-tts-vi/vieneu && uv sync
uv run python run.py --device cuda --backend pytorch --voice "Mai Anh"
uv run python run.py --device cpu --backend onnx --voice "Mai Anh"
uv run python synth_segments.py ../samples/segments.sample.json --device cpu --backend onnx   # CLI bàn giao (mục trên)

# Gemini: CHỈ sau khi có ảnh quota. Điền GEMINI_API_KEY vào .env (cùng thư mục spike; chỉ commit .env.example)
cd spikes/p1-tts-vi/gemini && uv sync && uv run --env-file ../.env python run.py --live --voice Kore

# Bảng số đo + bộ nghe mù
python spikes/p1-tts-vi/summarize.py
python spikes/p1-tts-vi/make_listening_kit.py
```

## Bộ nghe và phiếu chấm
Bộ nghe **v2**: `D:\Code\AI-Content-Review\tts-spike-output\listening-v2.zip` (cũng ở `output/listening/`) có 65 clip `L01.wav`… và `scoring-sheet.csv` (cột điểm trống), **không có đáp án**.
Gồm 5 cấu hình (Piper ×2 giọng, VieNeu `Mai Anh` PyTorch-GPU, VieNeu `Mai Anh` ONNX-CPU, VieNeu `Hải Đăng`) × 9 câu, thêm bản gốc không chuẩn hoá của 4 câu có số/tên riêng.
Đáp án `answer-key.json` nằm cạnh zip, **ngoài** `listening/` (**không mở trước khi chấm xong**).
Hướng dẫn chấm và thang điểm: `scoring-sheet.md`. Bộ nghe nằm trên máy của @PotatoMine725, **chưa upload**; cần gửi qua Drive/Zalo cho QA (@VD-PHU) (không commit audio vào Git).

**v1 → v2 (19/10/2026):** `v1` (`obsolete\listening-v1-sai-ngay-s6.zip`) có 5 clip câu `s6-date-money` bản `norm` đọc ngày sai do lỗi `normalize_vi` (xem mục "Chuẩn hoá"). `v2` thay đúng 5 clip đó, **giữ nguyên mã và bảng đáp án**: **L17, L31, L34, L49, L55**. 60 clip còn lại giống v1. Ai đã chấm bằng v1: bỏ điểm 5 clip này và chấm lại bằng v2; không cần chấm lại phần còn lại.

### Kết quả nghe (a): chất lượng giọng, đã có kết quả QA
@VD-PHU chấm mù bộ v2 (65 clip, thang 1–5), đã đối chiếu với `answer-key.json`; tổng hợp ở comment #73 ngày 21/10. Chi tiết từng clip nằm trong `scoring-sheet.xlsx` (QA gửi riêng, không commit). Số người chấm: 1.

| Cấu hình | Tự nhiên | Đúng dấu | Đọc số | Tên riêng | Clip có điểm ≤ 2 |
|---|---|---|---|---|---|
| VieNeu Hải Đăng, PyTorch CUDA | 4,23 | 4,92 | 4,90 | 3,62 | 1/13 |
| VieNeu Mai Anh, PyTorch CUDA | 4,08 | 4,85 | 4,90 | 3,75 | 1/13 |
| VieNeu Mai Anh, ONNX CPU | 4,00 | 4,77 | 4,90 | 3,50 | 2/13 |
| Piper vais1000 medium | 2,85 | 3,62 | 3,70 | 3,12 | 8/13 |
| Piper 25hours_single low | 1,38 | 1,62 | 2,90 | 1,50 | 13/13 |

Kết luận của lead (25/10, #73): đồng ý tiếp tục dùng VieNeu để ghép luồng P1; bản Mai Anh ONNX CPU là phương án đã có kết quả để đối chiếu khi chạy trên máy không có GPU; Piper không ưu tiên cho luồng chính, giữ số đo làm tài liệu so sánh. **Kết quả này xác nhận hướng lựa chọn cho bước tích hợp, chưa thay thế kiểm tra audio và video hoàn chỉnh trên sản phẩm thật.**

Điểm cần sửa theo kết quả (VieNeu, tên riêng): `ElevenLabs` để nguyên 4–5/5, phiên âm "I lép ven Láp" 2/5; `Starter` → "Sờ ta tơ" 3/5 (bộ v2 chưa có bản để nguyên); `Lock&Lock` với `&` đọc "và" 3/5, đổi `&` thành "en" 5/5. Số, ngày, giá, đơn vị: raw và chuẩn hoá đều ~5/5. Đã áp dụng vào bảng phát âm theo provider (mục "Bàn giao cho M2", 3).

### Nghe đối chiếu có chọn lọc `pron-ab`: đã sinh, CHƯA có kết quả
Theo lead (25/10), không chấm lại 65 clip; chỉ đối chiếu các tên mà QA chưa nghe bản để nguyên: `PDFCraft`, `PDF`, `Word` (để nguyên vs bản phiên âm đang dùng trong demo #78) và `Starter` (để nguyên vs "Sờ ta tơ"). Đã sinh 12 clip (3 câu × 2 bản × 2 lần; VieNeu Mai Anh, ONNX CPU, bản ghim), nghe mù theo cặp A/B, tên file là mã. Nằm ở `D:\Code\AI-Content-Review\tts-spike-output\pron-ab\` (ngoài Git; **chưa upload**, cần đường dẫn chia sẻ cho QA). Cấu hình, văn bản vào TTS và chỗ ghi kết quả ở `pron-ab.md` cùng thư mục (không gửi cho QA trước khi chấm).
**Cho đến khi QA chọn, bảng phát âm của `PDFCraft` / `Word` / `PDF` / `Starter` không đổi.**

### Kết quả nghe (b): vẫn CHƯA xác minh
Điểm nghe không nói gì về: nguồn gốc/license của giọng và dữ liệu huấn luyện VieNeu, revision codec ONNX, review `trust_remote_code` của BE, tích hợp vào worker (xem "Cờ license" và "trust_remote_code" ở trên).

## Tiêu chí nghiệm thu (prompt)
Phạm vi P1 theo lead (18/10): ưu tiên 1 TTS chạy được; Gemini là khảo sát thêm, không chặn.
- [x] **1 TTS tiếng Việt chạy được để ghép luồng P1**: VieNeu (adapter + CLI theo đoạn + log mẫu). Chất lượng giọng: đã có kết quả QA 21/10 và kết luận của lead 25/10 (hướng cho bước tích hợp). License/nguồn giọng, review mã remote, tích hợp worker và đo trên máy worker thật: chưa.
- [ ] Bảng ứng viên đủ cột: Gemini thiếu RTF và kết luận chất lượng (**khảo sát thêm**, chưa gọi thật vì chưa có ảnh quota).
- [ ] ≥ 3 ứng viên chạy trên bộ câu thử: **2/3** (Piper, VieNeu). Gemini không còn chặn PR theo lead; điều kiện này chưa đạt nguyên văn prompt.
- [x] `normalize_vi` có test (89 test trong `common/tests`, gồm bảng phát âm theo provider, `&` → "en", log/ID theo đoạn).
- [x] Phiếu chấm sẵn cho người nghe (`scoring-sheet.md` + bộ nghe mù v2); QA đã chấm 65 clip.
- [x] Adapter + `FakeTTS`; ruff, pyright sạch (4 môi trường).
- [x] ADR có đề xuất (`docs/adr/0004-tts-vietnamese.md`, **Proposed**).

## Việc còn lại
- [x] QA (@VD-PHU) chấm bộ v2; bảng điểm ở mục "Bộ nghe và phiếu chấm".
- [ ] QA nghe `pron-ab` (cần đường dẫn chia sẻ); theo kết quả chọn mới chỉnh bảng phát âm của `PDFCraft` / `Word` / `PDF` / `Starter`.
- [ ] Chốt ADR-0004 (hiện **Proposed**; khi chốt mới thêm decision-log).
- [ ] BE review mã remote (mục `trust_remote_code`) trước khi đưa vào worker; port adapter vào `services/worker` (việc riêng).
- [ ] Đo lại RTF/RAM trên máy worker thật.
- [ ] Làm rõ license/nguồn dữ liệu giọng (cờ 1–5 ở trên). Usage TTS theo #74.
- [ ] (Khảo sát thêm, không chặn) Gemini: khi có ảnh quota AI Studio thì chạy `gemini/run.py --live` (tối đa ~15 lần gọi) và thêm vào bộ nghe.
