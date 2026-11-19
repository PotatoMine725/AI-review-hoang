"""Dựng input của M2 (`p1-ac-03-input.v1-draft`) từ PKB đã duyệt.

Dùng ở hai chỗ: endpoint sinh script và runner video (kiểm lại kịch bản bằng validator M2 trước khi
dựng). Phần không suy ra được từ PKB (`permitted_assets`, `content_context`) được lưu cùng revision
trong `script_revisions.report["input"]`, nên dựng lại ra đúng input đã dùng khi sinh.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

M2_INPUT_VERSION = "p1-ac-03-input.v1-draft"


def build_m2_input(
    product_id: str,
    knowledge_version: int,
    pkb: Mapping[str, Any],
    permitted_assets: list[dict[str, Any]],
    content_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema_version": M2_INPUT_VERSION,
        "product_id": product_id,
        "knowledge_version": knowledge_version,
        "approved_pkb": {
            "status": "approved",
            "schema_version": pkb["data"]["schema_version"],
            "data": pkb["data"],
            "sources": pkb["sources"],
        },
        "permitted_assets": permitted_assets,
    }
    if content_context is not None:
        out["content_context"] = content_context
    return out


def input_context(
    permitted_assets: list[dict[str, Any]], content_context: dict[str, Any] | None
) -> dict[str, Any]:
    """Phần input không suy ra được từ PKB, lưu vào `report["input"]` của revision."""
    ctx: dict[str, Any] = {"permitted_assets": permitted_assets}
    if content_context is not None:
        ctx["content_context"] = content_context
    return ctx
