"""Nơi lưu markdown của trang. Supabase Storage làm sau (T-Storage), cắm vào `PageStore`."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple, Protocol
from urllib.parse import urlsplit


class StoredPaths(NamedTuple):
    fit_path: str
    raw_path: str


class PageStore(Protocol):
    def save_page(
        self,
        *,
        source_id: str,
        url: str,
        page_type: str,
        fetched_at: str,
        raw_md: str,
        fit_md: str,
    ) -> StoredPaths:
        """Ghi markdown raw và fit, trả đường dẫn trong store."""
        ...


def slugify(url: str) -> str:
    path = urlsplit(url).path.strip("/") or "home"
    return re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-")[:60] or "home"


class LocalPageStore:
    """Ghi vào thư mục `<root>/pages/`. Không xoá file cũ: trang `unchanged` không được ghi lại."""

    def __init__(self, root: Path) -> None:
        self._pages_dir = root / "pages"
        self._pages_dir.mkdir(parents=True, exist_ok=True)

    def save_page(
        self,
        *,
        source_id: str,
        url: str,
        page_type: str,
        fetched_at: str,
        raw_md: str,
        fit_md: str,
    ) -> StoredPaths:
        name = f"{source_id}-{page_type}-{slugify(url)}"
        header = (
            f"<!-- source_id: {source_id} | url: {url} | page_type: {page_type} "
            f"| fetched_at: {fetched_at} -->\n\n"
        )
        (self._pages_dir / f"{name}.md").write_text(header + fit_md, encoding="utf-8")
        (self._pages_dir / f"{name}.raw.md").write_text(header + raw_md, encoding="utf-8")
        return StoredPaths(fit_path=f"pages/{name}.md", raw_path=f"pages/{name}.raw.md")
