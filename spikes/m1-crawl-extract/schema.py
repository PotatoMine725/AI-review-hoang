"""PKB rút gọn (tập con của đặc tả M1, mục 1.4).

`PKBExtract` là phần LLM điền (dùng làm JSON schema cho structured output).
`PKB` = `PKBExtract` + `sources` + `meta`, do code điền sau khi gọi LLM.
Mọi fact có `origin`, `source_id`, `evidence` (≤ 200 ký tự, trích nguyên văn từ trang nguồn).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EVIDENCE_MAX = 200


class Fact(BaseModel):
    origin: Literal["crawled"] = Field(description='Luôn là "crawled".')
    source_id: str = Field(pattern=r"^src_\d{2}$", description="Id trang nguồn, vd. src_02.")
    evidence: str = Field(
        min_length=1,
        max_length=EVIDENCE_MAX,
        description="Câu trích NGUYÊN VĂN từ trang nguồn chứng minh fact, ≤ 200 ký tự.",
    )


class TextFact(Fact):
    value: str


class BoolFact(Fact):
    value: bool


class IntFact(Fact):
    value: int


class ModelVersion(Fact):
    name: str = Field(description="Tên model / phiên bản product, vd. 'Claude Opus 5.5', 'Seedance 2.0'.")


class Identity(BaseModel):
    name: TextFact
    tagline: TextFact | None = None
    description: TextFact | None = None
    category: TextFact | None = Field(
        None, description="Loại product, vd. 'AI assistant', 'AI video generator'."
    )
    company: TextFact | None = None
    version: TextFact | None = Field(None, description="Phiên bản product nếu trang ghi rõ.")
    models: list[ModelVersion] = Field(
        default_factory=list, description="Các model AI product đang cung cấp."
    )


class Plan(Fact):
    name: str = Field(description="Tên plan đúng như trên trang, vd. 'Pro'.")
    price: float | None = Field(None, description="Giá số cho 1 kỳ; null nếu 'Contact sales'.")
    price_text: str = Field(description="Giá nguyên văn, vd. '$17/month billed annually'.")
    billing_period: Literal["month", "year", "one_time", "usage", "unknown"]
    currency: str | None = Field(None, description="Mã tiền tệ ISO 4217, vd. USD, VND.")
    audience: str | None = Field(None, description="Đối tượng, vd. 'individuals', 'teams'.")


class Pricing(BaseModel):
    currency: TextFact | None = Field(None, description="Tiền tệ chính trên trang giá (ISO 4217).")
    plans: list[Plan] = Field(default_factory=list)
    free_plan: BoolFact | None = None
    trial_days: IntFact | None = None


class Feature(Fact):
    name: str
    description: str | None = None


class PKBExtract(BaseModel):
    identity: Identity
    pricing: Pricing
    features: list[Feature] = Field(default_factory=list)
    use_cases: list[TextFact] = Field(default_factory=list)
    limitations: list[TextFact] = Field(default_factory=list)


class Source(BaseModel):
    source_id: str
    url: str
    page_type: str
    fetched_at: str
    variant: Literal["raw", "fit"] = Field(description="Bản markdown đã gửi cho LLM.")
    content_hash: str


class Meta(BaseModel):
    product: str
    model: str
    mode: Literal["per_page", "batch"]
    generated_at: str
    llm_calls: int
    cache_hits: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    evidence_in_source: float = Field(description="Tỉ lệ evidence tìm thấy nguyên văn trong trang nguồn.")
    unknown_source_ids: list[str] = Field(default_factory=list)


class PKB(PKBExtract):
    sources: list[Source]
    meta: Meta
