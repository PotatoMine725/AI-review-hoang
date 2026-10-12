from worker.m1.config import CrawlSettings
from worker.m1.crawl.discover import Frontier, classify
from worker.m1.crawl.errors import SkipReason


def test_phan_loai_page_type() -> None:
    assert classify("https://x.com/", root_host="x.com") == ("other", 1000)
    assert classify("https://x.com/pricing")[0] == "pricing"
    assert classify("https://x.com/features")[0] == "features"
    assert classify("https://x.com/docs")[0] == "docs"
    assert classify("https://x.com/changelog")[0] == "changelog"
    assert classify("https://x.com/compare")[0] == "compare"
    assert classify("https://x.com/faq")[0] == "faq"
    assert classify("https://x.com/about") == ("other", 0)
    # Host phụ: help center là faq
    assert classify("https://support.x.com/", root_host="x.com")[0] == "faq"


def test_trang_sau_va_slug_dai_bi_tru_diem() -> None:
    overview = classify("https://x.com/features")[1]
    deep = classify("https://x.com/features/a/b")[1]
    long_slug = classify("https://x.com/features/how-to-make-great-videos-fast")[1]
    assert overview > deep and overview > long_slug


def make_frontier(extra_ok: bool = False) -> Frontier:
    return Frontier(
        "x.com", lambda h: h == "x.com" or (extra_ok and h.endswith(".x.com")), CrawlSettings()
    )


def test_ly_do_bo_qua_luc_them_ung_vien() -> None:
    f = make_frontier()
    for url in [
        "https://other.com/pricing",
        "https://x.com/logo.png",
        "https://x.com/fr/pricing",
        "https://x.com/ja-jp/features",
        "https://x.com/login",
        "https://x.com/blog/some-long-post",
    ]:
        f.add(url, "sitemap")
    f.add("mailto:a@x.com", "link")
    f.add("javascript:void(0)", "link")
    reasons = {u: c.skip_reason for u, c in f.skipped.items()}
    assert reasons["https://other.com/pricing"] == SkipReason.OUT_OF_SCOPE
    assert reasons["https://x.com/logo.png"] == SkipReason.NON_HTML
    assert reasons["https://x.com/fr/pricing"] == SkipReason.NOT_ENGLISH
    assert reasons["https://x.com/ja-jp/features"] == SkipReason.NOT_ENGLISH
    assert reasons["https://x.com/login"] == SkipReason.EXCLUDED_PATH
    assert reasons["https://x.com/blog/some-long-post"] == SkipReason.EXCLUDED_PATH
    assert not f.candidates


def test_trung_url_sau_chuan_hoa_chi_giu_mot() -> None:
    f = make_frontier()
    f.add("https://x.com/pricing/", "sitemap")
    f.add("https://X.com/pricing?utm_source=a#top", "link:home", "Pricing")
    assert list(f.candidates) == ["https://x.com/pricing"]
    assert f.candidates["https://x.com/pricing"].text == "Pricing"  # bổ sung anchor text


def test_trang_chu_theo_path_van_duoc_crawl_dau_tien() -> None:
    f = make_frontier()
    f.add("https://x.com/products/copilot-for-teams", "home")
    cand = f.candidates["https://x.com/products/copilot-for-teams"]
    assert cand.score == 1000
