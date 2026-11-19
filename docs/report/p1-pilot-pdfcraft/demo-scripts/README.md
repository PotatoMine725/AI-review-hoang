# Script quay demo trong PDFCraft Studio (viết tay)

Ba action-script cho `worker.demo record`, quay thao tác trong PDFCraft Studio (`/en/studio/`) thay vì trang công cụ lẻ. Trang công cụ lẻ (`/tools/merge-pdf`, `/tools/add-page-numbers`) làm xong chỉ có nút Download, không xem được kết quả, nên cảnh trông như đứng yên. Studio có khung xem PDF, kết quả hiện ngay trên tài liệu.

| Script | Cảnh run11 | Cho thấy |
|---|---|---|
| `pdfcraft-merge-studio.json` | s01 `pdfcraft-merge` | Nạp 2 file, Combine & Merge → Append, cuộn từ trang xanh dương sang trang xanh lá |
| `pdfcraft-pagenum-studio.json` | s02 `pdfcraft-pagenum` | Page Numbers, cỡ chữ 24 (tối đa của PDFCraft), Apply, cuộn tới chân trang 1 và 2 |
| `pdfcraft-word-studio.json` | s03 `pdfcraft-word-export` | PDF to Word → Export & Save, "Processing document", báo xuất xong (~26 s) |

Viết tay vì GPT (`worker.demo run`) chọn sai nút trong Studio sau 4 vòng. Khung xem PDF nằm trong iframe nên script không dùng selector bên trong nó, chỉ chờ và cuộn chuột.

```bash
uv run python -m worker.demo samples --out <fx>          # PDF mẫu (bìa màu, số trang lớn)
uv run python -m worker.demo record ../../docs/report/p1-pilot-pdfcraft/demo-scripts/pdfcraft-merge-studio.json \
    --fixtures <fx> --out <out> --assets <out>/assets.json
```

**Cần cắt tay sau khi quay (chưa tự động):** clip dài 26–54 s, cảnh chỉ 9–14 s, và `produce` lấy đúng độ dài cảnh từ đầu clip (không tua nhanh), nên phần kết quả ở cuối bị mất. Lần chạy 19/11/2026 cắt bằng FFmpeg (`trim` + `concat` vào một file, giây trong clip gốc):

- merge: 5.0–7.6, 8.6–10.8, 13.0–14.8, 16.6–19.0, 23.0–28.3 (14,3 s)
- pagenum: 5.0–6.3, 7.2–8.9, 14.4–15.8, 19.0–21.0, 22.2–25.2 (9,4 s)
- word: 4.2–5.7, 6.3–9.0, 10.0–13.0, 31.0–35.0 (11,2 s)

Mốc thay đổi theo mỗi lần quay (xem `step_times_s` trong `<asset_id>.run.json`). Bước tiếp theo nên tự động: cắt theo `step_times_s`, bỏ các bước `wait` dài.
