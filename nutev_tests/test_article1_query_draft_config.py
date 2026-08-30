from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"


def _load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_article1_query_draft_remains_prefreeze_and_non_formal() -> None:
    data = _load()
    assert data["draft_type"] == "NUTEV_ARTICLE1_QUERY_DRAFT_FOR_PRESS"
    assert data["status"] == "DRAFT_FOR_PRESS"
    assert data["formal_gate"]["gate_id"] == "GF-10"
    assert data["formal_gate"]["authorized"] is False
    assert data["press_plan"]["required_before_freeze"] is True
    assert data["guardrails"]["no_eligibility_decision"] is True
    assert data["guardrails"]["no_prisma_event"] is True
    assert data["guardrails"]["external_llm_calls"] == 0


def test_b_norm_does_not_promote_context_or_disease_noise() -> None:
    data = _load()
    bnorm = data["vocabulary_decisions"]["B-NORM"]
    assert bnorm["decision"] == "KEEP_BASELINE_ARCHITECTURE"
    promoted = {term.casefold() for term in bnorm["keep"]}
    for forbidden in (
        "lifestyle medicine",
        "type diabetes",
        "liver disease",
        "environmental sustainability",
        "overweight and obese",
    ):
        assert forbidden not in promoted


def test_c_struct_is_split_and_social_context_is_press_only() -> None:
    data = _load()
    cstruct = data["routes"]["C-STRUCT"]
    assert cstruct["aggregation"] == "UNION_AND_DEDUPLICATE_SUBROUTES"
    assert set(cstruct["subroutes"]) == {
        "C1-CARE-PROCESS",
        "C2-COMPETENCY-LITERACY",
        "C3-IMPLEMENTATION",
        "C4-SOCIAL-CONTEXT",
    }
    assert (
        cstruct["subroutes"]["C4-SOCIAL-CONTEXT"]["status"]
        == "PRESS_ONLY_CANDIDATE_NOT_APPROVED"
    )


def test_discovery_noise_is_not_promoted_into_c_struct_terms() -> None:
    data = _load()
    cstruct = data["routes"]["C-STRUCT"]
    searchable: set[str] = set()
    for name, route in cstruct["subroutes"].items():
        if name == "C4-SOCIAL-CONTEXT":
            continue
        searchable.update(str(value).casefold() for value in route.get("anchor", []))
        searchable.update(str(value).casefold() for value in route.get("terms", []))

    for forbidden in (
        "dietary patterns",
        "systematic review",
        "randomized controlled",
        "type diabetes",
        "metabolic syndrome",
        "mediterranean diet",
        "physical activity",
    ):
        assert forbidden not in searchable
