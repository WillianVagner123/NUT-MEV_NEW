from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_publication_uses_existing_local_only_release_coordinator() -> None:
    server = read("server.py")
    release_service = read("governed_synthesis_release.py")
    script = read("synthesis-publication.js")

    assert 'path == "/api/synthesis/releases"' in server
    assert 'path == "/api/synthesis/releases/prepare"' in server
    assert "_require_loopback" in server
    assert 'PUBLICATION_OPERATION = "PREPARE_PUBLICATION_MANIFEST"' in release_service
    assert "prepare_publication_manifest" in release_service
    assert "operation:PUBLICATION_OPERATION" in script
    assert "postJson('/api/synthesis/releases/prepare'" in script
    assert "/api/synthesis/publications" not in script


def test_publication_ui_never_auto_prepares_or_promotes_claims() -> None:
    html = read("synthesis-publication.html")
    script = read("synthesis-publication.js")

    assert "PUBLICATION PREPARATION · NOT CLAIM ACCEPTANCE" in html
    assert "Publication Statement Candidate != accepted EvidenceClaim" in html
    assert "no canonical scientific synthesis is created" in html
    assert "preparePublication').addEventListener('click',prepare)" in script
    load_body = script.split("async function load()", 1)[1]
    assert "prepare();" not in load_body
    assert "accepted_evidence_claim!==false" in script
    assert "publication_status!=='CANDIDATE_ONLY'" in script


def test_publication_service_revalidates_release_and_preserves_boundaries() -> None:
    service = read("governed_publication_manifest.py")

    assert 'MANIFEST_TYPE = "NUTEV_GOVERNED_PUBLICATION_MANIFEST_V1"' in service
    assert 'STATEMENT_TYPE = "NUTEV_PUBLICATION_STATEMENT_CANDIDATE_V1"' in service
    assert "build_governed_release(" in service
    assert '"canonical": False' in service
    assert '"publication_status": "CANDIDATE_ONLY"' in service
    assert '"accepted_evidence_claim": False' in service
    assert '"machine_inferred_scientific_claim": False' in service
    assert '"requires_human_author_editing": True' in service
    assert '"accepted_evidence_claims_created": False' in service
    assert '"canonical_scientific_synthesis_created": False' in service
    assert '"risk_of_bias_assessed": False' in service
    assert '"certainty_assessed": False' in service
    assert '"meta_analysis_performed": False' in service
    assert '"prisma_event_emitted": False' in service
    assert '"clinical_recommendation_created": False' in service
    assert '"external_llm_generated_scientific_claims": False' in service


def test_publication_citation_bundle_is_source_linked() -> None:
    service = read("governed_publication_manifest.py")

    for token in (
        '"citation_id"',
        '"decision_id"',
        '"document_id"',
        '"title"',
        '"identifiers"',
        '"bundle_id"',
        '"source_sentence_sha256"',
        '"result_text"',
    ):
        assert token in service


def test_publication_ledger_is_metadata_only() -> None:
    service = read("governed_publication_manifest.py")
    status_body = service.split("def publication_status", 1)[1]

    assert '"records": records' in status_body
    assert '"citation_bundle"' not in status_body
    assert '"statement_candidates"' not in status_body
    assert '"reviewed_decisions"' not in status_body


def test_publication_navigation_is_connected() -> None:
    dashboard = read("index.html")
    release = read("synthesis-release.html")
    publication = read("synthesis-publication.html")

    assert "/synthesis-publication.html" in dashboard
    assert "/synthesis-publication.html" in release
    assert "/synthesis-release.html" in publication
