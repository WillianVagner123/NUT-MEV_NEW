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
        "evidence.html",
        "evidence-map.html",
        "radar.html",
        "ask.html",
        "review-qa.html",
        "press-review.html",
        "regional-routes.html",
        "advanced.html",
        "scientific-dashboard.html",
    ):
        assert "product-ui.js" in read(WEB / name), name
    assert 'src="/product-ui.js"' in read(VALIDATION / "index.html")


def test_canonical_navigation_is_search_classification_first() -> None:
    script = read(WEB / "product-ui.js")
    nav = script.split("const NAV_GROUPS=", 1)[1].split("const GLOSSARY=", 1)[0]
    for label in ("Início", "Buscar artigos", "Biblioteca", "Minhas buscas", "Laboratório avançado"):
        assert label in nav
    for hibernated in ("Mapa de evidências", "Radar", "Perguntar ao corpus", "PRESS", "Review Control", "Review Routes", "Validação científica", "QA"):
        assert hibernated not in nav
    assert "normalizeNavigation" in script
    assert 'aria-current="page"' in script
    assert "AI Context" not in nav


def test_search_and_home_present_search_classification_as_primary_product() -> None:
    home = read(WEB / "index.html")
    search = read(WEB / "search.html")
    advanced = read(WEB / "advanced.html")
    assert "Motor de busca científica" in home
    assert "Classificação explicável" in home
    assert "Buscar artigos" in search
    assert "Busca avançada" in search
    assert "Modo revisão científica" not in search
    assert "Workflow tipo Rayyan / revisão sistemática" in advanced
    assert "hibernado" in advanced

def test_glossary_explains_search_terms_without_leaking_hibernated_workflows() -> None:
    script = read(WEB / "product-ui.js")
    css = read(WEB / "product-ui.css")
    glossary = script.split("const GLOSSARY=", 1)[1].split("const STRATEGY_FLOW_STORAGE_KEY", 1)[0]
    for term in ("Busca progressiva", "Provider", "Deduplicação", "Ranking", "Proveniência"):
        assert term in glossary
    for hidden in ("PRESS", "PRISMA", "EvidenceClaim", "EvidenceSet", "Freeze"):
        assert hidden not in glossary
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
