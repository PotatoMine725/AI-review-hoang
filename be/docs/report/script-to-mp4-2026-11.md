# P1-08 — Đường ghép kịch bản M2 → TTS → render → MP4 — Báo cáo

- **Prompt:** `prompts/be-p1-08-script-to-mp4.md` · **Ngày:** 2026-11-03 (lượt 1, 2), 2026-11-04 (lượt 3) · **Người viết:** coding agent (Claude Code)
- **PR:** #97 (draft, nhánh `feat/p1-script-to-mp4`, chồng lên #95) · **Issue:** #67, #61
- Máy đo: i7-12700H, RTX 4050 6 GB, 16 GB RAM, FFmpeg 8.0, Node 24, nguồn điện AC (gói Turbo). Lượt 2 đo lúc CPU nhàn rỗi 0–5%, RAM trống 5,4–6,9 GB. Mỗi mục 1 mẫu.

## Đã làm

Module `services/worker/src/worker/produce/` và CLI `uv run python -m worker.produce <script.json> --input <input.json> --assets <assets.json> --out <dir> [--mode preview|final] [--ratios 16:9,9:16] [--on-unsupported fail|skip]`.

| Phần | Là code worker hay gọi spike |
|---|---|
| Kiểm kịch bản bằng validator M2 (`m2.validate`), tra `fact_refs` trong PKB (`facts.py`) | worker |
| Ánh xạ M2 → `render-plan.v2-spike` (`mapping.py`), cắt đoạn clip vừa độ dài cảnh (`fit_parts`) | worker |
| Chia phụ đề dài thành nhiều cue theo từng tỉ lệ (`cues.py`, chỉ thư viện chuẩn) | worker |
| Cache TTS theo hash (model+backend/thiết bị, giọng, hash bảng phát âm, lời đã chuẩn hoá), log từng câu, đo `duration_s` từ file wav (`tts.py`) | worker |
| Timeline từ audio đo thật, nghỉ và chuyển cảnh tính một lần (`timeline.py`, cùng công thức `timeline.py` của #88) | worker |
| Kiểm MP4 bằng ffprobe, mốc 40–45 s đọc từ `config.py` của #77 (`check.py`, `config.load_limits`) | worker (đọc file #77 bằng importlib) |
| `render_report.json`, điều phối, CLI | worker |
| Chuẩn hoá lời + sinh giọng VieNeu (`drivers/tts_synth.py`) | **gọi spike #73** qua subprocess, venv của #73 |
| HyperFrames + FFmpeg ghép voice, phụ đề (`drivers/hf_render.py`) | **gọi spike #88** qua subprocess, venv của #88 |

Hai tỉ lệ chạy song song (hai tiến trình), `--workers 3` mỗi bên. `preview` = `-q draft`, `final` = `-q looks` (driver bọc `subprocess.run` như `hf_driver.py` của #95, không sửa spike). Driver đặt mốc 40–45 s rộng cho tiến trình con của #88 (nếu không #88 từ chối video 21,5 s); mốc thật do worker kiểm bằng ffprobe sau khi dựng: ngoài khoảng chỉ báo `too_short`/`too_long`, không kéo dài, không tua chậm, không cắt câu.

**Quyết định đã chốt (03/11):** (1) thiếu lời đọc CTA thì worker thêm cảnh `cta` đọc nguyên văn `cta.text`, `fact_refs` → `identity.name`, cảnh báo `cta_narration_derived`; (2) cảnh `proof`/`text_card` không có `stat_display`: không ghép từ `claims[0]/claims[1]` thành stat, không đọc `visual_plan.text` lên hình. Lượt 2: dùng layout chỉ-chữ `claim` (hiện claim nguyên văn); (3) `--input` bắt buộc, run (a) chỉ dựng `preview`.

### Bảng ánh xạ (layout #88: `hook`, `stat`, `feature_clip`, `cta`, và `claim` mới)

| M2 | Layout | Chữ trên hình lấy từ |
|---|---|---|
| `role=cta` | `cta` | tên sản phẩm, URL (`cta.destination` hoặc `identity.website`), `cta.text` (nút) |
| `visual_plan.kind=screen_recording` | `feature_clip` | `claims[0].text` làm tiêu đề, `claims[1:]` làm bước |
| `role=hook` | `hook` | `hook.text` (+ `hook.fact_refs`), ảnh trong `assets.json` |
| claim có `stat_display` | `stat` | `stat_display.{value, unit, label, scope}` (tuỳ chọn) |
| `kind=text_card`, có claim, không `stat_display` | **`claim`** (mới) | `claims[0].text` to, `claims[1:]` là ý phụ, nguyên văn, đúng thứ tự; mỗi chữ có `fact_refs` riêng |
| còn lại (`screenshot`, `product_asset`, `ai_generated_image`, `logo` không `screen_recording`/`stat_display`; `text_card` không có claim) | **lỗi rõ ở cảnh đó** | — |

`claim` chỉ nhận `text_card` có claim. Các `kind` cần hiện ảnh/logo vẫn báo lỗi thay vì âm thầm bỏ hình mà M2 đã yêu cầu.

## Thay đổi lượt 2

### 1. Phụ đề tự chia theo tỉ lệ (thay bản kịch bản sửa tay)

`cues.py` + bản vá `build_ass` trong `drivers/hf_render.py`:

- Câu vừa giới hạn (số dòng × ký tự từng tỉ lệ, đọc từ `LINE_CHARS`/`MAX_LINES` của #88: 9:16 = 2 × 24, 16:9 = 2 × 50) giữ nguyên một cue, đầu ra y như trước.
- Không vừa: chia thành ít cue nhất, mỗi cue vừa giới hạn; giữa các cách chia cùng số cue chọn cách các cue dài gần bằng nhau, ưu tiên ngắt sau dấu câu; chỉ ngắt ở ranh giới từ, không bỏ và không đổi chữ nào.
- **Thời gian mỗi cue chia theo tỉ lệ số ký tự** trong khoảng audio của câu (liền nhau, cue đầu bắt đầu đúng chỗ câu bắt đầu, cue cuối kết thúc đúng chỗ câu kết thúc). Đây là ước lượng vì VieNeu chưa có mốc từng chữ (ADR-0004): ranh giới cue có thể lệch vài trăm ms so với lời đọc.
- **Khác với #88:** docstring `subtitles.py` của #88 từ chối timing kiểu "chia theo số ký tự" ("không tạo timing giả"). P1-08 dùng nó có chủ đích, chỉ khi một câu không vừa giới hạn (chưa có cách nào khác ngoài việc bắt M2 viết lại phụ đề). #88 không bị sửa: driver gọi `build_ass` gốc của #88 trên plan/timeline đã chia.
- `render_report.json` ghi `subtitle_cues` ({segment_id: số cue}) từng tỉ lệ và cảnh báo `subtitle_split[<tỉ lệ>]`.
- Test: câu vừa không đổi; ghép các cue lại ra đúng chữ gốc; mỗi cue vừa giới hạn (cả với `wrap_caption` thật của #88 khi có spike); ưu tiên dấu câu; từ dài hơn dòng đứng riêng; cue liền nhau và còn phân biệt sau khi ASS làm tròn centi-giây; chạy trên 320 câu ngẫu nhiên không mất chữ.

Run4 gốc: `s01` (63 ký tự) ra **2 cue ở 9:16** ("Xử lý PDF miễn phí," / "riêng tư và mạnh mẽ ngay trong trình duyệt."), nguyên một cue ở 16:9. Bản sao `script.run4-subtitle-edited.json` và `run-a2-render_report.json` đã bỏ. `run-a1-render_report.json` giữ lại làm bằng chứng lỗi cũ.

### 2. Layout chỉ-chữ `claim` (sửa template #88)

**Đây là sửa template của #88**, nằm ở nhánh riêng `feat/render-v2-claim-layout` (commit `4e9f04f`, tách từ `origin/spike/p1-render-v2`; lượt 3 đã đưa lên nhánh #88 `spike/p1-render-v2`; không dùng worktree `p1-render-v2` cũ vì nó lệch origin 9/10 commit). Patch đầy đủ: `docs/report/script-to-mp4-2026-11/patches/render-v2-claim-layout.patch` (`git am`). Gồm:
- `template/layouts/claim.html` (mới): icon trung tính trong vòng tròn đồng tâm (cùng kiểu layout `stat`), eyebrow = tên sản phẩm, claim to, ý phụ dạng hàng có dấu tích; chỉ dùng class và biến của preset `dien-anh-toi-gian`.
- `plan.py`: thêm `"claim"` vào `Layout` (1 dòng, đúng như README của #88 hướng dẫn).
- `tests/test_core.py`: test có đủ 5 layout, và luật chữ trên hình (thiếu `fact_refs` ở claim hoặc ý phụ bị chặn); `README.md`: đổi "4 bố cục" thành 5.
- Test của spike: 26 xanh, ruff xanh.

Phía worker: nếu template #88 trên máy chưa có `claim.html`, cảnh báo lỗi `layout_missing_in_template` ở đúng cảnh kèm gợi ý nhánh. Trỏ `PRODUCE_RENDER_V2` vào worktree có layout mới để chạy.

**PR #97 phụ thuộc thay đổi này**: không có nó, run4 mặc định dừng ở `s05`. Lượt 3 (04/11): chốt đưa thẳng `4e9f04f` lên nhánh #88 `spike/p1-render-v2` (fast-forward từ `f0f705d`, push thường).

## Thay đổi lượt 3 (04/11): chất lượng hình

### 1. Giữ zoom khi phải cắt clip

Lượt 2 lấy clip từ đầu `parts` nên cả 3 cảnh clip mất zoom (`focus_dropped`): cảnh dài 3,6–4,0 s, còn `focus.source_t` nằm cuối đoạn (vd. `merge`: 16,0 trong 9,8–17,6).

`fit_parts(parts, scene_s, focus)` giờ cắt **một cửa sổ dài bằng cảnh trên dải các `parts` nối liền**:
- Có `focus`: cửa sổ chứa `focus.source_t`, đặt mốc zoom ở `min(60% cảnh, cảnh − 1,0 s)`. Số 1,0 s khớp kẹp của `slots.focus_time` (#88): zoom phải bắt đầu trước `cảnh − ZOOM_ANIM_S (0,9) − 0,1`. Cửa sổ bị kẹp theo mép clip khi focus sát đầu/cuối.
- Không có `focus`: lấy từ đầu như cũ.
- Mảnh ngắn hơn 0,05 s ở mép cửa sổ bị bỏ (tốc độ lệch ≤ 1,3%, #88 tự tính lại).
- Chỉ bỏ zoom khi `source_t` nằm ngoài đoạn gốc của nó (sai `assets.json`). Cảnh báo ghi số: `focus_dropped: focus.source_t 30.00 nằm ngoài đoạn gốc 9.80–17.60 (part 0); sửa assets.json`.

Kết quả run-b2 (`run-b2-render_report.json`): không còn `focus_dropped`. #88 tính mốc zoom:

| Cảnh | Asset | Đoạn đã cắt | Zoom lúc / dài cảnh |
|---|---|---|---|
| s02 | merge | 13,82–17,45 | 2,18 / 3,63 s (60%) |
| s03 | pagenum | 9,40–11,48 + 11,62–13,49 (bỏ đoạn 1,6–4,0) | 2,37 / 3,97 s (60%) |
| s04 | word-export | word-result 1,72–5,52 (bỏ đoạn export) | 2,28 / 3,80 s (60%) |

Đổi lại: cảnh `s03`, `s04` không còn đoạn đầu của thao tác (mở công cụ, bấm xuất), chỉ còn phần kết quả quanh vùng zoom. Muốn có cả hai thì cảnh phải dài hơn (kịch bản 40 s).

Test: 3 asset thật với độ dài cảnh của run-b2 (focus ở 60% ± 0,05 s, tổng = cảnh), cảnh ngắn 2 s (mốc 1,0 s), kẹp hai mép, bỏ mảnh vụn, `source_t` sai (bỏ zoom + lý do), clip ngắn hơn cảnh giữ nguyên. Test có điều kiện chạy plan qua `slots.clip_speed`/`slots.focus_time` thật của #88: không `PlanError`, mốc zoom lệch đích ≤ 0,06 s.

### 2. Khung hình cho coordinator

`D:\Code\AI-Content-Review\_refs\_analysis\p1-08\` (ngoài git): `16x9-*.png`, `9x16-*.png` cho hook, 3 × feature_clip, claim, cta; `run-b2-preview-16x9.mp4`. Khung `feature_clip` lấy ở mốc zoom + 1,1 s (zoom xong), các cảnh khác ở giữa cảnh. Đã xem bằng mắt: zoom vào đúng vùng thao tác ở cả 3 cảnh, chữ không tràn ở hai tỉ lệ.

### 3. Kiểm nhanh nguyên nhân chậm 2,2× so với #95 (hộp thời gian 30 phút)

| Giả thuyết | Cách kiểm | Kết quả |
|---|---|---|
| Giảm xung CPU | `Get-Counter` mỗi 3 s trong lúc chụp run-b2 (2 tỉ lệ song song) | `% Processor Performance` trung bình 127% (thấp nhất 114%, cao nhất 164%) của xung gốc 2,3 GHz, không rơi dưới xung gốc. CPU chỉ bận trung bình 39% (cao nhất 63%): bước chụp **không bị nghẽn CPU** |
| Nhiệt | `Thermal Zone Information` | Chỉ có vùng ACPI `TZ00`, đứng yên 28 °C suốt lần chạy: không phản ánh nhiệt lõi. **Chưa đo được** nhiệt lõi (cần HWiNFO/công cụ hãng, không cài thêm) |
| Phiên bản HyperFrames | `package.json`/lock của #88, `node_modules` | 0.8.173 ghim, lock khớp origin, cài 19/10. #95 gọi chính worktree `p1-render-v2` này (worktree claim dùng symlink `node_modules` tới đó): **cùng bản** |
| Bản Chrome | `~/.cache/hyperframes/chrome` | chrome-headless-shell 152.0.7977.30, tải 19/10, dùng chung: **cùng bản** |
| Chế độ GPU của Chrome | plan 40 s của #95, 16:9, draft, `--workers 3`, chạy tuần tự trên máy rảnh | `--browser-gpu off` (software gpu): chụp 328,3 s = **0,260 s/khung**; `on` (hardware gpu): 307,4 s = **0,243 s/khung** (trùng E3 hôm qua 307,6 s ở `auto` = hardware). GPU chỉ nhanh hơn 7% |

| Cập nhật Windows, gói nguồn | `Get-HotFix`, `powercfg`, log WindowsUpdateClient | Không có hotfix sau 14/10; gói nguồn vẫn Turbo. Chỉ có cập nhật Store/WinAppRuntime lúc 03/11 08:26, ngay trước các lần đo chậm (trùng thời điểm, chưa chứng minh là nguyên nhân) |

Kết luận: **máy đổi giữa 02/11 và 03/11**, không phải #95 đo sai. Mọi số đo tới 02/11 đều ~0,11–0,13 s/khung: #88 ngày 20/10 chụp 157–162 s cho 1263 khung (~0,125 s/khung, ở chất lượng mặc định, vốn chậm hơn draft; cả lần `--browser-gpu off`), #95 ngày 02/11 0,109. Mọi số đo từ 03/11 đều 0,24–0,26 s/khung trên cùng plan, cùng HyperFrames 0.8.173 và cùng Chrome 152. Đã loại trừ: phiên bản HyperFrames/Chrome, chế độ GPU, giảm xung dưới xung gốc, tải nền, hotfix Windows. Nguyên nhân gốc còn mở. Theo yêu cầu không sửa vì do môi trường; bước tiếp nếu cần: khởi động lại máy rồi đo lại plan 40 s một lần (cập nhật 03/11 có thể chưa áp dụng xong), kiểm driver GPU.

## Lượt 4 (05/11 và 09/11): kịch bản chỉnh tay của Khánh

Đầu vào: `feat/khanh-pr92-script` `68fb2a4`, `run3-2026-10-30/script.khanh-edited.json` + `input.json` cùng thư mục. Validator worker (contract `73f4df9`, và pin `609d93d` của #97): input 0 lỗi, script 0 lỗi. Asset: `script-to-mp4-2026-11/assets.pdfcraft-khanh.json` (4 clip `_refs/assets/pdfcraft/*.mp4` + ảnh AI cho hook).

### Tốc độ sau khi khởi động lại (05/11)

Đo lại plan 40 s của #88/#95 một lần, 16:9, `draft`, `--workers 3`, máy rảnh, ngay sau khởi động lại: chụp 371,8 s, tổng 406,5 s, 1263 khung = **0,294 s/khung**. So với #95 ngày 02/11: **0,109 s/khung**; E3 ngày 03/11: 0,244. Khởi động lại không đưa máy về mốc cũ (còn chậm hơn E3). Nghi vấn môi trường: cập nhật Store/WinAppRuntime 03/11 08:26 ngay trước các lần đo chậm (trùng thời điểm, chưa chứng minh). Theo quyết định 09/11: ghi nhận, không chặn, không tối ưu thêm trong PR này. Preview 2 tỉ lệ song song của kịch bản Khánh: chụp 456 s mỗi tỉ lệ, tổng ~534 s.

### Thay đổi code

| Việc | #97 (`produce/`) | #88 (`spike/p1-render-v2`) |
|---|---|---|
| CTA không có `destination` | Bỏ lấy `identity.website` thay. `destination: null` thì cảnh CTA chỉ có tên sản phẩm + `cta.text` | `cta.html`: `.url-pill` có `data-if="url"` |
| Ô clip to hơn | `Asset.crop_by_ratio` (`16:9`/`9:16`) chuyển nguyên vào plan | `Clip.crop_by_ratio` + `for_ratio()`; `compose` chọn crop theo tỉ lệ trước khi cắt clip và tính zoom. `feature_clip.html`: 16:9 lưới `1fr 480px` (ô clip ~60% ngang, chữ gọn bên phải); 9:16 ô clip tràn lề, ẩn hàng chip/bước, tiêu đề ngắn phía trên |
| Tiêu đề trùng phụ đề | Tiêu đề clip trùng ≥ 60% từ với lời/phụ đề cùng cảnh thì thay bằng `features[i].name` mà claim trỏ tới (có `fact_refs`, cảnh báo `title_shortened`); không có tên thì giữ claim, cảnh báo `title_duplicates_subtitle` | |
| Câu không có claim (09/11) | Câu dẫn không có claim (`s01-u02`, `s02-u04`): `fact_refs` rỗng + `exempt: "lead"`, cảnh báo `segment_without_claim`. **Không** mượn ref của claim khác (bản 05/11 có mượn, đã hoàn tác). Cảnh clip không có claim nào bị chặn `scene_without_claim` (không có tiêu đề có nguồn) | `Segment.exempt: "lead"`: chỉ khi có đánh dấu này mới được để `fact_refs` rỗng; thiếu đánh dấu vẫn bị chặn. Luật chữ trên hình không đổi |
| Hook không có `fact_refs` | Dùng `fact_refs` của chính câu đọc nguyên văn `hook.text` (contract `73f4df9`: hook đọc nguyên văn ở câu đầu và phải nằm trong claim đã đối chiếu). Không có câu khớp hoặc câu đó không có claim: chặn `hook_without_fact`. Bỏ nhánh "lấy ref của mọi câu trong cảnh" | |

Khác với quyết định 09/11 (điểm 3): quyết định xếp hook chung với câu dẫn không có claim. Hook khác hai câu kia: chữ hook **hiện trên hình** (luật #80 cần `fact_refs`), và câu đọc hook (`s01-u01`) có 3 claim riêng (`features[0]`, `[3]`, `[4]`). Nên hook dùng ref của chính câu đó, không mượn của câu khác. Làm đúng nghĩa đen (hook không có ref) cần thêm một lý do miễn mới cho chữ trên hình ở #88, tức nới luật #80. Chưa làm; cần coordinator chốt.

### Kiểm clip khớp lời (05/11, xem khung từng 0,25–1 s)

| Cảnh | Clip | Đoạn cắt + `focus` | Kết luận |
|---|---|---|---|
| s02 Merge | `pdfcraft-merge` | 9,8–21,8 s, focus 14,0 s | **Lệch lời.** Clip thêm nhanh một tài liệu đang mở, bấm **Append**, toast "Applied … in-place", kết quả 6 trang. Không có nút Merge, không sắp xếp, không tải xuống; lời `s02-u01` nói "sắp xếp thứ tự… bấm Merge… tải xuống". Coordinator báo Khánh sửa lời trên #92 |
| s03 Đánh số trang | `pdfcraft-pagenum` | 1,4–2,8 + 8,8–15,0 s, focus 13,5 s | Khớp: chọn vị trí Bottom R, Apply ở 11,0 s, toast, số "1" góc phải dưới ở 14,5 s |
| s04 Save & Export → Word | `pdfcraft-word-export` | 1,3–4,4 + **11,45**–12,25 s (09/11; trước 11,2), focus 3,0 s | Khớp: mở Save & Export, con trỏ trên "Export as Word (.docx)" 2,5–4,0 s; bỏ đoạn xử lý; toast "Export completed… .docx". 09/11 dời đoạn 2 để bỏ khung mờ của lớp Processing |
| s05 Kết quả Word | `pdfcraft-word-result` | **0–5,0 + 6,25–7,15 s** (09/11; trước 0–7,15), focus 4,0 s | Yếu: trình soạn Word cuộn tài liệu đã chuyển, không thấy tên tệp/.docx, không có thao tác sửa; chỉ đỡ một phần ý "DOCX có thể chỉnh sửa". 09/11 bỏ khoảng trống giữa hai trang (5,0–6,25 s) |

### Preview 05/11 (`68fb2a4`, trước khi sửa)

`status = out_of_range`: MP4 thật **51,833 s** cả hai tỉ lệ, ngoài 40–45 s (`too_long`; kịch bản đặt mục tiêu 42 s). Lời đọc VieNeu 11 câu ~49,9 s: s01-u01 3,68 · s01-u02 2,32 · s02-u01 7,68 · s02-u02 2,56 · s02-u03 3,60 · s02-u04 2,64 · s03-u01 7,68 · s04-u01 5,92 · s05-u01 8,40 · s06-u01 2,96 · s07-u01 2,48. Theo yêu cầu không cắt/kéo; Khánh rút ~7 s. Khung hình mỗi cảnh × 2 tỉ lệ: `_refs/_analysis/p1-08-final/` (ngoài git). Không chạy `final` (09/11: chờ Khánh sửa lời s02).

### Preview 09/11 (`68fb2a4`, sau khi dời s04/s05 và bỏ mượn ref) — bản chưa đạt thời lượng

Chạy lại chỉ để kiểm s04/s05 và plan có câu `exempt: "lead"`. Plan qua `RenderPlan` của #88 (`a7dc4f0`). `status = out_of_range`: MP4 thật **51,833 s** cả hai tỉ lệ (kịch bản không đổi). Cảnh báo mới: `segment_without_claim` (s01-u02, s02-u04), `hook_refs_from_segment` (s01-u01).

| | s04 | s05 |
|---|---|---|
| Clip / cảnh | 3,90 s / 6,03 s, tua **0,65×** | 5,90 s / 8,53 s, tua **0,69×** |
| Khung 25 / 50 / 75% | toàn giao diện / menu Save & Export mở / zoom "Export as Word (.docx)". Không còn khung mờ | trang bìa / chỗ nối trang + "1. Doanh thu theo tháng" / biểu đồ cột. Không còn khung trống |

Dựng: 16:9 602,1 s (chụp 535,1 s), 9:16 653,1 s (chụp 587,5 s), tổng 657,3 s (TTS trúng cache 0,8 s). Chậm hơn lượt 05/11 (456 s chụp). Khung: `_refs/_analysis/p1-08-final/r4b/` (ngoài git).

## Lượt 5 (09/11): hai lỗi produce do #92 run7/run8 phát hiện

Kịch bản M2 run7/run8 (#92 `0077cb7`, contract `4c5b72b`) qua validator nhưng `produce` `81f5108` không dựng được (mục C6 của `docs/report/m2-first-run-pdfcraft.md` trên #92). Sửa ở `163743e`:

| Lỗi | Sửa |
|---|---|
| `s04: [fact_ref_invalid] fact 'pricing.free_plan.value' không có chữ để trích`: path trỏ vào bool `true` | `produce/facts.py`: lá vô hướng (bool, số) ở cuối path dạng khoá lùi về nút cha, lấy `evidence`/`label`/`description` và `source_id` của nút đó. Id thành `src_01:pricing.free_plan.value`, chữ "Hoàn toàn Miễn phí". Không tự viết "Có"/"True". Phần tử mảng vô hướng (`sizes[0]`) vẫn báo lỗi |
| `s01: [asset_kind] hook cần asset kind=image (pdfcraft-merge)`: hook `kind: logo` trỏ clip, làm hỏng cả lần chạy | ~~`mapping.py`: cảnh báo `asset_kind_mismatch`, hook dựng chỉ chữ~~ **Đã hoàn tác ở lượt 6** (xem dưới): validator #83 `29f868a` chặn ở phía M2, `produce` giữ báo lỗi rõ ràng |

Test mới: `tests/produce/test_facts.py` (bool, số, phần tử mảng, path không có) và 2 test trong `test_mapping.py` (hook trỏ clip, claim trỏ `pricing.free_plan.value`). Lượt 6 đổi test hook trỏ clip thành kiểm lỗi `asset_kind`.

### Preview run7 nguyên bản (không sửa tay `visual_plan`)

Input `m2-first-run-pdfcraft/input.json` (#92), assets `assets.pdfcraft-khanh.json`, template #88 `a7dc4f0`.

| | Giá trị |
|---|---|
| `status` | `out_of_range` (`too_short`), đúng dự kiến; không kéo hay cắt |
| MP4 16:9 / 9:16 | **34,733 s** / **34,733 s** (khớp `predicted_s`) |
| Audio VieNeu | 8 segment, trúng cache 8/8 |
| Layout | s01 `hook` chỉ chữ, s02 `feature_clip`, s03 `feature_clip` (tua 0,80×), s04 `cta` |
| Cảnh báo (bản fallback của lượt 5, nay đã bỏ) | `asset_kind_mismatch` (s01), `title_duplicates_subtitle` (s02 100%, s03 79%: claim không trỏ `features[i]` có tên để thay), `clip_slowed` (s03), `predicted_too_short`, `subtitle_split[9:16]` × 7 |
| Dựng (CPU) | render 475,6 s, tổng 479,7 s |

Khung (`_refs/_analysis/p1-08-final/r5/`, ngoài git): s01 hiện logo + câu hook, **khung ảnh rỗng** vẫn vẽ ở bên phải (16:9) và bên dưới (9:16). Đây là hành vi sẵn có của layout hook khi không có ảnh (giống `hook_without_image`), thuộc template #88; chưa sửa. s04 CTA không URL.

## Lượt 6 (10/11): `final` cho kịch bản Khánh `4780fec`

Đầu vào: `feat/khanh-pr92-script` `4780fec`, `run3-2026-10-30/script.khanh-edited.json` + `input.json` (7 cảnh: s01 hook, s02–s05 clip, s06 claim, s07 CTA; mục tiêu 42 s). Asset: `assets.pdfcraft-khanh.json` (không đổi so với lượt 4b).

### Validator

| Validator | Kết quả |
|---|---|
| #92 `0077cb7` `worker.m2.validate.validate_script` (+ `validate_input`) | 0 lỗi |
| #83 `29f868a` `validate_contracts.py` (schema `p1-ac-03-script-vi.v1` + `validate_p1_vi_script_content`, context = `input.json`) | 0 lỗi |

### Kiểm lời–clip (xem khung clip nguồn, đối chiếu từng cảnh)

| Cảnh | Kết luận |
|---|---|
| s02 | **Khớp.** Clip 9,8–21,8 s: mở panel "Combine Files & Merge PDF", chọn tệp thứ hai, bấm **Append**, toast "Applied … in-place", tài liệu 6 trang. Lời "Chọn Append để thêm tệp PDF thứ hai; thay đổi được áp dụng ngay tại chỗ" đúng với thao tác |
| s03 | Khớp như lượt 4 (clip không đổi): chọn vị trí, Apply, số "1" góc phải dưới |
| s04 | **Khớp.** Đoạn 1: mở Save & Export, con trỏ trên "Export as Word (.docx)". Đoạn 2 từ 11,45 s: toast "Export completed… converted.docx", không còn khung mờ. Ghi chú: clip nguồn có 1 khung lộ thanh taskbar Windows (mốc chính xác ~12,05 s, không phải 11,95 s, xem lượt 7); không thấy trong MP4 final 16:9 ở các khung đã kiểm (27,9 / 28,3 / 28,6 s, lấy mẫu thưa, chưa quét hết) |
| s05 | **Khớp.** Tài liệu Word cuộn trong trình soạn thảo (bìa, tóm tắt, biểu đồ cột), không có khoảng trống giữa hai trang. Lời không nói tên tệp nên không lệch |

Không có cảnh lệch, nên không dừng.

### Thời lượng và dựng

| | Preview (`draft`) | Final (`looks`) |
|---|---|---|
| `status` | `out_of_range` (`too_short`) | `out_of_range` (`too_short`) |
| MP4 16:9 / 9:16 | **38,867 s** / **38,867 s** | **38,867 s** / **38,867 s** (h264 + aac, 1920×1080 / 1080×1920, 30 fps) |
| So với khung 40–45 s | thiếu 1,133 s | thiếu 1,133 s |
| Dựng (CPU) | render 593,2 s, tổng 619,3 s | render 574,1 s (chụp 508,0 s), 9:16 497,3 s (chụp 431,2 s); tổng 578,3 s |
| Dung lượng | | 6,09 MB (16:9), 5,42 MB (9:16) |
| TTS VieNeu | trúng cache 7/9, tổng hợp mới s02-u01 (4,64 s) và s05-u01 (3,68 s) | trúng cache 9/9 |

Không kéo dài, không cắt (`predicted_too_short: timeline 38,87 s ngoài 40–45 s`). Thời lượng cảnh: s01 3,83 · s02 11,17 · s03 7,80 · s04 6,03 · s05 3,80 · s06 3,10 · s07 3,13 s.

Cảnh báo (preview và final giống nhau): s01 `scene_asset_override` (ảnh `ai-paperwork` gán bằng assets.json vì script nêu `text_card`) và `hook_refs_from_segment` (dùng ref của `s01-u01`); s03 `clip_slowed` 0,97× + `title_shortened` (trùng 69%, dùng `features[3].name` "Đánh số trang"); s04 `clip_slowed` 0,65× + `title_shortened` (trùng 67%, "Chuyển PDF sang Word"); `predicted_too_short`; `subtitle_split[9:16]` × 5 (s02-u01, s02-u03, s03-u01, s06-u01, s07-u01). Không có `title_duplicates_subtitle`, không có lỗi cảnh.

Khung: `_refs/_analysis/p1-08-final/` (bản 05/11 đổi tên `*-r4`; MP4 final `khanh-4780fec-final-{16x9,9x16}.mp4` và `…-render_report.json`; ngoài git).

### Ghi chú chất lượng (chưa sửa, để Khánh quyết)

- Lời `s03-u01` có cụm "Clip minh họa chọn vị trí, bấm Apply rồi xem kết quả." Đây là lời mô tả clip, đọc lên trong voice nghe lạ.
- Thời lượng thiếu 1,133 s so với 40 s. Lời đọc 9 câu; muốn vào khung cần thêm lời hoặc đổi nhịp ở #92, không phải `produce` (theo quy tắc: không kéo/cắt).

### Hoàn tác fallback `asset_kind` (lượt 5)

Validator #83 `29f868a` đã chặn hook `kind: logo` trỏ clip ở phía M2, nên `mapping.py` trở lại `raise SceneError(sid, "asset_kind", …)` như `81f5108` (không fallback, không đổi asset). Test `test_hook_pointing_to_clip_is_a_clear_scene_error` kiểm lỗi có mã `asset_kind`, đúng cảnh `s01`, nêu `pdfcraft-merge`. Phần sửa fact_ref vô hướng (lượt 5) giữ nguyên.

## Lượt 7 (11/11): `final` cho kịch bản Khánh `d224316`

Khánh sửa lời `s03-u01` (bỏ "Clip minh họa…"): "Page Numbers thêm số trang và cho chỉnh vị trí, định dạng, số bắt đầu. Ví dụ chọn vị trí góc phải bên dưới rồi bấm Apply, số trang hiện ngay trên tài liệu." So với `4780fec` chỉ khác đúng trường `/scenes[2]/narration_segments[0]/text` (kiểm bằng so sánh JSON). Không đổi code `produce` trong lượt này; `assets.pdfcraft-khanh.json` và `input.json` giữ nguyên.

### Validator

| Validator | Kết quả |
|---|---|
| #92 `3679853` `worker.m2.validate.validate_script` (+ `validate_input`; mã lấy bằng `git archive`, không đụng worktree m2) | 0 lỗi |
| #83 `29f868a` `validate_contracts.py` (schema `p1-ac-03-script-vi.v1` + `validate_p1_vi_script_content`, context = `input.json`) | 0 lỗi |

### TTS và `predicted_s` (trước khi dựng)

Chạy các bước của `produce()` đến `build_timeline` (không dựng): chỉ `s03-u01` sinh mới, các câu khác trúng cache.

| Câu | r6 (`4780fec`) | r7 (`d224316`) |
|---|---|---|
| `s03-u01` | 7,68 s | **9,76 s** |
| Các câu còn lại | không đổi | không đổi |
| `predicted_s` | 38,867 s (`too_short`) | **40,933 s** (trong khung 40–45 s) |

Thời lượng cảnh (s): s01 3,83 · s02 11,17 · s03 **9,87** · s04 6,07 · s05 3,80 · s06 3,07 · s07 3,13. Không còn cảnh báo `predicted_too_short`.

### Kiểm lời–clip s03 (xem khung clip nguồn `pdfcraft-pagenum`, hai đoạn 1,4–2,8 s và 8,8–15,0 s)

**Khớp.** Đoạn 1: bảng Page Numbers mở, ô **Bottom R** đang chọn (nền xanh), Format Template "1 / 10". Đoạn 2: con trỏ ở Bottom R, bấm **Apply Changes**, toast "Applied "Page Numbers" in-place", số **"1"** hiện ở góc phải dưới trang. Lời "góc phải bên dưới … bấm Apply, số trang hiện ngay" đúng với thao tác. Ghi chú: cú bấm Bottom R nằm ở đầu đoạn 2 (con trỏ đã ở ô đó), không lệch lời.

Tốc độ clip s03: clip 7,60 s cho cảnh 9,87 s, **tua 0,77×** (r6: 0,97×). s04 vẫn 0,64× (clip 3,90 s cho cảnh 6,07 s; r6 ghi 0,65×, khác do làm tròn thời lượng cảnh 6,03 → 6,07 s).

### Dựng

| | Preview (`draft`) | Final (`looks`) |
|---|---|---|
| `status` | `ok` | `ok` |
| MP4 16:9 / 9:16 | **40,933 s** / **40,933 s** | **40,933 s** / **40,933 s** (h264 + aac, 1920×1080 / 1080×1920, 30 fps) |
| So với khung 40–45 s | trong khung | trong khung |
| Dung lượng | 7,51 MB / 6,41 MB | 6,24 MB / 5,52 MB |
| TTS VieNeu | trúng cache 9/9 (s03-u01 sinh ở bước dự đoán) | trúng cache 9/9 |
| Thời gian chạy | 08:48:36 → 08:58:25 | 08:58:44 → 09:08:21 |

Thời gian từng pha (giây, mỗi tỉ lệ một tiến trình HyperFrames, hai tiến trình chạy song song nên `render_s` = tỉ lệ chậm hơn):

| Pha | Preview 16:9 | Preview 9:16 | Final 16:9 | Final 9:16 |
|---|---|---|---|---|
| compile | 5,8 | 5,9 | 5,7 | 5,7 |
| extract | 8,4 | 8,3 | 8,1 | 7,9 |
| probe + setup | 2,3 + 1,4 | 2,3 + 1,4 | 2,2 + 1,1 | 2,3 + 1,1 |
| **capture** | **421,7** | **525,2** | **481,3** | **512,1** |
| encode | 6,1 | 5,3 | 17,2 | 15,7 |
| assemble | 0,4 | 0,3 | 0,4 | 0,4 |
| `rendered_in` | 446,0 | 548,0 | 515,8 | 544,5 |
| `render_wall` | 482,4 | 584,0 | 544,5 | 572,0 |

Tổng `produce`: preview 587,9 s (`render_s` 584,0), final 576,1 s (`render_s` 572,0). Mốc để so: r6 final tổng 578,3 s, preview 593,2 s. Máy đã loại trừ thư mục render khỏi Bitdefender (theo thông báo của người giao việc, không tự kiểm lại); số đo không cho thấy nhanh hơn r6 (chụp khung vẫn chiếm 88–95% thời gian, chênh giữa các lần chạy lớn hơn tác động nếu có).

Cảnh báo (preview và final giống nhau): s01 `scene_asset_override` và `hook_refs_from_segment` (như r6); s03 `clip_slowed` 0,77× + `title_shortened` (trùng 69%, "Đánh số trang"); s04 `clip_slowed` 0,64× + `title_shortened` (trùng 67%, "Chuyển PDF sang Word"); `subtitle_split[9:16]` × 5 (s02-u01, s02-u03, s03-u01, s06-u01, s07-u01). Không có lỗi cảnh, không còn `predicted_too_short`.

### Taskbar ở 9:16 quanh s04

Lấy khung dày 0,25 s của MP4 final 9:16 từ 23,0 đến 32,0 s (s04 nằm ở 24,87–30,93 s), ghép lưới 9×4, thêm 6 khung đáy ô clip ở độ phân giải gốc (24,9 · 26,5 · 27,9 · 28,3 · 28,6 · 30,8 s). **Không thấy thanh taskbar** ở khung nào: đáy ô clip chỉ là trang tài liệu, thanh cuộn và nền tối.

Kiểm thêm theo nguồn, vì lượt 6 ghi sai mốc: clip nguồn `pdfcraft-word-export` lộ taskbar Windows từ khoảng **12,05 s** (khung 11,95 s chưa có, 11,85 s chưa có), và 12,05 s nằm **trong** đoạn 2 được dùng (11,45–12,25 s). Với tua 0,64×, khung đó ứng với ~30,65 s của MP4. Đã xuất **từng khung 30 fps** từ 29,8 đến 31,0 s ở cả 9:16 và 16:9: không khung nào có taskbar. Lý do quan sát được: ô clip trong layout chỉ hiện vùng trên của màn hình nguồn (thanh công cụ, trang tài liệu), toast "Export completed" ở góc dưới cũng không hiện, nên phần đáy màn hình, nơi có taskbar, nằm ngoài vùng nhìn thấy. Đây là kết quả của vùng crop/zoom hiện tại; đổi `crop`/`focus` của clip này thì phải kiểm lại.

Khung và MP4: `_refs/_analysis/p1-08-final/` (bản `4780fec` đổi tên `*-r6`, giữ `*-r4`; MP4 mới `khanh-d224316-final-{16x9,9x16}.mp4`, `khanh-d224316-final-render_report.json`; thêm `clipcheck-s03a/b-r7.jpg`, `taskbar-9x16-23-32s-r7.jpg`, `taskbar-{9x16,16x9}-30fps-29.8-31.0s-r7.jpg`, `taskbar-source-11.85-11.95-12.05s-r7.jpg`; ngoài git).

## Chạy thật (a): `run4-2026-10-30/script.json` (kịch bản gốc, không sửa tay)

Đầu vào: 4 clip `_refs/assets/pdfcraft/*.mp4` + 1 ảnh AI `p1-render-v2/local/ai/paperwork-s1.jpg`, cấu hình ở `script-to-mp4-2026-11/assets.pdfcraft.json`. `preview`, `--on-unsupported fail` (mặc định), không cần `skip`.

Kết quả (`run-b1-render_report.json`): 6 cảnh dựng đủ (hook, 3 × feature_clip, **claim**, cta), `status = out_of_range`: **21,467 s ngoài 40–45 s** (`too_short`) vì script M2 chỉ ~19 s ước tính; ffprobe khớp timeline dự kiến (lệch 0,000 s cả hai tỉ lệ). MP4 ở `D:\tmp\p1-script-to-mp4\run-b1\`:
- `script-preview-16x9.mp4` (1920×1080, 21,467 s)
- `script-preview-9x16.mp4` (1080×1920, 21,467 s)

Khung hình (hook, demo, cta + cảnh `claim` + cue đầu của 9:16): `D:\tmp\p1-script-to-mp4\frames\` (`16x9-*.png`, `9x16-*.png`). Đã xem bằng mắt: chữ không tràn, `claim` hiện nguyên văn hai claim, phụ đề 9:16 hai dòng. Chưa xem chuyển động toàn video.

### Số liệu và so với #95 (lượt 2, 1 mẫu mỗi mục, máy rảnh)

| Bước | Giá trị | Ghi chú |
|---|---|---|
| Validate + map | 0,03 s | |
| TTS VieNeu ONNX CPU, 6 câu | **17,7 s** (nạp model 12,6 s + 1 câu miss) | 5/6 trúng cache (`s05` là câu mới vì lượt 1 bỏ cảnh này) |
| HyperFrames draft, 2 tỉ lệ song song, `--workers 3` mỗi bên | 16:9 **258,1 s** (chụp 190,1 s), 9:16 **252,6 s** (chụp 183,7 s) | 644 khung mỗi tỉ lệ → 0,295 / 0,285 s/khung |
| FFmpeg (voice + phụ đề) | 3,1 s / 4,5 s | |
| ffprobe | 3,3 s | |
| Tổng một lần chạy | **279,2 s** | |
| RAM đỉnh HyperFrames | 5,4 GB mỗi tiến trình | có thể tính trùng khi chạy song song |

**Điều tra "chậm hơn #95" (mục 3 của yêu cầu).** Chạy ba phép đo tuần tự, cùng máy, cùng cấu hình `draft`, `--workers 3`:

| Phép đo | Video | Khung | Chụp khung | Thời gian dựng | s/khung | Ghi chú |
|---|---|---|---|---|---|---|
| **#95** (02/11), plan 40 s, 1 tỉ lệ | 42 s | 1260 | 137 s | 152,7 s | **0,109** | số trong `pipeline-timing-2026-11.md` |
| **E3 đối chứng** (hôm nay), cùng plan 40 s của #88/#95, 16:9 một mình | 42,1 s | 1263 | **307,6 s** | 348,1 s | **0,244** | CPU nhàn rỗi 0,4% trước khi chạy |
| **E2**, run4, 16:9 một mình | 21,5 s | 644 | 139,4 s | 176,0 s | 0,216 | |
| **E1**, run4, 2 tỉ lệ song song | 21,5 s | 644 | 190,1 s | 258,1 s | 0,295 | |

Kết luận có chứng cứ:
1. **Chậm hơn #95 là do môi trường, không phải do module này hay nội dung run4.** Chạy lại đúng plan 40 s của #95 ngay hôm nay trên máy rảnh vẫn chậm 2,2× (0,244 so với 0,109 s/khung). Các phase không liên quan tới số khung cũng chậm theo: compile 11,1 s, probe 5,3 s (lượt 2 của tôi đo 4,2 s và 1,7 s khi máy bận).
2. **Nội dung run4 không nặng hơn:** 0,216 s/khung (run4) ≈ 0,244 s/khung (plan #95) trong cùng điều kiện. Nên cảnh clip, ảnh Ken Burns của hook, số cảnh không phải nguyên nhân.
3. **Chạy song song hai tỉ lệ:** mỗi tỉ lệ chậm thêm khoảng 36% mỗi khung (0,295 so với 0,216), nhưng tổng 258 s cho hai tỉ lệ so với 2 × 176 = 352 s tuần tự (nhanh hơn 27%). Giữ song song.
4. **Nguyên nhân gốc của hệ số 2,2× so với 02/11: chưa xác định.** Đã loại trừ: đang dùng pin (máy cắm AC, gói Turbo), tải CPU nền (0–5%), RAM (trống 5,4–6,9 GB, tương đương lúc đo #95). Chưa kiểm: nhiệt độ/giảm xung CPU, chế độ GPU của Chrome (`hardware gpu` ở cả E2/E3), phiên bản HyperFrames, quét Windows Defender. Không có số đo `draft` nào hôm nay tái lập được 0,109 s/khung.

Lượt 1 (kết quả cũ) so lượt 2 chênh 96 s cùng đầu vào cũng nhất quán với máy dao động lớn.

## Việc M2/#83 cần làm (gửi Định)

1. **M2 cần sinh lời đọc CTA.** Script chỉ có `cta.text` ("Xem thêm thông tin", `destination: null`) ở cấp trên cùng, không có cảnh/câu thoại. Worker tạm đọc nguyên văn `cta.text` (cảnh `s06`, cảnh báo `cta_narration_derived`).
2. ~~`stat_display` bắt buộc~~ **Không còn chặn.** `stat_display` giờ là tuỳ chọn: có thì cảnh dùng layout `stat` (số liệu nổi bật), không có thì `text_card` dùng layout `claim` (chữ). Sinh `stat_display` khi có số liệu đáng nhấn vẫn đẹp hơn.
3. ~~`subtitle_text` ngắn hơn cho 9:16~~ **Không còn chặn.** Renderer tự chia cue. M2 không cần biết giới hạn dòng. Việc còn lại phía M2/#73: mốc thời gian từng chữ để cue khớp lời đọc thay vì ước theo số ký tự.
4. **Cảnh hook `text_card` không có ảnh.** Layout `hook` cần ảnh; M2 không nêu `asset_id`. Run (a) gán ảnh qua `scene_assets` trong `assets.json` (cảnh báo `scene_asset_override`). Không có ảnh thì khung ảnh để trống (cảnh báo `hook_without_image`).
5. Dữ liệu biên tập clip (`crop`, đoạn clip, vùng zoom `focus`) M2 không sinh; hiện nằm trong `assets.json` thay cho BE Storage. Cần quyết định ai sở hữu dữ liệu này khi có Storage.
6. `layout stat` mới được kiểm bằng test (plan qua `RenderPlan` của #88), **chưa dựng thật**: run4 không có `stat_display`. `claim` và `cta` đã dựng thật (cta chỉ với `chips` rỗng).

## Khác với render thủ công #88 (`pdfcraft-40-45s.json`)

| | #88 viết tay | Đường ghép tự động (run4) |
|---|---|---|
| Độ dài, cảnh | 7 cảnh, 16 câu, 40–45 s | 6 cảnh, 6 câu, 21,5 s |
| Layout | hook, 2 × stat, 3 × feature_clip, cta | hook, 3 × feature_clip, claim, cta (không có stat vì M2 không có `stat_display`) |
| Chữ trên hình | viết tay, có chip, bước, callout | `hook.text`, `claims[].text`, tên sản phẩm; chip và callout để trống |
| Zoom vào vùng thao tác (`focus`) | có | có ở cả 3 cảnh clip từ lượt 3 (lượt 2: bị bỏ cả 3, `focus_dropped`) |
| Clip theo cảnh | đoạn tay chọn cho vừa lời | cửa sổ dài bằng cảnh trên các `parts` nối liền, chứa `focus` ở ~60% cảnh, tốc độ 1,0 |
| CTA | "Dùng thử ngay" + 2 chip | "Xem thêm thông tin", đọc thành tiếng, không chip |
| Phụ đề | lời đọc, mỗi câu một cue | `subtitle_text` của M2 (rút gọn so với lời đọc ở 3/5 cảnh); câu dài chia cue theo tỉ lệ ký tự |
| Nội dung clip | | clip `merge`/`pagenum` quay tài liệu "Acme Demo", không liên quan tiêu đề; chỉ là clip nguồn có sẵn |

## Khác với prompt

- Thêm tham số bắt buộc `--input` (cần PKB để tra `fact_refs`).
- Thêm `--on-unsupported fail|skip` (mặc định `fail`). Run4 không còn cần `skip`; vẫn dùng cho kịch bản có cảnh cần ảnh/logo mà #88 chưa có layout.
- Kiểm phụ đề trước khi chụp hình: dựng thử ASS trong driver (lỗi hiện sau vài giây, không phải sau ~4 phút chụp), không sửa spike.
- Sửa template #88 (layout `claim`): theo yêu cầu lượt 2, ở nhánh riêng (xem trên). Prompt gốc ghi "không sửa template #88".

## Đồng bộ với #92

#92 có thêm commit `398d5ae` (đồng bộ contract #83 lên `fb4f0ed`, thêm `content_context.video_description` tuỳ chọn ở input) mà #95 và #97 chưa có. Không ảnh hưởng `produce` (chỉ thêm trường input tuỳ chọn); cần rebase #95 rồi #97 khi gộp.

## Việc còn lại

- (b) Kịch bản Khánh `d224316`: **đã chạy `final`** (lượt 7): validator #92 `3679853` và #83 `29f868a` 0 lỗi, lời–clip s03 khớp, MP4 **40,933 s** trong khung 40–45 s (cả 2 tỉ lệ), không kéo/cắt. Lượt 6 (`4780fec`, 38,867 s, `too_short`) và cụm "Clip minh họa…" ở s03 đã được Khánh xử lý bằng `d224316`.
- Đo `preview` vs `final` trên cùng đầu vào (lượt 7): render_wall 482,4 s vs 544,5 s (16:9), 584,0 s vs 572,0 s (9:16); chụp khung (capture) chiếm 88–95%, chênh giữa các lần chạy lớn hơn chênh giữa hai chế độ. Máy đã loại trừ thư mục render khỏi Bitdefender; chưa thấy nhanh hơn r6.
- Coordinator đề xuất (comment #97, 09/11): hook giữ ref của chính câu đọc nó, không nới luật #80 (chờ Định xác nhận phía contract); thanh địa chỉ trong `feature_clip` **giữ** (domain thật của trang đang quay, không phải CTA).
- Layout hook không có ảnh vẫn vẽ khung ảnh rỗng (lượt 5). Đề xuất #88 ẩn khung hoặc giãn chữ khi thiếu `image`.
- Dựng thật một cảnh `stat` (cần `stat_display` từ M2 hoặc script chỉnh tay).
- Nguyên nhân hệ số 2,2× so với số #95: đã loại trừ phiên bản, Chrome, chế độ GPU, giảm xung (lượt 3); còn mở, cần đo lại bằng `bench.py` của #95.
- ~~Đưa layout `claim` vào #88~~: xong ở lượt 3 (`4e9f04f` trên `spike/p1-render-v2`).
- Cue phụ đề khớp lời đọc thật cần mốc từng chữ từ TTS.
- Port `drivers/` vào worker khi #73/#88 merge (hiện bắt buộc có hai worktree spike trên máy).

## Test

`tests/produce/`: 88 test (lượt 5: fact_ref vô hướng lùi về nút cha; lượt 6: hook trỏ asset không phải ảnh báo lỗi `asset_kind` rõ ràng; lượt 4: CTA không có URL, tiêu đề rút gọn, crop theo tỉ lệ, câu dẫn `exempt: "lead"`, hook lấy ref của câu đọc nó; lượt 3 thêm test cửa sổ cắt clip theo `focus` và test đối chiếu `slots.focus_time` của #88) (không cần mạng/GPU/trình duyệt): ánh xạ trên script run4 thật (gồm `claim`, `stat_display`, cảnh không hỗ trợ, template thiếu layout), chia cue và thời gian cue, phần ghép trong driver bằng đối tượng giả cùng hình dạng, timeline so với tính tay, cache key, model nạp một lần, kiểm thời lượng, cả đường ghép với runner giả. Hai test nạp `plan.py`/`subtitles.py` thật của #88 (nếu có spike trên máy; test `RenderPlan` bỏ qua khi spike chưa có layout `claim`). Toàn bộ worker (lượt 5, `P1_RENDER_V2` trỏ vào worktree `p1-render-v2-claim`): 357 test xanh, không bỏ qua; ruff, format, pyright xanh.
