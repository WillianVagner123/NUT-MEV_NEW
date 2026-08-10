from __future__ import annotations

from nutev.analysis.relevance import keep_candidate_for_download, score_record


EMPTY_SCORING_RULES = {
    "keyword_points": {},
    "source_points": {},
    "workstream_points": {},
    "editorial_authority_points": {},
}


def _score(title: str, scoring_rules: dict | None = None) -> dict:
    return score_record(
        {"title": title, "source": "pubmed"},
        scoring_rules or EMPTY_SCORING_RULES,
        "busca2b",
    )


def test_dashboard_does_not_trigger_dash_diet_bonus() -> None:
    dashboard = _score("Dashboard for nutrition evidence monitoring")
    baseline = _score("Nutrition evidence monitoring")

    assert dashboard["relevance_score"] == baseline["relevance_score"]


def test_strategy_does_not_trigger_rat_preclinical_penalty() -> None:
    record = _score(
        "Implementation strategy for dietary adherence in adults with obesity"
    )

    assert "animal_or_preclinical" not in record["out_of_scope_flags"]
    assert record["out_of_scope_penalty"] == 0


def test_real_rat_study_still_triggers_preclinical_penalty() -> None:
    record = _score("Rat model of dietary intervention and obesity")

    assert "animal_or_preclinical" in record["out_of_scope_flags"]
    assert record["out_of_scope_penalty"] < 0


def test_hyphen_and_space_variants_match_the_same_scientific_term() -> None:
    scoring_rules = {
        **EMPTY_SCORING_RULES,
        "keyword_points": {"plant-based": 5},
    }
    hyphenated = _score("Plant-based dietary intervention", scoring_rules)
    spaced = _score("Plant based dietary intervention", scoring_rules)

    assert hyphenated["relevance_score"] == spaced["relevance_score"]


def test_newsletter_does_not_trigger_letter_download_exclusion() -> None:
    record = {
        "title": "Nutrition newsletter for adult obesity guideline implementation",
        "abstract": "Dietary adherence and lifestyle intervention guidance",
        "relevance_score": 10,
    }

    assert keep_candidate_for_download(record, "busca2b")
