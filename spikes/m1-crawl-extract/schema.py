"""PKB v0.2: hợp đồng JSON của Module 1 (đặc tả M1, mục Output + Quy tắc trích xuất giá).

3 lớp:
- `PKBExtract`: phần LLM điền ở 1.4 (dùng làm JSON schema cho structured output).
- `PKBData`: nội dung cột `product_knowledge.data` (jsonb) = `PKBExtract` + các trường 1.5–1.6.
- `Source`: 1 phần tử của cột `product_knowledge.sources` (jsonb).

Cột của bảng (không nằm trong JSON): product_id, version, status, approved_by.
`PKBFile` chỉ dùng trong spike để ghi 1 file/lần chạy: data + sources + meta (số đo của spike, không thuộc contract).
Mọi fact có `origin`, `source_id`, `evidence` (≤ 200 ký tự, trích nguyên văn từ trang nguồn).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

PKB_SCHEMA_VERSION = "0.2"
SchemaVersion = Literal["0.2"]  # phải khớp PKB_SCHEMA_VERSION
EVIDENCE_MAX = 200

Origin = Literal["crawled", "merchant", "inferred"]
PriceUnit = Literal["month", "year", "seat_month", "seat_year", "one_time"]
BillingCycle = Literal["monthly", "quarterly", "yearly", "one_time"]


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
    website: str | None = Field(None, description="Code điền từ URL gốc. LLM để null.")
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


# Luật của validator `Plan` ở dạng JSON Schema. Chỉ gắn vào schema xuất ra (export_schema.py),
# không gắn vào PKBExtract: schema đó gửi cho Gemini và nằm trong khoá cache của run.py.
PLAN_PRICE_RULE = {
    "if": {"required": ["list_price"], "properties": {"list_price": {"type": "number"}}},
    "then": {
        "required": ["price_unit", "billing_cycle"],
        "properties": {"price_unit": {"not": {"type": "null"}}, "billing_cycle": {"not": {"type": "null"}}},
    },
}


class Plan(Fact):
    """1 dòng = 1 plan × 1 chu kỳ trả. Giá số là con số in trên trang, không tự tính."""

    name: str = Field(description="Tên plan đúng như trên trang, vd. 'Pro'.")
    currency: str | None = Field(None, description="Tiền tệ in trên trang, mã ISO 4217, vd. USD, VND.")
    list_price: float | None = Field(
        None, description="Giá niêm yết (giá thường) in trên trang; 0 nếu Free; null nếu 'Contact sales'."
    )
    promo_price: float | None = Field(None, description="Giá khuyến mãi in trên trang; null nếu không có.")
    promo_terms: str | None = Field(None, description="Điều kiện của giá khuyến mãi, vd. 'tháng đầu'.")
    price_unit: PriceUnit | None = Field(
        None, description="Giá tính cho đơn vị nào. Bắt buộc khi có list_price."
    )
    billing_cycle: BillingCycle | None = Field(None, description="Cách trả tiền. Bắt buộc khi có list_price.")
    price_text: str = Field(description="Giá nguyên văn, vd. '$17/month billed annually'.")
    limits: list[str] = Field(default_factory=list, description="Giới hạn của plan, nguyên văn từ trang.")
    audience: str | None = Field(None, description="Đối tượng, vd. 'individuals', 'teams'.")

    @model_validator(mode="after")
    def unit_and_cycle_required_with_price(self) -> Plan:
        if self.list_price is not None and (self.price_unit is None or self.billing_cycle is None):
            raise ValueError("plan có list_price thì price_unit và billing_cycle là bắt buộc")
        return self


class UsagePrice(Fact):
    """Giá theo đơn vị dùng (token, giây video, credit). Không phải plan đăng ký."""

    name: str = Field(description="vd. 'API input'.")
    unit: str = Field(description="vd. '1M tokens', 'second of video'.")
    price: float
    currency: str | None = Field(None, description="Mã ISO 4217.")


class Pricing(BaseModel):
    currency: TextFact | None = Field(None, description="Tiền tệ chính trên trang giá (ISO 4217).")
    region: str | None = Field(None, description="Vùng IP lúc crawl. Code điền. LLM để null.")
    locale: str | None = Field(None, description="Locale lúc crawl. Code điền. LLM để null.")
    default_view: str | None = Field(
        None, description="Tab / chu kỳ trang giá hiển thị mặc định, vd. 'monthly'."
    )
    other_views: list[str] = Field(
        default_factory=list, description="Các tab khác có trên trang giá mà nội dung chưa lấy được."
    )
    plans: list[Plan] = Field(default_factory=list)
    usage_prices: list[UsagePrice] = Field(default_factory=list)
    free_plan: BoolFact | None = None
    trial_days: IntFact | None = None


class Feature(Fact):
    id: str | None = Field(None, description="Code điền (f1, f2…). LLM để null.")
    name: str
    description: str | None = None
    screenshot_ids: list[str] = Field(default_factory=list, description="Code điền ở 1.3. LLM để rỗng.")


class UseCase(Fact):
    title: str


class Limitation(Fact):
    text: str


class PKBExtract(BaseModel):
    """Phần LLM điền ở 1.4."""

    identity: Identity
    pricing: Pricing
    features: list[Feature] = Field(default_factory=list)
    use_cases: list[UseCase] = Field(default_factory=list)
    limitations: list[Limitation] = Field(default_factory=list)


# ---------------------------------------------------------------- 1.5–1.6 (optional)
class Claim(BaseModel):
    """Mục không bắt buộc có nguồn crawl: origin cho biết ai nói."""

    origin: Origin
    source_id: str | None = Field(None, pattern=r"^src_\d{2}$")
    evidence: str | None = Field(None, max_length=EVIDENCE_MAX)


class Audience(Claim):
    segment: str
    jtbd: str | None = None


class Usp(Claim):
    text: str


class Competitor(Claim):
    name: str
    url: str | None = None


class Brand(Claim):
    logo_asset_id: str | None = None
    colors: list[str] = Field(default_factory=list)
    tone: str | None = None


class Compliance(Claim):
    forbidden_claims: list[str] = Field(default_factory=list)
    approved_claims: list[str] = Field(default_factory=list)


class Affiliate(Claim):
    link: str | None = None
    commission: str | None = None


class Conflict(BaseModel):
    field: str = Field(description="Đường dẫn trường, vd. 'pricing.plans[0].list_price'.")
    values: list[float | str]
    source_ids: list[str]


class Quality(BaseModel):
    completeness: float | None = Field(None, ge=0, le=1)
    conflicts: list[Conflict] = Field(default_factory=list)


class PKBData(PKBExtract):
    """Nội dung cột `product_knowledge.data`."""

    schema_version: SchemaVersion = Field(description="Version của contract này. Bắt buộc, luôn là '0.2'.")
    audiences: list[Audience] = Field(default_factory=list)
    usp: list[Usp] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    brand: Brand | None = None
    compliance: Compliance | None = None
    affiliate: Affiliate | None = None
    quality: Quality | None = None


class Source(BaseModel):
    """1 phần tử của cột `product_knowledge.sources`."""

    id: str = Field(pattern=r"^src_\d{2}$")
    url: str
    page_type: str
    fetched_at: str
    content_hash: str
    region: str | None = None
    locale: str | None = None
    variant: Literal["raw", "fit"] = Field(description="Bản markdown đã gửi cho LLM.")
    markdown_path: str | None = Field(None, description="Đường dẫn Storage (private) của markdown.")
    image_paths: list[str] = Field(default_factory=list, description="Đường dẫn Storage (private) của ảnh.")


# ---------------------------------------------------------------- chỉ của spike
class Meta(BaseModel):
    product: str
    schema_version: str = PKB_SCHEMA_VERSION
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


class PKBFile(BaseModel):
    """File `output/<slug>/pkb.<model>.json`: 2 cột của bảng + số đo."""

    data: PKBData
    sources: list[Source]
    meta: Meta
