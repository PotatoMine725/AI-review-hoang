"""Spike M1 — 1.2 Discover & Crawl.

Luồng cho 1 product:
  robots.txt → sitemap.xml → crawl trang chủ → frontier (link + sitemap) chấm điểm theo page_type
  → crawl lần lượt trang điểm cao nhất (≤ MAX_PAGES) → ghi pages/*.md và crawl.json.

Chạy riêng: `uv run python crawl.py [slug ...]` (mặc định: mọi product trong products.json).
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import itertools
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, PruningContentFilterLXML
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# ---------------------------------------------------------------- config
ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
PRODUCTS_FILE = ROOT / "products.json"

# User-Agent định danh dự án (NFR-05). Không giả trình duyệt, không đổi UA ngẫu nhiên.
USER_AGENT = (
    "AIReviewContentFactory-Spike/0.1 (+https://github.com/PotatoMine725/AI-review-BE; M1 research spike)"
)
MAX_PAGES = 30  # ≤ 30 trang/product, tính cả trang chủ
MAX_EXTRA_HOST_PAGES = 5  # trang từ subdomain (vd. support.claude.com), tính chung trong MAX_PAGES
# Host phụ chỉ dùng để bù FAQ / giá (help center). Không lấy docs/academy để không chiếm slot của host gốc.
EXTRA_HOST_TYPES = ("faq", "pricing")
MIN_INTERVAL_S = 1.0  # ≤ 1 request/giây/host ("request" = 1 lần mở trang hoặc tải robots/sitemap)
MAX_CHILD_SITEMAPS = 5  # sitemap index có thể rất lớn
MAX_SITEMAP_URLS = 5000
HTTP_TIMEOUT_S = 20
PAGE_TIMEOUT_MS = 45_000
RENDER_DELAY_S = 3.0  # chờ thêm sau domcontentloaded cho trang SPA
MIN_HOME_CHARS = 200  # trang chủ ít hơn mức này → coi là bị chặn / không render được
# Hạn mức trang theo page_type để không bị 1 loại (thường là features) chiếm hết 30 slot.
# Slot còn trống sau khi hết ứng viên trong hạn mức thì lấp theo điểm.
TYPE_QUOTA = {"other": 1, "pricing": 4, "features": 10, "docs": 6, "faq": 4, "compare": 3, "changelog": 2}

# page_type theo spec: pricing, features, docs, faq, changelog, compare, other.
# (page_type, điểm, regex trên path + anchor text). Thứ tự = ưu tiên khi trùng.
PAGE_TYPE_RULES: list[tuple[str, int, re.Pattern[str]]] = [
    (
        "pricing",
        100,
        re.compile(r"\bpric(e|es|ing)\b|/plans?\b(?!-)|billing|subscriptions?\b|membership", re.IGNORECASE),
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
    ("faq", 75, re.compile(r"\bfaqs?\b|frequently|common-questions|\bhelp\b|support", re.IGNORECASE)),
    ("compare", 70, re.compile(r"compare|comparison|\bvs\b|-vs-|alternative", re.IGNORECASE)),
    (
        "docs",
        60,
        re.compile(r"\bdocs?\b|documentation|\bguides?\b|tutorial|\blearn\b|\bapi\b", re.IGNORECASE),
    ),
    ("changelog", 50, re.compile(r"changelog|release-?notes|what-?s-?new|\bupdates?\b", re.IGNORECASE)),
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
LOGIN_URL = re.compile(r"login|signin|sign-in|signup|auth|accounts?\.", re.IGNORECASE)
# Dấu hiệu chặn bot. HTML: chỉ dò marker đặc thù của trang thử thách (chữ "captcha" có thể nằm trong CSS
# của form thường). Nội dung hiển thị: dò câu thông báo chặn.
BLOCK_HTML_MARKERS = re.compile(r"cf-chl|challenge-platform|cf_chl_opt|_cf_chl", re.IGNORECASE)
BLOCK_TEXT_MARKERS = re.compile(
    r"just a moment|attention required|access denied|verify you are human|unusual traffic|"
    r"checking your browser|enable javascript and cookies",
    re.IGNORECASE,
)
PRICE_RE = re.compile(
    r"([$€£¥₫]\s?\d)|(\b\d[\d.,]*\s?([$€£¥₫]|usd\b|eur\b|vnd\b|/\s?mo\b|/\s?month|per month))|"
    r"((usd|eur|vnd)\s?\d)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- helpers
def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def normalize_url(url: str) -> str:
    """Bỏ query, fragment, dấu / cuối; hạ chữ thường scheme + host."""
    p = urlsplit(url)
    path = p.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, "", ""))


def normalize_text(md: str) -> str:
    """Chuẩn hoá markdown trước khi băm: bỏ khoảng trắng thừa và dòng trống liên tiếp."""
    lines = [ln.rstrip() for ln in md.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    for ln in lines:
        if ln == "" and (not out or out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip() + "\n"


MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_TARGET = re.compile(r"\]\([^)]*\)")


def content_hash(text: str) -> str:
    """Băm nội dung đã bỏ ảnh và URL đích của link, để hash chỉ đổi khi chữ đổi (SP-07).
    Link có token đổi theo mỗi lần tải trang (vd. claude.ai/redirect/<uuid>/…); ảnh lazy-load đổi vị trí."""
    stable = MD_LINK_TARGET.sub("]", MD_IMAGE.sub("", text))
    stable = "\n".join(ln for ln in stable.splitlines() if ln.strip())
    return "sha256:" + hashlib.sha256(stable.encode("utf-8")).hexdigest()


def classify(url: str, text: str = "", root_host: str = "") -> tuple[str, int]:
    """Trả (page_type, điểm).

    Phạt độ sâu path (ưu tiên trang tổng quan) và slug dài nhiều từ (thường là bài viết / mục danh bạ).
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


def slugify(url: str) -> str:
    path = urlsplit(url).path.strip("/") or "home"
    return re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-")[:60] or "home"


# ---------------------------------------------------------------- polite fetching
class Throttle:
    """Giữ khoảng cách ≥ interval giữa 2 lần bắt đầu request tới cùng host, và ghi log.

    interval = max(MIN_INTERVAL_S, Crawl-delay trong robots.txt nếu có).
    """

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._interval: dict[str, float] = {}
        self._last: dict[str, float] = {}
        self.log: list[dict] = []

    def set_interval(self, host: str, seconds: float) -> None:
        self._interval[host] = max(self.min_interval, seconds)

    async def wait(self, url: str, kind: str) -> dict:
        host = urlsplit(url).netloc
        interval = self._interval.get(host, self.min_interval)
        last = self._last.get(host)
        # Lặp vì trên Windows asyncio.sleep có thể dậy sớm ~15 ms
        while last is not None and (gap := time.monotonic() - last) < interval:
            await asyncio.sleep(interval - gap + 0.005)
        t = time.monotonic()
        entry = {"url": url, "kind": kind, "host": host, "t": round(t, 3), "fetched_at": now_iso()}
        self._last[host] = t
        self.log.append(entry)
        return entry

    def min_observed_interval(self) -> dict[str, float | None]:
        by_host: dict[str, list[float]] = {}
        for e in self.log:
            by_host.setdefault(e["host"], []).append(e["t"])
        result: dict[str, float | None] = {}
        for host, ts in by_host.items():
            gaps = [b - a for a, b in itertools.pairwise(ts)]
            result[host] = round(min(gaps), 3) if gaps else None
        return result


def http_get(url: str) -> tuple[int | None, bytes, str, dict[str, str]]:
    """GET bằng urllib với UA dự án. Trả (status, body, lỗi, header viết thường)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.status, resp.read(), "", {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        # Đọc ít byte để dò trang challenge; lỗi HTTP không cần cả body
        body = e.read(4096)
        return e.code, body, str(e), {k.lower(): v for k, v in e.headers.items()}
    except Exception as e:  # noqa: BLE001 — spike: ghi lỗi mạng vào crawl.json
        return None, b"", f"{type(e).__name__}: {e}", {}


def waf_challenge(status: int | None, body: bytes, headers: dict[str, str]) -> str:
    """Trả mô tả nếu response là trang thử thách của WAF (Cloudflare…), ngược lại chuỗi rỗng.
    Không vượt thử thách: chỉ nhận diện để ghi đúng lý do."""
    text = body.decode("utf-8", errors="replace")
    if (
        headers.get("cf-mitigated", "").lower() == "challenge"
        or BLOCK_HTML_MARKERS.search(text)
        or BLOCK_TEXT_MARKERS.search(text)
    ):
        return f"waf_challenge: status={status} cf-ray={headers.get('cf-ray', '-')} server={headers.get('server', '-')}"
    return ""


UA_TOKEN = USER_AGENT.split("/", 1)[0].lower()  # product token để khớp nhóm User-agent trong robots.txt


def parse_robots(text: str) -> tuple[list[tuple[str, str]], float | None, list[str], str]:
    """Parse robots.txt theo RFC 9309. Trả (rule áp cho UA của dự án, crawl-delay, sitemaps, nhóm đã chọn).

    Không dùng urllib.robotparser vì nó không hỗ trợ wildcard `*`/`$` và lấy rule khớp đầu tiên
    thay vì rule khớp dài nhất.
    """
    groups: list[tuple[list[str], list[tuple[str, str]], float | None]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    delay: float | None = None
    sitemaps: list[str] = []
    last_was_agent = False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "sitemap":
            sitemaps.append(value)
        elif key == "user-agent":
            if not last_was_agent and agents:
                groups.append((agents, rules, delay))
                agents, rules, delay = [], [], None
            agents.append(value.lower())
            last_was_agent = True
            continue
        elif key in ("allow", "disallow") and agents:
            rules.append((key, value))
        elif key == "crawl-delay" and agents:
            try:
                delay = float(value)
            except ValueError:
                pass
        last_was_agent = False
    if agents:
        groups.append((agents, rules, delay))
    mine = [g for g in groups if UA_TOKEN in g[0]]
    chosen = mine or [g for g in groups if "*" in g[0]]
    merged_rules = [r for g in chosen for r in g[1]]
    delays = [g[2] for g in chosen if g[2] is not None]
    label = "own" if mine else ("*" if chosen else "none")
    return merged_rules, (max(delays) if delays else None), sitemaps, label


def _rule_regex(pattern: str) -> re.Pattern[str]:
    esc = re.escape(pattern).replace(r"\*", ".*")
    if esc.endswith(r"\$"):
        esc = esc[:-2] + "$"
    return re.compile("^" + esc)


def robots_decision(rules: list[tuple[str, str]], url: str) -> tuple[bool, str]:
    """Rule khớp dài nhất thắng; bằng nhau thì allow thắng. Không rule nào khớp → được phép."""
    p = urlsplit(url)
    target = (p.path or "/") + (f"?{p.query}" if p.query else "")
    hits = [(k, v) for k, v in rules if v and _rule_regex(v).match(target)]
    if not hits:
        return True, "no_match"
    kind, value = max(hits, key=lambda kv: (len(kv[1]), kv[0] == "allow"))
    return kind == "allow", f"{kind}: {value}"


@dataclass
class Robots:
    host: str
    url: str
    status: int | None
    policy: str  # "parsed" | "allow_all" | "disallow_all"
    sitemaps: list[str]
    fetched_at: str
    error: str = ""
    group: str = ""  # nhóm User-agent áp dụng: "own" | "*" | "none"
    rules: list[tuple[str, str]] = field(default_factory=list)
    crawl_delay: float | None = None

    def decide(self, url: str) -> tuple[bool, str]:
        if self.policy == "allow_all":
            return True, f"allow_all (robots.txt {self.status})"
        if self.policy == "disallow_all":
            return False, f"disallow_all (robots.txt {self.status})"
        return robots_decision(self.rules, url)

    def to_json(self) -> dict:
        return asdict(self)


async def fetch_robots(base: str, throttle: Throttle) -> Robots:
    """Tự tải robots.txt bằng UA dự án (RobotFileParser.read() dùng UA Python-urllib)."""
    url = urljoin(base, "/robots.txt")
    log = await throttle.wait(url, "robots")
    status, body, err, headers = await asyncio.to_thread(http_get, url)
    log["status"] = status
    host = urlsplit(base).netloc
    if challenge := waf_challenge(status, body, headers):
        # Trang thử thách của WAF, không phải robots.txt: không nói gì về việc được phép hay không → không crawl.
        return Robots(host, url, status, "disallow_all", [], log["fetched_at"], challenge)
    if status == 200:
        rules, delay, sitemaps, group = parse_robots(body.decode("utf-8", errors="replace"))
        if delay:
            throttle.set_interval(host, delay)
        return Robots(host, url, status, "parsed", sitemaps, log["fetched_at"], err, group, rules, delay)
    if status is not None and 400 <= status < 500 and status not in (401, 403, 429):
        # RFC 9309: robots.txt không tồn tại → được phép crawl
        return Robots(host, url, status, "allow_all", [], log["fetched_at"], err)
    # 401/403/429/5xx/lỗi mạng → thận trọng: không crawl host này
    return Robots(host, url, status, "disallow_all", [], log["fetched_at"], err)


async def fetch_sitemap_urls(
    sitemaps: list[str], base: str, throttle: Throttle
) -> tuple[list[str], list[dict]]:
    """Đọc sitemap (và tối đa MAX_CHILD_SITEMAPS sitemap con). Trả (danh sách URL, log)."""
    queue = list(sitemaps) or [urljoin(base, "/sitemap.xml")]
    seen: set[str] = set()
    urls: list[str] = []
    report: list[dict] = []
    child_budget = MAX_CHILD_SITEMAPS
    while queue and len(urls) < MAX_SITEMAP_URLS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        log = await throttle.wait(sm, "sitemap")
        status, body, err, _ = await asyncio.to_thread(http_get, sm)
        log["status"] = status
        entry = {"url": sm, "status": status, "urls": 0, "children": 0, "error": err}
        report.append(entry)
        if status != 200 or not body:
            continue
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            entry["error"] = f"ParseError: {e}"
            continue
        locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
        if root.tag.endswith("sitemapindex"):
            # Ưu tiên sitemap trang chính, để blog/news/post xuống cuối
            locs.sort(key=lambda u: bool(re.search(r"blog|post|news|article|customer", u, re.IGNORECASE)))
            take = locs[:child_budget]
            child_budget -= len(take)
            entry["children"] = len(locs)
            queue.extend(take)
        else:
            entry["urls"] = len(locs)
            urls.extend(locs)
    return urls[:MAX_SITEMAP_URLS], report


# ---------------------------------------------------------------- crawl
@dataclass
class Candidate:
    url: str
    source: str  # "home" | "sitemap" | "link:<url trang chứa>"
    text: str = ""
    page_type: str = "other"
    score: int = 0
    skip_reason: str = ""


def detect_block(result, is_home: bool) -> str:
    """Trả lý do nếu trang có dấu hiệu chặn bot / bắt đăng nhập, ngược lại chuỗi rỗng."""
    status = getattr(result, "status_code", None)
    if status in (404, 410):
        # Trang không tồn tại. Crawl4AI có thể gắn nhãn anti-bot cho trang lỗi ít chữ, nên kiểm tra trước.
        return f"not_found: http_{status}"
    if not result.success:
        return f"crawl_failed: {result.error_message}"[:300]
    if status in (401, 403, 429, 503):
        return f"http_{status}"
    final = getattr(result, "redirected_url", None) or result.url
    if final and LOGIN_URL.search(urlsplit(final).netloc + urlsplit(final).path):
        return f"login_redirect: {final}"
    raw = result.markdown.raw_markdown if result.markdown else ""
    title = str((result.metadata or {}).get("title") or "")
    if len(raw) < 3000 and (
        BLOCK_HTML_MARKERS.search((result.html or "")[:50000]) or BLOCK_TEXT_MARKERS.search(f"{title}\n{raw}")
    ):
        return "bot_challenge_marker"
    if is_home and len(raw) < MIN_HOME_CHARS:
        return f"home_too_short: {len(raw)} chars"
    return ""


def run_config() -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,  # không dùng cache: số liệu thời gian + log request phải thật
        user_agent=USER_AGENT,
        wait_until="domcontentloaded",  # networkidle hay treo ở SPA
        delay_before_return_html=RENDER_DELAY_S,
        scan_full_page=True,  # cuộn hết trang để nội dung lazy-load hiện ra
        page_timeout=PAGE_TIMEOUT_MS,
        word_count_threshold=3,  # mặc định cao làm rơi thẻ giá (ít chữ)
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilterLXML(
                threshold=0.45, threshold_type="dynamic", min_word_threshold=3
            ),
        ),
        verbose=False,
    )


async def crawl_product(product: dict) -> dict:
    slug, root_url = product["slug"], product["url"]
    root_host = urlsplit(root_url).netloc.lower()
    allowed_hosts = {root_host, *[h.lower() for h in product.get("extra_hosts", [])]}
    # allow_subdomains: nhận cả *.<domain gốc> (vd. support.claude.com). Không bật cho Dreamina,
    # vì domain gốc của dreamina.capcut.com là capcut.com — sản phẩm khác.
    sub_suffix = "." + root_host.removeprefix("www.") if product.get("allow_subdomains") else None

    def host_ok(host: str) -> bool:
        return host in allowed_hosts or bool(sub_suffix and host.endswith(sub_suffix))

    out_dir = OUTPUT_DIR / slug
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    for old in pages_dir.glob("*.md"):
        old.unlink()

    throttle = Throttle(MIN_INTERVAL_S)
    started = time.monotonic()
    report: dict = {
        "product": slug,
        "name": product["name"],
        "root_url": root_url,
        "allowed_hosts": sorted(allowed_hosts) + ([f"*{sub_suffix}"] if sub_suffix else []),
        "user_agent": USER_AGENT,
        "limits": {
            "max_pages": MAX_PAGES,
            "max_extra_host_pages": MAX_EXTRA_HOST_PAGES,
            "min_interval_s": MIN_INTERVAL_S,
        },
        "started_at": now_iso(),
        "blocked": None,
    }

    robots_by_host: dict[str, Robots] = {}

    async def robots_for(url: str) -> Robots:
        host = urlsplit(url).netloc.lower()
        if host not in robots_by_host:
            robots_by_host[host] = await fetch_robots(f"https://{host}", throttle)
        return robots_by_host[host]

    home_robots = await robots_for(root_url)
    sitemap_urls, sitemap_report = await fetch_sitemap_urls(home_robots.sitemaps, root_url, throttle)
    report["sitemaps"] = sitemap_report

    frontier: dict[str, Candidate] = {}
    skipped: dict[str, Candidate] = {}

    def add_candidate(raw_url: str, source: str, text: str = "") -> None:
        if not raw_url or raw_url.startswith(("mailto:", "tel:", "javascript:")):
            return
        url = normalize_url(raw_url)
        if url in frontier or url in skipped:
            if url in frontier and text and not frontier[url].text:
                frontier[url].text = text[:80]
            return
        c = Candidate(url, source, (text or "").strip()[:80])
        p = urlsplit(url)
        first_seg = next((s for s in p.path.split("/") if s), "")
        if p.scheme not in ("http", "https") or not host_ok(p.netloc):
            c.skip_reason = "out_of_scope"
        elif ASSET_EXT.search(p.path):
            c.skip_reason = "asset"
        elif LOCALE_SEG.match(first_seg):
            c.skip_reason = "locale_duplicate"
        elif SKIP_PATH.search(p.path):
            c.skip_reason = "excluded_path"
        if c.skip_reason:
            # Không lưu hết link ngoài domain cho gọn crawl.json, chỉ đếm
            skipped[url] = c
            return
        c.page_type, c.score = classify(url, c.text, root_host)
        frontier[url] = c

    add_candidate(root_url, "home")
    for u in sitemap_urls:
        add_candidate(u, "sitemap")

    browser_cfg = BrowserConfig(headless=True, user_agent=USER_AGENT, verbose=False)
    cfg = run_config()
    pages: list[dict] = []
    seen_hashes: dict[str, str] = {}
    crawled: set[str] = set()

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        while len(crawled) < MAX_PAGES:
            # `crawled` đếm cả lần mở trang lỗi/trùng → MAX_PAGES giới hạn số request trang, không chỉ trang dùng
            extra_used = sum(urlsplit(u).netloc != root_host for u in crawled)
            todo = [
                c
                for c in frontier.values()
                if c.url not in crawled
                and c.score > 0
                and (
                    urlsplit(c.url).netloc == root_host
                    or (extra_used < MAX_EXTRA_HOST_PAGES and c.page_type in EXTRA_HOST_TYPES)
                )
            ]
            if not todo:
                break
            used_by_type: dict[str, int] = {}
            for p in pages:
                used_by_type[p["page_type"]] = used_by_type.get(p["page_type"], 0) + 1
            in_quota = [c for c in todo if used_by_type.get(c.page_type, 0) < TYPE_QUOTA.get(c.page_type, 0)]
            todo = in_quota or todo
            todo.sort(key=lambda c: (-c.score, len(c.url)))
            cand = todo[0]
            crawled.add(cand.url)
            is_home = cand.source == "home"

            robots = await robots_for(cand.url)
            robots_ok, robots_rule = robots.decide(cand.url)
            if not robots_ok:
                cand.skip_reason = (
                    robots.error
                    if robots.error.startswith("waf_challenge")
                    else f"robots_disallow ({robots_rule})"
                )
                skipped[cand.url] = frontier.pop(cand.url)
                crawled.discard(cand.url)
                if is_home:
                    report["blocked"] = (
                        robots.error
                        if robots.error.startswith("waf_challenge")
                        else f"robots.txt không cho phép trang chủ (status {robots.status})"
                    )
                    break
                continue

            log = await throttle.wait(cand.url, "page")
            t0 = time.monotonic()
            result = await crawler.arun(cand.url, config=cfg)
            elapsed = round(time.monotonic() - t0, 2)
            log["status"] = getattr(result, "status_code", None)

            block = detect_block(result, is_home)
            if block.startswith("not_found") and not is_home:
                cand.skip_reason = block
                skipped[cand.url] = frontier.pop(cand.url)
                continue
            if block:
                cand.skip_reason = f"blocked: {block}"
                skipped[cand.url] = frontier.pop(cand.url)
                if is_home or block.startswith(("http_403", "http_429", "bot_challenge")):
                    # Dừng cả product: không cố vượt chặn. login_redirect ở trang con (vd. /app) chỉ bỏ qua trang đó.
                    report["blocked"] = f"{cand.url}: {block}"
                    break
                continue

            final_url = normalize_url(getattr(result, "redirected_url", None) or result.url)
            if not host_ok(urlsplit(final_url).netloc):
                cand.skip_reason = f"redirect_out_of_scope: {final_url}"
                skipped[cand.url] = frontier.pop(cand.url)
                continue

            raw_md = normalize_text(result.markdown.raw_markdown or "")
            fit_md = normalize_text(result.markdown.fit_markdown or "")
            # Bước 2 chọn gửi raw hay fit cho LLM, nên lưu hash của cả hai. Khử trùng theo raw.
            raw_hash, fit_hash = content_hash(raw_md), content_hash(fit_md)
            if raw_hash in seen_hashes:
                cand.skip_reason = f"duplicate_of: {seen_hashes[raw_hash]}"
                skipped[cand.url] = frontier.pop(cand.url)
                continue
            seen_hashes[raw_hash] = cand.url

            # Link mới từ trang này vào frontier (không tốn request thêm)
            for link in (result.links or {}).get("internal", []):
                add_candidate(link.get("href", ""), f"link:{cand.url}", link.get("text", ""))

            page_id = f"src_{len(pages) + 1:02d}"
            fname = f"{page_id}-{cand.page_type}-{slugify(cand.url)}"
            header = (
                f"<!-- source_id: {page_id} | url: {cand.url} | page_type: {cand.page_type} "
                f"| fetched_at: {log['fetched_at']} -->\n\n"
            )
            (pages_dir / f"{fname}.md").write_text(header + fit_md, encoding="utf-8")
            (pages_dir / f"{fname}.raw.md").write_text(header + raw_md, encoding="utf-8")
            pages.append(
                {
                    "id": page_id,
                    "url": cand.url,
                    "final_url": final_url,
                    "page_type": cand.page_type,
                    "score": cand.score,
                    "found_via": cand.source,
                    "anchor_text": cand.text,
                    "status": log["status"],
                    "robots_allowed": robots_ok,
                    "robots_rule": robots_rule,
                    "fetched_at": log["fetched_at"],
                    "render_seconds": elapsed,
                    "raw_chars": len(raw_md),
                    "fit_chars": len(fit_md),
                    "raw_has_price": bool(PRICE_RE.search(raw_md)),
                    "fit_has_price": bool(PRICE_RE.search(fit_md)),
                    "raw_hash": raw_hash,
                    "fit_hash": fit_hash,
                    "file": f"pages/{fname}.md",
                    "raw_file": f"pages/{fname}.raw.md",
                }
            )
            print(f"  [{len(pages):02d}] {cand.page_type:9} {cand.score:3} {len(fit_md):6}c  {cand.url}")

    # Trang còn trong frontier nhưng không crawl: vượt giới hạn hoặc điểm 0 (other)
    for c in frontier.values():
        if c.url not in crawled:
            c.skip_reason = "over_limit" if c.score > 0 else "low_score"
            skipped[c.url] = c

    report["finished_at"] = now_iso()
    report["crawl_seconds"] = round(time.monotonic() - started, 2)
    report["robots"] = {h: r.to_json() for h, r in robots_by_host.items()}
    report["requests"] = throttle.log
    report["min_observed_interval_s"] = throttle.min_observed_interval()
    report["pages_found"] = len(pages) + len(skipped)
    report["pages_used"] = len(pages)
    counts: dict[str, int] = {}
    for c in skipped.values():
        key = c.skip_reason.split(":")[0].split(" (")[0]
        counts[key] = counts.get(key, 0) + 1
    report["skipped_counts"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    report["skipped"] = trim_skipped(
        [
            {
                "url": c.url,
                "reason": c.skip_reason,
                "page_type": c.page_type,
                "score": c.score,
                "found_via": c.source,
            }
            for c in sorted(skipped.values(), key=lambda c: (-c.score, c.url))
        ]
    )
    report["pages"] = pages
    (out_dir / "crawl.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


SKIPPED_DETAIL_LIMIT = 50  # số trang over_limit điểm cao nhất được ghi chi tiết


def trim_skipped(rows: list[dict]) -> list[dict]:
    """Giữ crawl.json gọn: ghi đủ trang bị bỏ vì robots / chặn / trùng / redirect (bằng chứng AC-01),
    chỉ giữ SKIPPED_DETAIL_LIMIT trang over_limit điểm cao nhất; lý do khác chỉ đếm trong skipped_counts.
    `rows` phải đã sắp theo điểm giảm dần."""
    always = ("robots_disallow", "waf_challenge", "blocked", "duplicate_of", "redirect_out_of_scope")
    keep = [r for r in rows if r["reason"].startswith(always)]
    keep += [r for r in rows if r["reason"] == "over_limit"][:SKIPPED_DETAIL_LIMIT]
    return keep


def print_summary(report: dict) -> None:
    print(f"\n=== {report['name']} ({report['root_url']}) ===")
    if report["blocked"]:
        print(f"!! BLOCKED: {report['blocked']}")
    print(
        f"found={report['pages_found']} used={report['pages_used']} crawl_seconds={report['crawl_seconds']} "
        f"min_interval={report['min_observed_interval_s']}"
    )
    print(
        f"robots: {{{', '.join(f'{h}: {r["status"]}/{r["policy"]}' for h, r in report['robots'].items())}}}"
    )
    print(f"skipped: {report['skipped_counts']}")
    print(f"{'id':6} {'page_type':9} {'raw':>7} {'fit':>7} {'$raw':>4} {'$fit':>4}  url")
    for p in report["pages"]:
        print(
            f"{p['id']:6} {p['page_type']:9} {p['raw_chars']:7} {p['fit_chars']:7} "
            f"{'y' if p['raw_has_price'] else '-':>4} {'y' if p['fit_has_price'] else '-':>4}  {p['url']}"
        )


def load_products(slugs: list[str] | None = None) -> list[dict]:
    products = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    return [p for p in products if not slugs or p["slug"] in slugs]


async def main(slugs: list[str]) -> None:
    for product in load_products(slugs):
        print(f"\n--- crawl {product['slug']} ---")
        print_summary(await crawl_product(product))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # Windows cp1252
    asyncio.run(main(sys.argv[1:]))
