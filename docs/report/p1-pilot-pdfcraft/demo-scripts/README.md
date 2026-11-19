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

**Không cần cắt tay nữa.** `worker.demo` tự cắt đoạn chờ theo mốc từng bước (`step_times_s`): bước `wait`/`wait_for` dài hơn 1,2 s chỉ giữ 0,4 s đầu và 0,8 s cuối, giữ cuối 1,8 s (`encode.compact_spans`). Asset có `anchor: "end"`, nên khi clip vẫn dài hơn cảnh, `produce` tua nhanh tới 2× để giữ cả thao tác, dài hơn nữa thì bỏ phần đầu, giữ kết quả ở cuối.

Chờ kết quả lâu (PDF→Word ~26 s) thì dùng `wait_for` chờ đúng dấu hiệu xong (vd. thông báo `Export completed`), không dùng `wait` cố định, để đoạn giữ lại là lúc vừa có kết quả.

Lần chạy 19/11/2026 (run11): merge 25,5 s → tua 1,78×, số trang 18,7 s → 2× (giữ phần cuối), Word 12,4 s → 1,11×.
