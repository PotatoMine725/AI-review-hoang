"""Spike M1 — 1.4 Structured extraction bằng Gemini.

Mọi lời gọi Gemini đi qua 1 adapter: `call_gemini` (và `count_tokens` để ước tính trước khi gọi).
Model và bảng giá nằm trong config.py.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types

import config
from schema import EVIDENCE_MAX, PKBExtract

ROOT = Path(__file__).parent

SYSTEM_PROMPT = """Bạn trích xuất fact về 1 sản phẩm phần mềm/AI từ các trang web đã crawl, thành JSON theo schema.

Quy tắc:
- Chỉ dùng thông tin có trong các trang nguồn. Không suy đoán, không dùng kiến thức bên ngoài.
- Mỗi fact ghi `source_id` của trang chứa nó và `evidence`: 1 đoạn trích NGUYÊN VĂN, liên tục, từ trang đó
  (copy đúng chữ, ≤ 200 ký tự). Không viết lại evidence.
- `origin` luôn là "crawled".
- Giữ nguyên ngôn ngữ của trang nguồn cho tên và mô tả.
- pricing.plans: mỗi plan × mỗi cách tính tiền (trả tháng / trả năm) là 1 mục. Ghi `price_text` nguyên văn,
  `price` là số (null nếu không có giá, vd. "Contact sales"), `currency` theo mã ISO 4217 (USD, VND…).
  Chỉ lấy plan của sản phẩm chính; bỏ giá API theo token nếu nó không phải plan.
- features: tính năng cụ thể của sản phẩm (tối đa 15, quan trọng nhất trước). use_cases: tối đa 8. limitations: hạn
  chế, giới hạn dùng, điều kiện được ghi rõ (tối đa 8).
- Không tìm thấy thì để null hoặc danh sách rỗng."""


# ---------------------------------------------------------------- env + client
def load_env(path: Path = ROOT / ".env") -> None:
    """Đọc KEY=VALUE từ .env vào os.environ (không ghi đè biến đã có). Không cần thêm thư viện."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def make_client() -> genai.Client:
    load_env()
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("Thiếu GEMINI_API_KEY: đặt vào spikes/m1-crawl-extract/.env (xem .env.example).")
    retry = types.HttpRetryOptions(attempts=4, initial_delay=5.0, http_status_codes=[429, 500, 503])
    return genai.Client(api_key=key, http_options=types.HttpOptions(retry_options=retry))


# ---------------------------------------------------------------- adapter
@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int  # candidates + thoughts (cả hai tính giá output)
    thoughts_tokens: int
    seconds: float
    finish_reason: str = ""  # STOP = xong; MAX_TOKENS = bị cắt


def count_tokens(client: genai.Client, model: str, user_prompt: str) -> int:
    """Đếm token input (system prompt + user prompt). Chưa tính phần JSON schema gửi kèm."""
    resp = client.models.count_tokens(model=model, contents=SYSTEM_PROMPT + "\n\n" + user_prompt)
    return resp.total_tokens or 0


def call_gemini(client: genai.Client, model: str, user_prompt: str, max_output_tokens: int) -> LLMResult:
    """Adapter duy nhất gọi Gemini: structured output theo PKBExtract."""
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=config.TEMPERATURE,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
        response_json_schema=PKBExtract.model_json_schema(),
    )
    t0 = time.monotonic()
    resp = client.models.generate_content(model=model, contents=user_prompt, config=cfg)
    seconds = round(time.monotonic() - t0, 2)
    usage = resp.usage_metadata
    thoughts = (usage.thoughts_token_count or 0) if usage else 0
    finish = resp.candidates[0].finish_reason if resp.candidates else None
    return LLMResult(
        text=resp.text or "",
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=((usage.candidates_token_count or 0) if usage else 0) + thoughts,
        thoughts_tokens=thoughts,
        seconds=seconds,
        finish_reason=getattr(finish, "name", str(finish or "")),
    )


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = config.MODELS[model]
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


# ---------------------------------------------------------------- prompt
MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HEADER = re.compile(r"\A<!--.*?-->\s*", re.DOTALL)


def clean_for_llm(md: str) -> str:
    """Bỏ header, ảnh và URL đích của link (giữ chữ của link). URL dài chiếm nhiều token mà không chứa fact."""
    md = HEADER.sub("", md)
    md = MD_IMAGE.sub("", md)
    md = MD_LINK.sub(r"\1", md)
    lines = [ln.rstrip() for ln in md.splitlines()]
    return "\n".join(ln for ln in lines if ln.strip())


def build_prompt(product_name: str, docs: list[dict]) -> str:
    parts = [f"Sản phẩm: {product_name}\n"]
    for d in docs:
        parts.append(
            f"=== SOURCE {d['source_id']} | page_type: {d['page_type']} | url: {d['url']} ===\n{d['text']}\n"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------- kiểm tra evidence
def _norm(s: str) -> str:
    s = re.sub(r"[*_`#|>\\]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def iter_facts(obj):
    """Duyệt mọi dict có khoá source_id (tức là 1 fact)."""
    if isinstance(obj, dict):
        if "source_id" in obj:
            yield obj
        for v in obj.values():
            yield from iter_facts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_facts(v)


def check_evidence(pkb: dict, texts: dict[str, str]) -> tuple[float, list[str], int]:
    """Trả (tỉ lệ evidence có nguyên văn trong trang nguồn, source_id lạ, số fact)."""
    norm_texts = {k: _norm(v) for k, v in texts.items()}
    facts = list(iter_facts(pkb))
    unknown = sorted({f.get("source_id", "") for f in facts if f.get("source_id") not in texts})
    hit = sum(
        1
        for f in facts
        if f.get("source_id") in norm_texts and _norm(f.get("evidence", "")) in norm_texts[f["source_id"]]
    )
    return (round(hit / len(facts), 3) if facts else 0.0), unknown, len(facts)


# ---------------------------------------------------------------- gộp kết quả mode per_page
def _key(*vals) -> str:
    return "|".join(_norm(str(v or "")) for v in vals)


def merge(parts: list[dict]) -> dict:
    """Gộp PKB từng trang (thứ tự = thứ tự ưu tiên trang). Trường đơn: lấy giá trị đầu tiên khác null.
    Danh sách: nối và bỏ trùng theo tên/giá trị."""
    out: dict = {
        "identity": {"models": []},
        "pricing": {"plans": []},
        "features": [],
        "use_cases": [],
        "limitations": [],
    }
    seen: dict[str, set[str]] = {}

    def add(lst: list, item: dict, group: str, key: str) -> None:
        bucket = seen.setdefault(group, set())
        if key not in bucket:
            bucket.add(key)
            lst.append(item)

    for p in parts:
        ident = p.get("identity") or {}
        for field, value in ident.items():
            if field == "models":
                for m in value or []:
                    add(out["identity"]["models"], m, "models", _key(m.get("name")))
            elif value and not out["identity"].get(field):
                out["identity"][field] = value
        pricing = p.get("pricing") or {}
        for field, value in pricing.items():
            if field == "plans":
                for pl in value or []:
                    add(out["pricing"]["plans"], pl, "plans", _key(pl.get("name"), pl.get("price_text")))
            elif value and not out["pricing"].get(field):
                out["pricing"][field] = value
        for f in p.get("features") or []:
            add(out["features"], f, "features", _key(f.get("name")))
        for group in ("use_cases", "limitations"):
            for f in p.get(group) or []:
                add(out[group], f, group, _key(f.get("value")))
    # Trang không phải pricing hay nhắc tên plan mà không có giá ("Pro and Max plans"):
    # bỏ mục không có số nếu đã có mục cùng tên kèm giá.
    plans = out["pricing"]["plans"]
    priced = {_key(pl.get("name")) for pl in plans if re.search(r"\d", pl.get("price_text") or "")}
    out["pricing"]["plans"] = [
        pl
        for pl in plans
        if re.search(r"\d", pl.get("price_text") or "") or _key(pl.get("name")) not in priced
    ]
    return out


def repair_evidence(data: dict) -> int:
    """Gemini không luôn tuân maxLength trong schema. Cắt evidence > EVIDENCE_MAX tại ranh giới từ
    (vẫn là đoạn trích nguyên văn, nên vẫn kiểm được trong trang nguồn). Trả số evidence đã cắt."""
    n = 0
    for f in iter_facts(data):
        ev = f.get("evidence")
        if isinstance(ev, str) and len(ev) > EVIDENCE_MAX:
            f["evidence"] = ev[:EVIDENCE_MAX].rsplit(" ", 1)[0]
            n += 1
    return n


def parse_extract(text: str) -> tuple[dict | None, str, int]:
    """Trả (dict, lỗi, số evidence đã cắt). dict khác None nếu là JSON; lỗi rỗng nếu hợp lệ theo PKBExtract
    sau khi sửa evidence quá dài."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"json: {e}", 0
    repaired = repair_evidence(data)
    try:
        PKBExtract.model_validate(data)
    except Exception as e:  # noqa: BLE001 — ghi lỗi validate vào kết quả
        return data, f"schema: {str(e)[:500]}", repaired
    return data, "", repaired
