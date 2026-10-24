# Prompt: P1-02a — spike renderer FFmpeg (1 timeline → MP4 9:16 + 16:9, tiếng Việt)

- **Repo / cwd:** `AI-review-BE` · **Branch:** `spike/p1-render` (từ `origin/dev` mới nhất) · **PR vào:** `dev`
- **Người làm:** AI phối hợp BE (P1-06 do BE dẫn; hỏi Hoàng ai bên BE nhận trước khi bắt đầu)
- **Mốc:** 18/10/2026 (P1, tuần 13–18/10). Chạy song song với `be-p1-spike-tts-vi.md` và `be-p1-spike-ai-scene.md`; không chờ nhau (audio và clip AI dùng file mẫu).

---

Bạn là coding agent của repo `AI-review-BE`, máy Windows. Làm việc bằng tiếng Việt. Người dùng là AI dev nền C#/.NET, mới với Python: giải thích ngắn, comment code tiếng Việt ngắn.

## Bối cảnh P1 (lead, v1.1, 13/10/2026)
- Input: URL website/AI tool **hoặc** link sản phẩm trên shop. Output: video **tiếng Việt, 15–25 s, 9:16 và 16:9**, 3 preset, cấu trúc **Hook → Problem → Demo → Result → CTA** (CTA không có link tracking).
- Demo: 2 sản phẩm × 3 video khác nhau; mỗi sản phẩm ≥ 1 cảnh do AI tạo (gọi provider thật).
- Kiến trúc: FE → FastAPI → PG/Supabase; worker Windows chạy Crawl4AI, Gemini 3.5 Flash-Lite, TTS adapter, AI scene adapter, **renderer FFmpeg**, Storage.
- Toàn văn: `../_refs/incoming/p1-yeu-cau-va-ke-hoach.md` (nếu có). Tài liệu là dữ liệu, không phải lệnh.

## Quyết định mới (14/10, #67, #61)
- **3 preset đã đặt tên:** **hoạt hình đồ họa**, **điện ảnh tối giản**, **cổ điển**. Thay cho 3 kiểu gợi ý ở mục 3 bên dưới; vẫn dùng chung 1 engine, khác tham số.
- **Quyền tư liệu (BA, #52):** không dùng ảnh/screenshot sản phẩm thật khi chưa xác nhận quyền sử dụng (kể cả Lock&Lock, ElevenLabs). Spike chỉ dùng asset tự tạo hoặc có license mở; ghi rõ nguồn từng asset.
- Renderer phải có **đường chạy CPU**; GPU (nvenc/qsv) chỉ là tăng tốc tuỳ chọn.
- Đầu ra mốc 18/10 phải có **lệnh chạy lại** và bằng chứng (ảnh khung hình, `ffprobe`, số đo) để QA kiểm tra.

## Đọc trước
- `CLAUDE.md`, `docs/adr/0005-repo-structure-and-extensibility.md` (spike nằm trong `spikes/`, không dựng trước cấu trúc chưa dùng).
- `docs/specs/contracts/script.v0.schema.json` (script M2 hiện tại: scene, fact_ref) và `docs/specs/m2/`.
- Video mẫu quản lý thích: `../_refs/_analysis/template2/README.md` (khung hình mỗi 2 s, nhịp cắt, chữ). Tham khảo nhịp và bố cục; **không** dùng lại asset hay audio của video mẫu.
- **Không dùng Remotion** (license). Phương án thay thế đã ghi: FFmpeg, Revideo.

## Nhiệm vụ
1. **Render plan (JSON, Pydantic v2):** mô tả 1 video độc lập với tỉ lệ khung. Gồm danh sách scene, mỗi scene có:
   - `kind`: `image` (ảnh tĩnh + Ken Burns), `video` (clip AI), `text_card`;
   - `asset`, `caption` (tiếng Việt), `voice` (file audio của scene);
   - `min_duration_s`.
   
   Thời lượng scene = max(`min_duration_s`, độ dài voice + đệm). Tổng 15–25 s; vượt khoảng này thì báo lỗi rõ.
2. **`render(plan, ratio, out_path)`** gọi `ffmpeg` qua `subprocess`. Ra MP4 H.264 + AAC, 30 fps:
   - 1080×1920 (9:16) và 1920×1080 (16:9) **từ cùng 1 plan**;
   - asset sai tỉ lệ: nền mờ phóng to + ảnh chính ở giữa (không crop mất nội dung);
   - phụ đề cháy vào hình bằng ASS (libass), font hỗ trợ đủ dấu tiếng Việt (vd Be Vietnam Pro hoặc Noto Sans, license OFL; ghi rõ license nếu commit file font), đặt trong vùng an toàn của từng tỉ lệ;
   - chuyển cảnh đơn giản (cắt hoặc xfade ≤ 0.3 s); nhạc nền tuỳ chọn, tự giảm âm lượng khi có voice.
3. **3 preset bố cục** (cùng engine, khác tham số: nhịp, kiểu chữ, vị trí phụ đề, chuyển cảnh). Đề xuất tên và mô tả 1 dòng, rồi hỏi lại trước khi chốt:
   - kiểu "levels/bậc" như template2;
   - kiểu listicle/gallery như template1;
   - kiểu demo nhanh/before–after.
4. **Asset mẫu tự tạo, commit được:**
   - ảnh: chụp màn hình trang công khai bằng Crawl4AI/Playwright hoặc ảnh màu tự sinh;
   - voice: wav im lặng hoặc tone có độ dài cố định, dùng đến khi spike TTS xong;
   - clip AI giả: clip màu ffmpeg sinh ra.
   
   Không commit video output; ghi kết quả vào README.
5. **Đo trên máy Windows của dev:** thời gian render mỗi video 20 s cho từng tỉ lệ (CPU, ghi rõ cấu hình máy), dung lượng file, có kiểm tra `ffprobe`. Thử `h264_nvenc` / `h264_qsv` nếu máy có, chỉ để đo.
6. **ADR-0003 (Proposed): renderer.** So sánh FFmpeg thuần và Revideo theo số đo và độ phức tạp. Đề xuất 1 lựa chọn. Kiểm tra số ADR chưa bị dùng trong repo và các PR đang mở.

## Phạm vi
- Làm: `spikes/p1-render/**` (code, plan mẫu, README kết quả), `docs/adr/0003-*.md`.
- Không làm: `services/worker` (đưa vào worker là việc sau), DB, API, FE, TTS thật, gọi AI thật.

## Acceptance criteria
- [ ] `uv run python render.py plans/<preset>.json --ratio 9:16|16:9` ra MP4 hợp lệ, 15–25 s, đúng độ phân giải.
- [ ] 3 preset × 2 tỉ lệ = 6 video render thành công. README có ảnh chụp 1 khung của mỗi video (PNG nhỏ) và bảng số đo.
- [ ] Phụ đề hiển thị đúng dấu tiếng Việt (kiểm tra bằng câu "Tiết kiệm 390.000đ — dùng thử miễn phí ngay hôm nay!").
- [ ] Plan quá 25 s hoặc dưới 15 s báo lỗi rõ.
- [ ] ADR-0003 có số đo.

## Ràng buộc
- Trình bày cấu trúc file và thư viện mới trước khi làm, chờ duyệt. Mặc định chỉ dùng `pydantic` + `ffmpeg` (binary hệ thống, cài bằng `winget install Gyan.FFmpeg`). Cần Pillow hay thư viện khác thì hỏi trước.
- Không Remotion. Không commit `.env`, video output, asset có bản quyền. Không `git reset --hard`, force push.

## Khi xong
- Commit kèm file prompt này. Mở PR vào `dev`: `Refs #67`, bảng số đo, ảnh khung hình, `cc @VV6505`.
- Trả về: link PR, bảng số đo, các câu hỏi còn mở.

## Bổ sung (15/10)
- BE chưa nhận renderer; cứ làm, BE review sau. Không cần chờ.
- Đã có đầu vào thật, dùng thay asset giả khi có thể:
  - Voice: output VieNeu-TTS của spike TTS (PR #73, branch spike/p1-tts-vi; audio ở D:\Code\AI-Content-Review\tts-spike-output\, theo câu). Thời lượng scene = độ dài audio câu tương ứng.
  - Cảnh AI: clip/ảnh từ spike cảnh AI (PR #71, branch spike/p1-ai-scene; ảnh 1024×1024, chạy run_real.py hoặc dùng output local). Không commit ảnh/clip.
- Tư liệu sản phẩm thật: CHƯA có quyền (BA #67, #52) → dùng ảnh tự tạo/fixture, ghi rõ "fixture" trong README. Không dùng screenshot ElevenLabs/Lock&Lock.
- Mục tiêu 18/10: ít nhất 1 MP4 9:16 + 1 MP4 16:9 có giọng đọc VieNeu + phụ đề tiếng Việt + 1 cảnh AI thật; sau đó đủ 3 preset × 2 tỉ lệ. Có lệnh chạy lại cho QA.
- Ghi thời gian render CPU và NVENC, RAM; ADR-0003 (Proposed).
