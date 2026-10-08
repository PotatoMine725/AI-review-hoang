# Prompt Template v0: 20 Hooks từ PKB Approved

Tài liệu định nghĩa template prompt cho Module 2 (AI Hook Factory) để sinh 20 hooks cho video ngắn dọc (15–60s) từ Product Knowledge Base (PKB) đã được duyệt.

---

## 1. Biến đầu vào (Input Variables)

| Biến | Kiểu | Mô tả |
|---|---|---|
| `{{pkb_json}}` | string (JSON) | PKB approved của sản phẩm. **Chỉ chứa fact có `origin` là `crawled` hoặc `merchant`**. Mọi fact `inferred` chưa được approved bắt buộc phải bị loại bỏ trước khi truyền vào prompt (tuân thủ FR-05). |
| `{{platform}}` | string | Nền tảng phân phối (`tiktok`, `reels`, `shorts`). |
| `{{audience}}` | string / object | Đối tượng mục tiêu (segment, job-to-be-done, pain point chính). |
| `{{forbidden_claims}}` | list[string] | Danh sách từ khóa, cam kết hoặc luận điểm bị cấm bởi merchant hoặc chính sách quảng cáo. |
| `{{approved_claims}}` | list[string] | Danh sách thông điệp, góc truyền thông ưu tiên được merchant phê duyệt. |

---

## 2. Quy tắc sinh Hook (Business Rules)

1. **Chống bịa đặt (Zero-Hallucination — FR-QA-01, FR-QA-02, FR-QA-03):**
   - Giá tiền, đơn vị tính, chu kỳ thanh toán và giới hạn kỹ thuật phải lấy nguyên văn con số từ `{{pkb_json}}`.
   - Không tự ý thêm tính năng không tồn tại trong PKB.
2. **Cấm bịa trải nghiệm cá nhân (FR-QA-07):**
   - Không được sinh hook dạng "I tested this tool for 30 days...", "In my experience..." nếu trong PKB không có evidence tương ứng.
3. **Độ dài và ngôn ngữ:**
   - Mỗi hook có độ dài **tối đa 15 từ** (<= 15 words).
   - Ngôn ngữ: Tiếng Anh (`en`).
4. **Đa dạng thể loại (BR-20):**
   - Trong 20 hooks, bắt buộc phải có **ít nhất 6 loại hook (`type`) khác nhau**.
   - Các loại hook hợp lệ (PRD §13): `curiosity`, `pain`, `result`, `comparison`, `controversy`, `challenge`, `demo`, `mistake`.
5. **Góc tiếp cận (`angle` — FR-CONT-01):**
   - Mỗi hook phải gắn với 1 nhóm Content Idea: `problem`, `demo`, `comparison`, `tutorial`, `before_after`, `mistake`, `listicle`, `reaction`, `challenge`, `hidden_feature`, `cost_saving`, `workflow`.
6. **Truy xuất nguồn gốc (`fact_refs`):**
   - Mỗi hook dựa trên thông tin sản phẩm phải trỏ ít nhất 1 `fact_ref` về fact tương ứng trong PKB (`source_id` + `field_path`).
7. **Tuân thủ chính sách:**
   - Tuyệt đối không chứa bất kỳ nội dung nào trong `{{forbidden_claims}}`. Ưu tiên sử dụng `{{approved_claims}}`.

---

## 3. Nội dung Prompt gửi LLM

```text
You are an expert short-form video copywriter specializing in viral hooks for TikTok, Instagram Reels, and YouTube Shorts.

Your task is to generate exactly 20 high-converting video hooks for the product described in the Product Knowledge Base (PKB) below.

### INPUT DATA
- Platform: {{platform}}
- Target Audience: {{audience}}
- Forbidden Claims (DO NOT USE): {{forbidden_claims}}
- Approved Claims (PRIORITIZE): {{approved_claims}}
- Approved Product Knowledge (JSON):
{{pkb_json}}

### STRICT RULES
1. Output format: Return ONLY a valid JSON array of exactly 20 hook objects. No conversational text, no markdown wrapping outside JSON.
2. Hook length: Every hook text MUST be 15 words or fewer. Punchy, fast-paced, natural spoken English.
3. Zero-hallucination: Numbers, prices, plans, model names, and features MUST strictly match facts in the PKB. Never invent pricing or features.
4. Experience claims rule: NEVER use personal claims like "I tested", "I tried", or "I spent 10 hours" unless supported by explicit evidence in the PKB.
5. Diversity: You MUST include at least 6 different hook types across the 20 items. Choose from: curiosity, pain, result, comparison, controversy, challenge, demo, mistake.
6. Traceability: For each hook that references product facts (pricing, limits, models, features), include the exact fact_refs (source_id and field_path in the PKB).

### JSON OUTPUT SCHEMA
[
  {
    "hook_id": "h01",
    "text": "String, max 15 words",
    "type": "curiosity | pain | result | comparison | controversy | challenge | demo | mistake",
    "angle": "problem | demo | comparison | tutorial | before_after | mistake | listicle | reaction | challenge | hidden_feature | cost_saving | workflow",
    "fact_refs": [
      {
        "source_id": "src_01",
        "field_path": "pricing.plans[1]"
      }
    ]
  }
]
```

---

## 4. Inline JSON Schema kiểm tra đầu ra

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Hooks Output Schema",
  "type": "array",
  "minItems": 20,
  "maxItems": 20,
  "items": {
    "type": "object",
    "required": ["hook_id", "text", "type", "angle", "fact_refs"],
    "properties": {
      "hook_id": {
        "type": "string",
        "pattern": "^h(0[1-9]|1[0-9]|20)$"
      },
      "text": {
        "type": "string",
        "minLength": 5,
        "maxLength": 150
      },
      "type": {
        "type": "string",
        "enum": [
          "curiosity",
          "pain",
          "result",
          "comparison",
          "controversy",
          "challenge",
          "demo",
          "mistake"
        ]
      },
      "angle": {
        "type": "string",
        "enum": [
          "problem",
          "demo",
          "comparison",
          "tutorial",
          "before_after",
          "mistake",
          "listicle",
          "reaction",
          "challenge",
          "hidden_feature",
          "cost_saving",
          "workflow"
        ]
      },
      "fact_refs": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["source_id", "field_path"],
          "properties": {
            "source_id": { "type": "string", "pattern": "^src_[0-9]{2,}$" },
            "field_path": { "type": "string", "minLength": 1 }
          },
          "additionalProperties": false
        }
      }
    },
    "additionalProperties": false
  }
}
```
