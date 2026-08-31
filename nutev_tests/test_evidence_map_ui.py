from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_evidence_map_uses_rank_blind_article_context() -> None:
    html = read("evidence-map.html")
    script = read("evidence-map.js")

    assert "Evidence Map" in html
    assert "/agent-context/article1/ARTICLE_SUMMARIES.jsonl" in script
    for forbidden in (
        "reference_rank",
        "reference_score",
        "machine_relevance_score",
        "verbatim_excerpt",
    ):
        assert forbidden not in script


def test_evidence_map_does_not_hardcode_production_counts() -> None:
    script = read("evidence-map.js")
    for forbidden in ("33067", "33839", "41139", "662", "504", "316", "85"):
        assert forbidden not in script


def test_matrix_has_accessible_domain_document_shape_contract() -> None:
    html = read("evidence-map.html")
    script = read("evidence-map.js")

    assert "Domain × document type" in html
    assert 'caption class="sr-only"' in html
    assert "matrix-cell" in script
    assert "data-domain" in script
    assert "data-document-class" in script
    assert "Contagem não representa força da evidência" in script


def test_empty_cell_does_not_claim_evidence_gap() -> None:
    html = read("evidence-map.html").lower()
    script = read("evidence-map.js").lower()

    assert "no documents mapped" in html
    assert "no documents mapped" in script
    assert "não equivale a ausência de literatura" in html
    assert "evidence absent" not in html
    assert "evidence absent" not in script


def test_evidence_map_supports_matrix_route_and_timeline_views() -> None:
    html = read("evidence-map.html")
    script = read("evidence-map.js")

    for view in ("matrix", "route", "timeline"):
        assert f'data-view="{view}"' in html
    assert "renderMatrix" in script
    assert "renderRouteMatrix" in script
    assert "renderTimeline" in script


def test_map_drills_into_evidence_explorer_intersection() -> None:
    script = read("evidence-map.js")
    evidence = read("evidence.js")

    assert "document_class" in script
    assert "/evidence.html?" in script
    assert "params.get('document_class')" in evidence
    assert "effectiveClass(row)===selectedClass" in evidence
    assert "params.get('route')" in evidence


def test_main_navigation_surfaces_evidence_map() -> None:
    home = read("index.html")
    explorer = read("evidence.html")

    assert 'href="/evidence-map.html"' in home
    assert 'href="/evidence-map.html"' in explorer
