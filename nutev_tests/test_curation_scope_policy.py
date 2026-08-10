from __future__ import annotations

from nutev.export.curation import _curated_priority_signals, _is_prioritized


def test_generic_high_score_guideline_without_nutev_anchor_is_not_prioritized() -> None:
    row = {
        "title": "Clinical practice guideline for plaque psoriasis",
        "abstract": "Dermatology treatment recommendations for biologic therapy.",
        "relevance_score": 10,
        "editorial_priority_tier": "a1_proxy_high",
    }

    signals = _curated_priority_signals(row)
    assert signals["evidence_signal"] is True
    assert signals["anchor"] is False
    assert _is_prioritized(row) is False


def test_obesity_nutrition_guideline_with_anchor_is_prioritized() -> None:
    row = {
        "title": "Clinical practice guideline for nutrition care in adults with obesity",
        "relevance_score": 8,
        "editorial_priority_tier": "standard",
    }

    signals = _curated_priority_signals(row)
    assert signals["anchor"] is True
    assert signals["evidence_signal"] is True
    assert _is_prioritized(row) is True


def test_dashboard_does_not_match_dash_anchor() -> None:
    row = {
        "title": "Dashboard implementation evaluation for hospital operations",
        "relevance_score": 9,
        "editorial_priority_tier": "standard",
    }

    signals = _curated_priority_signals(row)
    assert signals["anchor"] is False
    assert _is_prioritized(row) is False


def test_dash_diet_remains_a_valid_anchor() -> None:
    row = {
        "title": "DASH dietary intervention for adults with hypertension",
        "relevance_score": 8,
        "editorial_priority_tier": "standard",
    }

    assert _curated_priority_signals(row)["anchor"] is True
    assert _is_prioritized(row) is True


def test_ultra_processed_food_and_nova_are_curated_anchors() -> None:
    upf = {
        "title": "Ultra-processed food intake and cardiometabolic risk",
        "relevance_score": 8,
    }
    nova = {
        "title": "NOVA classification and diet quality in adults",
        "relevance_score": 8,
    }

    assert _is_prioritized(upf) is True
    assert _is_prioritized(nova) is True


def test_high_value_editorial_still_requires_nutev_anchor() -> None:
    unrelated = {
        "title": "Consensus statement for dermatologic surgery",
        "relevance_score": 7,
        "editorial_priority_tier": "a1_proxy_moderate",
    }
    relevant = {
        "title": "Consensus statement on dietary care for cardiometabolic risk",
        "relevance_score": 7,
        "editorial_priority_tier": "a1_proxy_moderate",
    }

    assert _is_prioritized(unrelated) is False
    assert _is_prioritized(relevant) is True
