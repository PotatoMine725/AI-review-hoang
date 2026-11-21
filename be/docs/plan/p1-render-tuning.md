# Kế hoạch chỉnh tốc độ dựng video (máy RTX 4050 Laptop, 24 GB RAM)

Trạng thái: đề xuất, chờ số đo mới. Số cũ đo trên máy 16 GB, Windows, một máy duy nhất.

## Số liệu đã có (nguồn trong repo)

| Phát hiện | Nguồn |
|---|---|
| Với video 42 s, HyperFrames chiếm ~89% phần lặp lại mỗi video; 155 s trong 171 s là Chrome chụp khung, FFmpeg ghép chỉ 4,9 s | `docs/report/pipeline-timing-2026-11.md` §2 |
| Chrome bật/tắt GPU: 307 s so với 328 s (~6%) trên cùng plan | `docs/report/script-to-mp4-2026-11.md` (đo chế độ GPU của Chrome) |
| NVENC không rút ngắn thời gian tường (phần nặng chạy CPU), chỉ giảm CPU-s và RAM | `docs/adr/0003-render-engine.md`, `spikes/p1-render/README.md` |
| **NVENC treo một lần**: `Error submitting video frame to the encoder`, ffmpeg không thoát, chiếm CPU >10 phút; chạy lại cùng cấu hình thì ổn, chưa rõ nguyên nhân (driver/GPU laptop) | `spikes/p1-render/README.md` mục 6 (known issue) |
| TTS CUDA: 16,8 s so với ONNX CPU 22,2 s (cả nạp model), VRAM đỉnh 413 MB | `docs/report/pipeline-timing-2026-11.md` |
| Dựng song song theo cảnh, draft 16:9: tuần tự 187 s, P=4 78 s, P=6 70 s; final 2 tỉ lệ P=4 không nhanh hơn tuần tự, RAM đỉnh 9,5 GB | `docs/report/render-parallel-2026-11.md` |

Kết luận từ số liệu: nút thắt là Chrome chụp khung bằng CPU, không phải mã hoá video hay TTS. NVENC và TTS CUDA chỉ chạm phần chiếm vài giây nên không đáng đổi lấy rủi ro treo. Đường `produce` (HyperFrames) hiện cũng không có tùy chọn encoder để bật.

## Việc làm theo thứ tự

1. **Đo lại trên 24 GB** bằng `worker.produce.bench` (lệnh bên dưới). Chạy `preview` rồi `final`, ít nhất 2 lượt mỗi cấu hình, máy cắm điện, tắt ứng dụng nền.
2. **Chọn mặc định** `PRODUCE_RENDER_MODE` và `PRODUCE_RENDER_JOBS` theo quy tắc: tổng thời gian trung vị thấp nhất trong các cấu hình có 0 lỗi và RAM trống còn ≥ 2 GB lúc đỉnh. Chưa đổi mặc định trong code trước khi có số.
3. **NVENC: chưa thêm công tắc.** Chỉ xét lại nếu bước 1 cho thấy mã hoá chiếm phần đáng kể (cột `Enc %` của GPU cao và `hyperframes_phases` cho thấy encode lớn). Nếu bật: mặc định tắt, đặt timeout cho ffmpeg (đã có `kill_tree` trong `produce/runner.py`), tự lùi về CPU khi lỗi, giới hạn 1–2 phiên mã hoá đồng thời, và chỉ bật mặc định sau 20 lượt liên tiếp không treo.
4. **TTS giữ ONNX CPU** (`PRODUCE_TTS_DEVICE=cpu`). Chỉ thử `+cuda` trong bench để có số, không đổi mặc định.
5. **Cờ HyperFrames 0.9.69 (chỉ đo, không đổi mặc định):** thêm hậu tố vào tên cấu hình: `+nolock` (`HYPERFRAMES_RENDER_LOCK=off`, bỏ hàng đợi render cùng tài khoản, đáng thử nhất cho `par*`), `+fast` (`--experimental-fast-capture`, hãng nói ~2×, mặc định chỉ bật trên macOS có GPU nên cần kiểm hình/phụ đề có đúng không), `+gpu` (`--browser-gpu`). Đặt cố định bằng `PRODUCE_HF_ARGS` / `PRODUCE_HF_ENV` (`A=1,B=2`). Cờ nằm trong khoá cache cảnh. Chỉ nhận cấu hình nào nhanh hơn rõ rệt, 0 lỗi, và so sánh hình/phụ đề không khác bản gốc.
6. Sau khi có số: caption mốc từng chữ và QA vision bằng OpenAI (kế hoạch riêng).

## Cách đo (trên máy render)

Cần script đã duyệt, `input.json` tương ứng và `assets.json`. Ví dụ với dữ liệu run11 trong repo:

```bash
cd services/worker
uv run python -m worker.produce.bench ../../docs/report/m2-first-run-pdfcraft/run11-2026-11-12/script.json \
  --input ../../docs/report/m2-first-run-pdfcraft/input.json \
  --assets <đường dẫn assets.json trên máy, vd. bản pdfcraft-khanh> \
  --out D:/tmp/bench-1 --configs seq3,par4,par6,par8,par6+cuda,par4+nolock,par4+nolock+fast,par4+gpu --repeat 2 --mode preview
# lặp lại với --mode final, và với --cache warm để đo hiệu quả cache
```

Kết quả: `bench.md` (bảng trung vị TTS, render, tổng, RAM đỉnh HyperFrames, GPU/encoder/VRAM đỉnh nếu có `nvidia-smi`) và `bench.json` (từng lượt, gồm lượt lỗi). Lỗi bất định của một lượt được ghi lại và ma trận chạy tiếp, nên chạy lặp để thấy tần suất lỗi. Gửi hai file này để chốt cấu hình.
