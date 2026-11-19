from __future__ import annotations


class DemoError(Exception):
    """Lỗi chặn cả lần chạy (thiếu công cụ, LLM trả sai, không sinh được script)."""
