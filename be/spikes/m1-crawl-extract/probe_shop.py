"""Probe khảo sát URL shop (P1-03, `docs/report/p1-shop-url-survey.md`).

Dùng lại module crawl của worker (`worker.m1.crawl`), nên chạy bằng môi trường của worker:

    cd services/worker
    uv run python ../../spikes/m1-crawl-extract/probe_shop.py <out.json> <url>... [ro:<url>...]

`ro:<url>` chỉ kiểm robots cho mẫu đường dẫn, không gửi request trang.

Tuân thủ: robots trước (UA dự án); bị disallow thì KHÔNG gửi request trang. Mỗi URL: 1 GET tĩnh
(không JS) + 1 lần render Crawl4AI + 1 GET ảnh (sau khi kiểm robots host ảnh), cách nhau ≥ 1 s/host.
Không stealth, không đổi UA, không proxy. Chỉ lưu tóm tắt, không lưu HTML/markdown thô.
Không dùng CLI `python -m worker.m1.crawl` vì nó mở rộng tới 30 trang từ gốc và bỏ HTML,
trong khi cần JSON-LD / OpenGraph trên đúng 1 trang sản phẩm.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from worker.m1.config import CrawlSettings
from worker.m1.crawl.blocks import detect_block, waf_challenge_response
from worker.m1.crawl.fetcher import Crawl4AIFetcher
from worker.m1.crawl.http import UrllibHttpClient
from worker.m1.crawl.robots import fetch_robots
from worker.m1.crawl.throttle import Throttle

PRODUCT_TYPES = {"product", "productgroup", "individualproduct"}
OFFER_TYPES = {"offer", "aggregateoffer"}


class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ldjson: list[str] = []
        self.meta: dict[str, str] = {}
        self.itemtypes: list[str] = []
        self._in_ld = False
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ld, self._buf = True, []
        elif tag == "meta":
            key = a.get("property") or a.get("name")
            if key and "content" in a:
                self.meta.setdefault(key.lower(), a["content"])
        if "itemtype" in a:
            self.itemtypes.append(a["itemtype"])

    def handle_data(self, data: str) -> None:
        if self._in_ld:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_ld:
            self.ldjson.append("".join(self._buf))
            self._in_ld = False


def _types(node: dict) -> set[str]:
    t = node.get("@type", [])
    t = [t] if isinstance(t, str) else t
    return {str(x).rsplit("/", 1)[-1].lower() for x in t}


def _walk(node, out: list[dict]) -> None:
    if isinstance(node, list):
        for n in node:
            _walk(n, out)
    elif isinstance(node, dict):
        out.append(node)
        for v in node.values():
            if isinstance(v, (dict, list)):
                _walk(v, out)


def analyze_html(html: str) -> dict:
    s = _Scan()
    try:
        s.feed(html)
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)}
    nodes: list[dict] = []
    bad_json = 0
    for raw in s.ldjson:
        try:
            _walk(json.loads(raw), nodes)
        except json.JSONDecodeError:
            bad_json += 1
    products = [n for n in nodes if _types(n) & PRODUCT_TYPES]
    offers = [n for n in nodes if _types(n) & OFFER_TYPES]
    prices, currencies, avail = set(), set(), set()
    for o in offers:
        sub: list[dict] = []
        _walk(o, sub)  # giá có thể nằm trong priceSpecification lồng bên trong
        for d in sub:
            for k in ("price", "lowPrice", "highPrice"):
                if d.get(k) not in (None, ""):
                    prices.add(str(d[k]))
            if d.get("priceCurrency"):
                currencies.add(str(d["priceCurrency"]))
        if o.get("availability"):
            avail.add(str(o["availability"]).rsplit("/", 1)[-1])
    variants = sum(len(p["hasVariant"]) for p in products if isinstance(p.get("hasVariant"), list))
    img = None
    for p in products:
        im = p.get("image")
        im = im[0] if isinstance(im, list) and im else im
        if isinstance(im, dict):
            im = im.get("url")
        if isinstance(im, str):
            img = im
            break
    img = img or s.meta.get("og:image")
    m = s.meta
    return {
        "ldjson_blocks": len(s.ldjson),
        "ldjson_bad": bad_json,
        "ld_product": bool(products),
        "ld_product_types": sorted({t for p in products for t in _types(p)}),
        "ld_offer": bool(offers),
        "ld_offer_types": sorted({t for o in offers for t in _types(o)}),
        "ld_prices": sorted(prices)[:6],
        "ld_currency": sorted(currencies),
        "ld_availability": sorted(avail),
        "ld_hasVariant": variants,
        "ld_offers_count": len(offers),
        "ld_has_brand": any(p.get("brand") for p in products),
        "ld_has_sku": any(p.get("sku") or p.get("mpn") or p.get("gtin13") for p in products),
        "ld_has_description": any(p.get("description") for p in products),
        "ld_aggregateRating": any(p.get("aggregateRating") for p in products),
        "microdata_product": any("product" in t.lower() for t in s.itemtypes),
        "og": {k: (v[:80]) for k, v in m.items() if k.startswith("og:") and k != "og:description"},
        "og_price": {k: v for k, v in m.items() if "price" in k},
        "image_candidate": img,
        "html_chars": len(html),
        "platform": [
            name
            for name, pat in {
                "shopify": r"cdn\.shopify\.com|Shopify\.theme",
                "haravan": r"hstatic\.net|haravan",
                "sapo": r"bizweb|sapo\.vn|sapocdn|mysapo",
                "woocommerce": r"woocommerce",
                "magento": r"Magento_|/static/version\d+/frontend/",
                "demandware_sfcc": r"demandware",
                "lazada_moduleData": r"__moduleData__",
                "nextjs": r"__NEXT_DATA__",
            }.items()
            if re.search(pat, html, re.IGNORECASE)
        ],
    }


def price_in_text(html: str, prices: list[str]) -> bool | None:
    """Giá trong JSON-LD có xuất hiện (dạng số) trong HTML hay không."""
    if not prices:
        return None
    return any(p.split(".")[0] in html for p in prices if p)


async def probe(url: str, settings: CrawlSettings, throttle: Throttle, http, fetcher) -> dict:
    rec: dict = {"url": url, "host": urlsplit(url).netloc}
    base = f"https://{rec['host']}"
    robots = await fetch_robots(base, throttle, http, settings)
    allowed, rule = robots.decide(url)
    rec["robots"] = {
        "status": robots.status,
        "policy": robots.policy,
        "group": robots.group,
        "allowed": allowed,
        "rule": rule,
        "crawl_delay": robots.crawl_delay,
        "error": robots.error[:120],
    }
    if not allowed:
        rec["verdict"] = "robots_disallow_no_page_request"
        return rec

    # 1) GET tĩnh (không JS)
    await throttle.wait(url, "page")
    resp = await http.get(url)
    body = resp.body.decode("utf-8", errors="replace")
    rec["static"] = {
        "status": resp.status,
        "waf": waf_challenge_response(resp),
        "error": resp.error[:120],
        "final_note": "",
        **(analyze_html(body) if resp.status == 200 else {}),
    }
    if resp.status == 200 and rec["static"].get("ld_prices") is not None:
        rec["static"]["price_in_html"] = price_in_text(body, rec["static"]["ld_prices"])

    # 2) Render Crawl4AI
    await throttle.wait(url, "page")
    fr = await fetcher.fetch(url)
    block = detect_block(fr, True, settings.min_home_chars)
    rec["rendered"] = {
        "status": fr.status_code,
        "success": fr.success,
        "redirected_url": fr.redirected_url,
        "block": (block.kind + ":" + block.detail[:100]) if block else None,
        "raw_md_chars": len(fr.raw_markdown),
        "title": fr.title[:100],
        **(analyze_html(fr.html) if fr.html else {}),
    }
    # giá có trong markdown render?
    prices = rec["rendered"].get("ld_prices") or rec["static"].get("ld_prices") or []
    rec["rendered"]["price_in_markdown"] = (
        any(p.split(".")[0] in fr.raw_markdown for p in prices) if prices else None
    )

    # 3) Ảnh hero
    img = rec["static"].get("image_candidate") or rec["rendered"].get("image_candidate")
    if img:
        img_url = urljoin(url, img)
        ihost = urlsplit(img_url).netloc
        irobots = await fetch_robots(f"https://{ihost}", throttle, http, settings)
        iallowed, _irule = irobots.decide(img_url)
        rec["image"] = {"url": img_url[:200], "robots_allowed": iallowed}
        if iallowed:
            await throttle.wait(img_url, "page")
            ir = await http.get(img_url)
            rec["image"].update(
                status=ir.status,
                content_type=ir.headers.get("content-type"),
                bytes=len(ir.body),
            )
    rec["verdict"] = "probed"
    return rec


async def main(out: str, urls: list[str], robots_only: list[str]) -> None:
    settings = CrawlSettings.from_env()
    throttle = Throttle(settings.min_interval_s)
    http = UrllibHttpClient(settings.user_agent, settings.http_timeout_s)
    results = []
    async with Crawl4AIFetcher(settings) as fetcher:
        for url in urls:
            print("probing", url, flush=True)
            try:
                results.append(await probe(url, settings, throttle, http, fetcher))
            except Exception as e:  # noqa: BLE001
                results.append({"url": url, "verdict": f"probe_error: {type(e).__name__}: {e}"})
    for url in robots_only:  # chỉ kiểm robots cho mẫu đường dẫn, không gửi request trang
        host = urlsplit(url).netloc
        robots = await fetch_robots(f"https://{host}", throttle, http, settings)
        allowed, rule = robots.decide(url)
        results.append(
            {
                "url": url,
                "host": host,
                "verdict": "robots_only_no_page_request",
                "robots": {
                    "status": robots.status,
                    "policy": robots.policy,
                    "group": robots.group,
                    "allowed": allowed,
                    "rule": rule,
                    "error": robots.error[:160],
                },
            }
        )
    Path(out).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("min_interval", throttle.min_observed_interval())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    args = sys.argv[2:]
    ro = [a[3:] for a in args if a.startswith("ro:")]
    asyncio.run(main(sys.argv[1], [a for a in args if not a.startswith("ro:")], ro))
