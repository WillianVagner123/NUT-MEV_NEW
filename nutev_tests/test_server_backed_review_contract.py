from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_reviewer_token_stays_in_url_fragment_and_moves_to_authorization_header() -> None:
    reviewer = (VALIDATION_ROOT / "server-review.js").read_text(encoding="utf-8")
    launcher = (VALIDATION_ROOT / "launcher.js").read_text(encoding="utf-8")
    html = (VALIDATION_ROOT / "review.html").read_text(encoding="utf-8")
    assert "#token=" in launcher
    assert "location.hash" in reviewer
    assert "sessionStorage" in reviewer
    assert "history.replaceState" in reviewer
    assert "Authorization: `Bearer ${state.token}`" in reviewer
    assert "?token=" not in launcher
    assert "?token=" not in reviewer
    assert 'content="no-referrer"' in html


def test_coordinator_api_is_local_only_and_does_not_expose_decisions() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    backend = (WEB_ROOT / "validation_server.py").read_text(encoding="utf-8")
    assert 'path == "/api/validation/round"' in server
    assert 'path == "/api/validation/round/prepare"' in server
    assert "_require_loopback" in server
    assert "ipaddress.ip_address" in server
    assert '"relevance_grade"' not in backend.split("def round_status", 1)[1].split("def _reviewer_by_token", 1)[0]
    assert '"reason"' not in backend.split("def round_status", 1)[1].split("def _reviewer_by_token", 1)[0]


def test_private_reviewer_has_save_submit_and_lock_contract() -> None:
    server = (WEB_ROOT / "server.py").read_text(encoding="utf-8")
    backend = (WEB_ROOT / "validation_server.py").read_text(encoding="utf-8")
    reviewer = (VALIDATION_ROOT / "server-review.js").read_text(encoding="utf-8")
    assert '"/api/validation/reviewer/save"' in server
    assert '"/api/validation/reviewer/submit"' in server
    assert "assessment_submitted_locked" in backend
    assert "ready_for_adjudication" in backend
    assert "A avaliação já foi enviada e está travada" in backend
    assert "/api/validation/reviewer/save" in reviewer
    assert "/api/validation/reviewer/submit" in reviewer
    assert "Enviar avaliação" in reviewer


def test_server_side_validation_state_is_private_and_gitignored_by_location() -> None:
    backend = (WEB_ROOT / "validation_server.py").read_text(encoding="utf-8")
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert 'Path("project_output_reference") / "16_validation_server"' in backend
    assert "project_output*/" in gitignore
    assert "sqlite3" in backend
