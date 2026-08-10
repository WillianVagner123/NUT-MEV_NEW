from __future__ import annotations

from nutev.analysis.nutev_classifier import classify_evidence


def test_classifier_uses_term_boundaries_without_losing_valid_phrases() -> None:
    records = [
        {
            "title": "Reminder system for routine visits",
            "abstract": "A dashboard improved scheduling, but did not evaluate diet quality.",
        },
        {
            "title": "Food-based dietary guideline for adults",
            "abstract": "A plant-based diet pattern improved adherence.",
        },
    ]
    ontology = {
        "domains": {
            "diet_patterns": ["mind", "dash", "diet", "plant-based diet"],
            "guidelines": ["food-based dietary guideline"],
        },
        "outcomes": {"adherence": ["adherence"]},
    }
    lenses = {"lenses": {"nutrition": {"domains": ["diet_patterns"]}}}

    first, second = classify_evidence(records, ontology, lenses)

    assert first["domain_diet_patterns_count"] == 1
    assert first["domain_guidelines_count"] == 0
    assert first["outcome_adherence_count"] == 0
    assert second["domain_diet_patterns_count"] == 2
    assert second["domain_guidelines_count"] == 1
    assert second["outcome_adherence_count"] == 1


def test_classifier_reads_provider_summary_snippet_and_source_metadata() -> None:
    records = [
        {
            "title": "Provider record",
            "summary": "Dietary implementation evidence.",
            "snippet": "Cardiometabolic risk was a reported outcome.",
            "journal": "Nutrition Reviews",
            "source_institution": "Lifestyle Medicine Society",
            "evidence_type": "guideline",
        }
    ]
    ontology = {
        "domains": {
            "nutrition": ["nutrition"],
            "implementation": ["implementation"],
            "policy": ["guideline"],
        },
        "outcomes": {"cardiometabolic": ["cardiometabolic"]},
    }
    lenses = {
        "lenses": {
            "nutrition_lens": {"domains": ["nutrition"]},
            "implementation_lens": {"domains": ["implementation"]},
        }
    }

    [classified] = classify_evidence(records, ontology, lenses)

    assert classified["domain_nutrition_present"] == 1
    assert classified["domain_implementation_present"] == 1
    assert classified["domain_policy_present"] == 1
    assert classified["outcome_cardiometabolic_present"] == 1
    assert set(classified["evidence_lenses"]) == {
        "nutrition_lens",
        "implementation_lens",
    }


def test_scope_flags_also_use_term_boundaries() -> None:
    records = [
        {
            "title": "Metformin dashboard implementation",
            "abstract": "Operational software monitoring only.",
        }
    ]
    ontology = {"domains": {}, "outcomes": {}}

    [classified] = classify_evidence(records, ontology, {"lenses": {}})

    assert classified["scope_status"] == "off_scope_review"
    assert classified["scope_flags"] == ["pharmacology"]
