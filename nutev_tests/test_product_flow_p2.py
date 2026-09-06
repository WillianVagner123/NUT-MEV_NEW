import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_guided_strategy_flow_is_persistent_but_does_not_invent_cross_gate_authority() -> None:
    product = read("product-ui.js")
    sync = read("strategy-flow-sync.js")

    assert "nutev_strategy_flow:article1-scientific-closure-v1" in product
    assert "window.NutEVStrategyFlow" in product
    assert "os gates permanecem independentes" in product
    assert "nenhuma etapa autoriza automaticamente a decisão científica seguinte" in product

    assert "scientific_decision:'PENDING_HUMAN_REVIEW'" in sync
    assert "PRESS_REVIEW_COMPLETE_PENDING_CANONICAL_REGISTRATION" in sync
    assert "freeze_authorized:false" in sync
    assert "gf10_authorized:false" in sync
    assert "gf01_candidate_complete:true" in sync
    assert "technical_route_gate:'PASS'" in sync


def test_strategy_flow_sync_observes_existing_outputs_instead_of_reimplementing_science() -> None:
    sync = read("strategy-flow-sync.js")
    for selector in (
        "#qaSummary .qa-badge",
        "#classificationCounter",
        "#pressGate",
        "#regionalGate",
    ):
        assert selector in sync

    for page, page_script in (
        ("review-qa.html", "review-qa.js"),
        ("press-review.html", "press-review.js"),
        ("regional-routes.html", "regional-routes.js"),
    ):
        html = read(page)
        assert "strategy-flow-sync.js" in html
        assert html.index(page_script) < html.index("strategy-flow-sync.js")

    for forbidden in (
        "buildReport(",
        "evaluateReview(",
        "routeEvidence(",
        "sentinelFound(",
    ):
        assert forbidden not in sync


def test_search_keeps_maximum_coverage_mode_but_has_one_clear_visual_primary_action() -> None:
    search = read("search.html")
    styles = read("styles.css")

    assert 'id="searchBtn" class="primary"' in search
    assert 'id="globalSearchBtn" class="global-search"' in search
    assert "Cobertura máxima disponível" in search
    assert "sem teto interno do NutEV" in search
    assert 'aria-describedby="globalSearchNote"' in search
    assert 'id="globalSearchNote"' in search

    match = re.search(r"\.global-search\{([^}]*)\}", styles)
    assert match is not None
    global_rule = match.group(1)
    assert "background:#fff" in global_rule
    assert "color:var(--green2)" in global_rule
    assert "linear-gradient" not in global_rule


def test_search_kpis_are_explicitly_static_and_result_cap_remains_explained() -> None:
    product = read("product-ui.js")
    css = read("product-ui.css")

    assert "markStaticKpis" in product
    assert "Indicador informativo; não abre detalhamento." in product
    assert "static-kpi" in css
    assert "Exibindo ${returned.toLocaleString('pt-BR')} de ${unique.toLocaleString('pt-BR')} referências únicas" in product
