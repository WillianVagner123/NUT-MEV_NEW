from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_synthesis_governance_endpoints_are_local_only() -> None:
    server = read("server.py")

    assert 'path == "/api/synthesis/governance"' in server
    assert '"/api/synthesis/governance/stage"' in server
    assert '"/api/synthesis/governance/decide"' in server
    assert "_require_loopback" in server
    assert "MAX_GOVERNANCE_BODY_BYTES = 2 * 1024 * 1024" in server
    assert "self._read_json(max_bytes=MAX_GOVERNANCE_BODY_BYTES)" in server
    assert '"synthesis_governance_registry": True' in server


def test_governance_ui_distinguishes_stage_approval_and_science() -> None:
    html = read("synthesis-governance.html")
    script = read("synthesis-governance.js")

    assert "LOCAL-ONLY WRITE SURFACE · GOVERNANCE ≠ SCIENTIFIC VALIDATION" in html
    assert "Importar um Human Synthesis Brief cria somente um registro `STAGED`" in html
    assert "STAGED não significa aprovado" in html
    assert "APPROVED_FOR_GOVERNED_USE" in html
    assert "canonical scientific synthesis" in html.casefold()
    assert "Import != approval" in html
    assert "identity field != cryptographic identity authentication" in html
    assert "postJson('/api/synthesis/governance/stage'" in script
    assert "postJson('/api/synthesis/governance/decide'" in script
    assert "Importar não significa aprovar" in script


def test_governance_ui_never_auto_approves_on_import() -> None:
    script = read("synthesis-governance.js")

    stage_body = script.split("async function stage()", 1)[1].split("async function decide", 1)[0]
    assert "APPROVE" not in stage_body
    assert "decide(" not in stage_body
    assert "data-action=\"APPROVE\"" in script
    assert "data-action=\"REJECT\"" in script
    assert "rationale.length<20" in script
    assert "if(!governor)" in script


def test_registry_service_never_creates_canonical_scientific_synthesis() -> None:
    service = read("synthesis_governance.py")

    assert 'STAGED = "STAGED"' in service
    assert 'APPROVED = "APPROVED_FOR_GOVERNED_USE"' in service
    assert 'REJECTED = "REJECTED_BY_GOVERNANCE"' in service
    assert '"canonical_registry_record": True' in service
    assert '"canonical_scientific_synthesis_created": False' in service
    assert '"reviewer_identity_cryptographically_authenticated": False' in service
    assert '"identity_cryptographically_authenticated": False' in service
    assert '"source_revalidated_at_decision": True' in service
    assert "validate_brief(artifact, output_root=output_root)" in service


def test_registry_listing_does_not_send_full_brief_bodies() -> None:
    service = read("synthesis_governance.py")

    status_function = service.split("def registry_status", 1)[1].split("def stage_brief", 1)[0]
    assert '"entries": entries' in status_function
    assert "_artifact_path" not in status_function
    assert '"reviewed_decisions"' not in status_function
    assert '"artifact"' not in status_function


def test_dashboard_links_governance_registry_and_keeps_boundary_explicit() -> None:
    dashboard = read("index.html")

    assert 'href="/synthesis-governance.html"' in dashboard
    assert "Synthesis Registry" in dashboard
    assert "Governance Registry" in dashboard
    assert "governance approval ≠ scientific validation" in dashboard
