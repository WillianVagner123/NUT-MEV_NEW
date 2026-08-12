from __future__ import annotations

from pathlib import Path

from nutev.analysis.relevance import score_record
from nutev.settings import load_json


def test_behavior_change_planning_terms_gain_busca2b_priority() -> None:
    scoring_rules = load_json(Path("config/scoring_rules.json"))
    boosted = score_record(
        {
            "title": "Randomized trial of action planning and readiness to change for dietary adherence in obesity",
            "source": "pubmed",
        },
        scoring_rules,
        "busca2b",
    )
    baseline = score_record(
        {
            "title": "Randomized trial of dietary adherence in obesity",
            "source": "pubmed",
        },
        scoring_rules,
        "busca2b",
    )

    assert float(boosted["relevance_score"]) > float(baseline["relevance_score"])


def test_behavior_change_model_terms_gain_artigo3_priority() -> None:
    scoring_rules = load_json(Path("config/scoring_rules.json"))
    boosted = score_record(
        {
            "title": "Questionnaire validation using the transtheoretical model and self-regulation for nutrition literacy",
            "source": "pubmed",
        },
        scoring_rules,
        "artigo3_framework",
    )
    baseline = score_record(
        {
            "title": "Questionnaire validation for nutrition literacy",
            "source": "pubmed",
        },
        scoring_rules,
        "artigo3_framework",
    )

    assert float(boosted["relevance_score"]) > float(baseline["relevance_score"])
