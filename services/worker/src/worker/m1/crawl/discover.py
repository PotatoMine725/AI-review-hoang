"""Tìm trang đáng crawl: đọc sitemap, chấm điểm link, phân loại `page_type`, chọn trang kế tiếp.

Logic giữ nguyên từ spike `spikes/m1-crawl-extract/crawl.py`.
"""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from worker.m1.config import CrawlSettings
from worker.m1.crawl.errors import SkipReason
from worker.m1.crawl.http import HttpClient
from worker.m1.crawl.throttle import Throttle
from worker.m1.url import normalize_page_url

# page_type theo spec: pricing, features, docs, faq, changelog, compare, other.
# (page_type, điểm, regex trên path + anchor text). Thứ tự = ưu tiên khi trùng.
PAGE_TYPE_RULES: list[tuple[str, int, re.Pattern[str]]] = [
    (
        "pricing",
        100,
        re.compile(
            r"\bpric(e|es|ing)\b|/plans?\b(?!-)|billing|subscriptions?\b|membership", re.IGNORECASE
        ),
    ),
    (
        "features",
        80,
        re.compile(
            r"feature|\bproduct|solution|capabilit|\btools?\b|use-?cases?|\bmodels?\b|generator|"
            r"ai-(image|video|art|design)|image-to|text-to|\bcode\b|\bapps?\b|integration",
            re.IGNORECASE,
        ),
    ),
    (
        "faq",
        75,
        re.compile(r"\bfaqs?\b|frequently|common-questions|\bhelp\b|support", re.IGNORECASE),
    ),
    ("compare", 70, re.compile(r"compare|comparison|\bvs\b|-vs-|alternative", re.IGNORECASE)),
    (
        "docs",
        60,
        re.compile(
            r"\bdocs?\b|documentation|\bguides?\b|tutorial|\blearn\b|\bapi\b", re.IGNORECASE
        ),
    ),
    (
        "changelog",
        50,
        re.compile(r"changelog|release-?notes|what-?s-?new|\bupdates?\b", re.IGNORECASE),
    ),
]
# Không crawl: đăng nhập / tài khoản / pháp lý / tuyển dụng / bài blog dài dòng.
SKIP_PATH = re.compile(
    r"login|log-in|signin|sign-in|signup|sign-up|register|\bauth\b|oauth|account|logout|checkout|"
    r"\blegal\b|privacy|terms|cookie|careers?|\bjobs?\b|press|/blog/.+|/news/.+|/customers?/.+|/events?/|"
    r"/marketplace/.+",  # danh bạ app bên thứ ba, không phải fact của product
    re.IGNORECASE,
)
ASSET_EXT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|ico|pdf|zip|mp4|webm|mp3|css|js|json|xml|txt|gz)$", re.IGNORECASE
)
# Tiền tố ngôn ngữ khác tiếng Anh, ví dụ /fr/, /ja-jp/ → bỏ để không tốn slot cho bản dịch.
LOCALE_SEG = re.compile(
    r"^(fr|de|es|it|pt|ja|ko|zh|ru|id|vi|th|tr|nl|pl|ar|hi|sv|da|fi|no|nb|cs|uk|he|ms|fil|ro|hu|el)"
    r"([-_][a-z]{2,4})?$",
    re.IGNORECASE,
)


def classify(url: str, text: str = "", root_host: str = "") -> tuple[str, int]:
    """Trả (page_type, điểm).

    Phạt độ sâu path (ưu tiên trang tổng quan) và slug dài nhiều từ (thường là bài viết, danh bạ).
    """
    host, path = urlsplit(url).netloc, urlsplit(url).path
    extra_host = bool(root_host) and host != root_host
    if path in ("", "/") and not extra_host:
        return "other", 1000  # trang chủ: crawl đầu tiên (kiểm tra chặn bot), chứa identity + hero
    # Anchor text chỉ tính khi ngắn (link điều hướng như "Pricing"); tiêu đề bài viết dài gây nhiễu.
    haystack = f"{path} {text}" if len(text.split()) <= 4 else path
    if extra_host:
        haystack += f" {host}"  # host phụ như support.* → faq nếu path không khớp loại khác
    if not [s for s in path.split("/") if s]:
        path = "/home"  # trang gốc của host phụ
    segments = [s for s in path.split("/") if s]
    penalty = 15 * (len(segments) - 1)
    if len(re.split(r"[-_]", segments[-1])) > 3:
        penalty += 30
    for page_type, score, pattern in PAGE_TYPE_RULES:
        if pattern.search(haystack):
            return page_type, max(score - penalty, 1)
    return "other", 0


@dataclass
class Candidate:
    url: str
    source: str  # "home" | "sitemap" | "link:<url trang chứa>"
    text: str = ""
    page_type: str = "other"
    score: int = 0
    skip_reason: SkipReason | None = None
    skip_detail: str = ""


class Frontier:
    """Danh sách trang ứng viên. `host_ok` quyết định host nào nằm trong phạm vi crawl."""

    def __init__(
        self, root_host: str, host_ok: Callable[[str], bool], settings: CrawlSettings
    ) -> None:
        self.root_host = root_host
        self._host_ok = host_ok
        self._settings = settings
        self.candidates: dict[str, Candidate] = {}
        self.skipped: dict[str, Candidate] = {}

    def add(self, raw_url: str, source: str, text: str = "") -> None:
        if not raw_url or raw_url.startswith(("mailto:", "tel:", "javascript:")):
            return
        try:
            url = normalize_page_url(raw_url)
        except ValueError:
            return  # link rác
        if url in self.candidates or url in self.skipped:
            if url in self.candidates and text and not self.candidates[url].text:
                self.candidates[url].text = text[:80]
            return
        cand = Candidate(url, source, (text or "").strip()[:80])
        p = urlsplit(url)
        first_seg = next((s for s in p.path.split("/") if s), "")
        if p.scheme not in ("http", "https") or not self._host_ok(p.netloc):
            cand.skip_reason = SkipReason.OUT_OF_SCOPE
        elif ASSET_EXT.search(p.path):
            cand.skip_reason = SkipReason.NON_HTML
        elif LOCALE_SEG.match(first_seg):
            cand.skip_reason = SkipReason.NOT_ENGLISH
        elif SKIP_PATH.search(p.path):
            cand.skip_reason = SkipReason.EXCLUDED_PATH
        if cand.skip_reason:
            self.skipped[url] = cand
            return
        cand.page_type, cand.score = classify(url, cand.text, self.root_host)
        if source == "home":
            # Trang chủ luôn crawl đầu tiên, kể cả khi product nằm ở path (vd. /features/copilot)
            cand.score = 1000
        self.candidates[url] = cand

    def skip(self, cand: Candidate, reason: SkipReason, detail: str = "") -> None:
        """Chuyển ứng viên sang danh sách bỏ qua."""
        cand.skip_reason, cand.skip_detail = reason, detail
        self.candidates.pop(cand.url, None)
        self.skipped[cand.url] = cand

    def pick_next(
        self, tried: set[str], used_by_type: Counter[str], blocked_hosts: set[str]
    ) -> Candidate | None:
        """Chọn trang điểm cao nhất, ưu tiên loại còn trong hạn mức `type_quota`."""
        s = self._settings
        extra_used = sum(urlsplit(u).netloc != self.root_host for u in tried)
        todo = [
            c
            for c in self.candidates.values()
            if c.url not in tried
            and c.score > 0
            and urlsplit(c.url).netloc not in blocked_hosts
            and (
                urlsplit(c.url).netloc == self.root_host
                or (extra_used < s.max_extra_host_pages and c.page_type in s.extra_host_types)
            )
        ]
        if not todo:
            return None
        in_quota = [c for c in todo if used_by_type[c.page_type] < s.type_quota.get(c.page_type, 0)]
        todo = in_quota or todo
        todo.sort(key=lambda c: (-c.score, len(c.url)))
        return todo[0]


async def fetch_sitemap_urls(
    sitemaps: list[str],
    base: str,
    throttle: Throttle,
    http: HttpClient,
    settings: CrawlSettings,
) -> list[str]:
    """Đọc sitemap (và tối đa `max_child_sitemaps` sitemap con). Trả danh sách URL."""
    queue = list(sitemaps) or [urljoin(base, "/sitemap.xml")]
    seen: set[str] = set()
    urls: list[str] = []
    child_budget = settings.max_child_sitemaps
    while queue and len(urls) < settings.max_sitemap_urls:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        log = await throttle.wait(sm, "sitemap")
        resp = await http.get(sm)
        log.status = resp.status
        body = resp.body
        if resp.status != 200 or not body:
            continue
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue
        locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
        if root.tag.endswith("sitemapindex"):
            # Ưu tiên sitemap trang chính, để blog/news/post xuống cuối
            locs.sort(
                key=lambda u: bool(re.search(r"blog|post|news|article|customer", u, re.IGNORECASE))
            )
            take = locs[:child_budget]
            child_budget -= len(take)
            queue.extend(take)
        else:
            urls.extend(locs)
    return urls[: settings.max_sitemap_urls]
