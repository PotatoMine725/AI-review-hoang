# ADR-0001: Công cụ crawl cho Module 1 (sub-module 1.2)

- **Trạng thái:** Đã chốt (08/10/2026)
- **Ngày:** 2026-10-07
- **Ngày chốt:** 2026-10-08
- **Người đề xuất:** @PotatoMine725 (phụ trách M1)
- **Người xác nhận phương án:** @VV6505.
- **Tham chiếu:** decision-log #20; issue #59, #61. AI Dev và BE Dev phối hợp triển khai, QA kiểm chứng theo AC.
- **Liên quan:** issue #7 · spike #6 (`report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/README.md`, `spikes/m1-crawl-extract/output/metrics.csv`) · [đặc tả M1](../specs/m1-product-intelligence.md) · ADR-0005

> Chốt lựa chọn công cụ cho MVP. Mã crawl đã được đưa vào worker theo đặc tả M1 v0.3.2 (#41, #42); tích hợp API/queue và nghiệm thu NFR-01/NFR-03 vẫn cần thực hiện. Không xác nhận pipeline đã hoàn tất hoặc đã có biên bản review của toàn nhóm.

## Bối cảnh

Sub-module 1.2 (Discover & Crawl) nhận URL product và trả về ≤ 30 trang markdown có `page_type`. Đặc tả M1 hiện hành yêu cầu:

- **FR-02:** tôn trọng `robots.txt` của từng host; host phụ cùng domain gốc tối đa 5 trang, chỉ faq / pricing.
- **FR-03:** render được trang SPA (JavaScript).
- **NFR-01:** 1 product (30 trang) ≤ 5 phút p95, gồm cả trích xuất LLM.
- **NFR-05:** ≤ 1 request/giây/domain, User-Agent định danh platform. Không vượt chặn bot.
- **Quy tắc trích xuất giá + 1.4:** trang pricing gửi **raw markdown**, trang khác gửi markdown đã lọc (fit), vì bộ lọc làm mất thẻ giá.
- **ADR-0005:** provider nằm sau adapter, chọn bằng config. Crawl tool chạy trong `services/worker` (Python 3.12, uv).

Ràng buộc chung: team nhỏ, cần tận dụng spike thay vì viết crawler từ đầu; license phải phù hợp với sản phẩm. Giai đoạn internship không có ngân sách tiền mặt: chạy thư viện trên máy/hạ tầng sẵn có, không tự bật dịch vụ crawl hoặc proxy trả phí. NFR-02 ≤ $0.05/product là tiêu chí đo chi phí LLM của M1, không phải ngân sách đã được cấp.

### Spike #6 đã đo gì (chỉ đo Crawl4AI)

Spike chạy `crawl4ai` 0.9.4 (Playwright 1.63.0) trên 2 product, ngày 06/10/2026, 1 máy, 1 lần chạy:

| Chỉ số | Claude (site tĩnh) | Dreamina (SPA) | Nguồn |
|---|---|---|---|
| Trang tìm thấy / lấy | 3 770 / 29 | 5 139 / 27 | `metrics.csv` |
| Thời gian crawl | 198 s | 165 s | `metrics.csv` |
| Thời gian render trung bình | 6.4 s/trang | 5.1 s/trang (3 s là chờ cố định cho SPA) | README spike, nhận xét 6 |
| Khoảng cách request nhỏ nhất | 1.016 s | 1.000 s | README spike, kết quả bước 1 |
| Thời gian / product (crawl + LLM, mode `batch`) | ~3.4 phút (report ghi 1 số chung cho cả 2 product) | | report spike |

**Số liệu PKB v0.2 đã lưu:** bảng trên giữ số đo lịch sử của spike ban đầu. `output/metrics.csv` hiện lưu kết quả: Claude crawl 198.23 s + extract 12.59 s; Dreamina 165.30 s + 6.58 s; ElevenLabs 218.41 s + 10.44 s. Gamma bị WAF chặn, không có PKB. Đây là kết quả đã lưu, không phải lần chạy mới khi chốt ADR; số mẫu chưa đủ nghiệm thu p95 trên golden set.

Kết quả chất lượng (report và README spike):

- **Render SPA được:** trang chủ Dreamina ra 76 K ký tự raw markdown, có giá và tên model.
- **`fit_markdown` làm mất giá:** `PruningContentFilterLXML` bỏ thẻ giá vì ít chữ. Ở `claude.com/pricing`, bản fit chỉ còn giá Enterprise; bản raw đủ Free / Pro / Max / bảng giá API.
- **Chưa lấy được nội dung sau tab:** giá Dreamina theo năm / quý nằm sau tab; cần `js_code` để bấm, spike không làm.
- **Bộ nhận diện anti-bot của Crawl4AI báo nhầm:** trang 404 bị gắn nhãn "Blocked by anti-bot protection" vì ít chữ.
- **Spike tự viết phần lịch sự:** parse `robots.txt` theo RFC 9309, throttle theo host, dò trang bị chặn, chấm điểm link. Không dùng `arun_many` (mặc định chạy song song) và không dùng bộ phát hiện chặn sẵn có. Phần Crawl4AI thực sự đóng góp là **điều khiển trình duyệt + sinh markdown (raw và fit)**.
- **Dependency:** `crawl4ai` 0.9.4 ghim cứng `unclecode-litellm==1.81.13` (fork LiteLLM, chiếm tên module `litellm`) và kéo theo `patchright` (bản Playwright chống phát hiện, chỉ dùng khi bật `enable_stealth`; spike không bật). Coordinator đã kiểm tra wheel `unclecode-litellm` (không có file `.pth`, hash khớp `uv.lock`).

Các lựa chọn B, C, D bên dưới **chưa được đo trong spike**. ADR không ước tính số cho chúng.

## Các lựa chọn

| Lựa chọn | Ưu | Nhược | Chi phí / License |
|---|---|---|---|
| **A. Crawl4AI, dùng như thư viện Python trong worker** (không chạy Docker server của nó) | Đã chạy được trong spike: render SPA, sinh raw + fit markdown; các mẫu crawl + extract thành công dưới 5 phút, chưa chứng minh p95. Python, cài bằng uv, vào thẳng worker. Phát hành đều (0.9.2 → 0.9.4 trong ~10 tuần). Có sẵn `js_code`, `scan_full_page` cho trang có tab / lazy-load | Bộ lọc fit làm mất giá; nhận diện anti-bot báo nhầm (phải tự xử lý, như spike đã làm). Nhịp lỗ hổng bảo mật cao (xem mục Bảo mật). Ghim cứng `unclecode-litellm` và kéo `patchright` (gói nặng, thêm bề mặt tấn công). Commit tập trung ở 1–2 người. License có thêm điều khoản ghi công | Miễn phí. **Apache-2.0 kèm điều khoản ghi công bắt buộc** (xem mục License) |
| **B. Tự viết: Playwright for Python + thư viện HTML→markdown** | Ít dependency nhất; Playwright do Microsoft duy trì, đã có trong stack (1.3 Asset Capture dùng Playwright). Kiểm soát hoàn toàn: không có code chống phát hiện, không có fork LiteLLM. Phần lịch sự (robots, throttle, chặn) spike đã tự viết, mang sang được | Phải tự viết và bảo trì phần sinh markdown, lọc nội dung thừa, cuộn trang, chờ SPA. Chất lượng markdown **chưa đo**. Cần thêm 1 thư viện HTML→markdown, phải hỏi team trước khi thêm (quy tắc stack trong `CLAUDE.md`). Tốn công hơn ở tuần 2 | Miễn phí. Playwright: Apache-2.0. License thư viện markdown: tuỳ thư viện được chọn |
| **C. Firecrawl tự host** | Sản phẩm hoàn chỉnh: API crawl / scrape trả markdown, có hàng đợi riêng. Cộng đồng lớn | **Server là AGPL-3.0.** Là cụm service riêng: `docker-compose.yaml` của repo có 5 service lõi (API Node/TypeScript, playwright-service, Redis, RabbitMQ, Postgres) và 2 service FoundationDB thử nghiệm. Không chạy trong worker Python, phải vận hành thêm. Có lỗ hổng nghiêm trọng gần đây (RCE, đọc file tuỳ ý). Chất lượng markdown và tốc độ **chưa đo** | Miễn phí phần mềm; tốn hạ tầng. AGPL-3.0 (SDK là MIT) |
| **D. Firecrawl cloud (API trả phí)** | Không phải vận hành; không vướng AGPL vì không chạy code server | Request đi ra từ hạ tầng bên thứ ba. Việc kiểm soát throttle theo host, robots và User-Agent như FR-02, NFR-05 yêu cầu **chưa xác minh** trên tài liệu Firecrawl. Logic lịch sự spike đã viết không chạy được bên trong dịch vụ. Gửi URL product của merchant ra ngoài. Chưa đo | Trả phí theo lượng crawl (chưa tra giá) |

### So sánh theo tiêu chí

| Tiêu chí | A. Crawl4AI (thư viện) | B. Playwright + HTML→markdown | C. Firecrawl tự host |
|---|---|---|---|
| License | Apache-2.0 + điều khoản ghi công (phải ghi credit trên web app) | Apache-2.0 (Playwright) + license thư viện markdown | AGPL-3.0 cho server. Nếu sửa code server rồi cho người dùng tương tác qua mạng thì phải công bố mã nguồn bản sửa. Dùng nguyên bản như service nội bộ thì rủi ro thấp hơn, nhưng mọi bản vá riêng đều kéo theo nghĩa vụ này |
| Render JS (FR-03) | Có, đã kiểm chứng trên SPA Dreamina | Có (Playwright là engine mà A đang dùng) | Có (theo tài liệu; chưa kiểm chứng) |
| Chất lượng markdown | Raw đủ giá; fit mất thẻ giá → dùng raw cho pricing (đã ghi trong đặc tả M1) | Chưa đo | Chưa đo |
| Tốc độ (NFR-01) | 165–198 s / ~30 trang; tổng ~3.4 phút / product kèm LLM. Thời gian chủ yếu là chờ SPA 3 s + throttle 1 req/s + render | Chưa đo. Vì A cũng chạy trên Playwright và thời gian chủ yếu là chờ cố định + throttle, dự kiến tốc độ không phải yếu tố phân biệt A và B | Chưa đo. Vẫn bị giới hạn bởi throttle 1 req/s của NFR-05 |
| Bảo trì | 84 862 sao; release 0.9.4 ngày 23/09/2026; 45 issue mở. Commit tập trung: `unclecode` 1 033, người thứ hai 344 | Playwright-python: release 1.63.0 ngày 15/09/2026; 4 issue mở; Microsoft duy trì. Phần tự viết do team bảo trì | 189 233 sao; release v2.11.0 ngày 19/06/2026; 96 issue mở |
| Lỗ hổng đã biết | 21 GHSA từ 04/2025, 7 critical; phần lớn ở Docker API server; 0.9.4 đã vá tất cả (xem bảng dưới) | 1 GHSA (npm `playwright` < 1.55.1, tải trình duyệt không kiểm tra chứng chỉ SSL); dự án dùng 1.63.0 | 4 GHSA trong repo, gồm RCE critical CVE-2026-72905 (07/2026) |
| Dependency kéo theo | `unclecode-litellm==1.81.13`, `patchright`, `playwright` | `playwright` + 1 thư viện markdown | ≥ 5 service (API, playwright-service, Redis, RabbitMQ, Postgres; thêm FoundationDB thử nghiệm), ngoài worker |

Số sao và release tra bằng GitHub REST API; số issue mở (không tính PR) tra bằng GitHub Search API (`is:issue is:open`). Tra ngày 07/10/2026.

### License Crawl4AI

File `LICENSE` của Crawl4AI ở tag `v0.9.4` là Apache License 2.0, **cộng thêm mục "Attribution Requirement"**: mọi bản phân phối hoặc sử dụng công khai phải ghi câu *"This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai)."*. Với website / web app, câu này phải nằm ở mục "About" hoặc "Credits".

Mục Tech stack của đặc tả M1 v0.2 chỉ ghi "Apache-2.0". Ghi như vậy chưa đủ, vì điều khoản ghi công là nghĩa vụ thêm.

### Bảo mật Crawl4AI

Nguồn: GitHub Security Advisories của repo `unclecode/crawl4ai` và GitHub Advisory Database (`pip:crawl4ai`), tra ngày 07/10/2026. Mức độ lấy theo advisory của repo; nếu Advisory Database ghi khác thì ghi chú. GHSA-8qrg và GHSA-445m chỉ có trong Advisory Database, nên mức độ lấy từ đó.

| GHSA | Mức độ | Phiên bản bị ảnh hưởng | Bản vá | Phạm vi |
|---|---|---|---|---|
| GHSA-5w5p-vcv6-mm3f | high | 0.9.0–0.9.3 | 0.9.4 | Docker server (config không tin cậy, lộ biến môi trường) |
| GHSA-wh5w-hmj3-vgg7 | high | ≤ 0.9.3 | 0.9.4 | Docker server (SSRF qua URL seeder) |
| GHSA-f77g-77vp-r96v | medium | ≤ 0.9.3 | 0.9.4 | Docker server (SSRF qua fetch robots.txt) |
| GHSA-xpp7-j28w-2gvx | high | 0.9.0–0.9.2 | 0.9.3 | Docker server (ghi file qua config PDF) |
| GHSA-v2rm-hvrj-2x9q | medium | ≤ 0.9.2 | 0.9.3 | Docker server (DoS qua PDF) |
| GHSA-7g3g-vhm6-79f3 | medium | ≤ 0.9.2 | 0.9.3 | Docker Playground (XSS) |
| GHSA-q5rj-45vw-vp2g | high | ≤ 0.9.2 | 0.9.3 | Docker server (SSRF qua PDF) |
| GHSA-m446-hp3q-qfxp (CVE-2026-91944) | high | ≤ 0.9.2 | 0.9.3 | Docker Playground (XSS, lấy token) |
| GHSA-8qrg-7j2f-rf2h | critical | < 0.8.7 | 0.8.7 | Docker server (khoá JWT mặc định) |
| GHSA-wm69-2pc3-rmmf (CVE-2026-57573) | high | ≤ 0.8.9 | 0.9.0 | Docker server (SSRF) |
| GHSA-r253-r9jw-qg44 (CVE-2026-57572) | critical | ≤ 0.8.9 | 0.9.0 | Docker server (RCE qua `extra_args` của Chromium) |
| **GHSA-2jq4-q6vv-4cp3 (CVE-2026-57571)** | **critical** | ≤ 0.8.9 | 0.9.0 | **SDK và Docker server**: ghi file tuỳ ý khi lưu file tải về (tên file lấy từ header `Content-Disposition`) → có thể RCE |
| GHSA-6qhc-x826-342c (CVE-2026-53755) | high | ≤ 0.8.8 | 0.8.9 | Docker server (SSRF qua proxy) |
| GHSA-7cx2-g3h9-382p | high | ≤ 0.8.7 | 0.8.8 | Docker server (ghi file, chèn log / header) |
| GHSA-f989-c77f-r2cq | high | ≤ 0.8.7 | 0.8.8 | Docker server (lấy trộm key LLM) |
| GHSA-4qqr-vv2q-cmr5 (CVE-2026-53754) | high | ≤ 0.8.7 | 0.8.8 | Docker server (vượt lọc SSRF qua IPv6) |
| GHSA-365w-hqf6-vxfg | critical | ≤ 0.8.6 | 0.8.7 | Docker server (nhiều lỗi) |
| GHSA-qxjp-w3pj-48m7 (CVE-2026-53753) | critical | ≤ 0.8.6 | 0.8.7 | Docker server (thoát sandbox, RCE) |
| GHSA-5882-5rx9-xgxp | critical | < 0.8.0 | 0.8.0 | Docker server (RCE qua hooks) |
| GHSA-vx9w-5cx4-9796 | high (Advisory Database: critical) | < 0.8.0 | 0.8.0 | Docker server (đọc file local qua `file://`) |
| GHSA-445m-27cf-gr3x | medium | ≤ 0.4.247 | không ghi | SSRF |

Tổng: 21 advisory, 7 critical (6 nếu lấy mức của repo cho GHSA-vx9w). 20/21 công bố trong năm 2026. Bản 0.9.3 và 0.9.4 đều ra kèm advisory mới.

Đánh giá:
- Gần như mọi lỗ hổng nằm ở **Docker API server / Playground** của Crawl4AI, nơi nhận config từ client không tin cậy. Dự án **không chạy server này**: worker gọi Crawl4AI trong tiến trình và chỉ nhận URL product, không nhận config crawl từ người dùng.
- **GHSA-2jq4 chạm được từ SDK** qua đường lưu file tải về. Đã vá ở 0.9.0. Spike không bật tải file (không dùng `accept_downloads` hay `AsyncHTTPCrawlerStrategy`).
- Phiên bản spike (0.9.4) đã vá mọi advisory ở trên. Chi phí thật là **nhịp cập nhật**: phải theo dõi advisory và nâng phiên bản nhanh.

Firecrawl (repo `firecrawl/firecrawl`, tra 07/10/2026): GHSA-3p54-jg6f-68r8 (CVE-2026-72904, high, đọc file tuỳ ý qua `$ref` của JSON Schema), GHSA-7843-ffpq-5f9p (CVE-2026-72905, critical, RCE qua `/scrape` với `changeTracking`), GHSA-p2wg-prhf-jx79 (CVE-2025-57818, high, SSRF qua webhook), GHSA-vjp8-2wgg-p734 (CVE-2024-56800, high, SSRF qua URL scrape). Tự host Firecrawl nghĩa là dự án phải tự vá server này.

## Quyết định

**Chọn A: Crawl4AI dùng như thư viện Python trong `services/worker`**, với các điều kiện:

1. **Chỉ dùng như thư viện.** Không chạy Docker API server / Playground của Crawl4AI. Không nhận `BrowserConfig` / `CrawlerRunConfig` từ request bên ngoài; config do code dự án dựng.
2. **Ghim `crawl4ai >= 0.9.4`** trong `uv.lock`. Không bật `enable_stealth`, `magic`, `simulate_user`, `override_navigator`, proxy (giữ cấu hình của spike, đúng NFR-05). Không bật tải file nếu chưa cần (GHSA-2jq4).
3. **Đặt sau adapter** (ADR-0005): interface của dự án dạng "render trang → raw + fit markdown + metadata". Phần lịch sự (robots theo RFC 9309, throttle theo host, dò chặn, chấm điểm link) là code của dự án, không phụ thuộc Crawl4AI. Nhờ vậy thay bằng B chỉ phải viết lại phần render + sinh markdown.
4. **Phương án dự phòng là B** (Playwright + thư viện HTML→markdown), không phải Firecrawl.
5. **Giữ quy tắc nguồn và lỗi của M1:** pricing dùng raw markdown; trang khác dùng fit markdown. Khi gặp WAF hoặc chuyển hướng đăng nhập, dừng crawl và trả lỗi có hướng dẫn nguồn thay thế theo FR-10; không retry như lỗi tạm thời, không vượt chặn. Việc hoàn thành upload/screenshot theo #52/#53 được theo dõi riêng.

Lý do:
- A là lựa chọn duy nhất đã có số đo: render được SPA và các mẫu thành công có tổng crawl + extract dưới 5 phút. Chất lượng markdown hỗ trợ Quy tắc trích xuất giá (raw cho pricing), nhưng NFR-01 p95 và NFR-03 vẫn cần QA kiểm chứng trên golden set.
- License dùng được cho SaaS thương mại, chỉ cần ghi credit. C vướng AGPL-3.0 và phải vận hành thêm một cụm service. D tốn phí theo lượng dùng, đưa request ra hạ tầng bên thứ ba, chưa xác minh được NFR-05 và chưa có số đo.
- Rủi ro bảo mật lớn nhất của A nằm ở Docker server mà dự án không dùng. Rủi ro còn lại (dependency gián tiếp, nhịp vá) xử lý được bằng ghim phiên bản và quét dependency.
- B sạch hơn về dependency nhưng tốn công tuần 2 và chưa có số đo. Adapter giữ đường lui sang B với chi phí thấp.

**Xem xét lại khi:**
- Có advisory mới ảnh hưởng **chế độ thư viện** (không phải Docker server) mà sau 14 ngày chưa có bản vá.
- Crawl4AI đổi license, hoặc điều khoản ghi công thay đổi theo hướng không chấp nhận được với sản phẩm.
- Có sự cố bảo mật với fork `unclecode-litellm`, hoặc sau này cần thêm LiteLLM thật gây xung đột dependency. ADR-002 hiện đã chốt không dùng LiteLLM làm lớp gọi LLM.
- Đo trên golden set 10 product: không đạt NFR-01 (p95), hoặc lỗi giá còn lại do markdown (không phải do LLM) làm NFR-03 không đạt.
- Repo không có release hoặc không phản hồi advisory trong 3 tháng.

## Hệ quả

- **Những gì trở nên dễ hơn:**
  - Mang code spike (render, raw + fit markdown, `content_hash`) vào worker gần như nguyên vẹn.
  - Lấy nội dung sau tab / nút bấm (giá theo năm của Dreamina) bằng `js_code` có sẵn.
  - Dùng chung Playwright với 1.3 Asset Capture (cùng engine trình duyệt).
- **Những gì trở nên khó hơn hoặc nợ kỹ thuật:**
  - Phải theo dõi advisory của Crawl4AI và nâng phiên bản thường xuyên.
  - Dependency gián tiếp `unclecode-litellm` chiếm tên module `litellm`; vẫn cần theo dõi dù ADR-002 không dùng LiteLLM làm lớp gọi LLM.
  - `patchright` nằm trong cây dependency dù không dùng; image worker nặng hơn.
  - Không dùng được bộ lọc fit và bộ nhận diện anti-bot sẵn có cho mọi trang; phải giữ logic riêng của dự án.
  - Phải ghi credit Crawl4AI trên web app (chạm repo FE).
- **Việc cần làm tiếp:**
  - [x] Đồng bộ mục Tech stack của `specs/m1-product-intelligence.md`: lựa chọn đã chốt, ghi "Apache-2.0 + điều khoản ghi công", link ADR-0001, bỏ link blog so sánh.
  - [ ] Tạo issue bên `AI-review-FE`: thêm mục Credits / About có câu ghi công của Crawl4AI.
  - [ ] Thêm quét dependency vào CI của worker (pip-audit hoặc Dependabot cho `uv.lock`) khi Crawl4AI vào `services/worker`.
  - [ ] Thiết kế interface adapter crawl khi đưa code spike vào worker (ADR-0005: viết interface khi có provider đầu tiên).
  - [ ] Kiểm tra lại khi có bản Crawl4AI mới: còn ghim `unclecode-litellm` không; phối hợp với ADR-002 (#8).
  - [ ] Đo lại NFR-01, NFR-03 trên golden set 10 product (QA-2 bàn giao).

## Nguồn (tra cứu 07/10/2026)

- Spike #6: `docs/report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/README.md`, `spikes/m1-crawl-extract/output/metrics.csv`, `spikes/m1-crawl-extract/uv.lock`.
- Crawl4AI: https://github.com/unclecode/crawl4ai, `LICENSE` và `pyproject.toml` ở tag `v0.9.4`, https://github.com/unclecode/crawl4ai/security/advisories, https://github.com/advisories?query=ecosystem%3Apip+crawl4ai
- Playwright for Python: https://github.com/microsoft/playwright-python · GHSA-7mvr-c777-76hp: https://github.com/advisories/GHSA-7mvr-c777-76hp
- Firecrawl: https://github.com/firecrawl/firecrawl (`LICENSE` AGPL-3.0; `apps/python-sdk/LICENSE` MIT), https://github.com/firecrawl/firecrawl/security/advisories
- Số sao, release, issue mở, số commit theo người đóng góp: GitHub REST API (`/repos`, `/releases`, `/contributors`).
