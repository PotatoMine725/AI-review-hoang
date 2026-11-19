# P1-09 — Dựng song song theo cảnh + cache MP4 cảnh — Báo cáo

- **Prompt:** `_refs/drafts/2026-11-10_msg-agent-p1-09-render-parallel.md` · **Ngày:** 2026-11-12 · **Người viết:** coding agent (Claude Code)
- **PR:** draft, nhánh `feat/p1-render-parallel`, chồng lên #97 (`feat/p1-script-to-mp4`, chồng lên #95) · **Issue:** #67
- **Máy đo:** i7-12700H (20 luồng), RTX 4050 6 GB, 16 GB RAM, FFmpeg 8.0, Node 24, HyperFrames 0.8.173 (ghim), Windows 11, nguồn điện AC. Một máy, không lặp lại trên máy khác.
- **Đầu vào:** kịch bản Khánh (`D:/tmp/p1-08-r7/final/script-final.json`, 7 cảnh, 1228 khung = 40,93 s ở 30 fps) và plan PDFCraft 42,1 s của #88 (7 cảnh, 1263 khung).

## Kết luận ngắn

1. **Tính năng chạy được và đúng ở mức khung hình.** `--render-mode parallel` chia theo cảnh, dựng bằng pool tiến trình HyperFrames, nối bằng concat `-c copy`, rồi chạy `finalize` của #88. Số khung, fps, codec, thời lượng giống bản tuần tự ở cả hai kịch bản và cả hai tỉ lệ; audio giống hệt từng bit (md5 bằng nhau).
2. **Mặc định giữ `sequential`, `parallel` là tuỳ chọn** (đã được chấp nhận để merge). Lý do: dựng 2 tỉ lệ final, `parallel` không nhanh hơn (154,8 s so với 158,7 s) mà đỉnh RAM cao hơn (9,5 GB so với 8,2 GB, máy chỉ còn 0,6 GB trống). Về hình ảnh: các cụm PSNR thấp ở cảnh `<video>` **không phải lỗi của `parallel`**. Phép thử so với khung gốc của clip (mục Tương đương) cho thấy `parallel` chọn đúng khung, còn đường tuần tự lệch 1 khung ở các cảnh có mốc bắt đầu làm tròn `.4f` không tròn.
3. **`parallel` có ích ở hai chỗ:** dựng **một** tỉ lệ (draft 16:9: 187 s → 78 s với P=4, 70 s với P=6) và **cache** (chạy lại không đổi 14 s so với 158 s; sửa lời một cảnh còn 79 s).
4. **Đính chính chẩn đoán "node đơn luồng" của #95/#97:** chẩn đoán đúng một nửa. Một tiến trình HyperFrames bị trần ~5,5–6,6 khung/s dù `--workers` 1 hay 3 (draft 16:9: P=1 5,5 khung/s, tuần tự `--workers 3` 6,6 khung/s). Nhưng đó không phải trần của máy: nhiều tiến trình cộng dồn tới ~16–17,5 khung/s (P=4: 15,7; P=6: 17,5) với CPU chỉ 36–50% rồi bằng phẳng; nguyên nhân của trần máy chưa xác định. Hệ quả: một tỉ lệ thì `parallel` nhanh gấp 2,4–2,7×; hai tỉ lệ thì đường tuần tự (6 Chrome cùng lúc) đã chạm trần nên không còn gì để thêm. Xem mục "Đính chính chẩn đoán".
5. **Số 576 s → 158,7 s:** final 2 tỉ lệ cùng kịch bản Khánh, cùng đường tuần tự: 576,1 s ở lượt 7 của #97 (10/11) so với 158,7 s (trung vị 3 lượt, 12/11). Hiệu số này **không do P1-09** (cả hai là đường tuần tự, mã dựng không đổi) mà do trạng thái máy khác nhau giữa hai ngày (xem mục "So với số đo của #97").
6. **Quy trình đề xuất:** preview 16:9 dựng song song (`--ratios 16:9 --render-mode parallel`, draft: 187 s → 70–78 s); final 2 tỉ lệ dựng tuần tự (`--render-mode sequential`, 158,7 s).

## Đã làm

| Phần | Vị trí |
|---|---|
| Driver 4 chế độ `full / prepare / scene / finalize`: chia cảnh (plan con + timeline con `start_f = 0`), gọi `compose` thật của #88 trên plan con, khoá cache, ghi cache nguyên tử, concat, `finalize`, `check_output` | `produce/drivers/hf_render.py` (chạy trong venv của #88, không sửa #88) |
| Điều phối: hàng đợi job (cảnh × tỉ lệ), pool `ThreadPoolExecutor`, cảnh dài nhất chạy trước, `finalize` của một tỉ lệ chen lên đầu hàng ngay khi cảnh cuối của nó xong, giới hạn theo RAM, huỷ khi một job lỗi | `produce/render.py` |
| Runner có `cancel`, diệt cả cây tiến trình (`taskkill /T /F` trên Windows, `killpg` trên POSIX), timeout ném `TimeoutExpired` sau khi diệt cây | `produce/runner.py` |
| Cấu hình `PRODUCE_RENDER_MODE`, `PRODUCE_RENDER_JOBS` (4), `PRODUCE_RENDER_JOB_RAM_MB` (1900), `PRODUCE_RENDER_RAM_RESERVE_MB` (2048), `PRODUCE_RENDER_CACHE`; cờ CLI `--render-mode`, `--render-jobs`, `--no-cache` | `config.py`, `__main__.py`, `.env.example` |
| `render_report.json` có khối `render`: `mode, jobs, jobs_requested, cache, cache_hits, cache_misses, prepare_s, scenes_phase_s, scene_jobs` (thời gian từng job, trúng cache hay không) | `pipeline.py` |

**Khoá cache** = sha256 của cây thư mục làm việc sau `compose` (đường dẫn tương đối + nội dung `index.html`, `template/`, `media/`; bỏ `video.mp4`, `hyperframes.log`, `subs.ass`) + tỉ lệ + chất lượng + fps + dấu vân tay engine (phiên bản HyperFrames, hash `package-lock.json`, phiên bản Chrome). Mốc tuyệt đối không nằm trong khoá vì plan con có `start_f = 0`. Thư mục cache `~/.cache/.../render-scenes` (ngoài repo), ghi qua file tạm + `os.replace`.

**Nối:** concat demuxer `-c copy`; nếu số khung lệch thì encode lại một lần và ghi lý do vào report. Cả hai kịch bản đều đi nhánh `copy`, đúng 1228 và 1263 khung.

**RAM:** `effective_jobs = min(render_jobs, số job, (RAM trống − dự phòng) // RAM mỗi job)`. Đo được 1,7–1,9 GB mỗi tiến trình (node + Chrome + ffmpeg), nên mặc định là 1900 MB (prompt ước 1–1,5 GB: thấp hơn thực tế).

## Tương đương (parallel so với sequential)

Cách đo: dựng cùng plan hai lần (draft), `ffmpeg psnr` từng khung, gộp theo cảnh. Đường cơ sở: tuần tự so với tuần tự (cùng plan, hai lần chạy) để biết nhiễu giữa 2 lần chạy.

| Chỉ tiêu | Kịch bản Khánh | Plan PDFCraft |
|---|---|---|
| Số khung / fps / codec / thời lượng | 1228 / 30 / giống / giống, 2 tỉ lệ | 1263 / 30 / giống / giống, 2 tỉ lệ |
| Audio (md5) | giống hệt | giống hệt |
| Concat | `-c copy` | `-c copy` |

PSNR theo cảnh (dB; "<40" là số khung dưới 40 dB):

| Plan · tỉ lệ | Cảnh không `<video>` (min) | Cảnh có `<video>`: ngoại lệ |
|---|---|---|
| Khánh 16:9 | s01 43,1 · s06 40,7 · s07 41,5 | s04: khung đầu 9,2 dB, 4 khung <40; các cảnh `<video>` còn lại ≥ 41,3 |
| Khánh 9:16 | s01 42,3 · s06 43,9 · s07 40,9 | s04: khung đầu 8,3 dB, 6 khung <40; các cảnh `<video>` còn lại ≥ 43,2 |
| PDFCraft 16:9 | s01 42,9 · s02 40,8 · s06 40,6 · s07 41,4 | **s03: min 14,4, 38 khung <40 · s05: min 11,2, 13 khung <40**; s04 ≥ 44,1 |
| PDFCraft 9:16 | s01 42,9 · **s02 39,9 (4 khung <40)** · **s06 39,9 (15 khung <40)** · s07 41,0 | **s03: min 17,3, 32 khung <40 · s05: min 14,1, 13 khung <40**; s04 ≥ 43,7 |
| Đường cơ sở tuần tự↔tuần tự (PDFCraft) | ≥ 45,5 | ≥ 43,9 mọi cảnh |

Đối chiếu tiêu chí của prompt:

- **Cảnh không `<video>` cần ≥ 40 dB.** Khánh: đạt. PDFCraft 16:9: đạt. **PDFCraft 9:16: lọt xuống 39,9 dB ở s02 và s06 (trung bình cảnh 40,5 và 41,8), chưa đạt hoàn toàn**, dù chênh 0,1 dB. Đường cơ sở cho các cảnh này ≥ 45,5 dB, nên mức thấp hơn đó là khác biệt có hệ thống giữa hai đường dựng chứ không phải nhiễu giữa 2 lần chạy.
- **Cảnh có `<video>`:** s03 và s05 của PDFCraft có các cụm khung PSNR rất thấp (thấp nhất 11,2 dB), đường cơ sở ≥ 43,9 dB nên là khác biệt có hệ thống giữa hai đường. Nguyên nhân và đường nào đúng được xác định ở mục "Phép thử so với khung gốc của clip" ngay dưới.
- **s04 của Khánh (khung đầu 8–9 dB):** do khung đầu cảnh. Ở bản tuần tự, khung đầu s04 còn hiện khung cuối s03 (nhiều khả năng do mốc `data-start` làm tròn lên khi ghi `.4f`, chưa kiểm), bản song song hiện đúng khung đầu s04. Xem ảnh ranh giới: không giật nền, không mất animation vào cảnh ở bản song song.

### Phép thử so với khung gốc của clip

Mục đích: biết đường nào chọn đúng khung của `<video>`. Cách làm (`render-parallel-2026-11/clipmatch.py`, kết quả `clip-match-results.json`): với cảnh có clip, lấy **clip đã chuẩn bị** (`clip-*.mp4` do `prepare_clip` của #88 sinh, đúng số khung của cảnh, khung k của clip phải hiện ở khung k của cảnh) làm khung gốc; cắt ô clip của MP4 (920×670 tại 138,175, ở 16:9), co clip về cùng cỡ, rồi tính PSNR từng khung của cảnh so với khung `f+d` của clip, d từ −3 đến +3. Đường nào chọn đúng khung thì PSNR trung bình cao nhất ở d=0.

| Cảnh (mốc bắt đầu) | Mốc `.4f` so với mốc thật | Đường tuần tự: d tốt nhất; số khung gần d=0 hơn / gần d=−1 hơn | Đường song song: d tốt nhất; gần d=0 / gần d=−1 |
|---|---|---|---|
| s03 (khung 320 = 10,6667 s) | làm tròn **lên** | **−1**; 0 / 23 | **0**; 19 / 3 |
| s04 (khung 540 = 18,0 s) | tròn đúng | 0; 49 / 6 | 0; 49 / 6 (giống hệt) |
| s05 (khung 767 = 25,5667 s) | làm tròn **lên** | **−1**; 1 / 8 | **0**; 9 / 0 |

(Phần còn lại là khung mà d=0 và d=−1 không phân biệt được trong 0,5 dB vì clip đứng yên; PSNR tuyệt đối với khung gốc chỉ ~20–26 dB vì ánh xạ ô clip chỉ gần đúng, nên chỉ so sánh tương đối giữa hai đường.)

**Kết luận:** đường song song chọn đúng khung (d=0 ở cả ba cảnh). Đường tuần tự **lệch 1 khung** (cảnh chậm một khung) ở cảnh có mốc `.4f` làm tròn lên (s03, s05) và đúng ở cảnh có mốc tròn (s04, giống hệt song song). Cơ chế: `compose` ghi `data-start` với 4 chữ số, 10,666666… thành 10,6667 (muộn hơn 0,00003 s), nên video bắt đầu muộn một chút và khung hiện ra ở thời điểm lấy mẫu là khung trước. Đường song song dùng plan con có `start_f = 0` nên không dính. Các cụm PSNR thấp ở s03/s05 nằm đúng ở đoạn clip chuyển động nhanh (cuộn trang), nơi lệch 1 khung thấy rõ trong số đo. 1 khung = 33 ms, mắt thường không thấy.

Khớp với toàn bộ số đo PDFCraft: các cảnh có mốc bắt đầu `.4f` **tròn đúng** (s01 = 0, s04 = 18,0, s07 = 38,4) khớp giữa hai đường (min 42,9 / 44,1 / 41,4 dB); các cảnh còn lại (s02 làm tròn xuống, s03/s05/s06 làm tròn lên) đều lệch, kể cả cảnh không `<video>` s02 và s06 ở 9:16 (39,9 dB, vì mọi animation lệch 0,00003 s ở bản tuần tự). Nên việc dưới 40 dB ở s02/s06 cũng là lệch của đường tuần tự, không phải lỗi của `parallel`. Chưa chạy phép thử khung-gốc riêng cho hai cảnh này (không có clip), nên đây là suy luận từ cùng cơ chế.


## Tốc độ

Cách đo: `bench_render.py` (ngoài repo) gọi `render_ratios` với `use_cache=False`, các cấu hình xen kẽ giữa các lượt, 3 lượt mỗi cấu hình; một sampler PowerShell lấy mẫu mỗi 0,4 s: RAM (working set) của `node/chrome-headless-shell/ffmpeg` sinh ra sau mốc bắt đầu, CPU tổng (trung bình), RAM trống nhỏ nhất của máy. Sau mỗi lượt không còn `chrome-headless-shell` nào (mọi lượt `chrome_left = 0`). Giới hạn RAM tắt khi đo (để cấu hình P đúng như tên).

**Draft (`-q draft`), 16:9, kịch bản Khánh, 1228 khung:**

| Cấu hình | Trung vị | Min–max | RAM đỉnh | RAM trống nhỏ nhất | CPU TB | So với tuần tự |
|---|---|---|---|---|---|---|
| sequential (`--workers 3`) | 187,3 s | 173,8–194,9 | 4,0 GB | 4,7 GB | 20% | 1,00× |
| parallel P=1 | 223,0 s | 219,7–258,8 | 1,9 GB | 5,7 GB | 15% | 0,84× |
| parallel P=2 | 132,0 s | 127,6–138,6 | 3,7 GB | 4,6 GB | 22% | 1,42× |
| parallel P=4 | 78,3 s | 76,9–79,6 | 6,9 GB | 2,4 GB | 36% | 2,39× |
| parallel P=6 | 70,2 s | 70,1–70,2 | 7,9 GB | 1,8 GB | 50% | 2,67× |

- P=1 chậm hơn tuần tự vì mỗi cảnh phải khởi động Chrome + `compose` lại, và chỉ có 1 worker.
- P=6 chỉ nhanh hơn P=4 khoảng 10%: đường găng là cảnh dài nhất (s02, 335 khung, ~66 s/job), thêm tiến trình không rút ngắn được. P=6 được đo ở một phiên sau các cấu hình còn lại (không xen kẽ cùng lượt với sequential), nên so sánh P=6 với tuần tự chịu thêm sai số theo thời điểm.
- Thông lượng đỉnh: 1228 khung / 70 s ≈ 17,5 khung/s.

**Final (`-q looks`), 2 tỉ lệ, 3 lượt (xen kẽ), kịch bản Khánh, không cache:**

| Cấu hình | Trung vị | Min–max | RAM đỉnh | RAM trống nhỏ nhất | CPU TB |
|---|---|---|---|---|---|
| sequential (2 tỉ lệ chạy đồng thời, `--workers 3` mỗi bên) | 158,7 s | 153,5–159,0 | 8,2 GB | 1,7 GB | 40% |
| parallel P=2 | 257,1 s | 254,6–258,4 | 5,1 GB | 3,9 GB | 26% |
| parallel P=3 | 189,9 s | 188,4–190,6 | 7,6 GB | 1,8 GB | 35% |
| parallel P=4 | 154,8 s | 153,9–155,1 | 9,5 GB | **0,6 GB** | 44% |

P tốt nhất là 4 nhưng chỉ hơn tuần tự 2,5% và chỉ còn 0,6 GB RAM trống. P=6 ở final **không đo** (sẽ vượt RAM). Đường tuần tự đã chạy 6 Chrome (3 worker × 2 tỉ lệ) nên chạm trần thông lượng của máy (2456 khung / 158,7 s ≈ 15,5 khung/s); thêm tiến trình không giúp thêm.

## Cache (final, 2 tỉ lệ, P=4, kịch bản Khánh)

Đo bằng mã đã sửa (sau khi sửa khoá `prepare` và thêm file lock), một lượt mỗi bước, thư mục cache mới:

| Bước | Thời gian | Cảnh trúng cache | Cảnh dựng lại | Số khung |
|---|---|---|---|---|
| Nguội (cache rỗng) | 157,6 s | 0/7 | 7 | 1228 |
| Chạy lại không đổi | 14,4 s | 7/7 | 0 | 1228 |
| Sửa giọng s03 (296 → 279 khung) | 79,4 s | 4/7 (s01, s02, s05, s07) | 3 (s03, s04, s06) | 1211 |

Kiểm điều prompt đặt ra ("các cảnh sau chỉ dời mốc nên vẫn trúng cache"): **đúng với s05 và s07**; **s04 và s06 vẫn bị dựng lại** vì số khung của chúng đổi ±1 (s04: 182 → 181, s06: 92 → 93) do mốc tuyệt đối làm tròn sang khung, nên nội dung cục bộ thật sự khác. Đây là hành vi đúng, không phải lỗi khoá: khoá phản ánh đúng việc nội dung cảnh đổi. Hệ quả: sửa một cảnh có thể kéo theo dựng lại 1–2 cảnh kế cận, không phải đúng một cảnh.

**Lần đo có giới hạn RAM mặc định** (máy còn ~5–7 GB trống lúc chạy): `effective_jobs` tự hạ xuống 2 (`jobs_requested 4`), nguội mất 264,5 s, chạy lại 17,7 s, sửa s03 130,0 s. Cho thấy giới hạn RAM hoạt động, và cần ≥ ~9,6 GB trống (1900 × 4 + 2048) để chạy đủ P=4 ở mặc định. Các con số ở bảng trên đo với giới hạn RAM tắt, giống bộ đo tốc độ.

## Đính chính chẩn đoán "node đơn luồng" (#95/#97)

Chẩn đoán ở #97 (comment 10/11) và trong prompt P1-09: *"trong lúc dựng CPU tổng chỉ 13–18%, `node` chiếm ~1 luồng, bước chụp khung nghẽn ở luồng điều phối đơn của node"*. Số đo của P1-09 (draft 16:9, 1228 khung, trung vị 3 lượt) cho thấy chẩn đoán đúng ở mức một tiến trình, nhưng không phải là nghẽn của máy:

| Cấu hình | Khung/s | CPU tổng TB | Ghi chú |
|---|---|---|---|
| tuần tự, `--workers 3` (1 tiến trình HyperFrames) | 6,6 | 20% | |
| P=1 (`--workers 1`) | 5,5 | 15% | thêm worker (1 → 3) chỉ tăng ~20% |
| P=2 | 9,3 | 22% | |
| P=4 | 15,7 | 36% | |
| P=6 | 17,5 | 50% | chỉ hơn P=4 ~10% (đường găng = cảnh dài nhất) |
| final 2 tỉ lệ, tuần tự (2 tiến trình, 6 Chrome) | 15,5 | 40% | đã ở trần, P=4 chỉ 15,9 |

- **Đúng:** một tiến trình HyperFrames có trần ~5,5–6,6 khung/s và thêm `--workers` gần như không tăng (khớp README #88).
- **Chưa đúng/chưa đủ:** trần của cả máy cao hơn nhiều (~16–17,5 khung/s, gấp ~2,7× một tiến trình) và đạt được bằng nhiều tiến trình; vì vậy "một luồng của node" chỉ giải thích giới hạn *mỗi tiến trình*, không giải thích việc dựng một tỉ lệ chậm hay tổng thông lượng. Ở mức trần, CPU tổng chỉ 36–50%, nên cũng không phải "hết CPU". **Nguyên nhân của trần máy chưa xác định** (nghi vấn chưa kiểm: Chrome/GPU compositing, băng thông bộ nhớ, ffmpeg encode, nhân hiệu năng/nhân tiết kiệm điện của CPU lai).
- Số liệu "Chrome và cả hai GPU ~0%" của #97 không dùng để suy ra nghẽn ở node; chưa có phép đo GPU trong P1-09.
- Hệ quả thực tế: dựng **một** tỉ lệ thì song song theo cảnh nhanh gấp 2,4–2,7×; dựng **hai** tỉ lệ thì đường tuần tự đã chạy 2 tiến trình × 3 worker và chạm trần, nên `parallel` không giúp thêm.
- Giả định "dao động do Bitdefender" của #97 vẫn chưa được kiểm bằng A/B và P1-09 không kiểm thêm.

## So với số đo của #97 và quy trình đề xuất

| Lượt | Đường | Kịch bản | Thời gian |
|---|---|---|---|
| #97 lượt 7 (10/11) | tuần tự, final, 2 tỉ lệ | Khánh `d224316`, 1228 khung | **576,1 s** (`render_wall` 572,0 s; chụp khung chiếm 88–95%) |
| P1-09 (12/11) | tuần tự, final, 2 tỉ lệ | cùng kịch bản | **158,7 s** (trung vị 3 lượt, 153,5–159,0 s) |
| P1-09 (12/11) | song song P=4, final, 2 tỉ lệ | cùng kịch bản | 154,8 s |

- **576 → 158,7 s (3,6×, 4,3 → 15,5 khung/s) không đến từ P1-09:** cả hai là đường tuần tự, mã dựng giống nhau. Hiệu số do trạng thái máy khác nhau giữa hai ngày; #97 đã ghi nhận mức chụp khung dao động 1,8× và 0,294 s/khung ngày 09/11. P1-09 không tách được nguyên nhân (người đo xác nhận `D:/tmp` đã loại trừ khỏi Bitdefender từ trước phiên đo, nhưng không có A/B). So sánh công bằng cho P1-09 là 158,7 s (tuần tự) với 154,8 s (song song) cùng lúc đo.
- **Quy trình đề xuất:**
  1. **Preview 16:9: dựng song song** (một tỉ lệ, cảnh nào cũng được cache): `--mode preview --ratios 16:9 --render-mode parallel --render-jobs 4` → 70–78 s thay vì 187 s; chỉnh lời một cảnh rồi dựng lại ≈ chỉ dựng lại 1–3 cảnh.
  2. **Final 2 tỉ lệ: dựng tuần tự** (`--mode final`, mặc định `sequential`) → 158,7 s, RAM đỉnh 8,2 GB; không dùng `parallel` ở đây vì không nhanh hơn và chỉ còn ~0,6 GB RAM trống.
  Cả hai nằm trong khả năng của CLI hiện tại, không cần đổi mã.

## Dọn tiến trình và huỷ khi lỗi

- Thử huỷ khi Chrome thật đang chạy (draft, P=4, 16:9): tại giây 30 đang có 15 `chrome-headless-shell`, 7 `node`, 3 `ffmpeg`; đặt cờ huỷ, hàm trả về sau 32,3 s (khoảng 2 s sau huỷ) với `không dựng xong (job bị huỷ)`; **còn lại 0 Chrome**.
- Mọi lượt đo tốc độ (27 lượt) kết thúc với 0 Chrome còn lại.
- Test đơn vị cho: job lỗi → huỷ các job còn lại và báo đúng cảnh/tỉ lệ ("cảnh sXX (ratio) lỗi: ..."), job quá hạn, `prepare` lỗi, diệt cây tiến trình.

## Kiểm thử và CI

Test mới ở `tests/produce/test_render_parallel.py` (25 hàm test), `FakeRunner` mở rộng trong `tests/produce/support.py`. Bao gồm: chia cảnh (Σ khung đúng, `start_f = 0`, dời mốc tuyệt đối không đổi lát cắt, làm tròn xuống `.4f` cho 1–699 khung), khoá cache (đổi asset hoặc chất lượng thì đổi khoá; dời mốc không đổi), danh sách concat đúng thứ tự, ghi cache nguyên tử, `--no-cache`, thứ tự job (cảnh dài trước), giới hạn RAM, huỷ khi lỗi/quá hạn, đường tuần tự không đổi, khối `render` trong report, lock (ghi đồng thời, người giữ khoá bị diệt, clip dở dang bị dựng lại).

Chạy cuối: `ruff check`, `ruff format --check`, `pyright` sạch; `pytest` **1078 pass, 2 skip**. Không dùng HyperFrames hay GPU trong test (runner giả).

## Bài học và lỗi đã gặp

1. **`.4f` làm tròn lên → N+1 khung.** `compose` ghi thời lượng cảnh với 4 chữ số; làm tròn lên thì HyperFrames dựng thừa 1 khung. Sửa: làm tròn xuống 4 chữ số ở bản sao timeline của lát cắt (`_shaved_types`), có test cho 1–699 khung.
2. **Khoá clip của `prepare` lệch khoá của `scene`.** Cache clip của #88 tính khoá từ `clip.model_dump()`, `round(scene_s, 4)` và fps. Hai job 16:9/9:16 dùng thời lượng khác nhau (chưa làm tròn) cùng ghi một tên → file `clip-*.mp4` hỏng/dở dang. Sửa: dùng cùng thời lượng, `prepare` chạy `compose` thật trên từng (cảnh, tỉ lệ) để sinh đúng khoá.
3. **Cache clip của #88 không nguyên tử** → thêm khoá file mức hệ điều hành (`msvcrt.locking` / `fcntl.flock`) quanh `prepare_clip` kèm kiểm tra clip hợp lệ. Khoá `O_EXCL` ban đầu để lại tệp rác khi tiến trình bị diệt (khoá "chết"); khoá của hệ điều hành tự nhả.
4. **Lỗi/timeout của một job không huỷ pool** ở bản đầu → `run_task` bắt `TimeoutExpired`/`OSError`, mọi exception đều đặt cờ huỷ.
5. **Công cụ:** heredoc làm hỏng dấu `\` trong chuỗi Python (docstring `__main__.py`, test); dùng Write/Edit cho văn bản có `\`.

## Hạn chế và việc còn lại

1. **Đường tuần tự lệch 1 khung ở cảnh có mốc `.4f` không tròn** (xem Phép thử so với khung gốc). Đây là sai lệch nhỏ của đường cũ (#88/#97), không sửa trong PR này; đề xuất làm tròn `data-start` đúng ở #88 hoặc dùng `parallel`.
2. Phép thử khung gốc chỉ làm cho s03, s04, s05 của PDFCraft ở 16:9; chưa làm cho 9:16 và kịch bản Khánh. Ánh xạ ô clip gần đúng nên chỉ dùng so sánh tương đối.
3. P=6 ở final không đo; P=6 ở draft đo ở phiên riêng, không xen kẽ với sequential.
4. Một máy, một cấu hình phần cứng; số tuyệt đối sẽ khác trên máy khác. Dao động giữa các lượt trong bộ đo này từ ~1% (P=4, P=6) đến ~18% (P=1), và prompt lưu ý dao động tới 1,8× giữa các ngày.
5. **Ghi chú máy đo (Bitdefender):** người đo xác nhận `D:/tmp` đã được loại trừ khỏi Bitdefender từ trước phiên đo. Mọi thư mục render, cache cảnh, scratch và đầu ra của lượt này nằm dưới `D:/tmp/p1-09-*`, nên nằm trong loại trừ. Chưa xác nhận riêng cho `~/.cache/hyperframes` (nơi đặt Chrome headless).
6. Đề xuất ngoài phạm vi (chưa làm, đúng theo prompt): preview ở fps thấp (10 fps); ghép lai HyperFrames + FFmpeg cho clip (HyperFrames chỉ dựng lớp chữ/khung); dựng song song trên nhiều máy.

## Cách dùng

```bash
# song song, 4 tiến trình, có cache (một tỉ lệ nhanh nhất)
uv run python -m worker.produce script.json --input input.json --assets assets.json \
    --out out --ratios 16:9 --render-mode parallel --render-jobs 4
# bỏ cache
... --render-mode parallel --no-cache
```

Quy trình đề xuất: preview 16:9 dựng `parallel`; final 2 tỉ lệ dựng `sequential` (xem mục trên). Dùng `parallel` cho final chỉ khi dựng một tỉ lệ hoặc tận dụng cache.
