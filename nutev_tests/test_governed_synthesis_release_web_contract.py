from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_release_endpoints_are_local_only_and_server_revalidated() -> None:
    server = read("server.py")

    assert 'path == "/api/synthesis/releases"' in server
    assert 'path == "/api/synthesis/releases/prepare"' in server
    assert "release_status" in server
    assert "prepare_governed_release" in server
    assert "_require_loopback" in server
    assert '"governed_synthesis_release": True' in server


def test_release_ui_only_uses_approved_human_governance_sources() -> None:
    html = read("synthesis-release.html")
    script = read("synthesis-release.js")

    assert "GOVERNED DISSEMINATION · NOT A NEW SCIENTIFIC INFERENCE" in html
    assert "APPROVED_FOR_GOVERNED_USE" in html
    assert "canonical:false" in html
    assert "Approved governance source ≠ scientific validity" in html
    assert "entry.status===APPROVED" in script
    assert "entry.governance_decision?.action==='APPROVE'" in script
    assert "entry.governance_decision?.human_entered===true" in script
    assert "source_revalidated_at_decision===true" in script


def test_release_ui_never_auto_prepares_or_claims_scientific_validation() -> None:
    script = read("synthesis-release.js")

    assert "postJson('/api/synthesis/releases/prepare'" in script
    assert "prepareRelease').addEventListener('click',prepare)" in script
    assert "governed_release_is_not_scientific_validation" in script
    assert "Preparação ≠ scientific validation" in script
    load_body = script.split("async function load()", 1)[1]
    assert "prepare();" not in load_body


def test_release_package_contract_preserves_scientific_boundaries() -> None:
    service = read("governed_synthesis_release.py")

    assert 'RELEASE_TYPE = "NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1"' in service
    assert '"canonical": False' in service
    assert '"release_scope": "GOVERNED_DISSEMINATION_PACKAGE"' in service
    assert '"canonical_scientific_synthesis_created": False' in service
    assert '"accepted_evidence_claims_created": False' in service
    assert '"risk_of_bias_assessed": False' in service
    assert '"certainty_assessed": False' in service
    assert '"meta_analysis_performed": False' in service
    assert '"prisma_event_emitted": False' in service
    assert '"formal_search_state_changed": False' in service
    assert '"identity_cryptographically_authenticated": False' in service
    assert "validate_brief(brief, output_root=output_root)" in service


def test_release_ledger_is_metadata_only() -> None:
    service = read("governed_synthesis_release.py")

    status_body = service.split("def release_status", 1)[1]
    assert '"records": records' in status_body
    assert '"reviewed_decisions"' not in status_body
    assert '"package":' not in status_body
