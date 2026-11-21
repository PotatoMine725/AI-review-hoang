# ADR-0002: LLM provider cho M1 (model, SDK; hoãn embedding)

- **Trạng thái:** Đã chốt (08/10/2026)
- **Ngày:** 2026-10-07
- **Ngày chốt:** 2026-10-08
- **Người đề xuất:** @PotatoMine725 (phụ trách M1)
- **Người xác nhận phương án:** @VV6505.
- **Tham chiếu:** decision-log #20; issue #59, #61. AI Dev và BE Dev phối hợp triển khai, QA kiểm chứng theo AC.
- **Liên quan:** issue #8 · [spike M1](../report/m1-spike-crawl-extract.md) · [đặc tả M1](../specs/m1-product-intelligence.md) (NFR-02, NFR-08, mục Tech stack) · [ADR-0005](0005-repo-structure-and-extensibility.md) · decision-log #9, #17, #20

> Chốt provider/model cho MVP; chưa xác nhận tích hợp worker hoặc nghiệm thu golden set. Giai đoạn internship không có ngân sách tiền mặt: chỉ chạy API thật trong quota miễn phí đã xác minh, không tự bật billing hay chuyển sang provider/model trả phí.

## Bối cảnh
Module 1 cần LLM để trích xuất fact từ trang đã crawl (1.4) và làm giàu PKB (1.6); gộp/chuẩn hóa (1.5) ưu tiên code. MVP không có vector RAG: 1.8, embedding và pgvector hoãn theo qa-log #5 và decision-log #17. ADR này chốt model và SDK cho M1, không chốt provider TTS/render/video.

Ràng buộc:
- **NFR-02:** chi phí LLM của job M1 crawl + extract ≤ $0.05 mỗi product, không cộng chi phí script M2 hoặc video M3. Đây là tiêu chí đo theo bảng giá Standard, không phải ngân sách được cấp. **NFR-01:** ≤ 5 phút p95 mỗi product.
- **NFR-08 + ADR-0005:** đổi model bằng config, không sửa code; code nghiệp vụ không gọi SDK của provider rải rác.
- **Sai giá là lỗi nghiêm trọng nhất** (đặc tả M1, mục Input), nên độ đúng quan trọng hơn vài phần nghìn đô.
- **Chuỗi cung ứng:** LiteLLM bị cài mã độc ngày 24/03/2026 (decision-log #9). Spike đã gọi thẳng `google-genai`.
- **Model đã chọn là Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`).** Không sử dụng hoặc fallback sang `gemini-2.5-flash-lite`, vì bản 2.5 không dùng được cho dự án này (issue #5, qa-log #6). Các số đo model 3.1 bên dưới chỉ là dữ liệu so sánh lịch sử.

Dữ liệu so sánh model ban đầu chỉ có 2 product. Kết quả đã lưu hiện có 3 product trích xuất thành công với PKB v0.2 và 1 ca WAF; chưa nghiệm thu trên golden set 10 product. Spike chỉ đo 1.4; **1.5–1.6 chưa có số đo**, các con số cho phần đó là ước tính. Cập nhật tài liệu không chạy lại API hoặc phát sinh phí.

**Mode `batch`:** gom top-k trang (spike k = 10) vào một lời gọi `generate_content` thông thường, pricing dùng raw markdown và trang khác dùng fit markdown. Không dùng Gemini Batch API bất đồng bộ; không áp dụng giá chiết khấu Batch API cho số đo này.

## Số liệu đầu vào

### So sánh lịch sử của spike ban đầu (báo cáo ngày 06/10/2026)

Bảng dưới giữ dữ liệu so sánh 3.1/3.5 của spike ban đầu; không đại diện cho `output/metrics.csv` hiện tại.
| Product | Model | Chi phí | Input / output token | Evidence khớp nguồn | Giá + tên plan đúng |
|---|---|---|---|---|---|
| Claude | `gemini-3.1-flash-lite` | $0.0099 | 22 354 / 2 863 | 100 % | Không: tự tính 16.67 thay vì $17 |
| Claude | `gemini-3.5-flash-lite` | $0.0135 | 22 354 / 2 706 | 100 % | Có (period của Pro năm còn mơ hồ) |
| Dreamina | `gemini-3.1-flash-lite` | $0.0085 | 22 589 / 1 901 | 95.7 % | Không: lấy giá khuyến mãi tháng đầu |
| Dreamina | `gemini-3.5-flash-lite` | $0.0129 | 22 589 / 2 442 | 92.3 % | Không: như trên |

- `3.1` rẻ hơn `3.5` 27 % (Claude) và 34 % (Dreamina), tức chênh $0.004 mỗi product trong lần so sánh ban đầu.
- Cả 2 model đều trả `thoughts_token_count = 0` với cấu hình mặc định, 0 lời gọi bị cắt (`finish_reason = STOP`).
- Mode `per_page` đắt gấp 2.6–3.6 lần và sinh plan nhiễu (báo cáo spike); không dùng làm mặc định.
- Lỗi giá ban đầu được đưa vào "Quy tắc trích xuất giá" v0.2. Các kết quả mới dưới đây đã dùng schema v0.2; chưa có lần so sánh lại cả hai model trên cùng golden set.

### Kết quả PKB v0.2 đã lưu (`spikes/m1-crawl-extract/output/metrics.csv`)

| Product | Schema / model | Chi phí quy đổi Standard | Crawl + extract | Evidence khớp nguồn | Giới hạn chất lượng |
|---|---|---|---|---|---|
| Claude | v0.2 / `gemini-3.5-flash-lite` | $0.019544 | 198.23 + 12.59 s | 100% | Giá đã trích khớp nguồn; còn vấn đề phân loại tab/gói |
| Dreamina | v0.2 / `gemini-3.5-flash-lite` | $0.012865 | 165.30 + 6.58 s | 81% | Giá đã trích khớp; thiếu Free và các kỳ thanh toán khác |
| ElevenLabs | v0.2 / `gemini-3.5-flash-lite` | $0.014297 | 218.41 + 10.44 s | 93.8% | Giá đã trích khớp; chưa đầy đủ giá năm/API; chờ QA đối chiếu Golden Facts |
| Gamma | Không có PKB | $0, không gọi LLM | 2.17 + 0 s | Không áp dụng | WAF `waf_challenge`; không tính là một mẫu trích xuất đạt |

Các PKB thành công hợp lệ schema, nhưng nhãn `price_plan_correct` trong spike không chứng minh đầy đủ ≥95% trên golden set. Evidence khớp nguồn cũng là chỉ số riêng, không thay thế độ chính xác hoặc độ đầy đủ của fact. Chi phí là quy đổi từ token, không phải hóa đơn thanh toán hoặc bằng chứng quota miễn phí của tài khoản.

### Bảng giá (tra 07/10/2026, [trang giá chính thức](https://ai.google.dev/gemini-api/docs/pricing), gói trả phí, tier Standard, USD / 1M token, input text; output gồm thinking token)
| Model | Input | Output | Ghi chú |
|---|---|---|---|
| `gemini-3.1-flash-lite` | $0.25 | $1.50 | |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | |
| `gemini-3.5-flash` | $1.50 | $9.00 | trang giá mô tả là "earlier Flash model", không ghi ngày ngừng |
| `gemini-embedding-2` | $0.20 | n/a | Batch API giảm 50 % (input $0.10) |

Giá ở bảng là mốc tham chiếu đã tra ngày 07/10/2026, khớp cấu hình spike; không mặc định triển khai gói trả phí. Phải kiểm quota/model thực tế của project và điều khoản xử lý dữ liệu trước khi gọi API thật với dữ liệu merchant. Khi hết quota miễn phí, dừng job với lỗi rõ; không tự chuyển sang billing. CI dùng fixture, kết quả fixture không được coi là bằng chứng chạy LLM thật.

## Quyết định 1: Model cho 1.4 (trích xuất)

So sánh bên dưới dựa trên số đo ban đầu; số đo v0.2 hiện tại được ghi riêng ở trên.
| Lựa chọn | Ưu | Nhược | Chi phí (mode `batch`, đo) |
|---|---|---|---|
| A. `gemini-3.1-flash-lite` | Rẻ nhất; evidence khớp nguồn hơi cao hơn ở Dreamina (95.7 % so với 92.3 %) | Đã tự tính giá (16.67), 0/2 lần đúng giá | $0.0085–0.0099 |
| B. `gemini-3.5-flash-lite` | Chép giá nguyên văn, điền `currency` từng plan; lần chạy đúng duy nhất (1/4 lần `batch`) là của model này | Đắt hơn A khoảng 27–34 % | $0.0129–0.0135 |
| C. Dùng A cho trang features, B cho trang pricing | Tiết kiệm lý thuyết | Mode `batch` gom mọi trang vào 1 lời gọi; tách ra là thêm lời gọi và thêm logic định tuyến để tiết kiệm ~$0.004 | Chưa đo |

**Chọn B, `gemini-3.5-flash-lite`, mode `batch`.** Tận dụng structured output và prompt/schema của spike; không chọn C vì thêm định tuyến khi chưa có số đo. Chi phí quy đổi 1.4 hiện tại $0.012865–0.019544 dưới ngưỡng NFR-02 nhưng chưa đo cả pipeline M1. Chỉ chạy trong quota miễn phí đã xác minh; chất lượng vẫn cần kiểm chứng trên golden set.

## Quyết định 2: Model cho 1.5–1.6 (merge, enrich)
**Chưa có số đo nào của spike cho bước này.** Ước tính chi phí 1 lời gọi, giữ giả định so sánh ban đầu: input ≈ 5 000 token, output ≈ 3 000 token, **không thinking**. PKB v0.2 hiện tại có output 2 400–5 100 token nên input enrichment thực tế có thể cao hơn giả định; cần đo khi triển khai. Giá lấy ở bảng tham chiếu trên.

| Lựa chọn | Ưu | Nhược | Chi phí ước tính / product | Cộng với 1.4 (B, $0.012865–0.019544) |
|---|---|---|---|---|
| A. `gemini-3.5-flash-lite` | Cùng model với 1.4, vẫn cấu hình riêng extract/enrich | Suy luận audience/JTBD/đối thủ có thể yếu hơn | ≈ $0.009 | ≈ $0.0219–0.0285 |
| B. `gemini-3.5-flash` ("mạnh hơn 1 bậc", như v0.2 ghi) | Suy luận tốt hơn (chưa đo) | Có thể vượt ngưỡng NFR-02 | ≈ $0.0345 | ≈ $0.0474–0.0540 |

- Với B, kết hợp mẫu Claude hiện tại đã ước tính vượt $0.05 trước khi tính retry hoặc thinking phát sinh. Không chọn model mạnh hơn chỉ dựa trên tên model.
- Mode `batch` của 1.4 đã gộp fact của top-10 trang trong 1 lời gọi. Do đó 1.5 phần lớn là code (chuẩn hóa tiền tệ, chu kỳ, thứ tự ưu tiên merchant > crawl > inferred, đánh dấu xung đột). LLM chỉ cần cho khử trùng tính năng khi gộp nhiều nguồn và cho 1.6. AI Dev phối hợp BE Dev thống nhất contract khi triển khai; fact inferred phải được duyệt trước khi dùng ở M2–M4.

**Chọn A (`gemini-3.5-flash-lite`) làm mặc định cho phần LLM của 1.5–1.6.** Không tự nâng lên `gemini-3.5-flash`. Chỉ xem xét thay model khi QA có số đo chất lượng, chi phí vẫn đạt NFR-02, quota miễn phí đáp ứng và các nhóm liên quan thống nhất. Khi triển khai cần giới hạn token/retry và kiểm quota; các biến `MAX_OUTPUT_TOKENS` / `BUDGET_USD` trong spike không tự bảo đảm toàn bộ hệ thống không phát sinh phí.

## Quyết định 3: Gọi `google-genai` trực tiếp hay qua LiteLLM
**Sự cố (nguồn: [bài của LiteLLM](https://docs.litellm.ai/blog/security-update-march-2026), tra 07/10/2026):** ngày 24/03/2026, `litellm` 1.82.7 và 1.82.8 trên PyPI bị cài mã độc rồi bị PyPI cách ly (thời gian tồn tại: theo blog LiteLLM). Bản 1.82.8 còn có `litellm_init.pth` (tự chạy mỗi lần khởi động Python, không cần import). Mã độc quét biến môi trường (API key), khóa SSH, credential cloud, token Kubernetes, mật khẩu DB rồi gửi ra `models.litellm.cloud`. Image Docker proxy chính thức không bị ảnh hưởng vì ghim dependency trong `requirements.txt`. LiteLLM cho biết các bản 1.78.0–1.82.6 đã được kiểm tra sạch và 1.83.0 phát hành qua pipeline CI/CD mới. Worker giữ `GEMINI_API_KEY` trong môi trường, đúng loại thông tin mã độc nhắm tới.

| Lựa chọn | Ưu | Nhược | Chi phí / License |
|---|---|---|---|
| A. `google-genai` trực tiếp, qua adapter mỏng của dự án | Ít dependency; structured output, `usage_metadata`, `count_tokens` đã dùng ở spike; đúng ADR-0005 (provider sau adapter, chọn bằng config) | Thêm provider khác = viết thêm 1 adapter (1 file) | SDK miễn phí |
| B. LiteLLM | Một giao diện cho nhiều provider | Kéo nhiều dependency; từng bị chiếm quyền publish; vẫn cần theo dõi tính năng Gemini (structured output, thinking) có đi qua đủ không; hiện chỉ cần 1 provider | Miễn phí; rủi ro chuỗi cung ứng |
| C. LiteLLM chỉ làm proxy tách riêng | Cô lập khỏi worker | Thêm 1 service để vận hành, trái nguyên tắc không dựng trước cấu trúc chưa dùng (ADR-0005 nguyên tắc 4) | Hạ tầng thêm |

**Chọn A.** Adapter là hàm / module mỏng trong `services/worker`, theo ADR-0005 nguyên tắc 3 ("interface viết khi có provider đầu tiên"): provider đầu tiên là Gemini, nên interface rút ra từ `call_gemini` và `count_tokens` của spike, không thiết kế trước cho nhiều provider. Model và bảng giá nằm trong config; biến môi trường dự kiến `LLM_EXTRACT_MODEL=gemini-3.5-flash-lite`, `LLM_ENRICH_MODEL=gemini-3.5-flash-lite`. Không thêm `EMBED_MODEL` / `EMBED_DIM` cho MVP. Thiết kế đáp ứng NFR-08 về đổi model trong cùng provider; đổi provider cần adapter khác. Việc nghiệm thu khả năng cấu hình được thực hiện sau triển khai.

**Ghim phiên bản + hash (áp cho mọi dependency của worker, không riêng LLM):**
1. Commit `uv.lock`. Nó ghi phiên bản chính xác và `sha256` từng file (kiểm tra trên `uv.lock` của spike: `google-genai 2.28.0`, 2 231 dòng `sha256`).
2. CI và Docker cài bằng `uv sync --locked` (lỗi nếu lock không khớp `pyproject.toml`), không để lock tự cập nhật. Nếu cần ép kiểm tra hash cứng: `uv export --format requirements-txt` rồi `uv pip install --require-hashes` (uv: "Require all distributions to have matching hashes", [tài liệu settings](https://docs.astral.sh/uv/reference/settings/), tra 07/10/2026).
3. Nâng phiên bản là 1 PR riêng, xem changelog và wheel trước khi merge. Cân nhắc `exclude-newer` kiểu khoảng thời gian (uv hỗ trợ ví dụ `1 week`, cùng tài liệu), để chưa nhận bản vừa phát hành.
4. Nếu sau này có dùng LiteLLM (bản thật hoặc fork): ghim cứng ≥ 1.83.0 hoặc ≤ 1.82.6, không dùng khoảng phiên bản, và tìm file `litellm_init.pth` trong môi trường.
5. Không đặt `GEMINI_API_KEY` ở nơi build/CI không cần; quét dependency trong CI (đã ghi ở README spike).

Dependency gián tiếp `unclecode-litellm 1.81.13` do `crawl4ai` kéo vào thuộc phạm vi ADR-001, không lặp lại ở đây.

## Quyết định 4: Hoãn embedding / vector RAG sau MVP
> **Đã chốt hoãn:** MVP không có chunk, embedding, pgvector hay API search (ERD v1.3.1, qa-log #5, #23). M2/M4 dùng nguyên PKB approved (JSON). So sánh dưới là nghiên cứu lịch sử cho phase sau, không phải lựa chọn được phê duyệt hoặc yêu cầu migration của Sprint 1.

Nguồn: [tài liệu embedding của Gemini](https://ai.google.dev/gemini-api/docs/embeddings) và [README pgvector](https://github.com/pgvector/pgvector#hnsw), tra 07/10/2026.

- `gemini-embedding-2` và `gemini-embedding-001` đều mặc định **3 072 chiều**, nhận giá trị 128–3 072, Google khuyên dùng 768, 1 536 hoặc 3 072. `gemini-embedding-2` nhận tối đa 8 192 token mỗi lần (bản `001`: 2 048), tự chuẩn hóa vector khi cắt chiều (bản `001` cần chuẩn hóa tay) và hỗ trợ hơn 100 ngôn ngữ.
- Index HNSW của pgvector: kiểu `vector` tối đa **2 000** chiều, `halfvec` tối đa 4 000, `bit` 64 000, `sparsevec` 1 000 phần tử khác 0. Nên 3 072 chiều với `vector` không lập được index HNSW.
- Chưa có số đo chất lượng tìm kiếm cho bất kỳ lựa chọn nào; spike không đo embedding.

| Lựa chọn | Ưu | Nhược |
|---|---|---|
| A. `gemini-embedding-2`, 768 chiều, cột `vector(768)` | Nhỏ nhất (768 × 4 byte mỗi vector), index gọn nhất, dưới giới hạn 2 000; đúng khuyến nghị của Google; v0.2 đã nêu | Chất lượng có thể thấp hơn 1 536 / 3 072 (chưa đo) |
| B. `gemini-embedding-2`, 1 536 chiều, `vector(1536)` | Gấp đôi chiều, vẫn dưới 2 000 | Gấp đôi dung lượng; cần đo mới biết có hơn A |
| C. `gemini-embedding-2`, 3 072 chiều, `halfvec(3072)` | Giữ đủ 3 072 chiều; `halfvec` cho phép HNSW tới 4 000 chiều | Dung lượng tương đương B ở dạng nửa độ chính xác, index nặng nhất; chưa có lý do cần |
| D. `gemini-embedding-001` | Có tham số `task_type` (RETRIEVAL_DOCUMENT, QUESTION_ANSWERING…) | Input chỉ 2 048 token, cần chuẩn hóa tay, chưa tra giá |

**Ứng viên nghiên cứu cho phase sau: A**, chưa chốt model/số chiều. Nếu mở lại RAG, cần ADR và migration riêng cùng số đo chất lượng tìm kiếm; lưu model/số chiều để quản lý re-embed. Không tạo `knowledge_chunks` hoặc cột vector trong MVP theo đề xuất cũ của migration v0.

Chi phí embedding lịch sử (tier Standard $0.20 / 1M token, ước tính): index riêng PKB approved (giả định ≈ 3 000 token) ≈ **$0.0006**; index cả markdown nguồn (≈ 70 000 token) ≈ **$0.014**. Không tính vào phương án MVP vì 1.8 đã hoãn; qa-log #5 và #12 đã trả lời.

## Đối chiếu NFR-02 (ước tính tổng chi phí mỗi product)
| Thành phần | Chi phí | Cơ sở |
|---|---|---|
| 1.4 `gemini-3.5-flash-lite`, `batch` | $0.012865–0.019544 | Số đo v0.2 đã lưu, quy đổi Standard |
| 1.5–1.6 `gemini-3.5-flash-lite` | ≈ $0.009 | Ước tính, giả định ở Quyết định 2 |
| **Tổng M1 dự kiến, không embedding** | **≈ $0.0219–0.0285** | Chưa phải số đo cả pipeline, chưa tính retry phát sinh |
| Nếu 1.6 dùng `gemini-3.5-flash` | ≈ $0.0474–0.0540 | Có thể vượt $0.05; không chọn mặc định |

Theo mẫu có chi phí cao nhất hiện tại, khoảng cách đến ngưỡng là $0.05 − $0.019544 = **$0.030456**. Đây là dư địa kỹ thuật theo giá quy đổi, không phải số tiền được phép chi. Đo lại toàn bộ job M1 và mọi lời gọi/retry khi triển khai; chi phí script M2 và video M3 theo dõi riêng.

**Phạm vi đã thống nhất (qa-log #12, decision-log #19):** NFR-02 chỉ tính job M1 crawl + extract. Không có embedding trong MVP; không cần mở lại câu hỏi này để triển khai ADR-002.

## Quyết định (tóm tắt, đã chốt 08/10/2026)
1. **1.4:** `gemini-3.5-flash-lite`, mode `batch`.
2. **1.5–1.6:** merge/chuẩn hóa ưu tiên code; phần LLM dùng `gemini-3.5-flash-lite`, không tự nâng model.
3. **SDK:** gọi `google-genai` trực tiếp qua adapter mỏng; **không dùng LiteLLM**; ghim phiên bản + hash bằng `uv.lock`, CI dùng `uv sync --locked`.
4. **Embedding:** hoãn sau MVP; M2/M4 dùng PKB approved JSON, không tạo chunk/vector/search.
5. **Ngân sách:** chỉ chạy thật trong quota miễn phí đã xác minh; hết quota thì báo lỗi và dừng, không tự bật billing hoặc fallback trả phí. Test thường xuyên/CI dùng fixture; QA ghi rõ kết quả mock và chạy thật.

**Xem lại khi:**
- Golden set (10 product) cho thấy độ đúng giá + tên plan < 95 % sau khi áp Quy tắc trích xuất giá → ưu tiên sửa nguồn/prompt/validator; thử model khác hoặc chia lời gọi chỉ khi quota miễn phí đáp ứng và được thống nhất.
- Chi phí đo thực tế > $0.05, hoặc Google đổi giá, hoặc ngừng model (`gemini-3.5-flash-lite`/`3.1-flash-lite`).
- Cần provider thứ hai (ví dụ DeepSeek, giá ghi ở v0.2 chưa kiểm tra lại) → viết adapter thứ hai, đánh giá lại LiteLLM với bản đã ghim và đã duyệt.
- Free tier không đáp ứng hoặc hết quota → ghi blocker chạy AI thật, giữ phần kiểm thử độc lập bằng fixture; không coi fixture là nghiệm thu pipeline thật.
- Phạm vi sau MVP thực sự cần RAG → mở ADR riêng cho embedding/index/search.

## Hệ quả
- **Dễ hơn:** một SDK, ít dependency; `usage_metadata` để worker ghi `cost_breakdown` v1 của `generation_jobs`, DB suy dẫn token/cost theo NFR-07; đổi model bằng config, không dựng RAG chưa cần.
- **Khó hơn / nợ kỹ thuật:** thêm provider thứ hai phải viết adapter; 1.5–1.6 mới có ước tính; chưa nghiệm thu golden set; phụ thuộc quota miễn phí thực tế.
- **Việc cần làm tiếp:**
  - Đo 1.6 và toàn bộ pipeline M1 (token vào/ra, kể cả thinking/retry) trong quota miễn phí để thay ước tính bằng số đo. So sánh model khác khi kết quả golden set chỉ ra nhu cầu.
  - Khi golden set (QA-2) sẵn sàng: đo NFR-03 và NFR-02 trên 10 product; so `3.1` với `3.5`.
  - Giữ quyết định qa-log #5/#12: không có embedding/RAG trong MVP.
  - Kiểm tra điều khoản xử lý dữ liệu của Gemini API gói miễn phí so với gói trả phí trước khi đưa dữ liệu merchant vào (chưa kiểm tra).
  - Đã đồng bộ lựa chọn vào đặc tả M1, decision log và các ghi chú kế hoạch/báo cáo liên quan. Khi port LLM vào worker: thêm các biến model vào `.env.example`, adapter/validator, xử lý quota/lỗi và bước quét dependency vào CI; chưa triển khai các phần này trong lần cập nhật tài liệu.

## Nguồn (tra ngày 07/10/2026)
- Spike: `docs/report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/output/metrics.csv`, `spikes/m1-crawl-extract/config.py`, `spikes/m1-crawl-extract/uv.lock`
- Giá Gemini: <https://ai.google.dev/gemini-api/docs/pricing>
- Embedding Gemini: <https://ai.google.dev/gemini-api/docs/embeddings>
- pgvector HNSW: <https://github.com/pgvector/pgvector#hnsw>
- Sự cố LiteLLM 24/03/2026: <https://docs.litellm.ai/blog/security-update-march-2026>
- uv settings (`require-hashes`, `exclude-newer`): <https://docs.astral.sh/uv/reference/settings/>
