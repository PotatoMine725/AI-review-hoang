# Nguồn contract M2

Các file trong thư mục này là **bản chép nguyên byte** từ commit `e33827c` (nhánh
`feat/m2-p1-ac-03-script-vi`, PR #83). Chủ sở hữu là Định (@VoHoangDinh). **Không sửa tại đây**:
muốn đổi thì đề xuất ở #83, rồi chép lại bản mới và cập nhật SHA trong
`tests/m2/test_contract.py`.

| File ở đây | Đường dẫn ở commit e33827c |
|---|---|
| `p1-ac-03-script-vi.prompt.md` | `docs/specs/m2/p1-ac-03-script-vi.prompt.md` |
| `p1-ac-03-script-vi-repair.prompt.md` | `docs/specs/m2/p1-ac-03-script-vi-repair.prompt.md` (template một lượt sửa) |
| `p1-ac-03-script-vi.v1.schema.json` | `docs/specs/m2/p1-ac-03-script-vi.v1.schema.json` |
| `p1-ac-03-input.v1.schema.json` | `docs/specs/m2/p1-ac-03-input.v1.schema.json` |
| `examples/*-script-p1-ac-03-vi*.json` | `docs/specs/m2/examples/` |
| `examples/elevenlabs-pkb.gemini-3.5-flash-lite.json` | `spikes/m1-crawl-extract/output/elevenlabs/pkb.gemini-3.5-flash-lite.json` (PKB mà `valid-script-p1-ac-03-vi.context.json` trỏ tới) |

Chép bằng `git cat-file blob e33827c:<đường dẫn> > <file>` (Git Bash, không qua PowerShell để tránh
BOM/CRLF). `.gitattributes` đặt `-text` cho thư mục này để git không đổi xuống dòng.

Từ `4c5b72b` đến `29f868a` chỉ prompt đổi trong thư mục này (blob `f70564b` → `2487354`); schema, ví dụ và PKB
giữ nguyên blob. `validate_contracts.py` đổi (`09224cf` → `638f499`): thêm luật `visual_plan.kind` phải
khớp `kind` của asset trong allowlist khi `source_type: existing_asset`, đã port vào `validate.py`. Parity ghi
lại ở `tests/m2/fixtures/parity-29f868a.json`.

Từ `29f868a` đến `8008cbf` (bàn giao 11/11): prompt sinh đổi (blob `2487354` → `f222ad1`, thêm luật 12 và ghi chú
tích hợp), thêm template sửa `p1-ac-03-script-vi-repair.prompt.md` (blob `a2f073d`), README đổi. Schema, ví dụ,
PKB và `validate_contracts.py` (blob `638f499`) giữ nguyên, nên `validate.py` và parity
(`tests/m2/fixtures/parity-29f868a.json`) không đổi. Chuẩn bị `kind` và lượt sửa là việc của worker
(`kind.py`, `repair.py`, `generate.py`), không nằm trong contract này.

Từ `8008cbf` đến `e33827c` (18/11, review run12 của Định): chỉ hai prompt đổi (sinh: blob `f222ad1` → `904e0c5`;
sửa: `a2f073d` → `eec7480`), thêm luật CTA trung tính “Xem thêm thông tin.” không phải claim sản phẩm (`claims: []`,
bỏ `cta.fact_refs` khi không có claim). Schema, ví dụ, PKB và luật validator giữ nguyên; `validate_contracts.py`
(blob `638f499` → `39e7b55`) chỉ thêm hai ca hồi quy trong `main()`, đã thêm vào `tests/m2/parity_cases.py`
(`neutral-cta-empty-claims`, `cta-product-claim-still-needs-refs`). Kỳ vọng parity ghi lại từ chính script của Định
ở `e33827c`: `tests/m2/fixtures/parity-e33827c.json` (52 ca cũ giữ nguyên kết quả).

Từ `e33827c` đến `5378a70` (dev, 20/11): ba file đổi, chép nguyên byte từ `docs/specs/m2/` của dev.
- Mục tiêu thời lượng 40–45 s → 30–40 s (#126): sinh `p1-ac-03-script-vi.prompt.md` (blob `904e0c5` → `3681390`),
  sửa `p1-ac-03-script-vi-repair.prompt.md` (`eec7480` → `0166168`) và `p1-ac-03-script-vi.v1.schema.json`
  (`149ba9f` → `955dd69`, `target_duration_s` nhận 30–45 để kịch bản cũ vẫn hợp lệ).
- Quy nguồn tự công bố nói tự nhiên, không mở mọi video bằng “Theo X công bố” (#129): hai prompt trên.
- Input schema, ví dụ, PKB không đổi. `validate_contracts.py` chỉ đổi ca thời lượng; parity ghi lại ở
  `tests/m2/fixtures/parity-5378a70.json` (chỉ 4 ca thời lượng khác `e33827c`: 29, 30, 35, 39 s).
