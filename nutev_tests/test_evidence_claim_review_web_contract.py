from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_claim_review_reuses_existing_local_only_coordinator() -> None:
    server = read("server.py")
    release = read("governed_synthesis_release.py")
    script = read("evidence-claims.js")

    assert 'path == "/api/synthesis/releases"' in server
    assert 'path == "/api/synthesis/releases/prepare"' in server
    assert "_require_loopback" in server
    assert 'CLAIM_STAGE_OPERATION = "STAGE_EVIDENCE_CLAIM_REVIEW"' in release
    assert 'CLAIM_DECIDE_OPERATION = "DECIDE_EVIDENCE_CLAIM"' in release
    assert "stage_claim_candidates" in release
    assert "decide_claim_candidate" in release
    assert "operation:STAGE_OPERATION" in script
    assert "operation:DECIDE_OPERATION" in script
    assert "fetch('/api/synthesis/releases/prepare'" in script


def test_claim_candidates_come_from_atomic_citations_not_pairwise_statements() -> None:
    service = read("evidence_claim_review.py")
    html = read("evidence-claims.html")

    assert 'candidate_scope": "ATOMIC_SOURCE_SNAPSHOT_FOR_HUMAN_CLAIM_REVIEW"' in service
    assert '"directly_promotable_to_evidence_claim": False' in service
    assert '"pairwise_statement_directly_promotable": False' in service
    assert "EvidenceClaim belongs to one EvidenceRecord" in service
    assert "PAIRWISE SYNTHESIS IS NOT AN ATOMIC CLAIM" in html
    assert "não promove os pairwise statement candidates" in html


def test_accept_requires_real_evidence_record_and_explicit_human_confirmations() -> None:
    service = read("evidence_claim_review.py")
    script = read("evidence-claims.js")

    assert 'output_root / "scientific" / "evidence_records.jsonl"' in service
    assert "EvidenceRecord correspondente não foi localizado" in service
    assert "source_attribution_confirmed" in service
    assert "scientific_boundary_confirmed" in service
    assert "source_attribution_confirmed:field(card,'source_attribution_confirmed')" in script
    assert "scientific_boundary_confirmed:field(card,'scientific_boundary_confirmed')" in script
    assert "ACCEPT bloqueado: EvidenceRecord não resolvido" in script


def test_claim_statement_is_not_prefilled_from_result_text() -> None:
    script = read("evidence-claims.js")

    assert "Human claim statement — starts empty" in script
    assert "O result text acima não é copiado automaticamente" in script
    assert "data-field=\"claim_statement\"" in script
    assert "value=\"${esc(candidate.result_text" not in script
    assert "claim_statement:candidate.result_text" not in script


def test_canonical_claim_preserves_source_level_boundary() -> None:
    service = read("evidence_claim_review.py")

    assert 'CANONICAL_CLAIM_RECORD_TYPE = "NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1"' in service
    assert '"canonical": True' in service
    assert '"claim_semantics": "SOURCE_REPORTED_PROPOSITION"' in service
    assert '"source_evidence_record_verified": True' in service
    assert '"claim_acceptance_is_not_screening_inclusion": True' in service
    assert '"screening_eligibility_verified": False' in service
    assert '"claim_evaluation_created": False' in service
    assert '"risk_of_bias_assessed": False' in service
    assert '"certainty_assessed": False' in service
    assert '"evidence_set_created": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"meta_analysis_performed": False' in service
    assert '"prisma_event_emitted": False' in service
    assert '"pairwise_synthesis_statement_promoted": False' in service
    assert '"identity_cryptographically_authenticated": False' in service


def test_claim_ui_has_no_external_llm_or_auto_accept_path() -> None:
    script = read("evidence-claims.js")
    lowered = script.casefold()

    for token in ("openai", "anthropic", "claude", "gemini", "chatgpt"):
        assert token not in lowered
    load_body = script.split("async function load()", 1)[1]
    assert "decide(" not in load_body
    stage_body = script.split("async function stage()", 1)[1].split("function field", 1)[0]
    assert "DECIDE_OPERATION" not in stage_body
    assert "decision:'ACCEPT'" not in stage_body


def test_claim_navigation_is_connected() -> None:
    dashboard = read("index.html")
    publication = read("synthesis-publication.html")
    claims = read("evidence-claims.html")

    assert "/evidence-claims.html" in dashboard
    assert "/evidence-claims.html" in publication
    assert "/synthesis-publication.html" in claims
