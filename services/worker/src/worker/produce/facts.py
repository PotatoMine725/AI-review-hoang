"""`fact_refs` của M2 (`{source_id, field_path}`) → `facts{id → trích dẫn}` của plan #88.

Plan #88 cần mỗi chữ trên hình và mỗi câu thoại trỏ tới một id trong `facts`. M2 chỉ cho đường
dẫn vào PKB đã duyệt, nên worker tra PKB ở đây. Trích dẫn = `value` (nếu là chuỗi), không thì
`evidence` nguyên văn của fact. Id = `<source_id>:<field_path>`.

Path trỏ thẳng vào giá trị vô hướng (vd. `pricing.free_plan.value` = `true`, ví dụ trong prompt
#83 `4c5b72b`) vẫn hợp lệ: chữ và `source_id` lấy từ nút cha, không tự viết "Có"/"True".
"""

from __future__ import annotations

from typing import Any

from worker.m2.validate import resolve_field_path
from worker.produce.errors import ProduceError


class FactError(ProduceError):
    pass


def _parent(pkb_data: dict[str, Any], field_path: str, node: Any) -> Any:
    """Lá vô hướng (bool, số) `a.b.value` → nút cha `a.b`; còn lại giữ `node`."""
    parent_path, dot, last = field_path.rpartition(".")
    if isinstance(node, bool | int | float) and dot and "[" not in last:
        return resolve_field_path(pkb_data, parent_path)
    return node


def _quote(node: Any, field_path: str) -> str:
    if isinstance(node, str) and node.strip():
        return node.strip()
    if isinstance(node, dict):
        value = node.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
        evidence = node.get("evidence")
        if isinstance(evidence, str) and evidence.strip():
            return evidence.strip()
        for key in ("label", "description"):
            text = node.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise FactError(f"fact '{field_path}' không có chữ để trích (value/evidence)")


def _source_id(pkb_data: dict[str, Any], field_path: str) -> str | None:
    node = _parent(pkb_data, field_path, resolve_field_path(pkb_data, field_path))
    sid = node.get("source_id") if isinstance(node, dict) else None
    return sid if isinstance(sid, str) else None


class FactBook:
    """Gom các fact đã dùng, giữ thứ tự xuất hiện."""

    def __init__(self, pkb_data: dict[str, Any]) -> None:
        self._pkb = pkb_data
        self.facts: dict[str, str] = {}

    def add(self, field_path: str, source_id: str | None = None) -> str:
        try:
            node = resolve_field_path(self._pkb, field_path)
        except (KeyError, IndexError, TypeError, ValueError) as ex:
            raise FactError(f"fact_ref '{field_path}' không tồn tại trong PKB: {ex}") from ex
        fid = f"{source_id or _source_id(self._pkb, field_path) or 'pkb'}:{field_path}"
        self.facts.setdefault(fid, _quote(_parent(self._pkb, field_path, node), field_path))
        return fid

    def add_refs(self, refs: list[dict[str, Any]]) -> list[str]:
        out: list[str] = []
        for ref in refs:
            fid = self.add(ref["field_path"], ref.get("source_id"))
            if fid not in out:
                out.append(fid)
        return out

    def text(self, field_path: str) -> str:
        """Chữ của một fact (vd. tên sản phẩm `identity.name`), không ghi vào `facts`."""
        node = resolve_field_path(self._pkb, field_path)
        return _quote(_parent(self._pkb, field_path, node), field_path)
