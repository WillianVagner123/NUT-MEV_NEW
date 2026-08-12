from __future__ import annotations

import json
from pathlib import Path

from nutev.analysis.relevance import score_record

SCORING_RULES = json.loads(
    (Path(__file__).resolve().parents[1] / "config" / "scoring_rules.json").read_text(
        encoding="utf-8"
    )
)


def _score(title: str, workstream: str) -> float:
    record = score_record({"title": title, "source": "pubmed"}, SCORING_RULES, workstream)
    return float(record["relevance_score"])


def test_behavior_framework_titles_gain_priority_in_busca2b() -> None:
    boosted = _score(
        "Behavior Change Wheel and COM-B for dietary adherence implementation in obesity",
        "busca2b",
    )
    baseline = _score("Dietary adherence implementation in obesity", "busca2b")

    assert boosted > baseline


def test_behavior_framework_titles_gain_priority_in_a3() -> None:
    boosted = _score(
        "Behaviour Change Wheel, COM-B and intervention mapping for a food literacy questionnaire",
        "a3",
    )
    baseline = _score("Food literacy questionnaire", "a3")

    assert boosted > baseline
