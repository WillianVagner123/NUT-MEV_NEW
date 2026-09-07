from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_public_search_uses_portuguese_first_labels() -> None:
    html = (WEB / "search.html").read_text(encoding="utf-8")

    assert "Busca NutEV" in html
    assert "verificando motor" in html
    assert "usuários avançados" in html
    assert "consulta por fonte" in html
    assert "NutEV Search" not in html
    assert "usuários experts" not in html
    assert "verificando engine" not in html


def test_public_library_and_dossier_use_portuguese_first_labels() -> None:
    html = (WEB / "articles.html").read_text(encoding="utf-8")
    dossier = (WEB / "article-dossier.js").read_text(encoding="utf-8")

    assert "O dossiê do artigo abre aqui" in html
    assert "Limites de interpretação científica" in html
    assert "Scientific Dossier" not in html
    assert "Scientific interpretation boundary" not in html

    for label in (
        "Visão geral",
        "Métodos",
        "Evidência",
        "Domínios",
        "Proveniência",
        "Revisão humana",
        "Dossiê do artigo",
        "Estado da revisão humana",
    ):
        assert label in dossier

    for legacy_label in (
        "Overview",
        "Methods",
        "Evidence",
        "Domains",
        "Provenance",
        "Human Review",
        "Article dossier",
        "Human review status",
        "Open Review Control Center",
    ):
        assert legacy_label not in dossier


def test_brand_name_and_technical_identifiers_remain_stable() -> None:
    html = (WEB / "search.html").read_text(encoding="utf-8")
    dossier = (WEB / "article-dossier.js").read_text(encoding="utf-8")

    assert "Evidence Engine" in html
    assert "EvidenceClaims" in dossier
