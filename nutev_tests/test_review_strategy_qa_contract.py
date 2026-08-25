from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_review_qa_profile_is_versioned_and_deterministic() -> None:
    payload = json.loads((WEB / "review-qa-profiles.json").read_text(encoding="utf-8"))
    profiles = payload["profiles"]
    assert profiles
    profile = profiles[0]
    assert profile["strategy_id"] == "C-STRUCT-PUBMED"
    assert profile["strategy_version"] == "v0.5.1"
    assert profile["run_class"] == "PILOT"
    assert profile["sampling_order"] == "publication_date_desc"
    assert profile["sample_size"] == 10
    assert profile["baseline"] == {"strategy_version": "v0.5", "count": 1526}
    assert [branch["id"] for branch in profile["branches"]] == [
        "F4_F7",
        "F5A",
        "F5B",
        "F6",
        "F3",
    ]
    assert all("2026/08/25" in branch["query"] for branch in profile["branches"])
    assert all("Date - Publication" in branch["query"] for branch in profile["branches"])


def test_review_qa_keeps_scientific_decision_human() -> None:
    script = (WEB / "review-qa.js").read_text(encoding="utf-8")
    assert "scientific_decision:'PENDING_HUMAN_REVIEW'" in script
    assert "publication date desc" in script
    assert "membership.get(recordKey(record))===1" in script
    assert "per_provider:0,max_results:0" in script
    assert "AVANÇAR" not in script
    assert "BLOQUEAR" not in script


def test_review_qa_is_exposed_in_web_navigation() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    page = (WEB / "review-qa.html").read_text(encoding="utf-8")
    assert 'href="/review-qa.html"' in index
    assert 'id="runQaBtn"' in page
    assert 'src="./review-qa.js"' in page
