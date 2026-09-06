from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
VALIDATION = ROOT / "apps" / "nutev-validation"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_core_product_surfaces_load_shared_product_ui() -> None:
    for name in (
        "index.html",
        "search.html",
        "articles.html",
        "radar.html",
        "review-qa.html",
        "press-review.html",
        "regional-routes.html",
    ):
        assert "product-ui.js" in read(WEB / name), name
    assert 'src="/product-ui.js"' in read(VALIDATION / "index.html")


def test_canonical_navigation_is_single_compact_contract() -> None:
    script = read(WEB / "product-ui.js")
    for label in (
        "Dashboard",
        "Buscar evidências",
        "Corpus",
        "Radar de evidências",
        "QA",
        "PRESS",
        "Rotas regionais",
        "Validação científica",
        "Minhas buscas",
    ):
        assert label in script
    assert "normalizeNavigation" in script
    assert "aria-current=\"page\"" in script
    assert "AI Context" not in script


def test_glossary_explains_scientific_terms_without_rewriting_raw_code() -> None:
    script = read(WEB / "product-ui.js")
    css = read(WEB / "product-ui.css")
    for term in (
        "ResultBundle",
        "EvidenceClaim",
        "EvidenceSet",
        "PRESS",
        "Pré-freeze",
        "Freeze",
        "PRISMA",
        "Proveniência",
    ):
        assert term in script
    assert "code,pre,script,style,textarea" in script
    assert "glossary-trigger" in css
    assert "glossary-dialog" in css


def test_strategy_pages_form_one_explicit_three_step_flow() -> None:
    qa = read(WEB / "review-qa.html")
    press = read(WEB / "press-review.html")
    regional = read(WEB / "regional-routes.html")

    for page in (qa, press, regional):
        assert 'class="strategy-flow"' in page
        assert "1 · QA" in page
        assert "2 · PRESS" in page
        assert "3 · Rotas regionais" in page

    assert 'aria-current="step"' in qa
    assert 'href="/press-review.html"' in qa
    assert 'aria-current="step"' in press
    assert 'href="/review-qa.html"' in press and 'href="/regional-routes.html"' in press
    assert 'aria-current="step"' in regional
    assert 'href="/validation/"' in regional
