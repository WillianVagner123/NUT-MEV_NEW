from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_review_control_center_is_fail_closed() -> None:
    html = read("review.html")
    script = read("review-control.js")
    assert "FAIL-CLOSED" in html
    assert "Start formal screening" in html
    assert "disabled" in html
    assert "reviewer-level article UI still unavailable" in script


def test_review_control_separates_calibration_from_formal_screening() -> None:
    html = read("review.html")
    script = read("review-control.js")
    assert "Current reading workspace" in html
    assert "Formal screening readiness" in html
    assert "calibration/navigation artifacts" in script
    assert "ARTICLE_SUMMARIES.jsonl" in script
    assert "SEARCH_STATE.json" in script


def test_review_control_does_not_create_screening_decisions() -> None:
    html = read("review.html").lower()
    script = read("review-control.js").lower()
    assert "screeningdecision" in html
    assert "fetch('/api" not in script
    assert "method:'post'" not in script
    assert "method: 'post'" not in script
    assert "automatic inclusion" in html
    assert "proibida" in html


def test_dashboard_exposes_review_control() -> None:
    assert 'href="/review.html"' in read("index.html")
