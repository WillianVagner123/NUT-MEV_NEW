from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_human_synthesis_review_is_explicitly_human_and_noncanonical() -> None:
    html = read("synthesis-review.html")
    js = read("synthesis-review.js")

    assert "Human Synthesis Review" in html
    assert "HUMAN JUDGMENT · LOCAL DRAFT · NOT CANONICAL" in html
    assert "Nenhuma decisão aqui altera screening, PRESS, GF-10, RoB, certainty ou PRISMA." in html
    assert "NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1" in js
    assert "canonical:false" in js
    assert "human_entered:true" in js
    assert "automatic_convergence_divergence:false" in js
    assert "accepted_evidence_claims_created:false" in js
    assert "screening_decisions_created:false" in js
    assert "risk_of_bias_assessed:false" in js
    assert "certainty_assessed:false" in js
    assert "prisma_event_emitted:false" in js
    assert "formal_search_state_changed:false" in js


def test_human_synthesis_review_requires_reviewer_relation_and_rationale() -> None:
    html = read("synthesis-review.html")
    js = read("synthesis-review.js")

    assert 'id="reviewerName"' in html
    assert "Informe o nome do revisor antes de salvar." in js
    assert "Selecione a relação antes de salvar." in js
    assert "justificativa com pelo menos 20 caracteres" in js
    for relation in ("CONVERGENT", "DIVERGENT", "COMPLEMENTARY", "NOT_COMPARABLE", "UNCLEAR"):
        assert relation in js
    for dimension in ("population", "construct_intervention", "outcome", "timeframe"):
        assert f'data-dimension="{dimension}"' in js


def test_human_synthesis_review_uses_bounded_source_linked_details() -> None:
    js = read("synthesis-review.js")

    assert "DETAIL_BATCH_LIMIT=18" in js
    assert "DETAIL_CONCURRENCY=4" in js
    assert "/agent-context/article1/ARTICLE_SUMMARIES.jsonl" in js
    assert "/agent-context/article1/SEARCH_STATE.json" in js
    assert "fetchJson(`/api/articles/${encodeURIComponent(documentId)}`)" in js
    assert "source_sentence_sha256" in js
    assert "bundle_id" in js
    assert "full_text" not in js.casefold()


def test_human_synthesis_review_only_persists_browser_draft_and_export() -> None:
    js = read("synthesis-review.js")

    assert "localStorage.getItem" in js
    assert "localStorage.setItem" in js
    assert "localStorage.removeItem" in js
    assert "crypto.subtle.digest('SHA-256'" in js
    assert "content_sha256" in js
    assert "new Blob" in js
    assert "Export does not make the draft canonical" in js
    assert "method:'POST'" not in js.replace(" ", "")
    assert 'method:"POST"' not in js.replace(" ", "")
    assert "api.openai.com" not in js
    assert "api.anthropic.com" not in js


def test_scientific_intelligence_and_dashboard_link_human_review() -> None:
    intelligence = read("intelligence.html")
    dashboard = read("index.html")

    assert 'href="/synthesis-review.html"' in intelligence
    assert "Abrir revisão humana" in intelligence
    assert 'href="/synthesis-review.html"' in dashboard
    assert "Human Synthesis Review" in dashboard
