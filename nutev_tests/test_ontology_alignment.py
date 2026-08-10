from __future__ import annotations

from pathlib import Path

from nutev.analysis.nutev_classifier import classify_evidence
from nutev.settings import load_json


CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"


def _classify(title: str) -> dict:
    [record] = classify_evidence(
        [{"title": title}],
        load_json(CONFIG_ROOT / "nutev_ontology.json"),
        load_json(CONFIG_ROOT / "evidence_lenses.json"),
    )
    return record


def test_ontology_classifies_upf_nova_as_dietary_pattern() -> None:
    record = _classify(
        "NOVA classification of ultra-processed foods and diet quality in adults"
    )
    assert record["domain_dietary_patterns_present"] == 1


def test_ontology_classifies_dietary_adherence_as_implementation() -> None:
    record = _classify(
        "Dietary adherence and self-monitoring implementation strategy in obesity care"
    )
    assert record["domain_implementation_present"] == 1
    assert record["outcome_cardiometabolic_present"] == 1


def test_ontology_classifies_ckm_and_metabolic_liver_scope() -> None:
    ckm = _classify(
        "Nutrition guideline for cardiovascular-kidney-metabolic risk in adults"
    )
    liver = _classify(
        "Dietary intervention for metabolic dysfunction-associated steatotic liver disease MASLD"
    )

    assert ckm["outcome_cardiometabolic_present"] == 1
    assert ckm["domain_policy_systems_present"] == 1
    assert liver["outcome_cardiometabolic_present"] == 1


def test_ontology_classifies_food_access_and_food_as_medicine() -> None:
    record = _classify(
        "Food is Medicine produce prescription for healthy food access in low-income adults"
    )
    assert record["domain_policy_systems_present"] == 1
    assert record["domain_equity_present"] == 1
