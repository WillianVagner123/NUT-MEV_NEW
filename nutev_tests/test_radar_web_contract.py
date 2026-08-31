from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_radar_is_first_class_in_main_navigation() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    radar = (WEB / "radar.html").read_text(encoding="utf-8")
    assert 'href="/radar.html"' in index
    assert "Evidence Radar" in index
    assert "Evidence Radar" in radar
    assert 'id="summaryCards"' in radar
    assert 'id="priorityBoard"' in radar
    assert 'id="providerBoard"' in radar
    assert 'id="topicCards"' in radar
    assert 'id="watchSection"' in radar
    assert 'id="topicDialog"' in radar


def test_radar_api_is_read_only_and_fail_closed() -> None:
    server = (WEB / "server.py").read_text(encoding="utf-8")
    data = (WEB / "radar_data.py").read_text(encoding="utf-8")
    assert 'if path == "/api/radar"' in server
    assert '"radar_dashboard": True' in server
    assert "RadarDataError" in server
    assert "SHA-256 mismatch" in data
    assert '"status": "not_ready"' in data
    assert '"metrics_are_verified_from_manifests": True' in data
    assert "document_counts_are_not_evidence_strength" in data
    assert "prisma_not_implied" in data
    assert 'path == "/api/radar"' not in server.split("def do_POST", 1)[1]


def test_radar_frontend_does_not_fabricate_demo_metrics() -> None:
    app = (WEB / "radar.js").read_text(encoding="utf-8")
    css = (WEB / "radar.css").read_text(encoding="utf-8")
    assert "fetch('/api/radar'" in app
    assert "Radar ainda sem snapshot" in app
    assert "O painel não usa números demonstrativos" in app
    assert "Watch desatualizado" in app
    assert "zero verificado" in app
    assert ".topic-card" in css
    assert ".priority-board" in css
    assert ".topic-dialog" in css
