# ADR-0002: LLM provider (model, cách gọi SDK, embedding)

- **Trạng thái:** Đề xuất (chốt ở buổi review thứ Sáu 09/10)
- **Ngày:** 2026-10-07
- **Người đề xuất:** @PotatoMine725 (phụ trách M1)
- **Người quyết định:** team lead @VV6505 (decision-log #12)
- **Liên quan:** issue #8 · [spike M1](../report/m1-spike-crawl-extract.md) · [đặc tả M1 v0.2](../specs/m1-product-intelligence.md) (NFR-02, NFR-08, mục Tech stack) · [ADR-0005](0005-repo-structure-and-extensibility.md) · decision-log #9

## Bối cảnh
Module 1 cần LLM ở 3 chỗ: trích xuất fact từ trang đã crawl (1.4), gộp và làm giàu PKB (1.5–1.6), và embedding để index RAG (1.8). ADR này chọn model cho từng chỗ, cách gọi SDK, và embedding.

Ràng buộc:
- **NFR-02:** chi phí LLM ≤ $0.05 mỗi product. **NFR-01:** ≤ 5 phút mỗi product.
- **NFR-08 + ADR-0005:** đổi model bằng config, không sửa code; code nghiệp vụ không gọi SDK của provider rải rác.
- **Sai giá là lỗi nghiêm trọng nhất** (đặc tả M1, mục Input), nên độ đúng quan trọng hơn vài phần nghìn đô.
- **Chuỗi cung ứng:** LiteLLM bị cài mã độc ngày 24/03/2026 (decision-log #9). Spike đã gọi thẳng `google-genai`.
- Gemini 2.5 Flash-Lite không dùng được cho dự án mới (issue #5, qa-log #6), nên ứng viên là họ Flash-Lite 3.x.

Dữ liệu của spike còn mỏng: **2 product, 4 lần chạy `batch` mỗi model**, chưa có golden set (qa-log #7). Spike chỉ đo 1.4. **1.5–1.6 và embedding chưa có số đo**; các con số cho phần đó trong ADR là **ước tính từ giả định ghi rõ**, không phải kết quả đo.

## Số liệu đầu vào

### Spike, trích xuất 1.4, mode `batch` (nguồn: `spikes/m1-crawl-extract/output/metrics.csv`, đo 06/10/2026)
| Product | Model | Chi phí | Input / output token | Evidence khớp nguồn | Giá + tên plan đúng |
|---|---|---|---|---|---|
| Claude | `gemini-3.1-flash-lite` | $0.0099 | 22 354 / 2 863 | 100 % | Không: tự tính 16.67 thay vì $17 |
| Claude | `gemini-3.5-flash-lite` | $0.0135 | 22 354 / 2 706 | 100 % | Có (period của Pro năm còn mơ hồ) |
| Dreamina | `gemini-3.1-flash-lite` | $0.0085 | 22 589 / 1 901 | 95.7 % | Không: lấy giá khuyến mãi tháng đầu |
| Dreamina | `gemini-3.5-flash-lite` | $0.0129 | 22 589 / 2 442 | 92.3 % | Không: như trên |

- `3.1` rẻ hơn `3.5` 27 % (Claude) và 34 % (Dreamina), tức chênh $0.004 mỗi product (tính từ CSV).
- Cả 2 model đều trả `thoughts_token_count = 0` với cấu hình mặc định, 0 lời gọi bị cắt (`finish_reason = STOP`).
- Mode `per_page` đắt gấp 2.6–3.6 lần và sinh plan nhiễu (báo cáo spike); không dùng làm mặc định.
- Lỗi giá của cả 2 model đều thuộc nhóm đã đưa vào "Quy tắc trích xuất giá" v0.2 (lỗi nằm ở schema và prompt hơn là ở model). **Spike chưa chạy lại với schema v0.2**, nên chưa biết độ đúng sau khi sửa.

### Bảng giá (tra 07/10/2026, [trang giá chính thức](https://ai.google.dev/gemini-api/docs/pricing), gói trả phí, tier Standard, USD / 1M token, input text; output gồm thinking token)
| Model | Input | Output | Ghi chú |
|---|---|---|---|
| `gemini-3.1-flash-lite` | $0.25 | $1.50 | |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | |
| `gemini-3.5-flash` | $1.50 | $9.00 | trang giá mô tả là "earlier Flash model", không ghi ngày ngừng |
| `gemini-embedding-2` | $0.20 | n/a | Batch API giảm 50 % (input $0.10) |

Khớp với giá spike dùng (`spikes/m1-crawl-extract/config.py`). Cả 4 model đều có free tier (có giới hạn); production dùng gói trả phí. Chưa kiểm tra điều khoản xử lý dữ liệu của gói miễn phí so với gói trả phí (xem "Việc cần làm tiếp").

## Quyết định 1: Model cho 1.4 (trích xuất)
| Lựa chọn | Ưu | Nhược | Chi phí (mode `batch`, đo) |
|---|---|---|---|
| A. `gemini-3.1-flash-lite` | Rẻ nhất; evidence khớp nguồn hơi cao hơn ở Dreamina (95.7 % so với 92.3 %) | Đã tự tính giá (16.67), 0/2 lần đúng giá | $0.0085–0.0099 |
| B. `gemini-3.5-flash-lite` | Chép giá nguyên văn, điền `currency` từng plan; lần chạy đúng duy nhất (1/4 lần `batch`) là của model này | Đắt hơn A khoảng 27–34 % | $0.0129–0.0135 |
| C. Dùng A cho trang features, B cho trang pricing | Tiết kiệm lý thuyết | Mode `batch` gom mọi trang vào 1 lời gọi; tách ra là thêm lời gọi và thêm logic định tuyến để tiết kiệm ~$0.004 | Chưa đo |

**Đề xuất: B, `gemini-3.5-flash-lite`, mode `batch`.** Cả hai model đều nằm xa dưới NFR-02 (B dùng khoảng 26–27 % ngân sách), nên không có lý do hy sinh độ đúng của giá để tiết kiệm $0.004 mỗi product (khoảng $4 trên 1 000 product). Không chọn C vì chưa có số đo và thêm độ phức tạp. Bằng chứng mỏng (n = 2); xem điều kiện xem lại.

## Quyết định 2: Model cho 1.5–1.6 (merge, enrich)
**Chưa có số đo nào của spike cho bước này.** Ước tính chi phí 1 lời gọi, theo giả định: input ≈ 5 000 token (PKB draft ≈ 1 900–2 900 token output của 1.4 trong CSV, cộng prompt + schema ≈ 2 000), output ≈ 3 000 token, **không thinking**. Giá lấy ở bảng trên.

| Lựa chọn | Ưu | Nhược | Chi phí ước tính / product | Cộng với 1.4 (B, $0.0129–0.0135) |
|---|---|---|---|---|
| A. `gemini-3.5-flash-lite` | Cùng model với 1.4: 1 giá trị config, 1 cách viết prompt | Suy luận audience/JTBD/đối thủ có thể yếu hơn | ≈ $0.009 | ≈ $0.022–0.023 |
| B. `gemini-3.5-flash` ("mạnh hơn 1 bậc", như v0.2 ghi) | Suy luận tốt hơn (chưa đo) | Gần hết ngân sách NFR-02 | ≈ $0.0345 | ≈ $0.047–0.048 |

- Với B, ngân sách còn dư khoảng $0.002, tương đương **~220 token output** ở giá $9.00 / 1M. Chỉ cần model dùng thinking vài trăm token, hoặc 1.8 tốn thêm, là vượt $0.05. Mỗi 1 000 token thinking của `3.5-flash` thêm $0.009.
- Mode `batch` của 1.4 đã gộp fact của top-10 trang trong 1 lời gọi. Do đó 1.5 phần lớn là code (chuẩn hóa tiền tệ, chu kỳ, thứ tự ưu tiên merchant > crawl > inferred, đánh dấu xung đột). LLM chỉ cần cho khử trùng tính năng khi gộp nhiều nguồn và cho 1.6. Có thể gộp thành 1 lời gọi; AI-1 quyết khi viết plan.

**Đề xuất: bắt đầu bằng A (`gemini-3.5-flash-lite`) cho 1.5–1.6; `gemini-3.5-flash` là phương án nâng cấp có điều kiện**, vì chưa có bằng chứng cho thấy cần model mạnh hơn, còn B gần như hết ngân sách. Nâng cấp khi golden set cho thấy fact `inferred` kém *và* chi phí đo thực tế vẫn ≤ $0.05. Dù chọn model nào, đặt `max_output_tokens` và giới hạn chi phí mỗi job (spike đã có `MAX_OUTPUT_TOKENS` và `BUDGET_USD`) để thinking token không âm thầm đẩy chi phí vượt NFR-02.

## Quyết định 3: Gọi `google-genai` trực tiếp hay qua LiteLLM
**Sự cố (nguồn: [bài của LiteLLM](https://docs.litellm.ai/blog/security-update-march-2026), tra 07/10/2026):** ngày 24/03/2026, `litellm` 1.82.7 và 1.82.8 trên PyPI bị cài mã độc rồi bị PyPI cách ly (thời gian tồn tại: theo blog LiteLLM). Bản 1.82.8 còn có `litellm_init.pth` (tự chạy mỗi lần khởi động Python, không cần import). Mã độc quét biến môi trường (API key), khóa SSH, credential cloud, token Kubernetes, mật khẩu DB rồi gửi ra `models.litellm.cloud`. Image Docker proxy chính thức không bị ảnh hưởng vì ghim dependency trong `requirements.txt`. LiteLLM cho biết các bản 1.78.0–1.82.6 đã được kiểm tra sạch và 1.83.0 phát hành qua pipeline CI/CD mới. Worker giữ `GEMINI_API_KEY` trong môi trường, đúng loại thông tin mã độc nhắm tới.

| Lựa chọn | Ưu | Nhược | Chi phí / License |
|---|---|---|---|
| A. `google-genai` trực tiếp, qua adapter mỏng của dự án | Ít dependency; structured output, `usage_metadata`, `count_tokens` đã dùng ở spike; đúng ADR-0005 (provider sau adapter, chọn bằng config) | Thêm provider khác = viết thêm 1 adapter (1 file) | SDK miễn phí |
| B. LiteLLM | Một giao diện cho nhiều provider | Kéo nhiều dependency; từng bị chiếm quyền publish; vẫn cần theo dõi tính năng Gemini (structured output, thinking) có đi qua đủ không; hiện chỉ cần 1 provider | Miễn phí; rủi ro chuỗi cung ứng |
| C. LiteLLM chỉ làm proxy tách riêng | Cô lập khỏi worker | Thêm 1 service để vận hành, trái nguyên tắc không dựng trước cấu trúc chưa dùng (ADR-0005 nguyên tắc 4) | Hạ tầng thêm |

**Đề xuất: A.** Adapter là hàm / module mỏng trong `services/worker`, theo ADR-0005 nguyên tắc 3 ("interface viết khi có provider đầu tiên"): provider đầu tiên là Gemini, nên interface rút ra từ `call_gemini` và `count_tokens` của spike, không thiết kế trước cho nhiều provider. Model và bảng giá nằm trong config và biến môi trường (tên gợi ý: `LLM_EXTRACT_MODEL`, `LLM_ENRICH_MODEL`, `EMBED_MODEL`, `EMBED_DIM`). Như vậy **NFR-08 đạt cho việc đổi model trong cùng provider**; đổi sang provider khác cần viết thêm 1 adapter, và ADR chấp nhận chi phí đó thay cho rủi ro của B.

**Ghim phiên bản + hash (áp cho mọi dependency của worker, không riêng LLM):**
1. Commit `uv.lock`. Nó ghi phiên bản chính xác và `sha256` từng file (kiểm tra trên `uv.lock` của spike: `google-genai 2.28.0`, 2 231 dòng `sha256`).
2. CI và Docker cài bằng `uv sync --locked` (lỗi nếu lock không khớp `pyproject.toml`), không để lock tự cập nhật. Nếu cần ép kiểm tra hash cứng: `uv export --format requirements-txt` rồi `uv pip install --require-hashes` (uv: "Require all distributions to have matching hashes", [tài liệu settings](https://docs.astral.sh/uv/reference/settings/), tra 07/10/2026).
3. Nâng phiên bản là 1 PR riêng, xem changelog và wheel trước khi merge. Cân nhắc `exclude-newer` kiểu khoảng thời gian (uv hỗ trợ ví dụ `1 week`, cùng tài liệu), để chưa nhận bản vừa phát hành.
4. Nếu sau này có dùng LiteLLM (bản thật hoặc fork): ghim cứng ≥ 1.83.0 hoặc ≤ 1.82.6, không dùng khoảng phiên bản, và tìm file `litellm_init.pth` trong môi trường.
5. Không đặt `GEMINI_API_KEY` ở nơi build/CI không cần; quét dependency trong CI (đã ghi ở README spike).

Dependency gián tiếp `unclecode-litellm 1.81.13` do `crawl4ai` kéo vào thuộc phạm vi ADR-001, không lặp lại ở đây.

## Quyết định 4: Model embedding cho 1.8
> **Hoãn:** MVP không dùng vector RAG (ERD v1.3.1, qa-log #5, #23). 1.8 ra khỏi MVP nên chưa cần chọn embedding. Nội dung dưới giữ lại để dùng khi làm RAG ở phase sau.

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

**Đề xuất: A**, qua adapter, kèm 2 điều kiện: (1) lưu `embedding_model` và `embedding_dim` cùng mỗi chunk trong `knowledge_chunks`, để re-embed khi đổi model mà không đoán; (2) khi QA đo chất lượng tìm kiếm thấy 768 thiếu thì lên B. **Đổi số chiều phải làm trước hoặc cùng migration v0** (issue #23), vì là thay kiểu cột và re-embed toàn bộ. Các nhà cung cấp embedding khác (ví dụ OpenAI) chưa được đánh giá trong ADR này.

Chi phí embedding (tier Standard $0.20 / 1M token, ước tính): index riêng PKB approved (giả định ≈ 3 000 token) ≈ **$0.0006**; index cả markdown nguồn (≈ 70 000 token, theo input của `per_page` trong CSV, tức khoảng 29 trang) ≈ **$0.014**, dùng Batch API còn khoảng $0.007. Phụ thuộc qa-log #5 (phạm vi RAG: phương án A full-text trước, hay B pgvector ngay).

## Đối chiếu NFR-02 (ước tính tổng chi phí mỗi product)
| Thành phần | Chi phí | Cơ sở |
|---|---|---|
| 1.4 `gemini-3.5-flash-lite`, `batch` | $0.0129–0.0135 | Đo (spike) |
| 1.5–1.6 `gemini-3.5-flash-lite` | ≈ $0.009 | Ước tính, giả định ở Quyết định 2 |
| 1.8 embedding, chỉ PKB | ≈ $0.0006 | Ước tính |
| **Tổng, phương án đề xuất** | **≈ $0.023** | ≈ 46 % của $0.05 |
| Nếu 1.6 dùng `gemini-3.5-flash` | ≈ $0.048 | Dư ≈ $0.002 |
| Nếu thêm embedding toàn bộ markdown nguồn | + $0.014 (Standard) | Có thể vượt mức khi kết hợp với `3.5-flash` |

Chỉ dựa trên số đo và giá chính thức: sau 1.4 (đo $0.0135 ở `3.5-flash-lite`, mức cao nhất của 2 product), ngân sách còn $0.05 − $0.0135 = **$0.0365** cho mọi bước còn lại. Số đó mua được tối đa khoảng 14 600 token output của `gemini-3.5-flash-lite` ($2.50 / 1M) hoặc khoảng 4 050 token output của `gemini-3.5-flash` ($9.00 / 1M), chưa tính input.

**Câu hỏi cho BA (qa-log #12):** NFR-02 "chi phí LLM" có tính embedding không? Con số trên cho thấy câu trả lời quyết định có thể dùng `3.5-flash` ở 1.6 và index toàn bộ markdown hay không. Spike không tính embedding và không tính screenshot.

## Quyết định (tóm tắt, trạng thái: đề xuất)
1. **1.4:** `gemini-3.5-flash-lite`, mode `batch`.
2. **1.5–1.6:** bắt đầu bằng `gemini-3.5-flash-lite`; `gemini-3.5-flash` chỉ khi đo thấy cần và chi phí vẫn ≤ $0.05.
3. **SDK:** gọi `google-genai` trực tiếp qua adapter mỏng; **không dùng LiteLLM**; ghim phiên bản + hash bằng `uv.lock`, CI dùng `uv sync --locked`.
4. **Embedding:** `gemini-embedding-2`, 768 chiều, `vector(768)` + HNSW; lưu model và số chiều theo từng chunk.

**Xem lại khi:**
- Golden set (10 product) cho thấy độ đúng giá + tên plan < 95 % (NFR-03) *sau khi* áp Quy tắc trích xuất giá v0.2 → thử `3.5-flash` cho 1.4 hoặc chia 2 lời gọi.
- Chi phí đo thực tế > $0.05, hoặc Google đổi giá, hoặc ngừng model (`gemini-3.5-flash-lite`/`3.1-flash-lite`).
- Cần provider thứ hai (ví dụ DeepSeek, giá ghi ở v0.2 chưa kiểm tra lại) → viết adapter thứ hai, đánh giá lại LiteLLM với bản đã ghim và đã duyệt.
- Đo chất lượng tìm kiếm cho thấy 768 chiều không đủ → 1 536 chiều.
- qa-log #5 chọn full-text search: hoãn cột `embedding` và Quyết định 4.

## Hệ quả
- **Dễ hơn:** một SDK, ít dependency, bề mặt tấn công nhỏ; mỗi lời gọi có `usage_metadata` để ghi chi phí chính xác vào `crawl_jobs` (NFR-07); đổi model bằng config.
- **Khó hơn / nợ kỹ thuật:** thêm provider thứ hai phải viết thêm adapter; quyết định 1.5–1.6 dựa trên ước tính, chưa có số đo; bằng chứng chọn model 1.4 mới có 2 product; số chiều embedding khó đổi sau khi có dữ liệu.
- **Việc cần làm tiếp:**
  - Chạy lại spike với schema v0.2 trên cả 2 model (đo độ đúng giá và chi phí thật), và thêm 1 bước đo 1.6 (token vào/ra, kể cả thinking) để thay các ước tính trên bằng số đo.
  - Khi golden set (QA-2) sẵn sàng: đo NFR-03 và NFR-02 trên 10 product; so `3.1` với `3.5`.
  - Trả lời qa-log #12 (NFR-02 có tính embedding?) và #5 (phạm vi RAG).
  - Kiểm tra điều khoản xử lý dữ liệu của Gemini API gói miễn phí so với gói trả phí trước khi đưa dữ liệu merchant vào (chưa kiểm tra).
  - Cập nhật mục Tech stack của đặc tả M1 khi ADR được chốt (hiện ghi "chờ ADR-002"); `.env.example` của `services/worker` thêm các biến model; thêm bước quét dependency vào CI.

## Nguồn (tra ngày 07/10/2026)
- Spike: `docs/report/m1-spike-crawl-extract.md`, `spikes/m1-crawl-extract/output/metrics.csv`, `spikes/m1-crawl-extract/config.py`, `spikes/m1-crawl-extract/uv.lock`
- Giá Gemini: <https://ai.google.dev/gemini-api/docs/pricing>
- Embedding Gemini: <https://ai.google.dev/gemini-api/docs/embeddings>
- pgvector HNSW: <https://github.com/pgvector/pgvector#hnsw>
- Sự cố LiteLLM 24/03/2026: <https://docs.litellm.ai/blog/security-update-march-2026>
- uv settings (`require-hashes`, `exclude-newer`): <https://docs.astral.sh/uv/reference/settings/>
