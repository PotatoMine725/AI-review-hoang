"""System prompt lấy nguyên văn từ prompt của Định (khối ```text trong `contract/*.prompt.md`)."""

from __future__ import annotations

import json
import re
from functools import cache
from typing import Any

from worker.m2.validate import CONTRACT_DIR

PROMPT_FILE = "p1-ac-03-script-vi.prompt.md"
_BLOCK_RE = re.compile(r"```text\n(.*?)\n```", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
PLACEHOLDERS = (
    "product_id",
    "knowledge_version",
    "approved_pkb_json",
    "permitted_assets_json",
    "content_context_json",
)


@cache
def prompt_template() -> str:
    text = (CONTRACT_DIR / PROMPT_FILE).read_text(encoding="utf-8")
    blocks = _BLOCK_RE.findall(text)
    if len(blocks) != 1:
        raise ValueError(f"{PROMPT_FILE}: cần đúng 1 khối ```text, có {len(blocks)}")
    return blocks[0]


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)  # giữ tiếng Việt có dấu, không \uXXXX


def build_system_prompt(inp: dict[str, Any]) -> str:
    values = {
        "product_id": str(inp["product_id"]),
        "knowledge_version": str(inp["knowledge_version"]),
        "approved_pkb_json": _dump(inp["approved_pkb"]),
        "permitted_assets_json": _dump(inp["permitted_assets"]),
        "content_context_json": _dump(inp.get("content_context") or {}),
    }
    out = prompt_template()
    # Kiểm trên template (không kiểm trên kết quả: dữ liệu PKB có thể chứa "{{").
    found = set(_PLACEHOLDER_RE.findall(out))
    if found != set(PLACEHOLDERS):
        raise ValueError(f"placeholder trong prompt {sorted(found)} khác {list(PLACEHOLDERS)}")
    # Thay 1 lượt: dữ liệu đã điền không bị thay tiếp.
    return _PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], out)


def conflicted_paths(inp: dict[str, Any]) -> list[str]:
    """Đường dẫn fact mà `quality.conflicts` của PKB ghi là đang xung đột (validator sẽ từ chối)."""
    data = (inp.get("approved_pkb") or {}).get("data") or {}
    found: set[str] = set()
    for conflict in (data.get("quality") or {}).get("conflicts") or []:
        if isinstance(conflict, dict):
            found.update(
                v for k in ("field_path", "field", "path") if isinstance(v := conflict.get(k), str)
            )
    return sorted(found)


def build_user_prompt(inp: dict[str, Any]) -> str:
    prompt = "Tạo kịch bản theo các quy tắc trong system prompt. Chỉ trả JSON."
    if paths := conflicted_paths(inp):
        prompt += (
            " Các fact sau đang xung đột nên TUYỆT ĐỐI không dùng làm hook, lời đọc hay claim "
            "(kể cả đường dẫn con): "
            + ", ".join(paths)
            + ". Chọn fact khác không nằm trong danh sách."
        )
    return prompt
