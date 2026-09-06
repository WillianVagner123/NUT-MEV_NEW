from __future__ import annotations

from pathlib import Path

from nutev.querypacks.provider_queries import render_queries_for_provider
from nutev.querypacks.semantic_blocks import semantic_terms
from nutev.settings import load_json


ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = load_json(ROOT / "config" / "keyword_taxonomy.json")


def _provider_query_text(workstream: str, provider: str) -> str:
    return "\n".join(render_queries_for_provider(TAXONOMY, workstream, provider)).lower()


def test_busca2b_semantic_blocks_keep_core_nutmev_retrieval_terms() -> None:
    terms = {term.lower() for term in semantic_terms("busca2b", min_priority=5)}

    expected_terms = {
        "masld",
        "nafld",
        "metabolic dysfunction-associated steatotic liver disease",
        "food as medicine intervention",
        "produce prescription program",
        "nutrition care pathway",
        "dietary adherence",
        "hybrid effectiveness-implementation",
        "implementation outcomes",
        "mediterranean diet",
        "plant-based diet",
    }

    assert expected_terms <= terms


def test_busca2b_provider_queries_surface_clinical_and_delivery_anchors() -> None:
    pubmed_queries = _provider_query_text("busca2b", "pubmed")
    europepmc_queries = _provider_query_text("busca2b", "europepmc")

    for query_text in (pubmed_queries, europepmc_queries):
        assert "masld" in query_text
        assert "nutrition care pathway" in query_text
        assert "food as medicine" in query_text
        assert "implementation" in query_text


def test_busca2a_guideline_queries_preserve_high_value_document_types() -> None:
    query_text = _provider_query_text("busca2a", "pubmed")

    assert "clinical practice guideline" in query_text
    assert "consensus" in query_text
    assert "standards of care" in query_text
    assert "clinical decision pathway" in query_text
    assert "masld" in query_text
