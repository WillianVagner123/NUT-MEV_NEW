from __future__ import annotations

import json
from pathlib import Path


def test_article1_search_master_keeps_formal_gate_closed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    master_path = repo_root / "config/nutev/article1_search_master_v1.json"
    master = json.loads(master_path.read_text(encoding="utf-8"))

    assert master["master_type"] == "NUTEV_ARTICLE1_SEARCH_MASTER"
    assert master["status"] == "DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE"
    assert master["canonical_human_file"] == "ARTICLE1_SEARCH_MASTER.md"
    assert master["agent_entrypoint"] == "AI_CONTEXT.md"

    formal = master["formal_search"]
    assert formal["press_status"] != "PASS"
    assert formal["gf10_authorized"] is False
    assert formal["query_freeze_complete"] is False
    assert formal["formal_provider_search_executed"] is False
    assert formal["prisma_search_event_emitted"] is False

    assert (repo_root / "ARTICLE1_SEARCH_MASTER.md").is_file()
    assert (repo_root / "AI_CONTEXT.md").is_file()
    assert (repo_root / "CLAUDE.md").is_file()
    assert (repo_root / "docs/ARTICLE1_AGENT_CONTEXT.md").is_file()

    c4 = master["search_architecture"]["C-STRUCT"]["subroutes"]["C4-SOCIAL-CONTEXT"]
    assert c4 == "PRESS_ONLY_CANDIDATE_NOT_APPROVED"

    guardrails = master["guardrails"]
    assert guardrails["discovery_is_not_formal_prisma_search"] is True
    assert guardrails["structural_quarantine_is_not_scientific_exclusion"] is True
    assert guardrails["review_route_is_not_screening_decision"] is True
    assert guardrails["formal_search_must_remain_false_until_freeze"] is True
