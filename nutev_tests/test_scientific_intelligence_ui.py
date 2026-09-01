from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_scientific_intelligence_is_rank_blind_and_read_only() -> None:
    html = read(WEB / "intelligence.html")
    js = read(WEB / "intelligence.js")

    assert "Scientific Intelligence" in html
    assert "SYNTHESIS SUPPORT · NOT AUTOMATED CONCLUSION" in html
    assert "Recorrência não significa consenso" in html
    assert "não evidence gaps" in html
    assert "/agent-context/article1/ARTICLE_SUMMARIES.jsonl" in js
    assert "/agent-context/article1/SEARCH_STATE.json" in js
    assert "fetchJson(`/api/articles/${encodeURIComponent(documentId)}`)" in js
    assert "FINDING_BATCH_LIMIT=24" in js
    assert "DETAIL_CONCURRENCY=4" in js
    assert "method:'POST'" not in js.replace(" ", "")
    assert 'method:"POST"' not in js.replace(" ", "")
    assert "reference_rank" not in js
    assert "reference_score" not in js
    assert "machine_relevance_score" not in js
    assert "machine_relevance_band" not in js
    assert "api.openai.com" not in js
    assert "api.anthropic.com" not in js


def test_scientific_intelligence_keeps_human_review_boundary() -> None:
    html = read(WEB / "intelligence.html")
    js = read(WEB / "intelligence.js")

    assert "não classifica automaticamente agreement, contradiction ou certainty" in html
    assert "recurrence_is_not_consensus:true" in js
    assert "convergence_divergence_requires_human_review:true" in js
    assert "sparse_mapping_is_not_evidence_gap:true" in js
    assert "result_bundles_are_not_accepted_evidence_claims:true" in js
    assert "not_prisma:true" in js
    assert "Recurring outcome labels" in html
    assert "Corpus coverage signals" in html


def test_scientific_intelligence_export_is_bounded_snapshot_of_current_view() -> None:
    js = read(WEB / "intelligence.js")

    assert "NUTEV_SCIENTIFIC_INTELLIGENCE_VIEW_V1" in js
    assert "loaded_finding_candidates" in js
    assert "structural_domain_synthesis" in js
    assert "new Blob" in js
    assert "window.print()" in js
    assert "full_text_in_export:false" in js


def test_dashboard_links_scientific_intelligence() -> None:
    html = read(WEB / "index.html")

    assert 'href="/intelligence.html"' in html
    assert "Scientific Intelligence" in html
