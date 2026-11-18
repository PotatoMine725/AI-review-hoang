# PKB nháp PDFCraft cho pilot #99

Spec: [`docs/specs/p1-pilot-pdfcraft.md`](../../specs/p1-pilot-pdfcraft.md). Ngày: 17/11/2026.

## File

| File | Nội dung |
|---|---|
| `pkb-draft.v0.3.json` | `{data, sources}` của PKB nháp, `status` sẽ là `draft` khi nạp DB |

## Nguồn gốc

**(Mục này mô tả bản dựng đầu, từ crawl 21/10; bản hiện hành dựng lại từ crawl 17/11, xem mục cuối.)** **Không phải kết quả crawl mới.** Phiên tạo file này không ra được `pdfcraft.devtoolcafe.com` (proxy của sandbox chặn, `403` ở bước CONNECT), nên không chạy lại M1 crawl. Dữ liệu lấy từ lần crawl 21/10/2026 (PKB `lang-p4`, 4 trang `src_01`, `src_02`, `src_03`, `src_10`) đã nằm trong repo ở PR #92: `docs/report/m2-first-run-pdfcraft/input.json`, trường `approved_pkb`.

Đã làm so với `approved_pkb`:

- Giữ `data` và `sources` (evidence nguyên văn đã được `check_facts.py` kiểm ở #78 / #92).
- Bỏ phần mô phỏng duyệt (người duyệt giả, `status = approved`): đây là bản **nháp**, chưa ai duyệt.
- Thêm `quality.conflicts` cho số công cụ: `field = "features"`, `values = [67, 132]`, `source_ids = ["src_01", "src_02"]`. Giá trị 67 ghi theo `facts.json` (F04, trang `/vi`); chưa mở lại trang để xác minh trên `src_01` vì không có mạng.

Kiểm: qua `pkb-data.v0.3.schema.json`, `pkb-sources.v0.3.schema.json` và model Pydantic `schema_v03.PKBData`; mọi `source_id` trỏ tới `sources`.

## Giới hạn

- Chỉ 6 feature, `free_plan = true` (chưa có plan nào), 1 limitation; thiếu use case, FAQ (chưa có câu trả lời trong dữ liệu crawl), audience.
- Extractor từng bỏ sót 5/9 fact BA yêu cầu; một số fact trong file này do người trích từ markdown (bước BA bổ sung ở #92; xem README spike #78), không do pipeline tự sinh.
- `identity.name.evidence` là câu trên trang FAQ ("Find answers to common questions about PDFCraft"), yếu; nên thay bằng evidence rõ hơn khi crawl lại.
- Markdown trang không nằm trong repo; `markdown_path` chỉ là đường dẫn tương đối của lần crawl cũ.

## Crawl lại 17/11/2026 (máy Hoàng) và PKB nháp hiện hành

M1 crawl `https://pdfcraft.devtoolcafe.com` trên `dev`, không đổi code: `completed`, không lỗi, `partial = false`, 30 trang dùng / 2498 tìm thấy, 178,7 s. Extract (PR #90, 1 lời gọi `gemini-3.5-flash-lite`, ~$0,0056 giá niêm yết): `completed`, 12 fact, 5 feature, evidence nguyên văn 100%. Output đầy đủ nằm ngoài repo: `D:\tmp\crawl-pdfcraft-2026-11-17`, `D:\tmp\extract-pdfcraft-2026-11-17`.

| File | Nội dung |
|---|---|
| `pkb-extract-2026-11-17.raw.json` | Output extract nguyên văn, không sửa. `sources` là 10 trang đầu; `content_hash` ở đây là hash bản fit |
| `pkb-draft.v0.3.json` | Bản nháp hiện hành, dựng từ file trên (qua schema v0.3 + Pydantic, mọi `source_id` trỏ tới `sources`) |

Khác file thô (đều là chọn tay, cần BA xác nhận):

- **Bỏ** `identity.description` và `usp[0]` (cùng mang "132+", cảnh báo `self_reported_metric`) vì số công cụ chưa chốt.
- **Bỏ** `pricing.currency = "USD"`: không có trong nguồn (evidence "Hoàn toàn Miễn phí" không nói tiền tệ).
- **Thêm** `f6`–`f10` (không đăng ký, xử lý trong trình duyệt, đánh số trang, PDF → Word, cách ghép) và 1 limitation (100 tệp / 500MB) từ bản nháp 21/10, vì extractor vẫn không lấy được các fact này. Evidence của `f6`, `f7`, `f10` và limitation nằm ở `src_01`, `src_10`, hash bản fit không đổi so với 21/10. `f8`, `f9` nằm ở `src_02` (`/en/tools`), hash đã đổi; đã đối chiếu evidence với markdown crawl 17/11 trên máy Hoàng, cả hai khớp nguyên văn.
- **Thêm** `f11` ("Trang công cụ PDFCraft hiện liệt kê 132 công cụ", src_02, evidence "Showing all 132 tools") và đặt `quality.conflicts = []` theo quyết định BA 17/11: chốt 132, không dùng 67 (xem spec mục 4). Evidence "Showing all 132 tools" do máy chạy crawl trích từ markdown `/en/tools` 17/11, chưa tự kiểm lại trong repo.

Số công cụ: **trang chủ `/vi` tự mâu thuẫn**, vừa ghi "Hơn 67 công cụ" (khối "Công cụ Mạnh mẽ") vừa ghi "Hơn 132 công cụ" (mục danh mục); các thẻ danh mục cộng lại 26+23+21+32+16+14 = 132. `/en/tools` ghi "132+" và "Showing all 132 tools". BA đã chốt 132 (spec mục 4). Số 67 không đưa vào PKB vì markdown `/vi` không có trong repo và `src_01.url` là `/`.

Các trang crawl 17/11 (30 trang): hash raw từng trang nằm trong `crawl.json` trên máy Hoàng; hash raw khác hash fit trong `sources`.
