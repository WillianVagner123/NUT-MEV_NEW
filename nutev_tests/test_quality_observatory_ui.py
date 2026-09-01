import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_quality_observatory_is_system_quality_not_evidence_quality() -> None:
    html = read(WEB / "quality.html")
    js = read(WEB / "quality.js")

    assert "Quality Observatory" in html
    assert "SYSTEM QUALITY · NOT EVIDENCE QUALITY" in html
    assert "Não mede qualidade metodológica, RoB ou certeza da evidência." in html
    assert "não ausência de literatura" in html
    assert "não é screening" in html
    assert "não é exclusão" in html
    assert "method:'POST'" not in js.replace(" ", "")
    assert 'method:"POST"' not in js.replace(" ", "")


def test_press_status_is_not_pass_by_substring() -> None:
    dashboard = read(WEB / "dashboard.js")
    quality = read(WEB / "quality.js")

    assert "function pressPassed(formal)" in dashboard
    assert "toUpperCase()==='PASS'" in dashboard
    assert ".includes('PASS')" not in dashboard
    assert '.includes("PASS")' not in dashboard
    assert "const pressPass=String(formal.press_status||'').trim().toUpperCase()==='PASS'" in quality
    assert "NOT_YET_RECORDED_AS_PASS" not in dashboard


def test_quality_observatory_uses_runtime_safe_surfaces_without_production_totals() -> None:
    js = read(WEB / "quality.js")

    for source in (
        "/api/health",
        "/api/articles/status",
        "/api/radar",
        "/agent-context/article1/SEARCH_STATE.json",
        "/agent-context/article1/CONTEXT_MANIFEST.json",
        "/agent-context/article1/ARTICLE_SUMMARIES.jsonl",
        "/build-info.json",
    ):
        assert source in js
    assert "buildScientificSnapshot" in js
    assert "33067" not in js
    assert "33839" not in js
    assert "reference_rank" not in js
    assert "reference_score" not in js


def test_scientific_workspace_death_test_executes_and_passes() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "audit_scientific_workspace_v2.py"), "--compact"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mode"] == "NUTEV_SCIENTIFIC_WORKSPACE_V2_DEATH_TEST"
    assert payload["status"] == "PASS"
    assert payload["errors"] == []
    assert payload["read_only"] is True
