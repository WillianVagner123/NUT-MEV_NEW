from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_corpus_wires_scientific_dossier_layer() -> None:
    html = read("articles.html")
    assert 'href="./article-dossier.css"' in html
    assert 'src="./article-dossier.js"' in html
    assert html.index('src="./articles.js"') < html.index('src="./article-dossier.js"')


def test_dossier_has_required_tabs_and_fail_closed_review() -> None:
    script = read("article-dossier.js")
    for label in ("Overview", "Methods", "Evidence", "Domains", "Provenance", "Human Review"):
        assert label in script
    assert "Formal" not in script or "formal" in script.lower()
    assert "Decisões formais de screening não são registradas nesta tela" in script
    assert "/review.html" in script


def test_dossier_does_not_fetch_full_text_or_write_decisions() -> None:
    script = read("article-dossier.js").lower()
    assert "fetch(" not in script
    assert "full_text" not in script
    assert "method:'post'" not in script
    assert "method: 'post'" not in script


def test_dossier_keeps_machine_artifacts_separate_from_accepted_claims() -> None:
    script = read("article-dossier.js")
    assert "Result bundles e excerpts são artefatos candidatos rastreáveis" in script
    assert "Não são EvidenceClaims aceitos" in script
    assert "Ausência de campo não é preenchida por inferência" in script
