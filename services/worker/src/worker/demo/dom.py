"""Ảnh chụp DOM rút gọn cho LLM: chỉ phần tử tương tác nhìn thấy, kèm selector gợi ý."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from playwright.sync_api import Page

MAX_ELEMENTS = 120

_JS = """
(max) => {
  const sel = 'a[href],button,input,select,textarea,summary,[role=button],[role=tab],[role=link],'
    + '[role=menuitem],[role=switch],[role=checkbox],[contenteditable=true],[data-testid]';
  const q = (s) => JSON.stringify(s);
  const vis = (e) => {
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 2 && r.height > 2 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  const label = (e) => (e.getAttribute('aria-label') || e.innerText || e.value
    || e.getAttribute('placeholder') || e.getAttribute('title') || '').trim().replace(/\\s+/g, ' ');
  const hint = (e) => {
    const tid = e.getAttribute('data-testid');
    if (tid) return `[data-testid=${q(tid)}]`;
    if (e.id && !/\\d{3,}/.test(e.id)) return `#${CSS.escape(e.id)}`;
    const al = e.getAttribute('aria-label');
    if (al) return `${e.tagName.toLowerCase()}[aria-label=${q(al)}]`;
    const role = e.getAttribute('role') || ({BUTTON: 'button', A: 'link'}[e.tagName] || '');
    const t = label(e).slice(0, 40);
    if (role && t) return `role=${role}[name=${q(t)}]`;
    if (e.name) return `${e.tagName.toLowerCase()}[name=${q(e.name)}]`;
    return e.tagName.toLowerCase();
  };
  const out = [];
  for (const e of document.querySelectorAll(sel)) {
    const isFile = e.tagName === 'INPUT' && e.type === 'file';
    if (!isFile && !vis(e)) continue;   // input file thường bị ẩn nhưng vẫn upload được
    const r = e.getBoundingClientRect();
    out.push({
      tag: e.tagName.toLowerCase(), type: e.type || undefined,
      text: label(e).slice(0, 80), selector: hint(e),
      accept: e.getAttribute('accept') || undefined,
      href: e.tagName === 'A' ? (e.getAttribute('href') || '').slice(0, 80) : undefined,
      disabled: e.disabled || undefined,
      box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
    });
    if (out.length >= max) break;
  }
  const h = [...document.querySelectorAll('h1,h2')].slice(0, 6).map((e) => e.innerText.trim());
  return {title: document.title, url: location.href, headings: h, elements: out};
}
"""


def snapshot(page: Page) -> dict[str, Any]:
    return page.evaluate(_JS, MAX_ELEMENTS)


def dom_hash(snap: dict[str, Any]) -> str:
    """Hash theo cấu trúc (tag/selector/chữ), bỏ toạ độ nên cuộn trang không đổi hash."""
    keys = [(e["tag"], e["selector"], e["text"]) for e in snap["elements"]]
    raw = json.dumps(keys, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
