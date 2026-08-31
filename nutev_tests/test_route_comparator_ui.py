from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_route_comparator_is_rank_blind_and_runtime_derived() -> None:
    html = read("review-routes.html")
    script = read("review-routes.js")
    assert "Route comparator" in html
    assert "ARTICLE_SUMMARIES.jsonl" in script
    for forbidden in ("33067", "662", "316", "85", "reference_rank", "reference_score", "machine_relevance_score"):
        assert forbidden not in script


def test_route_comparator_exposes_required_descriptive_views() -> None:
    html = read("review-routes.html")
    script = read("review-routes.js")
    for marker in ("Document types", "Full-text status", "Providers", "Publications over time", "Operational domains", "Exclusive and shared documents"):
        assert marker in html
    assert "exclusiveRows" in script
    assert "overlapRows" in script
    assert "renderTimeline" in script


def test_route_comparator_does_not_call_routed_documents_included() -> None:
    html = read("review-routes.html").lower()
    script = read("review-routes.js").lower()
    assert "não significa inclusão" in html
    assert "não significa inclusão" in script
    assert "included studies" not in html
    assert "included studies" not in script


def test_route_comparator_has_drilldown_to_evidence_explorer() -> None:
    script = read("review-routes.js")
    assert "/evidence.html?route=" in script
    assert "/evidence.html?domain=" in script
    assert "view==='compare'" in script
    assert "params.set('view','compare')" in script
