"""Spike M1 — bước 2: markdown đã crawl → PKB JSON, đo token / chi phí, ghi metrics.csv.

  uv run python run.py --dry-run        # chỉ chọn trang + đếm token + in ước tính chi phí (không gọi generate)
  uv run python run.py                  # ước tính, rồi chạy 2 product × 2 model × 2 mode
  uv run python run.py claude --models gemini-3.1-flash-lite --modes batch --no-cache

Mode: per_page = 1 lời gọi / trang rồi gộp; batch = gom TOP_PAGES trang vào 1 lời gọi. Hai mode dùng cùng tập trang.
SP-07: kết quả mỗi lời gọi được cache theo (model, prompt, content_hash các trang). Chạy lại khi nội dung
không đổi → không gọi LLM; số token / chi phí trong metrics lấy từ lần gọi gốc, cột cache_hits cho biết.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import config
import extract
from schema import PKB, PKBExtract

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
METRICS_FILE = OUTPUT_DIR / "metrics.csv"
MODES = ("per_page", "batch")
COLUMNS = [
    # cột theo spec
    "product", "model", "mode", "pages_found", "pages_used", "crawl_seconds", "llm_calls",
    "input_tokens", "output_tokens", "cost_usd", "extract_seconds", "schema_valid", "price_plan_correct",
    # đối chiếu tay (AC-04)
    "price_plan_note",
    # cột thêm
    "pages_sent", "cache_hits", "thoughts_tokens", "facts", "plans", "evidence_in_source", "schema_errors", "truncated", "evidence_truncated",
]  # fmt: skip
# Ước tính output cho bảng "dự kiến" (chặn trên vẫn tính theo MAX_OUTPUT_TOKENS)
EXPECTED_OUTPUT = {"per_page": 1500, "batch": 4000}
PROMPT_VERSION = hashlib.sha256(
    (extract.SYSTEM_PROMPT + json.dumps(PKBExtract.model_json_schema(), sort_keys=True)).encode()
).hexdigest()[:12]


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------- chọn trang
def load_docs(slug: str) -> tuple[dict, list[dict]]:
    """Trả (crawl report, mọi trang đã crawl xếp theo điểm giảm dần). Pricing dùng raw, trang khác dùng fit."""
    report = json.loads((OUTPUT_DIR / slug / "crawl.json").read_text(encoding="utf-8"))
    pages = sorted(report["pages"], key=lambda p: (-p["score"], p["id"]))
    docs = []
    for p in pages:
        variant = "raw" if p["page_type"] in config.RAW_PAGE_TYPES else "fit"
        md = (OUTPUT_DIR / slug / p[f"{'raw_' if variant == 'raw' else ''}file"]).read_text(encoding="utf-8")
        docs.append(
            {
                "source_id": p["id"],
                "url": p["url"],
                "page_type": p["page_type"],
                "score": p["score"],
                "fetched_at": p["fetched_at"],
                "variant": variant,
                "content_hash": p[f"{variant}_hash"],
                "text": extract.clean_for_llm(md),
            }
        )
    return report, docs


def mode_docs(docs: list[dict], mode: str) -> list[dict]:
    """per_page: mọi trang; batch: TOP_PAGES trang điểm cao nhất."""
    return docs if mode == "per_page" else docs[: config.TOP_PAGES]


def plan_calls(docs: list[dict], mode: str) -> list[list[dict]]:
    docs = mode_docs(docs, mode)
    return [[d] for d in docs] if mode == "per_page" else [docs]


def cache_path(slug: str, model: str, call_docs: list[dict]) -> Path:
    key = "|".join([model, PROMPT_VERSION, *(f"{d['source_id']}={d['content_hash']}" for d in call_docs)])
    return OUTPUT_DIR / slug / "llm_cache" / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"


# ---------------------------------------------------------------- ước tính
def estimate(client, products: list[dict], models: list[str], modes: list[str], use_cache: bool) -> float:
    """Đếm token input thật bằng count_tokens; in bảng chi phí dự kiến và chặn trên. Trả chặn trên (USD)."""
    print(f"\n{'product':9} {'model':22} {'mode':9} {'calls':>5} {'cached':>6} {'in_tok':>8} "
          f"{'$expected':>9} {'$worst':>8}")  # fmt: skip
    total_exp = total_worst = 0.0
    for prod in products:
        for model in models:
            for mode in modes:
                calls = plan_calls(prod["docs"], mode)
                todo = [c for c in calls if not (use_cache and cache_path(prod["slug"], model, c).exists())]
                in_tok = sum(
                    extract.count_tokens(client, model, extract.build_prompt(prod["name"], c)) for c in todo
                )
                exp = extract.cost_usd(model, in_tok, EXPECTED_OUTPUT[mode] * len(todo))
                worst = extract.cost_usd(model, int(in_tok * 1.1), config.MAX_OUTPUT_TOKENS[mode] * len(todo))
                total_exp += exp
                total_worst += worst
                print(f"{prod['slug']:9} {model:22} {mode:9} {len(calls):5} {len(calls) - len(todo):6} "
                      f"{in_tok:8} {exp:9.4f} {worst:8.4f}")  # fmt: skip
    print(f"TOTAL expected ${total_exp:.4f} | worst case ${total_worst:.4f} (input +10% cho schema, "
          f"output = {config.MAX_OUTPUT_TOKENS} token/lời gọi) | budget ${config.BUDGET_USD}")  # fmt: skip
    return total_worst


# ---------------------------------------------------------------- chạy 1 tổ hợp
def run_one(client, prod: dict, model: str, mode: str, use_cache: bool) -> dict:
    slug, docs = prod["slug"], mode_docs(prod["docs"], mode)
    parts: list[dict] = []
    errors: list[str] = []
    calls = cache_hits = in_tok = out_tok = thoughts = truncated = ev_cut = 0
    seconds = fresh_cost = 0.0
    for call_docs in plan_calls(docs, mode):
        path = cache_path(slug, model, call_docs)
        if use_cache and path.exists():
            res = extract.LLMResult(**json.loads(path.read_text(encoding="utf-8")))
            cache_hits += 1
        else:
            prompt = extract.build_prompt(prod["name"], call_docs)
            res = extract.call_gemini(client, model, prompt, config.MAX_OUTPUT_TOKENS[mode])
            fresh_cost += extract.cost_usd(model, res.input_tokens, res.output_tokens)
        calls += 1
        in_tok, out_tok, thoughts = (
            in_tok + res.input_tokens,
            out_tok + res.output_tokens,
            thoughts + res.thoughts_tokens,
        )
        seconds += res.seconds
        data, err, cut = extract.parse_extract(res.text)
        ev_cut += cut
        label = call_docs[0]["source_id"] if mode == "per_page" else "batch"
        if res.finish_reason != "STOP":
            truncated += 1
            err = f"finish_reason={res.finish_reason}; {err}"
        if err:
            errors.append(f"{label}: {err}")
        if res.finish_reason == "STOP" and data is not None and not path.exists():
            # Chỉ cache kết quả hoàn chỉnh (JSON đủ); kết quả bị cắt không bị phát lại ở lần chạy sau.
            # Sửa evidence quá dài là bước tất định, nên kết quả cần sửa vẫn được cache.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(res), ensure_ascii=False), encoding="utf-8")
        if data is not None:
            parts.append(data)

    data = extract.merge(parts) if mode == "per_page" else (parts[0] if parts else {})
    texts = {d["source_id"]: d["text"] for d in docs}
    ev_ratio, unknown, n_facts = extract.check_evidence(data, texts)
    cost = extract.cost_usd(model, in_tok, out_tok)
    pkb = {
        **data,
        "sources": [
            {k: d[k] for k in ("source_id", "url", "page_type", "fetched_at", "variant", "content_hash")}
            for d in docs
        ],
        "meta": {
            "product": slug,
            "model": model,
            "mode": mode,
            "generated_at": now_iso(),
            "llm_calls": calls,
            "cache_hits": cache_hits,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": round(cost, 6),
            "evidence_in_source": ev_ratio,
            "unknown_source_ids": unknown,
        },
    }
    try:
        pkb = PKB.model_validate(pkb).model_dump(mode="json")
        valid = not errors
    except Exception as e:  # noqa: BLE001 — ghi lỗi validate vào file để xem lại
        errors.append(f"final: {str(e)[:500]}")
        valid = False
    if errors:
        pkb["_errors"] = errors
    suffix = "" if mode == "batch" else ".per-page"
    out = OUTPUT_DIR / slug / f"pkb.{model}{suffix}.json"
    out.write_text(json.dumps(pkb, ensure_ascii=False, indent=2), encoding="utf-8")

    report = prod["report"]
    return {
        "product": slug, "model": model, "mode": mode,
        "pages_found": report["pages_found"], "pages_used": report["pages_used"],
        "crawl_seconds": report["crawl_seconds"], "llm_calls": calls,
        "input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": f"{cost:.6f}",
        "extract_seconds": round(seconds, 2), "schema_valid": valid, "price_plan_correct": "", "price_plan_note": "",
        "pages_sent": len(docs), "cache_hits": cache_hits, "thoughts_tokens": thoughts, "facts": n_facts,
        "plans": len((data.get("pricing") or {}).get("plans") or []),
        "evidence_in_source": ev_ratio, "schema_errors": len(errors), "truncated": truncated,
        "evidence_truncated": ev_cut,
        "_fresh_cost": fresh_cost,  # không ghi vào csv (extrasaction="ignore")
    }  # fmt: skip


def smoke(client, prod: dict, model: str) -> None:
    """Kiểm tra Gemini nhận JSON schema và trả về PKB hợp lệ, trước khi chạy cả ma trận."""
    doc = min(prod["docs"], key=lambda d: len(d["text"]))
    res = extract.call_gemini(
        client, model, extract.build_prompt(prod["name"], [doc]), config.MAX_OUTPUT_TOKENS["per_page"]
    )
    _, err, _ = extract.parse_extract(res.text)
    cost = extract.cost_usd(model, res.input_tokens, res.output_tokens)
    print(f"\nsmoke {prod['slug']} {doc['source_id']} {model}: finish={res.finish_reason} in={res.input_tokens} "
          f"out={res.output_tokens} (thoughts {res.thoughts_tokens}) ${cost:.6f} {res.seconds}s")  # fmt: skip
    print("schema:", err or "hợp lệ")
    print(res.text[:1500])


def write_metrics(rows: list[dict]) -> None:
    """Thay dòng cùng (product, model, mode), giữ dòng khác và giữ cột price_plan_correct, price_plan_note đã điền tay."""

    def key(r: dict) -> tuple[str, str, str]:
        return r["product"], r["model"], r["mode"]

    existing: dict = {}
    if METRICS_FILE.exists():
        with METRICS_FILE.open(encoding="utf-8", newline="") as f:
            existing = {key(r): r for r in csv.DictReader(f)}
    for r in rows:
        old = existing.get(key(r))
        for col in ("price_plan_correct", "price_plan_note"):
            if old and old.get(col):
                r[col] = old[col]
        existing[key(r)] = r
    with METRICS_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--models", default=",".join(config.MODELS))
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--dry-run", action="store_true", help="chỉ ước tính, không gọi generate")
    ap.add_argument("--no-cache", action="store_true", help="bỏ qua cache content_hash (SP-07)")
    ap.add_argument("--smoke", action="store_true", help="1 lời gọi thử trên trang nhỏ nhất, model đầu tiên")
    args = ap.parse_args()
    models, modes = args.models.split(","), args.modes.split(",")
    for m in models:
        if m not in config.MODELS:
            raise SystemExit(f"Model lạ: {m}. Có: {list(config.MODELS)}")

    products = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    selected = []
    for p in products:
        if args.slugs and p["slug"] not in args.slugs:
            continue
        report, docs = load_docs(p["slug"])
        selected.append({"slug": p["slug"], "name": p["name"], "report": report, "docs": docs})
        print(f"\n{p['name']}: {len(docs)} trang gửi LLM")
        for d in docs:
            print(
                f"  {d['source_id']} {d['page_type']:9} {d['score']:4} {d['variant']} {len(d['text']):6}c  {d['url']}"
            )

    client = extract.make_client()
    worst = estimate(client, selected, models, modes, use_cache=not args.no_cache)
    if worst > config.BUDGET_USD:
        raise SystemExit(f"Dừng: chi phí xấu nhất ${worst:.4f} > ngân sách ${config.BUDGET_USD}.")
    if args.dry_run:
        return
    if args.smoke:
        smoke(client, selected[0], models[0])
        return

    rows = []
    for prod in selected:
        for model in models:
            for mode in modes:
                row = run_one(client, prod, model, mode, use_cache=not args.no_cache)
                rows.append(row)
                print(f"{prod['slug']:9} {model:22} {mode:9} calls={row['llm_calls']} cache={row['cache_hits']} "
                      f"in={row['input_tokens']} out={row['output_tokens']} ${row['cost_usd']} "
                      f"{row['extract_seconds']}s valid={row['schema_valid']} plans={row['plans']} "
                      f"facts={row['facts']} evidence_ok={row['evidence_in_source']}")  # fmt: skip
    write_metrics(rows)
    fresh = sum(r["_fresh_cost"] for r in rows)
    print(f"\nĐã ghi {METRICS_FILE.relative_to(ROOT)}. Chi phí API thật của lần chạy này: ${fresh:.4f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    main()
