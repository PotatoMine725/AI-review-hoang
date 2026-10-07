"""Spike M1 — trang demo: đọc output đã có, sinh 1 file HTML tĩnh `output/demo.html`.

  uv run python demo.py                              # PKB mode batch của gemini-3.5-flash-lite
  uv run python demo.py --model gemini-3.1-flash-lite

Không gọi LLM, không crawl, không cần mạng. Chỉ dùng thư viện chuẩn.
Mọi chuỗi lấy từ PKB / web / README đều đi qua `esc()` trước khi chèn vào HTML.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from schema import PKB_SCHEMA_VERSION

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
OUT_FILE = OUTPUT_DIR / "demo.html"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Mục "Đề xuất cho đặc tả v0.2" trong README: các số thứ tự nói về giá (1, 2, 4, 5)
PRICE_LESSON_ITEMS = (1, 2, 4, 5)
LESSON_MAX_CHARS = 170
LESSON_HEADING = "## Đề xuất cho đặc tả v0.2"

CSS = """
:root { --fg:#1b1f24; --muted:#57606a; --line:#d0d7de; --bg:#fff; --soft:#f6f8fa; --accent:#0b5cad;
        --ok:#1a7f37; --bad:#c62828; --hl:#fff4c2; }
* { box-sizing:border-box; }
body { margin:0; font:18px/1.55 system-ui,"Segoe UI",Roboto,sans-serif; color:var(--fg); background:var(--bg); }
main { max-width:1400px; margin:0 auto; padding:24px 32px 64px; }
h1 { font-size:34px; margin:0 0 8px; }
h2 { font-size:28px; margin:48px 0 12px; border-bottom:2px solid var(--line); padding-bottom:6px; }
h3 { font-size:21px; margin:28px 0 8px; }
.flow { font-size:22px; font-weight:600; color:var(--accent); margin:8px 0 12px; overflow-wrap:anywhere; }
.meta { color:var(--muted); margin:0; }
.meta b { color:var(--fg); }
table { width:100%; border-collapse:collapse; table-layout:fixed; margin:8px 0 16px; }
th, td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top;
         overflow-wrap:anywhere; }
th { background:var(--soft); }
td.num, th.num { text-align:right; }
tr.hl td { background:var(--hl); font-weight:600; }
.ok { color:var(--ok); font-weight:700; }
.bad { color:var(--bad); font-weight:700; }
dl.id { display:grid; grid-template-columns:max-content 1fr; gap:4px 20px; margin:8px 0; }
dl.id dt { color:var(--muted); }
dl.id dd { margin:0; overflow-wrap:anywhere; }
ul.facts { list-style:none; padding:0; margin:8px 0; }
ul.facts li { border-left:4px solid var(--line); padding:6px 12px; margin:8px 0; }
ul.facts .desc { color:var(--muted); }
.ev { color:var(--muted); font-style:italic; white-space:pre-line; overflow-wrap:anywhere; }
.src { font-size:16px; }
a { color:var(--accent); }
.warn { background:var(--hl); border-radius:4px; padding:0 6px; font-size:16px; }
ul.lessons li { margin:8px 0; }
.card { border:1px solid var(--line); border-radius:8px; padding:12px 24px 20px; margin:24px 0; }
.card > h2 { margin-top:12px; }
"""


def esc(value: object) -> str:
    """Escape mọi chuỗi từ nguồn ngoài. `None` → chuỗi rỗng."""
    return html.escape("" if value is None else str(value), quote=True)


# ---------------------------------------------------------------- đọc dữ liệu
def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def available_models() -> list[str]:
    names = {p.name[4:-5] for p in OUTPUT_DIR.glob("*/pkb.*.json") if ".per-page" not in p.name}
    return sorted(names)


def load_metrics() -> list[dict]:
    with (OUTPUT_DIR / "metrics.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_lessons() -> list[tuple[str, str]]:
    """Lấy (tiêu đề in đậm, câu đầu của phần giải thích) từ mục đề xuất v0.2 trong README."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.find(LESSON_HEADING)
    if start < 0:
        return []
    section = text[start + len(LESSON_HEADING) :]
    nxt = re.search(r"^## ", section, flags=re.MULTILINE)
    section = section[: nxt.start()] if nxt else section
    lessons = []
    for m in re.finditer(
        r"^(\d+)\. \*\*(.+?)\*\*\s*(.*?)(?=^\d+\. |\Z)", section, flags=re.MULTILINE | re.DOTALL
    ):
        if int(m.group(1)) not in PRICE_LESSON_ITEMS:
            continue
        rest = re.sub(r"\s+", " ", m.group(3).replace("`", "")).strip()
        first = re.split(r"(?<=\.)\s", rest, maxsplit=1)[0] if rest else ""
        if len(first) > LESSON_MAX_CHARS:
            first = first[:LESSON_MAX_CHARS].rsplit(" ", 1)[0] + "…"
        lessons.append((m.group(2).replace("`", "").rstrip("."), first))
    return lessons


# ---------------------------------------------------------------- dựng HTML
def fmt_price(price: float | None) -> str:
    if price is None:
        return "—"
    return f"{price:,.0f}" if price == int(price) else f"{price:,.2f}"


def short_url(url: str) -> str:
    p = urlparse(url)
    return (p.netloc + p.path).rstrip("/")


def source_link(source_id: str, sources: dict[str, dict]) -> str:
    src = sources.get(source_id)
    if src is None:
        return f'<span class="warn">{esc(source_id)}: không có trong sources</span>'
    url = src["url"]
    label = f"{esc(source_id)} · {esc(short_url(url))}"
    if urlparse(url).scheme not in ("http", "https"):  # không tạo link nếu scheme lạ (vd. javascript:)
        return label
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{label}</a>'


def fact_item(title: str, desc: str | None, fact: dict, sources: dict[str, dict]) -> str:
    desc_html = f' <span class="desc">— {esc(desc)}</span>' if desc else ""
    return (
        "<li>"
        f"<div><b>{esc(title)}</b>{desc_html}</div>"
        f'<div class="ev">“{esc(fact.get("evidence"))}”</div>'
        f'<div class="src">{source_link(fact.get("source_id", ""), sources)}</div>'
        "</li>"
    )


def fact_list(heading: str, items: list[str]) -> str:
    if not items:
        return f"<h3>{esc(heading)}</h3><p class='meta'>Không có.</p>"
    return f'<h3>{esc(heading)} ({len(items)})</h3><ul class="facts">{"".join(items)}</ul>'


def identity_html(pkb: dict, product: dict) -> str:
    ident = pkb["identity"]

    def val(key: str) -> str:
        fact = ident.get(key)
        return esc(fact["value"]) if fact else "—"

    models = ", ".join(esc(m["name"]) for m in ident.get("models", [])) or "—"
    rows = [
        ("Tên", val("name")),
        ("Website", esc(product["url"])),
        ("Loại", val("category")),
        ("Version", val("version")),
        ("Models", models),
        ("Tagline", val("tagline")),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return f'<h3>Identity</h3><dl class="id">{dl}</dl>'


def plans_html(data: dict) -> str:
    pricing = data["pricing"]
    plans = pricing.get("plans", [])
    head = (
        "<tr><th style='width:11%'>Plan</th><th class='num' style='width:9%'>list_price</th>"
        "<th class='num' style='width:9%'>promo_price</th><th style='width:8%'>Tiền tệ</th>"
        "<th style='width:10%'>price_unit</th><th style='width:10%'>billing_cycle</th>"
        "<th>price_text (nguyên văn)</th></tr>"
    )
    rows = "".join(
        f"<tr><td>{esc(p['name'])}</td><td class='num'>{esc(fmt_price(p.get('list_price')))}</td>"
        f"<td class='num' title='{esc(p.get('promo_terms'))}'>{esc(fmt_price(p.get('promo_price')))}</td>"
        f"<td>{esc(p.get('currency') or '—')}</td><td>{esc(p.get('price_unit') or '—')}</td>"
        f"<td>{esc(p.get('billing_cycle') or '—')}</td><td>{esc(p.get('price_text'))}</td></tr>"
        for p in plans
    )
    views = (
        f"Tab mặc định: <b>{esc(pricing.get('default_view') or '—')}</b> · "
        f"tab chưa lấy: <b>{esc(', '.join(pricing.get('other_views') or []) or '—')}</b> · "
        f"vùng IP: <b>{esc(pricing.get('region') or '—')}</b> · locale: <b>{esc(pricing.get('locale') or '—')}</b>"
    )
    return f"<h3>Plan và giá ({len(plans)})</h3><p class='meta'>{views}</p><table>{head}{rows}</table>"


def usage_prices_html(data: dict) -> str:
    items = data["pricing"].get("usage_prices", [])
    if not items:
        return "<h3>usage_prices</h3><p class='meta'>Không có.</p>"
    head = (
        "<tr><th style='width:30%'>Tên</th><th style='width:25%'>Đơn vị</th>"
        "<th class='num' style='width:15%'>Giá</th><th>Tiền tệ</th></tr>"
    )
    rows = "".join(
        f"<tr><td>{esc(u['name'])}</td><td>{esc(u['unit'])}</td>"
        f"<td class='num'>{esc(fmt_price(u.get('price')))}</td><td>{esc(u.get('currency') or '—')}</td></tr>"
        for u in items
    )
    return f"<h3>usage_prices ({len(items)})</h3><table>{head}{rows}</table>"


def blocked_html(product: dict, report: dict) -> str:
    return (
        f'<section class="card"><h2>{esc(product["name"])}</h2>'
        f"<p><span class='bad'>Không crawl được.</span> {esc(report.get('blocked') or 'không rõ lý do')}</p>"
        "<p class='meta'>Không có PKB. Không vượt chặn: không đổi User-Agent, không dùng proxy.</p></section>"
    )


def product_html(product: dict, pkb: dict) -> str:
    data = pkb["data"]
    sources = {s["id"]: s for s in pkb["sources"]}
    meta = pkb["meta"]
    features = [fact_item(f["name"], f.get("description"), f, sources) for f in data["features"]]
    use_cases = [fact_item(f["title"], None, f, sources) for f in data["use_cases"]]
    limitations = [fact_item(f["text"], None, f, sources) for f in data["limitations"]]
    unknown = meta.get("unknown_source_ids") or []
    note = (
        f"Evidence khớp nguyên văn nguồn: <b>{meta['evidence_in_source'] * 100:.1f}%</b> "
        f"(PKB không ghi cờ theo từng fact, nên chỉ hiện tỉ lệ này)."
    )
    if unknown:
        note += f" <span class='warn'>source_id lạ: {esc(', '.join(unknown))}</span>"
    return (
        f'<section class="card"><h2>{esc(product["name"])}</h2>'
        f'<p class="meta">{note}</p>'
        f"{identity_html(data, product)}{plans_html(data)}{usage_prices_html(data)}"
        f"{fact_list('Features', features)}"
        f"{fact_list('Use cases', use_cases)}"
        f"{fact_list('Limitations', limitations)}"
        "</section>"
    )


def metrics_html(rows: list[dict], names: dict[str, str]) -> str:
    cols = [
        ("Product", "", "9%"),
        ("Model", "", "13%"),
        ("Mode", "", "9%"),
        ("Chi phí", "num", "9%"),
        ("Thời gian", "num", "9%"),
        ("Plan", "num", "6%"),
        ("Fact", "num", "6%"),
        ("Giá đúng?", "", "9%"),
        ("price_plan_note", "", ""),
    ]
    head = "".join(
        f'<th class="{c}"' + (f' style="width:{w}"' if w else "") + f">{esc(n)}</th>" for n, c, w in cols
    )
    body = []
    for r in rows:
        correct = r["price_plan_correct"].strip().lower()
        verdict = {
            "true": '<span class="ok">✔ Đúng</span>',
            "false": '<span class="bad">✘ Sai</span>',
        }.get(correct, "—")
        cls = ' class="hl"' if r["mode"] == "batch" else ""
        body.append(
            f"<tr{cls}><td>{esc(names.get(r['product'], r['product']))}</td>"
            f"<td>{esc(r['model'].removeprefix('gemini-'))}</td><td>{esc(r['mode'])}</td>"
            f"<td class='num'>${float(r['cost_usd']):.4f}</td>"
            f"<td class='num'>{float(r['extract_seconds']):.1f} s</td>"
            f"<td class='num'>{esc(r['plans'])}</td><td class='num'>{esc(r['facts'])}</td>"
            f"<td>{verdict}</td><td>{esc(r['price_plan_note'])}</td></tr>"
        )
    return (
        f"<table><tr>{head}</tr>{''.join(body)}</table>"
        "<p class='meta'>Hàng nền vàng = mode <b>batch</b> (mặc định đề xuất cho v0.2). "
        "Thời gian = thời gian gọi LLM, chưa tính crawl. Chi phí tính theo giá gói trả phí.</p>"
    )


def lessons_html(lessons: list[tuple[str, str]]) -> str:
    if not lessons:
        return "<p class='meta'>Không đọc được mục đề xuất v0.2 trong README.</p>"
    items = "".join(f"<li><b>{esc(title)}.</b> {esc(first)}</li>" for title, first in lessons)
    return f'<ul class="lessons">{items}</ul>'


def build_page(
    model: str, products: list[dict], pkbs: dict[str, dict], reports: dict[str, dict], metrics: list[dict]
) -> str:
    names = {p["slug"]: p["name"] for p in products}
    run_date = max(p["meta"]["generated_at"] for p in pkbs.values())[:10]
    run_total = sum(float(r["cost_usd"] or 0) for r in metrics)
    cards = "".join(
        product_html(p, pkbs[p["slug"]]) if p["slug"] in pkbs else blocked_html(p, reports[p["slug"]])
        for p in products
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demo PKB — Spike M1</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Spike M1: từ URL đến Product Knowledge Base</h1>
<div class="flow">URL → crawl (Crawl4AI) → markdown → Gemini (structured output) → PKB (JSON)</div>
<p class="meta">Ngày chạy: <b>{esc(run_date)}</b> · Model đang xem: <b>{esc(model)}</b> (mode batch) ·
Schema PKB: <b>v{esc(PKB_SCHEMA_VERSION)}</b> · Tổng chi phí các lần chạy trong bảng: <b>${run_total:.3f}</b>
· Chi phí tính theo giá gói trả phí.</p>

<h2>1. Product knowledge base (PKB)</h2>
{cards}

<h2>2. Số liệu lần chạy v0.2</h2>
{metrics_html(metrics, names)}

<h2>3. Bài học về giá</h2>
{lessons_html(load_lessons())}
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"model của PKB hiển thị (mặc định {DEFAULT_MODEL})"
    )
    args = parser.parse_args()

    products = load_json(ROOT / "products.json")
    pkbs: dict[str, dict] = {}
    reports: dict[str, dict] = {}
    for p in products:
        reports[p["slug"]] = load_json(OUTPUT_DIR / p["slug"] / "crawl.json")
        if reports[p["slug"]]["pages_used"] == 0:  # crawl bị chặn: hiện thẻ báo lỗi, không có PKB
            continue
        path = OUTPUT_DIR / p["slug"] / f"pkb.{args.model}.json"
        if not path.exists():
            print(
                f"Không có {path.relative_to(ROOT)}. Model có sẵn: {', '.join(available_models())}",
                file=sys.stderr,
            )
            return 1
        pkbs[p["slug"]] = load_json(path)

    OUT_FILE.write_text(build_page(args.model, products, pkbs, reports, load_metrics()), encoding="utf-8")
    print(f"Đã ghi {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
