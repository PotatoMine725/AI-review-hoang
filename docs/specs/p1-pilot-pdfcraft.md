# P1 pilot — PDFCraft: đầu vào, kết quả mong đợi, ánh xạ PKB, lưu trữ

**Issue:** #99 (mục BE/M1/n8n) · **Ngày:** 17/11/2026 · **Người duyệt URL:** Hoàng · **Trạng thái:** đề xuất, chờ BA xác nhận bộ fact và giấy phép AGPL.

## 1. Pilot

| | |
|---|---|
| URL pilot | `https://pdfcraft.devtoolcafe.com` (PDFCraft, mã nguồn mở AGPL-3.0) |
| Dự phòng | `aisoeasy.co`. Chưa dùng được: chờ quyền quay màn hình và tài khoản demo (#67); extract từng sai giá Pro ("$9 $18") |
| Lý do chọn | Mã nguồn mở AGPL-3.0 (ghi công mã nguồn, xem mục 4a); clip do nhóm tự quay, chỉ dùng `internal_demo`. Ghi công mã nguồn **không** cấp quyền cho logo, UI, nội dung website hay clip: phát hành công khai cần quyền riêng. Đã có crawl 30 trang, fact, input M2 (#92), video demo (#78), số đo thời gian (#95) |
| Loại | `software`, PKB v0.3 |

## 2. Đầu vào

| Trường | Giá trị |
|---|---|
| `website_url` | `https://pdfcraft.devtoolcafe.com` (chuẩn hoá bằng `normalize_product_url`, không có dấu `/` cuối) |
| Owner | 1 merchant thử (tài khoản nhóm); `products.affiliate_url = NULL` |
| Brief | Giới thiệu PDFCraft cho người dùng Việt cần xử lý PDF nhanh, không cài phần mềm. Không có ưu đãi, không có link theo dõi. CTA đọc "Xem thêm thông tin." |
| Ngôn ngữ video | Tiếng Việt (giọng VieNeu), phụ đề tiếng Việt |
| Tỉ lệ | 16:9 trước, 9:16 sau |
| Thời lượng | 40–45 s đo trên MP4 cuối |
| Tư liệu | 4 clip tự quay (`pdfcraft-pagenum`, `pdfcraft-word-export`, `pdfcraft-word-result`, `pdfcraft-merge`), quyền `internal_demo`. Clip nằm ngoài repo; phải thành asset của Product (đường dẫn Storage riêng tư) trước bước dựng |
| Cảnh AI | Ít nhất 1 ảnh AI sinh thật, có provider/model/thời điểm/chi phí (AC-P1-05) |

## 3. Kết quả mong đợi

| Bước | Kết quả đạt | Cách kiểm |
|---|---|---|
| Crawl | Job `completed`, ≤ 30 trang, mỗi trang có `content_hash` | `generation_jobs.status`, `result_manifest.pages` |
| PKB nháp (version 1) | Qua schema PKB v0.3; mọi fact có `source_id` + evidence nguyên văn; chỉ dùng số công cụ theo quyết định BA (132, có phạm vi) | Schema + `validate_contracts.py` + so evidence với markdown |
| Duyệt 1 | `product_knowledge.status = approved`, `reviewed_by/at` có giá trị, `products.current_knowledge_version = 1` | Truy vấn DB |
| Script (revision 1) | Qua validator M2; mỗi claim có `fact_refs`; 4–5 cảnh; 150–170 âm tiết (khuyến nghị của #83; lần chạy 12/11 mới đạt 100–133) | `script_revisions.content`, báo cáo validator |
| Duyệt 2 | `script_revisions.status = approved`, đúng `knowledge_version` của PKB đã duyệt | Truy vấn DB |
| MP4 | 1 file H.264/AAC, 40–45 s, có tiếng, phụ đề, ≥ 1 cảnh AI, 16:9 | ffprobe + xem tay; Job `completed` có `result_manifest` |
| Truy vết | Từ MP4 truy ngược Job ID → script revision → PKB version → source URL; có `n8n_execution_id` | Truy vấn `generation_jobs` |
| Chạy lại | Gửi lại cùng `idempotency_key` không tạo job hay revision thứ hai | Test DB `supabase/tests/` |
| Chi phí/thời gian | Bảng thời gian từng bước, RAM, chi phí LLM/TTS/ảnh | `cost_breakdown`, báo cáo bench #95 |

## 4. PKB nháp và nguồn dữ liệu

File: [`docs/report/p1-pilot-pdfcraft/pkb-draft.v0.3.json`](../report/p1-pilot-pdfcraft/pkb-draft.v0.3.json) (`{data, sources}`, qua schema v0.3 và model Pydantic). Nguồn gốc và giới hạn: [README cùng thư mục](../report/p1-pilot-pdfcraft/README.md).

### Quyết định BA (Khánh, PR #100, 17/11/2026)

1. **Số công cụ chốt 132**, diễn đạt có phạm vi: "Trang công cụ PDFCraft hiện liệt kê 132 công cụ". Không dùng "hơn 132" hay "67". Nguồn: `/en/tools` ghi "132+" và "Showing all 132 tools"; các thẻ danh mục ở trang chủ cộng lại 132. PKB nháp có fact `f11` (src_02, evidence "Showing all 132 tools") và `quality.conflicts = []`. Con số 67 chỉ là ghi chú QA chưa xác minh: máy chạy crawl báo trang `/vi` ghi "Hơn 67", nhưng markdown `/vi` không có trong repo và `src_01.url` là `/`, nên không đưa vào PKB.
2. **Không dùng "không giới hạn" trong video**: trang ghi "Không đăng ký, không giới hạn, không chi phí ẩn" nhưng việc ghép có giới hạn 100 tệp / 500 MB. Chỉ dùng "không cần đăng ký, không chi phí ẩn" (`f6`).
3. **Không dùng USD**: nguồn không xác nhận tiền tệ.
4. `f6`–`f10` là fact **thêm tay** (extractor bỏ sót), chưa phải extractor đã sửa. Evidence `f8` (đánh số trang) và `f9` (PDF → Word) ở `src_02`: hash `src_02` đã đổi nên đã đối chiếu với markdown crawl 17/11 trên máy Hoàng, cả hai khớp nguyên văn (`f9` là chuỗi con của mô tả đầy đủ, vốn còn câu "Preserve formatting and layout." mà clip không chứng minh, không dùng câu đó).

Còn mở trước khi duyệt:

1. **Extractor bỏ sót 5/9 fact BA yêu cầu**; cần sửa prompt extract (#90) để bước crawl→PKB tự lấy được.
2. **FAQ chưa có câu trả lời** trong dữ liệu crawl.
3. **Merchant duyệt thật:** bản nháp chưa được ai duyệt, không dùng làm đầu vào `approved`.

### 4a. Ghi công AGPL (đề xuất của BA)

End card / mô tả video: "PDFCraft — phần mềm mã nguồn mở theo GNU Affero General Public License v3.0 (AGPL-3.0). Mã nguồn: github.com/PDFCraftTool/pdfcraft." (URL repo do BA đề xuất, chưa kiểm). Câu này chỉ ghi công mã nguồn; không cấp quyền dùng logo, UI, nội dung website hay clip. Clip hiện chỉ `internal_demo`; phát hành công khai cần xác nhận quyền riêng.

## 5. Ánh xạ dữ liệu explorer của Thông vào PKB nháp

Chưa có output thật của explorer trong repo BE, nên bảng này là **đề xuất ánh xạ**, chưa kiểm trên dữ liệu thật. Cần Thông gửi 1 lần chạy mẫu (commit/run ID, URL, bước, mốc clip, kích thước khung, quyền dùng).

| Dữ liệu explorer | Vào đâu | Luật |
|---|---|---|
| Phát hiện (finding) về tính năng, có trích dẫn trang | `features[]` (origin `crawled`) + `sources[]` | Chỉ nhận khi có `source_id` trỏ tới trang đã crawl và evidence nguyên văn ≤ 200 ký tự. Không có nguồn thì không vào PKB |
| Finding không có trích dẫn (suy luận) | Không vào `data`; lưu `script_revisions.report` hoặc ghi chú owner | PKB v0.3 chỉ có fact có nguồn hoặc `owner` |
| Bước demo (step) và đoạn clip | Asset của Product (`permitted_assets` của M2), không nằm trong PKB | `asset_id`, `kind=screen_recording`, `allowed_use`, `rights_basis`, mốc thời gian. Step không có file + quyền thì không thành asset |
| Ảnh chụp màn hình | `media.images[]` hoặc asset | Chỉ khi có quyền; lưu Storage riêng tư |
| Bằng chứng thất bại/điều kiện đăng nhập | `generation_jobs.error` / `result_manifest` | Không lưu credential hay session trong DB hay Git |
| Fact trùng giữa crawl và explorer | Giữ 1 fact, ghi cả hai nguồn; lệch giá trị thì vào `quality.conflicts` | |

## 6. Lưu trữ BE (migration `20261117020000_p1_pipeline_persistence.sql`)

| Cần lưu | Nơi | Ghi chú |
|---|---|---|
| Product | `products` | `website_url` unique; owner qua `merchant_id` |
| PKB version | `product_knowledge (product_id, version)` | Cấp version bằng `create_pkb_version` (khoá dòng product); bản đã duyệt bất biến |
| Script revision | `script_revisions (product_id, revision)` | Chỉ sinh từ PKB đã duyệt; `parent_revision`, `report`, `cost_breakdown`; bản đã duyệt bất biến |
| Job ID | `generation_jobs.id` | `job_type` `crawl` hoặc `video`; `pkb_version`, `script_revision` gắn rõ |
| Trạng thái / lỗi | `generation_jobs.status`, `error` | `queued → running → completed/failed`; `failed` bắt buộc có `error`; trạng thái cuối bất biến |
| n8n execution ID | `generation_jobs.n8n_execution_id` | Chỉ là ID để tra log; n8n không giữ dữ liệu chuẩn |
| Chạy lại không trùng | `(product_id, idempotency_key)` unique; 1 crawl đang chạy/product; 1 video chưa fail mỗi (revision, `render_profile`) | Chạy lại có chủ đích sau khi fail dùng key mới. Chi tiết: [`p1-pipeline-db-contract.md`](p1-pipeline-db-contract.md) |

Hai điểm owner duyệt = `review_pkb` và `review_script_revision`; chỉ merchant sở hữu Product được duyệt. n8n dừng khi `status` chưa `approved` và tiếp tục với **đúng revision đã duyệt** (truyền `pkb_version`, `script_revision` vào job video).

Khác ERD v1.3.3 (decision-log #24, lead đồng ý 18/11): `script_revisions` là giải pháp chuyển tiếp thay `content_scripts` (cần `campaigns`, chưa có); `generation_jobs` thêm `pkb_version`, `script_revision`, `render_profile`, `n8n_execution_id` và thay `content_script_id`; `products.affiliate_url` cho phép NULL. Hợp đồng DB đầy đủ: [`p1-pipeline-db-contract.md`](p1-pipeline-db-contract.md).

Endpoint FastAPI (xem [api-contract](api-contract.md), mục P1) và khung workflow n8n (`services/n8n/`) đã có ở PR riêng. Chưa làm (cần quyết hoặc PR sau): cột `tokens_*`/`cost_usd` tự suy từ `cost_breakdown`, hàng đợi claim job, bảng `videos`, Storage bucket.

## 7. Việc còn lại để chạy pilot thật

1. ~~Crawl lại PDFCraft~~ Đã chạy 17/11 (30 trang, extract 12 fact); PKB nháp dựng từ kết quả này. Còn phải đối chiếu evidence `f8`, `f9` với trang `/en/tools` mới (hash đổi).
2. Đối chiếu `f8`, `f9`, rồi merchant duyệt thật bằng `review_pkb` (BA đã chốt số công cụ, xem mục 4).
3. Thông gửi mẫu explorer để kiểm bảng mục 5.
4. ~~Viết endpoint FastAPI và khung workflow n8n~~ Xong ở PR riêng; còn nối các bước crawl/extract/script/render thật và chạy thử trên n8n.
