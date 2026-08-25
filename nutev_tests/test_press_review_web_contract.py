from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"


def test_press_profile_preserves_canonical_strategy_versions_and_gate() -> None:
    payload = json.loads((WEB_ROOT / "press-review-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    assert profile["gate_id"] == "GF-03"
    strategies = {
        (item["strategy_id"], item["strategy_version"]): item
        for item in profile["strategies"]
    }
    assert ("B-NORM-PUBMED", "v0.7") in strategies
    assert ("C-STRUCT-PUBMED", "v0.5.1") in strategies
    assert strategies[("B-NORM-PUBMED", "v0.7")]["pilot_evidence"]["count"] == 6681
    assert strategies[("C-STRUCT-PUBMED", "v0.5.1")]["pilot_evidence"]["count"] == 1600
    assert "não autoriza freeze" in profile["freeze_guardrail"].lower()
    assert "PILOT" in profile["freeze_guardrail"]


def test_press_profile_has_independent_review_checklist() -> None:
    payload = json.loads((WEB_ROOT / "press-review-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    checklist_ids = [item["id"] for item in profile["checklist"]]
    assert checklist_ids == [f"P{index:02d}" for index in range(1, 15)]
    values = {item["value"] for item in profile["decision_options"]}
    assert {"ACCEPT", "ACCEPT_MINOR", "MATERIAL_REVISION", "REJECT"} <= values


def test_press_ui_never_authorizes_freeze_and_returns_material_change_to_pilot() -> None:
    script = (WEB_ROOT / "press-review.js").read_text(encoding="utf-8")
    html = (WEB_ROOT / "press-review.html").read_text(encoding="utf-8")
    assert "freeze_authorized:false" in script
    assert "RETURN_TO_PILOT" in script
    assert "MATERIAL_REVISION" in script
    assert "independentAttestation" in html
    assert "PRESS da estratégia" in html


def test_main_navigation_exposes_press_module() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    review_qa = (WEB_ROOT / "review-qa.html").read_text(encoding="utf-8")
    for source in (index, review_qa):
        assert 'href="/press-review.html"' in source
        assert "PRESS da estratégia" in source
