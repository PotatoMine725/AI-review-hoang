"""Kiểm tra contract bằng JSON Schema (jsonschema, dependency-group dev).

  uv run python validate_contracts.py

- `docs/specs/contracts/examples/valid-*.json` phải pass `cost-breakdown.v1.schema.json` hoặc `script.v0.schema.json`.
- `docs/specs/contracts/examples/invalid-*.json` phải fail schema tương ứng.
- `docs/specs/contracts/examples/*script*.json` kiểm tra thêm tổng thời lượng 15–60s và fact_ref trỏ tới PKB.
- `data` và `sources` của các PKB trong `output/` phải pass schema PKB v0.2.
Thoát với mã 1 nếu có dòng nào sai kỳ vọng.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "docs" / "specs"
EXAMPLES = SPECS / "contracts" / "examples"
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
    for path in PKB_FILES:
        doc = load(path)
        name = f"{path.parent.name}/{path.name}"
        err = first_error(data_v, doc["data"])
        rows.append((f"{name} (data)", "pass", not err, err or "hợp lệ"))
        err = next((e for s in doc["sources"] if (e := first_error(source_v, s))), "")
        rows.append((f"{name} (sources)", "pass", not err, err or "hợp lệ"))

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
