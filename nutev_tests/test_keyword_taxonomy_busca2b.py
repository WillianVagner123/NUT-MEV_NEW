from pathlib import Path

from nutev.querypacks.builders import build_structured_components
from nutev.settings import load_json


def test_busca2b_includes_fatty_liver_clinical_terms_in_structured_queries() -> None:
    taxonomy = load_json(Path("config/keyword_taxonomy.json"))

    _, components = build_structured_components(taxonomy, "busca2b")
    clinical_terms = {term.lower() for term in components["clinical_terms"]}

    assert "fatty liver" in clinical_terms
    assert "steatohepatitis" in clinical_terms
    assert "metabolic dysfunction-associated steatohepatitis" in clinical_terms
