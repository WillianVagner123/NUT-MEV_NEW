from pathlib import Path

from nutev.analysis.nutev_classifier import classify_evidence
from nutev.settings import load_json


CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"


def _load_ontology() -> dict:
    return load_json(CONFIG_ROOT / "nutev_ontology.json")


def _load_lenses() -> dict:
    return load_json(CONFIG_ROOT / "evidence_lenses.json")


def test_evidence_lenses_reference_known_ontology_domains():
    ontology = _load_ontology()
    lenses = _load_lenses()
    known_domains = set(ontology["domains"])
    configured_domains = {
        domain
        for lens in lenses["lenses"].values()
        for domain in lens.get("domains", [])
    }

    assert configured_domains <= known_domains


def test_evidence_lenses_classify_semantic_records():
    records = [
        {
            "title": "Mediterranean diet quality guideline for low-income adults",
            "abstract": "",
            "extracted_text": "",
        },
        {
            "title": "Implementation delivery program for diabetes remission risk",
            "abstract": "",
            "extracted_text": "",
        },
    ]

    classified = classify_evidence(records, _load_ontology(), _load_lenses())

    assert classified[0]["lens_policy_systems_present"] == 1
    assert classified[0]["lens_clinical_outcomes_present"] == 1
    assert classified[1]["lens_implementation_present"] == 1
    assert "implementation" in classified[1]["evidence_lenses"]
