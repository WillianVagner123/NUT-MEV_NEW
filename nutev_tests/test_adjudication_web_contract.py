from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_adjudication_api_is_local_only_and_explicitly_human() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    service = (WEB_ROOT / "validation_adjudication.py").read_text(encoding="utf-8")
    assert 'path == "/api/validation/adjudication"' in server
    assert '"/api/validation/adjudication/save"' in server
    assert '"/api/validation/adjudication/finalize"' in server
    assert "_require_loopback" in server
    assert "adjudicator_id" in service
    assert "conflict_adjudicated" in service
    assert "adjudication_complete" in service


def test_adjudication_ui_shows_only_conflicts_and_never_preselects_assessor_choice() -> None:
    script = (VALIDATION_ROOT / "adjudicate.js").read_text(encoding="utf-8")
    html = (VALIDATION_ROOT / "adjudicate.html").read_text(encoding="utf-8")
    assert "/api/validation/adjudication" in script
    assert "Somente conflitos são exibidos" in script
    assert "Nenhuma decisão é escolhida automaticamente" in script
    assert "Identificador do adjudicador" in script
    assert "Salvar decisão humana" in script
    assert "Encerrar adjudicação" in script
    assert "adjudicate.js" in html


def test_coordinator_opens_adjudication_only_after_locked_initial_assessments() -> None:
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    assert "ready_for_adjudication" in launcher
    assert "adjudicating" in launcher
    assert "adjudication_complete" in launcher
    assert "/validation/adjudicate.html" in launcher
    assert "Os dois envios estão travados" in launcher
