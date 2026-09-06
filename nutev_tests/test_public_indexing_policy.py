from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
DOMAIN = "https://nutev.mindsperformance.com.br"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_sitemap_contains_only_core_public_surfaces() -> None:
    tree = ET.parse(WEB / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text for node in tree.findall("sm:url/sm:loc", namespace)]

    assert locations == [
        f"{DOMAIN}/",
        f"{DOMAIN}/search.html",
        f"{DOMAIN}/articles.html",
    ]
    for forbidden in (
        "/advanced.html",
        "/scientific-dashboard.html",
        "/review.html",
        "/validation/",
        "/review-qa.html",
        "/press-review.html",
        "/regional-routes.html",
        "/agent-context/",
        "/evidence.html",
        "/evidence-map.html",
        "/radar.html",
        "/ask.html",
        "/api/",
        "/synthesis-",
        "/recommendation-",
    ):
        assert all(forbidden not in location for location in locations)


def test_robots_declares_sitemap_and_excludes_internal_workflow_surfaces() -> None:
    robots = read("robots.txt")
    assert f"Sitemap: {DOMAIN}/sitemap.xml" in robots
    for path in (
        "/advanced.html",
        "/scientific-dashboard.html",
        "/review.html",
        "/validation/",
        "/review-qa.html",
        "/press-review.html",
        "/regional-routes.html",
        "/strategy.html",
        "/quality.html",
        "/review-routes.html",
        "/intelligence.html",
        "/evidence-claims.html",
        "/claim-appraisal.html",
        "/evidence-sets.html",
        "/ai-context.html",
        "/agent-context/",
        "/synthesis-",
        "/recommendation-",
        "/api/",
    ):
        assert f"Disallow: {path}" in robots


def test_secure_server_emits_fail_closed_noindex_header_for_internal_surfaces() -> None:
    server = read("secure_server.py")
    assert "NOINDEX_EXACT_PATHS" in server
    assert "NOINDEX_PATH_PREFIXES" in server
    assert "_should_noindex(path)" in server
    assert 'self.send_header("X-Robots-Tag", "noindex, nofollow")' in server

    for path in (
        '"/validation"',
        '"/review-qa.html"',
        '"/press-review.html"',
        '"/regional-routes.html"',
        '"/evidence.html"',
        '"/evidence-map.html"',
        '"/radar.html"',
        '"/ask.html"',
        '"/agent-context/"',
        '"/api/"',
    ):
        assert path in server


def test_advanced_laboratory_has_page_level_noindex_defense() -> None:
    advanced = read("advanced.html")
    assert '<meta name="robots" content="noindex,nofollow">' in advanced
    assert "Workflow tipo Rayyan / revisão sistemática" in advanced
    assert "hibernado" in advanced
