from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"
PRESS_RECORD = REPO_ROOT / "config" / "nutev" / "article1_press_review_v1.json"


def test_press_profile_tracks_current_search_master_and_downstream_gate() -> None:
    payload = json.loads((WEB_ROOT / "press-review-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    assert profile["gate_id"] == "PRESS"
    assert profile["downstream_gate_id"] == "GF-10"
    assert profile["source_search_master"] == "config/nutev/article1_search_master_v1.json"
    assert profile["source_query_draft"] == "config/nutev/article1_query_draft_v1.json"
    assert profile["source_press_record"] == "config/nutev/article1_press_review_v1.json"
    assert profile["gate_status_before_review"] == "NOT_YET_RECORDED_AS_PASS"
    guardrail = profile["freeze_guardrail"].lower()
    assert "ainda não autoriza" in guardrail
    assert "gf-10" in guardrail
    assert "freeze" in guardrail
    assert "prisma" in guardrail


def test_press_profile_exposes_current_routes_without_fabricating_provider_queries() -> None:
    payload = json.loads((WEB_ROOT / "press-review-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    strategies = {item["strategy_id"]: item for item in profile["strategies"]}
    assert set(strategies) == {
        "B-NORM",
        "C1-CARE-PROCESS",
        "C2-COMPETENCY-LITERACY",
        "C3-IMPLEMENTATION",
        "C4-SOCIAL-CONTEXT",
    }
    assert strategies["C4-SOCIAL-CONTEXT"]["status"] == "PRESS_ONLY_CANDIDATE_NOT_APPROVED"
    for strategy in strategies.values():
        assert strategy["strategy_version"] == "article1-query-draft-v1"
        assert strategy["query"] is None
        assert strategy["query_note"]


def test_press_profile_has_independent_review_checklist() -> None:
    payload = json.loads((WEB_ROOT / "press-review-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    checklist_ids = [item["id"] for item in profile["checklist"]]
    assert checklist_ids == [f"P{index:02d}" for index in range(1, 11)]
    values = {item["value"] for item in profile["decision_options"]}
    assert {"ACCEPT", "ACCEPT_MINOR", "MATERIAL_REVISION", "REJECT"} <= values


def test_canonical_press_record_is_fail_closed_and_human_only() -> None:
    record = json.loads(PRESS_RECORD.read_text(encoding="utf-8"))
    assert record["status"] == "DRAFT"
    assert record["human_review_required"] is True
    assert record["reviewer"] is None
    assert record["press_decision"] is None
    assert record["downstream_gate"]["gate_id"] == "GF-10"
    assert record["downstream_gate"]["authorized"] is False
    assert len(record["delta_tests"]) == 5
    assert all(item["status"] == "PENDING" for item in record["delta_tests"])
    assert record["c4_social_context"]["decision"] == "PENDING_HUMAN_DECISION"
    assert record["guardrails"]["no_automatic_press_pass"] is True
    assert record["guardrails"]["no_automatic_gf10_authorization"] is True


def test_press_ui_never_authorizes_freeze_or_gf10() -> None:
    script = (WEB_ROOT / "press-review.js").read_text(encoding="utf-8")
    html = (WEB_ROOT / "press-review.html").read_text(encoding="utf-8")
    assert "freeze_authorized:false" in script
    assert "gf10_authorized:false" in script
    assert "REVISION_REQUIRED" in script
    assert "PRESS_REVIEW_COMPLETE_PENDING_CANONICAL_REGISTRATION" in script
    assert "RETURN_TO_PILOT" not in script
    assert "GF-03" not in script
    assert "GF-03" not in html
    assert "B-NORM-PUBMED" not in html
    assert "C-STRUCT-PUBMED" not in html
    assert "independentAttestation" in html
    assert "PRESS Workspace" in html
    assert "GF-10" in html


def test_main_navigation_exposes_press_module() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    review_qa = (WEB_ROOT / "review-qa.html").read_text(encoding="utf-8")
    for source in (index, review_qa):
        assert 'href="/press-review.html"' in source
        assert ">PRESS<" in source
