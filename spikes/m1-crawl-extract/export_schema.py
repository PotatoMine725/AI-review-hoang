"""Xuất JSON Schema của PKB (v0.2 và v0.3) thành contract dùng chung cho FE / BE / AI.

  uv run python export_schema.py

Ghi 4 file vào docs/specs/pkb/. Chạy lại không đổi nội dung (sort_keys, newline cố định).
File v0.2 phải không đổi so với bản đã commit (v0.2 giữ nguyên để đọc PKB cũ).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema

import schema as v02
import schema_v03 as v03

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "specs" / "pkb"

# (version, {tên file: (cột, model)}, {lớp: luật JSON Schema bổ sung})
TARGETS: list[tuple[str, dict[str, tuple[str, type[BaseModel]]], dict[type, dict[str, Any]]]] = [
    (
        v02.PKB_SCHEMA_VERSION,
        {
            "data": ("product_knowledge.data", v02.PKBData),
            "sources": ("product_knowledge.sources[] (1 phần tử)", v02.Source),
        },
        {v02.Plan: v02.PLAN_PRICE_RULE},
    ),
    (
        v03.PKB_SCHEMA_VERSION,
        {
            "data": ("product_knowledge.data", v03.PKBData),
            "sources": ("product_knowledge.sources[] (1 phần tử)", v03.Source),
        },
        v03.JSON_RULES,
    ),
]


def generator_with(rules: dict[type, dict[str, Any]]) -> type[GenerateJsonSchema]:
    """Sinh class thêm luật (if/then, allOf…) vào định nghĩa của lớp có trong `rules`."""

    class ExportSchema(GenerateJsonSchema):
        def model_schema(self, schema):  # type: ignore[no-untyped-def]
            json_schema = super().model_schema(schema)
            if (rule := rules.get(schema["cls"])) is not None:
                json_schema.update(rule)
            return json_schema

    return ExportSchema


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for version, files, rules in TARGETS:
        for kind, (column, model) in files.items():
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                **model.model_json_schema(schema_generator=generator_with(rules)),
                "description": f"PKB schema v{version}: {column}.",
            }
            text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            name = f"pkb-{kind}.v{version}.schema.json"
            (OUT_DIR / name).write_text(text, encoding="utf-8", newline="\n")
            print(f"Đã ghi {OUT_DIR / name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    main()
