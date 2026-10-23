# P1-03 — Khảo sát URL shop cho demo: Báo cáo

- **Prompt:** `prompts/be-p1-pkb-v0-3-shop.md` (mục 1) · **Issue:** #67 · **Ngày đo:** 2026-10-13 · **Người viết:** coding agent
- **Phạm vi:** 7 trang sản phẩm đã đo đủ; 3 mẫu đường dẫn sàn chỉ kiểm robots; 2 trang landing (Shopee, TikTok Shop) đo 1 request mỗi trang. Mỗi nền tảng chỉ 1 mẫu, nên đây là xu hướng, không phải thống kê.
- **Trạng thái:** @PotatoMine725 đã duyệt mục 1 (13/10/2026). Sau góp ý của BA (@khanhphi27) và lead (@VV6505) trên #67 và #68 (14/10/2026): **ElevenLabs là URL website demo; Lock&Lock chỉ là ứng viên chờ xác nhận quyền dùng dữ liệu / asset, hoặc thay URL.** Xem [Quyết định và trạng thái](#quyết-định-và-trạng-thái). Schema PKB v0.3 và spec M1 v0.4.0 không phụ thuộc việc chọn URL demo.
- **Dữ liệu trong báo cáo này chỉ là bằng chứng khảo sát.** Số đo, tên sản phẩm, giá và tên file ảnh của các trang bên dưới không phải asset đã được duyệt cho demo và không dùng làm fixture dùng chung (fixture trong repo là dữ liệu giả, xem [`docs/specs/pkb/examples/`](../specs/pkb/examples/)).

## Cách đo

Probe `spikes/m1-crawl-extract/probe_shop.py` (chạy lại được: `cd services/worker && uv run python ../../spikes/m1-crawl-extract/probe_shop.py <out.json> <url>… [ro:<url>…]`) dùng lại đúng module của worker: `fetch_robots` + `Robots.decide`, `Throttle`, `UrllibHttpClient`, `Crawl4AIFetcher`, `detect_block`. Với mỗi URL:

1. Tải `robots.txt` của host bằng UA dự án `AIReviewContentFactory/0.1`. Bị disallow thì **không** gửi request trang.
2. 1 GET tĩnh (không chạy JS) và parse `application/ld+json`, thẻ `meta` OpenGraph / `product:*`, microdata.
3. 1 lần render Crawl4AI (`detect_block`), parse lại bằng cùng bộ phân tích → so sánh tĩnh với render.
4. 1 GET ảnh sản phẩm (sau khi kiểm robots của host ảnh).

Không dùng CLI `python -m worker.m1.crawl` cho khảo sát: `crawl_product` đi từ URL gốc, đọc sitemap và mở tới 30 trang, và chỉ lưu markdown, bỏ HTML (chứa JSON-LD / OpenGraph). Đây cũng là lý do mục 3 của prompt cần chế độ `shop_item` riêng (1 trang sản phẩm, giữ HTML).

Không stealth, không đổi UA, không proxy, không gọi API nội bộ của sàn, không gọi `/products/<handle>.json`. Khoảng cách request nhỏ nhất đo được: **1.0 s** trên mọi host. Chỉ lưu bản tóm tắt; không lưu HTML hay markdown thô.

## Bảng khảo sát

Viết tắt: LD = JSON-LD, tĩnh = HTML trả về khi không chạy JS.

| # | Nền tảng / loại | URL đã đo | robots | WAF / đăng nhập | LD `Product` + `Offer` | OpenGraph | Giá / biến thể | Ảnh sản phẩm |
|---|---|---|---|---|---|---|---|---|
| 1 | **Tiki** (sàn) | `tiki.vn/binh-giu-nhiet-tiger-mct-a050-500ml-p37937221.html` | Cho phép (`*`, không rule khớp) | Không; render 200 | Có `Product` + `Offer`: 950000 VND, **OutOfStock**, có brand/sku/description | `og:title/image/type/url`; không có `og:price` | Giá có trong LD tĩnh. Không có biến thể (`hasVariant` = 0, 1 offer) | Có. Ảnh 750×750 jpeg, 200, 41 KB |
| 2 | **Lazada** (sàn) | `lazada.vn/products/…-i2373087762.html` | Cho phép | Không; render 200 | `Product` + **`AggregateOffer` không có giá, không có tiền tệ** (chỉ `availability` = InStock) | `og:title/image/type/url`; không có `og:price` | Giá **chỉ** nằm trong blob JS nhúng `__moduleData__` (`pdt_price` = "210.000 ₫"), có sẵn trong HTML tĩnh nhưng không phải dữ liệu chuẩn. Tuỳ chọn biến thể cũng nằm trong blob đó | Có. CDN jpeg, 200, 48 KB |
| 3 | **Shopee** (sàn) | Mẫu đường dẫn `shopee.vn/<slug>-i.<shop>.<item>` (**chưa có URL sản phẩm thật**); landing `shopee.vn/` | Mẫu đường dẫn không bị cấm (`*`, không rule khớp) | Landing: GET tĩnh 200 (vỏ SPA ~200 KB, không LD); **render Crawl4AI thất bại** (`crawl_failed`, không có status). Chưa điều tra thêm, vì không vượt chặn | Chưa đo trang sản phẩm | Chưa đo | Chưa đo | Chưa đo |
| 4 | **TikTok Shop** (sàn) | Mẫu `shop.tiktok.com/view/product/<id>`, `tiktok.com/shop/pdp/<slug>/<id>` (**chưa có URL thật**); landing `shop.tiktok.com/vn` | Mẫu đường dẫn không bị cấm (robots.txt không có nhóm cho `*`/UA dự án) | Landing: tĩnh 200 (5 KB), render 200 nhưng chỉ **343 ký tự** markdown (vỏ ứng dụng) | Chưa đo trang sản phẩm; landing không có LD | Chưa đo | Chưa đo | Chưa đo |
| 5 | **Shopify** (shop tự host, US) | `shop.thehighline.org/products/hl-water-bottle` | Cho phép (`allow: /`) | Không; render 200 | Có `Product` + `Offer`: 26.25 **USD**, InStock, có brand/sku/description | Đủ, gồm `og:price:amount` / `og:price:currency` | Giá có trong tĩnh. 1 variant, không có `hasVariant` | Có. Ảnh webp lớn (1.5 MB), 200 |
| 6 | **Haravan** (shop tự host, VN) | `simplecarry.com/products/balo-e-city-2-d-red` | Cho phép | Không; render 200 | **Không có LD `Product`.** Có microdata (`itemprop`) | `og:price:amount` = "690,000₫" (chuỗi đã định dạng), `og:price:currency` = VND | Giá và biến thể nằm trong JSON nhúng `var meta = {"product":{…,"variants":[{price, title, sku}]}}` ở HTML tĩnh. **Giá ở đơn vị ×100** (`69000000.0` = 690.000₫) | Có. `cdn.hstatic.net` jpeg, 200, 25 KB (URL ảnh để `http://`, thumbnail `_grande`) |
| 7 | **Sapo Web** (shop tự host, VN) | `shop.sapo.vn/may-tinh-tien-s6-max` (shop của chính Sapo) | Cho phép | Không; render 200 | Có `Product` + `Offer`: 7800000 VND, InStock, có brand, **không có sku** | `og:price:amount` = "7.800.000" (dấu chấm VN) | Giá có trong tĩnh. Không có biến thể | Có. `bizweb.dktcdn.net` png, 200, 155 KB |
| 8 | **WooCommerce** (shop tự host, VN) | `binhdep.vn/binh-thuy-tinh-yongcheon-17-lit-han-quoc-ngam-ruou-sam-mn-139-17l` | Cho phép | Không; render 200 | Có `Product` + `Offer`, nhưng **giá nằm trong `offers[].priceSpecification[].price`** (1449000 VND), không phải `offers.price`. Không có brand | `product:price:amount` / `product:price:currency` | Giá có trong tĩnh. Không có biến thể | Có nhưng kém: png 240 KB (ảnh chụp màn hình) |
| 9 | **Site thương hiệu** (Lock&Lock VN, Salesforce Commerce Cloud) | `locknlock.vn/vi-vn/binh-giu-nhiet-locknlock-riga-tumbler-phien-ban-viet-nam-897ml/B80015105.html` | Cho phép | Không; render 200 | Có `Product` + `Offer`: 520000 VND, InStock, brand, sku/model `B80015105`, `aggregateRating` 3.9 (14 đánh giá). **LD không có `image`**; `description` là HTML kèm `iframe` | `og:title/image/url`; không có `og:price`. **`og:image` là banner chung của site** (`opengraphVN.jpg`), không phải ảnh sản phẩm | Giá LD (520.000₫) là của biến thể đang chọn (màu BEG); chưa kiểm giá 3 màu còn lại. "4 mẫu" là swatch màu (`data-attr="Color"`: BEG, DGRN, NVY, VOL) trong HTML, không có trong LD | Có. Gallery DOM có 3 thẻ `<img itemprop="image">` mang mã `LHC4160…B80015105_N.jpg` (khớp sản phẩm). Đã tải thử 2 ảnh: 200, jpeg, 25 KB và 35 KB (sw=800). Ảnh số 3 mang mã `B80015107` (cùng dòng LHC4160, màu khác) |

Nền tảng nhận diện bằng dấu hiệu trong HTML (không dựa vào danh sách nguồn): Shopify (`cdn.shopify.com`), Haravan (`hstatic.net`), Sapo (`bizweb`), WooCommerce, Salesforce Commerce Cloud (`demandware`). Trang `binhdep.vn` được Sapo giới thiệu như khách hàng Sapo Web nhưng thực tế chạy WooCommerce, nên không dùng làm mẫu Sapo.

## Kết quả chính

1. **Sàn lớn: Shopee và TikTok Shop chưa kiểm chứng, hoãn tới sau luồng P1 chính** (lead, #67). Tiki và Lazada đọc được bằng crawler hiện có (robots cho phép, không WAF). Shopee và TikTok Shop chỉ có số liệu mẫu đường dẫn và landing, vì tìm kiếm không cho URL sản phẩm thật; số liệu landing không cho phép kết luận gì về trang sản phẩm. **Không kết luận hỗ trợ hay bị chặn.** Khi mở lại cần URL sản phẩm thật, điều kiện sử dụng phù hợp và vẫn tuân thủ robots / WAF (không vượt chặn).
2. **JSON-LD `Product` có ở 6/7 trang sản phẩm đã đo** (trừ Haravan). **Giá đọc được từ JSON-LD ở 5/7** (trừ Lazada và Haravan). Cả 7 trang đều có giá trong HTML tĩnh, dưới dạng LD, `og:price`, hoặc JSON nhúng.
3. **GET tĩnh cho cùng dữ liệu cấu trúc như render JS ở cả 7 trang.** Trích xuất cấu trúc có thể chạy trên HTML tĩnh (rẻ hơn, không cần trình duyệt); render chỉ cần làm phương án dự phòng.
4. **Định dạng giá không đồng nhất.** Cần bộ chuẩn hoá: `26.25` (USD), `"690,000₫"`, `"7.800.000"`, `"210.000 ₫"`, `69000000.0` (Haravan, ×100). Lấy tiền tệ từ `priceCurrency` / `og:price:currency`, không đoán.
5. **Giá trong LD có thể nằm sâu hơn `offers.price`:** `AggregateOffer.lowPrice`, `offers[].priceSpecification[].price`, hoặc không có (Lazada).
6. **Biến thể gần như không có trong LD** (`hasVariant` = 0 ở mọi trang). Chỉ lấy được từ JSON nhúng riêng của nền tảng (Haravan `meta`, Lazada `__moduleData__`) hoặc DOM (swatch Lock&Lock). Nên coi `variants[]` là tuỳ chọn, ưu tiên "biến thể đang được chọn".
7. **Ảnh:** `og:image` có thể là banner chung (Lock&Lock). LD `image` có thể vắng. Ảnh sản phẩm tốt phải lấy từ gallery DOM hoặc LD khi có. Mọi ảnh đã thử tải đều trả 200 (robots host ảnh cho phép).
8. **Tình trạng hàng:** trang Tiki đo được là `OutOfStock`. Ca hết hàng được giữ làm ca kiểm thử `out_of_stock` bằng fixture dữ liệu giả; không cần tìm thêm sản phẩm Tiki còn hàng.
9. **Không thấy chặn bot** ở 7 trang sản phẩm đã đo (không 403/429, không challenge). Chỉ một lần đo mỗi host, chưa chứng minh ổn định khi crawl lặp.

## Đề xuất 2 URL demo (website đã chốt; shop là ứng viên chờ xác nhận quyền, xem phần Quyết định và trạng thái)

| Loại | URL đề xuất | Lý do | Rủi ro / việc cần làm |
|---|---|---|---|
| **Shop (vật lý), ứng viên** | `https://www.locknlock.vn/vi-vn/binh-giu-nhiet-locknlock-riga-tumbler-phien-ban-viet-nam-897ml/B80015105.html` | Site thương hiệu chính hãng, robots cho phép, không WAF. LD `Product` + `Offer` đủ trong HTML tĩnh: 520.000₫ (VND), InStock, brand, sku, rating. Có 4 mẫu màu để thử `variants[]`. Dữ liệu QA đối chiếu dễ (trang chính hãng) | Ảnh phải lấy từ gallery DOM (`img[itemprop=image]`; LD không có `image`, `og:image` là banner chung) và lọc theo mã sản phẩm, vì ảnh số 3 là của màu khác. `description` trong LD là HTML lẫn `iframe`, cần làm sạch. Giá/biến thể: LD chỉ cho 1 màu. **Quyền sử dụng chưa xác nhận:** robots cho phép và HTTP 200 chỉ chứng minh truy cập được về kỹ thuật; [điều khoản của site](https://www.locknlock.vn/vi-vn/account-register) còn hạn chế khai thác dữ liệu và sao chép / lưu nội dung (BA, #67). Cần xác nhận quyền dùng dữ liệu và asset, hoặc thay bằng URL khác |
| **Mẫu để thiết kế quy tắc** (không phải URL demo, không phải fixture) | `https://simplecarry.com/products/balo-e-city-2-d-red` (Haravan) | Cho thấy đường **không có LD** (microdata, `og:price`, JSON `meta`). Fixture `valid-v03-physical-no-jsonld.json` dùng dữ liệu giả cùng hình dạng | Giá ×100 trong JSON nhúng; thumbnail `_grande` cần đổi sang ảnh gốc |
| **Website / công cụ AI** | `https://elevenlabs.io` | Đã crawl và trích xuất trong spike (7 plan / 32 fact, giá đã đối chiếu tay), đã có Golden Facts QA ở `docs/qa/T12b-golden-facts-elevenlabs.md` | Không có rủi ro mới |

Không đề xuất sàn (Tiki / Lazada) làm demo chính: ảnh và mô tả thuộc người bán lẻ, Lazada thiếu giá chuẩn, trang Tiki đo được đang hết hàng. Shopee / TikTok Shop chưa kiểm chứng.

## Quyết định và trạng thái

Nguồn: @PotatoMine725 (13/10/2026), BA @khanhphi27 và lead @VV6505 (#67, 14/10/2026).

| Câu hỏi | Trạng thái | Áp dụng ở đâu |
|---|---|---|
| URL website / công cụ AI | **Chốt:** `https://elevenlabs.io` (lead đồng ý, QA có Golden Facts T12b) | Spec M1, mục Sản phẩm vật lý (P1) |
| URL sản phẩm vật lý | **Lock&Lock chỉ là ứng viên**, chờ xác nhận quyền dùng dữ liệu / asset, hoặc thay URL. Site thương hiệu bán hàng chính hãng **được tính là link shop** (không bắt buộc là sàn); điều kiện còn thiếu là quyền sử dụng. Robots cho phép và HTTP 200 chỉ là truy cập kỹ thuật | Spec M1; chưa dùng làm nguồn crawl, ảnh hay fixture |
| Biến thể | Nếu Lock&Lock được dùng: demo **một biến thể đã đối chiếu đủ** giá, thông tin, ảnh. Không suy giá hoặc ảnh cho biến thể chưa kiểm, không coi giá màu BEG là giá chung | Spec M1 quy tắc 4 và 5; README PKB |
| Quyền dùng ảnh / screenshot | **Chỉ lưu và dùng khi có quyền sử dụng** (quy tắc #52). Chưa có thì báo thiếu asset và lấy nguồn được phép (merchant cung cấp kèm xác nhận, #53; asset có license; media kit chính thức). "Demo nội bộ + ghi nguồn" **không** thay cho quyền | Spec M1, mục "Ảnh sản phẩm: quyền sử dụng" |
| Fixture dùng chung | **Dữ liệu giả** (thương hiệu giả, `example.com`). Dữ liệu Lock&Lock, simplecarry, Tiki, Lazada chỉ nằm trong báo cáo này làm bằng chứng khảo sát. Ca `out_of_stock` giữ bằng dữ liệu giả, không cần tìm sản phẩm Tiki còn hàng | `docs/specs/pkb/examples/valid-v03-physical-*.json` |
| Shopee, TikTok Shop | **Chưa kiểm chứng, hoãn tới sau luồng P1 chính.** Không kết luận hỗ trợ hay bị chặn | Mục "Kết quả chính" 1; spec M1 |

## Câu hỏi còn mở

1. Ai xác nhận quyền dùng dữ liệu và asset của Lock&Lock (hoặc chọn shop khác cho phép)? Lead đề nghị AI–BA làm trước; không kịp thì thay URL sản phẩm vật lý.
2. Dữ liệu v0.2 cũ có `origin: merchant`: BE điền `edited_by` / `edited_at` thế nào khi chuyển lên 0.3 (README PKB, mục "Mục do owner nhập hoặc sửa").
3. Quan hệ sở hữu Product với tài khoản đăng nhập thường, không bắt buộc là merchant: BE đề xuất (xem spec M1, Danh sách thay đổi cho BE, mục 4).
