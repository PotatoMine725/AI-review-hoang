"""Xuất JSON Schema của PKB v0.2 thành contract dùng chung cho FE / BE / AI.

  uv run python export_schema.py

Ghi 2 file vào docs/specs/pkb/. Chạy lại không đổi nội dung (sort_keys, newline cố định).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic.json_schema import GenerateJsonSchema

from schema import PKB_SCHEMA_VERSION, PLAN_PRICE_RULE, PKBData, Plan, Source

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "specs" / "pkb"
FILES = {
    f"pkb-data.v{PKB_SCHEMA_VERSION}.schema.json": ("product_knowledge.data", PKBData),
    f"pkb-sources.v{PKB_SCHEMA_VERSION}.schema.json": ("product_knowledge.sources[] (1 phần tử)", Source),
}


class ExportSchema(GenerateJsonSchema):
    """Thêm luật `list_price` → `price_unit` + `billing_cycle` (if/then) vào `Plan`."""

    def model_schema(self, schema):  # type: ignore[no-untyped-def]
        json_schema = super().model_schema(schema)
        if schema["cls"] is Plan:
            json_schema.update(PLAN_PRICE_RULE)
        return json_schema


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (column, model) in FILES.items():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **model.model_json_schema(schema_generator=ExportSchema),
            "description": f"PKB schema v{PKB_SCHEMA_VERSION}: {column}.",
        }
        text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (OUT_DIR / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"Đã ghi {OUT_DIR / name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    main()
