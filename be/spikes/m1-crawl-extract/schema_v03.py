"""PKB v0.3: thêm sản phẩm vật lý (P1, issue #67). Superset của v0.2 (`schema.py`, giữ nguyên).

Dùng lại các kiểu của v0.2 (Fact, Plan, Pricing, Feature…). Chỉ định nghĩa lại phần khác:
- `Identity`: thêm `product_kind`, `brand_name`, `sku`, `gtin`. Các trường owner được sửa
  (`name`, `description`, `category`, `brand_name`, `sku`, `gtin`) là `IdentityFact`.
- `SourcedItem`: Fact mở rộng cho `offers[]`, `variants[]`, `specs[]`, `media.images[]`.
  `origin` là `crawled` hoặc `owner`. `crawled` bắt buộc có `source_id` + `evidence`.
- Mọi mục `origin: owner` (SourcedItem, IdentityFact, Claim) bắt buộc `edited_by` + `edited_at`;
  `origin` khác thì cấm hai trường đó (`OwnerEdited`).
- `Claim` (audiences, usp, competitors, brand, compliance): `origin` thêm `owner`, giữ `merchant` chỉ để đọc v0.2.
- `PKBData`: `pricing` chỉ bắt buộc khi `software`; `physical` bắt buộc `offers[]`.
- `Source`: thêm `structured_path`.

Luật mà JSON Schema diễn đạt được thì gắn vào schema xuất ra qua `JSON_RULES` (export_schema.py).
Luật tham chiếu chéo (variant_ref trỏ tới variant có thật…) chỉ có ở validator Pydantic và validate_contracts.py.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

import schema as v02
from schema import EVIDENCE_MAX, Conflict, Feature, Pricing, UseCase

PKB_SCHEMA_VERSION = "0.3"
SchemaVersion = Literal["0.2", "0.3"]  # v0.3 đọc được cả dữ liệu v0.2 (coi như software)

ProductKind = Literal["software", "physical"]
# `merchant` chỉ còn để đọc dữ liệu v0.2. Dữ liệu 0.3 phải dùng `owner` (xem JSON_RULES).
Origin = Literal["crawled", "owner", "inferred", "merchant"]
ItemOrigin = Literal["crawled", "owner"]
# Nguồn dữ liệu có cấu trúc, để kiểm "ưu tiên dữ liệu có cấu trúc, không LLM".
ExtractedVia = Literal["jsonld", "microdata", "og", "embedded", "dom"]
Availability = Literal["in_stock", "out_of_stock", "preorder", "unknown"]
ImageRole = Literal["hero", "gallery"]

SOURCE_ID_PATTERN = r"^src_\d{2}$"
VARIANT_ID_PATTERN = r"^v\d{1,3}$"
UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|\+00:00)$"


class OwnerEdited(BaseModel):
    """Mục có `origin`: nếu là `owner` thì ghi người sửa và thời điểm; `origin` khác thì cấm hai trường này.

    `edited_by` là user id (UUID, không phải email). BE ghi từ phiên đăng nhập, client không tự gửi.
    `edited_at` là ISO 8601 UTC (`...Z` hoặc `...+00:00`), do server ghi.
    """

    edited_by: str | None = Field(
        None, pattern=UUID_PATTERN, description="User id (UUID) của người sửa. Bắt buộc khi origin owner."
    )
    edited_at: str | None = Field(
        None, pattern=UTC_PATTERN, description="Thời điểm sửa, ISO 8601 UTC. Bắt buộc khi origin owner."
    )

    @model_validator(mode="after")
    def owner_edit_fields(self) -> OwnerEdited:
        origin = getattr(self, "origin", None)
        has = self.edited_by is not None or self.edited_at is not None
        if origin == "owner" and (self.edited_by is None or self.edited_at is None):
            raise ValueError("origin owner thì edited_by và edited_at là bắt buộc")
        if origin != "owner" and has:
            raise ValueError("edited_by / edited_at chỉ dùng cho origin owner")
        return self


class SourcedItem(OwnerEdited):
    """Một mục có nguồn của sản phẩm vật lý.

    `crawled`: `source_id` là trang chứa dữ liệu, `evidence` là chuỗi giá trị gốc (≤ 200 ký tự).
    Với dữ liệu có cấu trúc thì evidence là chuỗi nguyên văn trong JSON-LD / meta, vd. `"price":"520000"`.
    `owner`: người dùng nhập hoặc sửa ở bước 2, có thể không có nguồn; kèm `edited_by` + `edited_at`.
    """

    origin: ItemOrigin
    source_id: str | None = Field(None, pattern=SOURCE_ID_PATTERN)
    evidence: str | None = Field(None, min_length=1, max_length=EVIDENCE_MAX)
    extracted_via: ExtractedVia | None = Field(None, description="Cách code lấy ra. Null nếu `owner`.")

    @model_validator(mode="after")
    def crawled_needs_source(self) -> SourcedItem:
        if self.origin == "crawled" and (self.source_id is None or self.evidence is None):
            raise ValueError("origin crawled thì source_id và evidence là bắt buộc")
        return self


# `if origin == crawled then required [source_id, evidence]` cho mọi SourcedItem.
CRAWLED_ITEM_RULE: dict[str, Any] = {
    "if": {"properties": {"origin": {"const": "crawled"}}, "required": ["origin"]},
    "then": {
        "required": ["source_id", "evidence"],
        "properties": {"source_id": {"type": "string"}, "evidence": {"type": "string"}},
    },
}


# `origin == owner` thì bắt buộc edited_by + edited_at; `origin` khác thì hai trường này phải null/vắng.
OWNER_EDIT_RULE: dict[str, Any] = {
    "if": {"required": ["origin"], "properties": {"origin": {"const": "owner"}}},
    "then": {
        "required": ["edited_by", "edited_at"],
        "properties": {"edited_by": {"type": "string"}, "edited_at": {"type": "string"}},
    },
    "else": {"properties": {"edited_by": {"type": "null"}, "edited_at": {"type": "null"}}},
}
# Luật chung cho mọi SourcedItem: crawled cần nguồn, owner cần người sửa.
ITEM_RULE: dict[str, Any] = {"allOf": [CRAWLED_ITEM_RULE, OWNER_EDIT_RULE]}


def _number_needs(field: str, needed: str) -> dict[str, Any]:
    """Khi `field` là số thì `needed` bắt buộc và khác null."""
    return {
        "if": {"required": [field], "properties": {field: {"type": "number"}}},
        "then": {"required": [needed], "properties": {needed: {"type": "string"}}},
    }


class Offer(SourcedItem):
    """1 mức giá của sản phẩm. Giá số là con số in trên trang, không tự quy đổi tiền tệ."""

    price_text: str | None = Field(None, description="Giá nguyên văn, vd. '690,000₫'.")
    amount: float | None = Field(
        None,
        ge=0,
        description="Giá đã chuẩn hoá thành số. Null nếu trang không có giá hoặc chỉ có khoảng giá.",
    )
    currency: str | None = Field(
        None, pattern=r"^[A-Z]{3}$", description="ISO 4217 lấy từ trang. Bắt buộc khi có amount."
    )
    original_amount: float | None = Field(None, ge=0, description="Giá gốc (trước giảm) nếu trang ghi.")
    availability: Availability = "unknown"
    seller: str | None = Field(None, description="Người bán / shop, vd. tên shop.")
    platform: str | None = Field(None, description="Nền tảng hoặc host, vd. 'shop.example.com', 'shopify'.")
    variant_ref: str | None = Field(
        None, pattern=VARIANT_ID_PATTERN, description="Id của variants[] mà giá này áp dụng."
    )

    @model_validator(mode="after")
    def currency_required_with_amount(self) -> Offer:
        if (self.amount is not None or self.original_amount is not None) and self.currency is None:
            raise ValueError("offer có amount thì currency là bắt buộc")
        return self


OFFER_RULE: dict[str, Any] = {
    "allOf": [
        ITEM_RULE,
        _number_needs("amount", "currency"),
        _number_needs("original_amount", "currency"),
    ]
}


class VariantAttribute(BaseModel):
    key: str = Field(description="vd. 'Màu', 'Size', 'Dung tích'.")
    value: str


class Variant(SourcedItem):
    """Biến thể. KHÔNG chứa giá: giá nằm ở `offers[]`, liên kết bằng `variant_ref`."""

    id: str = Field(pattern=VARIANT_ID_PATTERN, description="Code điền (v1, v2…). Duy nhất trong PKB.")
    name: str
    attributes: list[VariantAttribute] = Field(default_factory=list)
    sku: str | None = None
    selected: bool = Field(False, description="Biến thể đang được chọn khi crawl. Tối đa 1.")


class Spec(SourcedItem):
    key: str
    value: str
    unit: str | None = None


class Image(SourcedItem):
    """Ảnh sản phẩm. `source_id` là TRANG chứa URL ảnh, không phải host CDN."""

    url: str | None = Field(
        None, description="URL ảnh gốc. Chỉ để ghi nguồn; ảnh dùng cho video lấy từ Storage."
    )
    storage_path: str | None = Field(None, description="Đường dẫn Storage (private) của ảnh đã tải.")
    alt: str | None = None
    role: ImageRole
    variant_ref: str | None = Field(
        None, pattern=VARIANT_ID_PATTERN, description="Ảnh của biến thể nào. Null = chung cho cả sản phẩm."
    )
    generic: bool = Field(
        False, description="Ảnh chung của site (banner `og:image`), không phải ảnh sản phẩm."
    )

    @model_validator(mode="after")
    def has_location(self) -> Image:
        if self.url is None and self.storage_path is None:
            raise ValueError("ảnh cần url hoặc storage_path")
        return self


IMAGE_RULE: dict[str, Any] = {
    "allOf": [
        ITEM_RULE,
        {
            "anyOf": [
                {"required": ["url"], "properties": {"url": {"type": "string"}}},
                {"required": ["storage_path"], "properties": {"storage_path": {"type": "string"}}},
            ]
        },
    ]
}

# Tối đa 1 phần tử thoả điều kiện: `contains` + `maxContains` (JSON Schema 2020-12).
AT_MOST_ONE_SELECTED = {
    "contains": {"properties": {"selected": {"const": True}}, "required": ["selected"]},
    "minContains": 0,
    "maxContains": 1,
}
AT_MOST_ONE_HERO = {
    "contains": {"properties": {"role": {"const": "hero"}}, "required": ["role"]},
    "minContains": 0,
    "maxContains": 1,
}


class Media(BaseModel):
    images: list[Image] = Field(default_factory=list, json_schema_extra=AT_MOST_ONE_HERO)


class PreviousValue(BaseModel):
    """Giá trị ĐÃ CRAWL bị owner ghi đè, giữ lại để đối chiếu. Luôn là giá trị crawl, không bao giờ là
    giá trị owner nhập trước đó: owner sửa nhiều lần thì `previous` không đổi (lịch sử sửa do BE lưu)."""

    value: str
    source_id: str = Field(pattern=SOURCE_ID_PATTERN, description="Trang nguồn của giá trị đã crawl.")
    evidence: str = Field(min_length=1, max_length=EVIDENCE_MAX)


class IdentityFact(SourcedItem):
    """Fact văn bản của `identity` mà owner được sửa ở bản nháp. Dữ liệu v0.2 (`TextFact`) đọc được như `crawled`.

    `origin: owner` nghĩa là chưa kiểm chứng (kể cả sku / gtin do owner nhập): không có cờ `verified`.
    """

    value: str
    previous: PreviousValue | None = Field(
        None, description="Giá trị đã crawl bị ghi đè. Chỉ khi origin owner và đã có giá trị crawl."
    )

    @model_validator(mode="after")
    def previous_only_for_owner(self) -> IdentityFact:
        if self.previous is not None and self.origin != "owner":
            raise ValueError("previous chỉ dùng khi origin owner")
        return self


# SourcedItem + `previous` chỉ có khi origin owner.
IDENTITY_FACT_RULE: dict[str, Any] = {
    "allOf": [
        ITEM_RULE,
        {
            "if": {"required": ["origin"], "properties": {"origin": {"const": "owner"}}},
            "else": {"properties": {"previous": {"type": "null"}}},
        },
    ]
}


class Identity(v02.Identity):
    # Trường owner được sửa ở bản nháp. `tagline`, `company`, `version`, `models`, `website` giữ như v0.2.
    name: IdentityFact  # type: ignore[assignment]
    description: IdentityFact | None = None  # type: ignore[assignment]
    category: IdentityFact | None = Field(  # type: ignore[assignment]
        None, description="Loại product, vd. 'AI assistant', 'Bình giữ nhiệt'."
    )
    product_kind: ProductKind | None = Field(
        None, description="software | physical. Bắt buộc khi schema_version 0.3; v0.2 không có = software."
    )
    brand_name: IdentityFact | None = Field(
        None, description="Thương hiệu (khác `company`), vd. 'Acme Demo'."
    )
    sku: IdentityFact | None = Field(None, description="Mã sản phẩm / model của sản phẩm vật lý.")
    gtin: IdentityFact | None = Field(None, description="GTIN / mã vạch (EAN, UPC) nếu trang ghi.")


# ---------------------------------------------------------------- 1.5–1.6 (optional)
class Claim(OwnerEdited):
    """Mục không bắt buộc có nguồn crawl: origin cho biết ai nói. `merchant` đã đổi tên thành `owner`.

    `origin: owner` bắt buộc `edited_by` + `edited_at`. `merchant` (chỉ dữ liệu v0.2) không có hai trường này.
    """

    origin: Origin
    source_id: str | None = Field(None, pattern=SOURCE_ID_PATTERN)
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
    """DEPRECATED (P1 bỏ affiliate). Chỉ để đọc dữ liệu v0.2, dữ liệu 0.3 không được có."""

    link: str | None = None
    commission: str | None = None


class Quality(BaseModel):
    completeness: float | None = Field(None, ge=0, le=1)
    conflicts: list[Conflict] = Field(default_factory=list)


class PKBData(BaseModel):
    """Nội dung cột `product_knowledge.data`."""

    schema_version: SchemaVersion = Field(
        description="Version của contract. Bắt buộc: '0.3' (đọc được cả '0.2')."
    )
    identity: Identity
    pricing: Pricing | None = Field(None, description="Bắt buộc khi software. Với physical thì không cần.")
    features: list[Feature] = Field(
        default_factory=list, description="Physical: lợi ích / điểm bán (LLM, có evidence)."
    )
    use_cases: list[UseCase] = Field(default_factory=list)
    limitations: list[v02.Limitation] = Field(default_factory=list)
    offers: list[Offer] = Field(default_factory=list, description="Chỉ physical. Cần ≥ 1.")
    variants: list[Variant] = Field(default_factory=list, json_schema_extra=AT_MOST_ONE_SELECTED)
    specs: list[Spec] = Field(default_factory=list)
    media: Media | None = None
    audiences: list[Audience] = Field(default_factory=list)
    usp: list[Usp] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    brand: Brand | None = None
    compliance: Compliance | None = None
    affiliate: Affiliate | None = Field(
        None, description="DEPRECATED. Chỉ có trong dữ liệu v0.2.", json_schema_extra={"deprecated": True}
    )
    quality: Quality | None = None

    @model_validator(mode="after")
    def kind_rules(self) -> PKBData:
        kind = self.identity.product_kind
        v03 = self.schema_version == "0.3"
        if v03 and kind is None:
            raise ValueError("schema_version 0.3 thì identity.product_kind là bắt buộc")
        if kind == "physical":
            if not self.offers:
                raise ValueError("physical thì offers cần ít nhất 1 phần tử")
        else:  # software, hoặc v0.2 không có product_kind
            if self.pricing is None:
                raise ValueError("software thì pricing là bắt buộc")
            if self.offers or self.variants or self.specs:
                raise ValueError("offers, variants, specs chỉ dùng cho physical")
        if v03:
            if self.affiliate is not None:
                raise ValueError("affiliate đã deprecated, dữ liệu 0.3 không được có")
            claims = [*self.audiences, *self.usp, *self.competitors, self.brand, self.compliance]
            if any(c is not None and c.origin == "merchant" for c in claims):
                raise ValueError("origin 'merchant' đã đổi thành 'owner' trong 0.3")
        return self

    @model_validator(mode="after")
    def refs_are_consistent(self) -> PKBData:
        ids = [v.id for v in self.variants]
        if len(ids) != len(set(ids)):
            raise ValueError("variants[].id phải duy nhất")
        if sum(v.selected for v in self.variants) > 1:
            raise ValueError("chỉ được 1 variant selected")
        images = self.media.images if self.media else []
        if sum(i.role == "hero" for i in images) > 1:
            raise ValueError("chỉ được 1 ảnh hero")
        refs = [o.variant_ref for o in self.offers] + [i.variant_ref for i in images]
        dangling = {r for r in refs if r is not None and r not in ids}
        if dangling:
            raise ValueError(f"variant_ref không trỏ tới variant nào: {sorted(dangling)}")
        return self


def _origin_not_merchant(path: str) -> dict[str, Any]:
    items = {"properties": {"origin": {"not": {"const": "merchant"}}}}
    return {path: {"items": items} if path in ("audiences", "usp", "competitors") else items}


# Luật gốc của PKBData, gắn vào schema xuất ra. 2 khối độc lập nên đặt trong allOf.
PKB_ROOT_RULE: dict[str, Any] = {
    "allOf": [
        {  # physical cần offers; software cần pricing và không có offers / variants / specs
            "if": {
                "required": ["identity"],
                "properties": {
                    "identity": {
                        "required": ["product_kind"],
                        "properties": {"product_kind": {"const": "physical"}},
                    }
                },
            },
            "then": {"required": ["offers"], "properties": {"offers": {"minItems": 1}}},
            "else": {
                "required": ["pricing"],
                "properties": {
                    "pricing": {"type": "object"},
                    "offers": {"maxItems": 0},
                    "variants": {"maxItems": 0},
                    "specs": {"maxItems": 0},
                },
            },
        },
        {  # dữ liệu 0.3: có product_kind, không merchant, không affiliate
            "if": {"required": ["schema_version"], "properties": {"schema_version": {"const": "0.3"}}},
            "then": {
                "properties": {
                    "identity": {
                        "required": ["product_kind"],
                        "properties": {"product_kind": {"type": "string"}},
                    },
                    **_origin_not_merchant("audiences"),
                    **_origin_not_merchant("usp"),
                    **_origin_not_merchant("competitors"),
                    **_origin_not_merchant("brand"),
                    **_origin_not_merchant("compliance"),
                    "affiliate": {"type": "null"},
                }
            },
        },
    ]
}

# Lớp Pydantic -> luật JSON Schema bổ sung (export_schema.py gắn vào định nghĩa của lớp đó).
JSON_RULES: dict[type, dict[str, Any]] = {
    v02.Plan: v02.PLAN_PRICE_RULE,
    Offer: OFFER_RULE,
    Variant: ITEM_RULE,
    Spec: ITEM_RULE,
    Image: IMAGE_RULE,
    IdentityFact: IDENTITY_FACT_RULE,
    Audience: OWNER_EDIT_RULE,
    Usp: OWNER_EDIT_RULE,
    Competitor: OWNER_EDIT_RULE,
    Brand: OWNER_EDIT_RULE,
    Compliance: OWNER_EDIT_RULE,
    Affiliate: OWNER_EDIT_RULE,
    PKBData: PKB_ROOT_RULE,
}


class Source(v02.Source):
    """1 phần tử của cột `product_knowledge.sources`."""

    structured_path: str | None = Field(
        None,
        description=(
            "Đường dẫn Storage (private) của bản chụp dữ liệu có cấu trúc (JSON-LD, meta, microdata) "
            "đã trích từ trang này. Evidence của fact lấy từ dữ liệu có cấu trúc được đối chiếu với file này."
        ),
    )
