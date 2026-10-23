"""Kiểm tra contract bằng JSON Schema (jsonschema, dependency-group dev).

  uv run python validate_contracts.py

- `docs/specs/contracts/examples/valid-*.json` phải pass `cost-breakdown.v1.schema.json` hoặc `script.v0.schema.json`.
- `docs/specs/contracts/examples/invalid-*.json` phải fail schema tương ứng.
- `docs/specs/contracts/examples/*script*.json` kiểm tra thêm tổng thời lượng 15–60s và fact_ref trỏ tới PKB.
- `data` và `sources` của các PKB trong `output/` phải pass schema PKB v0.2, và cũng phải pass v0.3
  (v0.3 là superset: PKB v0.2 cũ đọc được, coi như `software`).
- `docs/specs/pkb/examples/valid-*.json` (dạng `{data, sources}`) phải pass schema PKB v0.3 và model Pydantic,
  `invalid-*.json` phải bị bắt bởi schema, hoặc bởi kiểm tham chiếu chéo (variant_ref, source_id).
- Với mỗi ví dụ, schema JSON và Pydantic phải cho cùng kết quả (chống lệch giữa 2 nơi khai báo luật).
Thoát với mã 1 nếu có dòng nào sai kỳ vọng.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from schema_v03 import PKBData as PKBDataV03

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "docs" / "specs"
EXAMPLES = SPECS / "contracts" / "examples"
PKB_EXAMPLES = SPECS / "pkb" / "examples"
PKB_FILES = sorted(Path(__file__).resolve().parent.glob("output/*/pkb.gemini-3.5-flash-lite.json"))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(path: Path) -> Draft202012Validator:
    schema = load(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def first_error(v: Draft202012Validator, doc) -> str:
    errors = sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if not errors:
        return ""
    e = errors[0]
    where = "/".join(str(p) for p in e.absolute_path) or "(gốc)"
    return f"{where}: {e.message}"[:90]


def resolve_field_path(data: dict, path_str: str):
    tokens = re.findall(r"[^.\[\]]+|\[\d+\]", path_str)
    curr = data
    for token in tokens:
        if token.startswith("[") and token.endswith("]"):
            curr = curr[int(token[1:-1])]
        else:
            curr = curr[token]
    return curr


def pydantic_error(data: dict) -> str:
    """Kiểm bằng model Pydantic v0.3 (nguồn của schema)."""
    try:
        PKBDataV03.model_validate(data)
    except ValidationError as e:
        err = e.errors()[0]
        where = "/".join(str(p) for p in err["loc"]) or "(gốc)"
        return f"{where}: {err['msg']}"[:90]
    return ""


def ref_error(data: dict) -> str:
    """variant_ref phải trỏ tới variants[].id có thật. JSON Schema không diễn đạt được luật này."""
    ids = {v.get("id") for v in data.get("variants", [])}
    refs = [("offers", o) for o in data.get("offers", [])]
    refs += [("media.images", i) for i in (data.get("media") or {}).get("images", [])]
    for where, item in refs:
        ref = item.get("variant_ref")
        if ref is not None and ref not in ids:
            return f"{where}: variant_ref '{ref}' không có trong variants[]"
    return ""


def source_id_error(data: dict, sources: list[dict]) -> str:
    """Mọi `source_id` trong data phải có trong sources[].id."""
    known = {s["id"] for s in sources}
    stack: list = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            sid = node.get("source_id")
            if isinstance(sid, str) and sid not in known:
                return f"source_id '{sid}' không có trong sources"
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return ""


def pkb_example_rows(data_v3, source_v3, data_v2) -> list[tuple[str, str, bool, str]]:
    rows: list[tuple[str, str, bool, str]] = []
    for path in sorted(PKB_EXAMPLES.glob("*.json")):
        want_valid = path.name.startswith("valid-")
        if not want_valid and not path.name.startswith("invalid-"):
            continue
        doc = load(path)
        data, sources = doc["data"], doc["sources"]
        schema_err = first_error(data_v3, data)
        sources_err = next((e for s in sources if (e := first_error(source_v3, s))), "")
        refs_err = ref_error(data)
        ids_err = source_id_error(data, sources)
        pyd_err = pydantic_error(data)
        err = schema_err or sources_err or refs_err or ids_err
        note = err or "hợp lệ"
        ok = (not err) == want_valid
        # Schema JSON và Pydantic phải cùng kết luận (source_id vs sources chỉ có ở validator này)
        if bool(schema_err or refs_err) != bool(pyd_err):
            ok = False
            note = f"LỆCH schema={schema_err or refs_err or 'đạt'!r} / pydantic={pyd_err or 'đạt'!r}"
        rows.append((f"examples/{path.name}", "pass" if want_valid else "fail", ok, note))
        if path.name.startswith("valid-v02-"):  # ví dụ v0.2 cũng phải đạt schema v0.2 gốc
            err = first_error(data_v2, data)
            rows.append((f"examples/{path.name} (schema 0.2)", "pass", not err, err or "hợp lệ"))
    return rows


def validate_script_content(doc: dict) -> str:
    """Kiểm tra logic phụ cho script: tổng thời lượng 15-60s và fact_ref trỏ tới PKB ElevenLabs."""
    scenes = doc.get("scenes", [])
    total_duration = sum(s.get("duration_s", 0) for s in scenes)
    if not (15.0 <= total_duration <= 60.0):
        return f"tổng thời lượng {total_duration}s ngoài khoảng 15–60s"

    elevenlabs_pkb_path = (
        ROOT / "spikes" / "m1-crawl-extract" / "output" / "elevenlabs" / "pkb.gemini-3.5-flash-lite.json"
    )
    if elevenlabs_pkb_path.exists():
        pkb = load(elevenlabs_pkb_path)
        valid_sources = {s["id"] for s in pkb.get("sources", [])}
        pkb_data = pkb.get("data", {})
        for s in scenes:
            for c in s.get("claims", []):
                fref = c.get("fact_ref")
                if not fref:
                    continue
                sid = fref.get("source_id")
                if sid not in valid_sources:
                    return f"source_id '{sid}' không có trong sources của PKB"
                fpath = fref.get("field_path", "")
                try:
                    val = resolve_field_path(pkb_data, fpath)
                    if val is None:
                        return f"fact_ref '{fpath}' trả về None"
                except (KeyError, IndexError, TypeError) as ex:
                    return f"fact_ref '{fpath}' không tồn tại trong PKB: {ex}"

    return ""


def main() -> int:
    rows: list[tuple[str, str, bool, str]] = []  # (file, kỳ vọng, đạt, ghi chú)

    cost_v = validator(SPECS / "contracts" / "cost-breakdown.v1.schema.json")
    script_v = validator(SPECS / "contracts" / "script.v0.schema.json")

    for path in sorted(EXAMPLES.glob("*.json")):
        want_valid = path.name.startswith("valid-")
        if not want_valid and not path.name.startswith("invalid-"):
            continue

        doc = load(path)
        if "-script-" in path.name:
            err = first_error(script_v, doc)
            if want_valid and not err:
                err = validate_script_content(doc)
            rows.append(
                (
                    path.name,
                    "pass" if want_valid else "fail",
                    (not err) == want_valid,
                    err or "hợp lệ",
                )
            )
        else:
            err = first_error(cost_v, doc)
            rows.append(
                (
                    path.name,
                    "pass" if want_valid else "fail",
                    (not err) == want_valid,
                    err or "hợp lệ",
                )
            )

    data_v = validator(SPECS / "pkb" / "pkb-data.v0.2.schema.json")
    source_v = validator(SPECS / "pkb" / "pkb-sources.v0.2.schema.json")
    data_v3 = validator(SPECS / "pkb" / "pkb-data.v0.3.schema.json")
    source_v3 = validator(SPECS / "pkb" / "pkb-sources.v0.3.schema.json")
    for path in PKB_FILES:
        doc = load(path)
        name = f"{path.parent.name}/{path.name}"
        err = first_error(data_v, doc["data"])
        rows.append((f"{name} (data)", "pass", not err, err or "hợp lệ"))
        err = next((e for s in doc["sources"] if (e := first_error(source_v, s))), "")
        rows.append((f"{name} (sources)", "pass", not err, err or "hợp lệ"))
        err = first_error(data_v3, doc["data"])  # superset: PKB v0.2 cũ vẫn hợp lệ ở schema 0.3
        rows.append((f"{name} (data, schema 0.3)", "pass", not err, err or "hợp lệ"))
        err = next((e for s in doc["sources"] if (e := first_error(source_v3, s))), "")
        rows.append((f"{name} (sources, schema 0.3)", "pass", not err, err or "hợp lệ"))

    rows += pkb_example_rows(data_v3, source_v3, data_v)

    width = max(len(r[0]) for r in rows)
    print(f"{'File'.ljust(width)}  Kỳ vọng  Kết quả  Ghi chú")
    for name, want, ok, note in rows:
        print(f"{name.ljust(width)}  {want.ljust(7)}  {'ĐẠT' if ok else 'SAI'.ljust(3)}     {note}")
    bad = [r for r in rows if not r[2]]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} đạt kỳ vọng")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    raise SystemExit(main())
