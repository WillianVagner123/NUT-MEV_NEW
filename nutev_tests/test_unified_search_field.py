"""Regression tests for the article-independent global search field."""
from __future__ import annotations

from nutev.search.strategy_builder import (
    ARTICLE_SCOPE_ALL,
    build_all,
    parse_strategy,
    unified_from_text,
)


def test_unified_field_applies_to_all_articles_and_splits_alternatives():
    payload = unified_from_text(
        "adesão alimentar; competências alimentares\nguias alimentares",
        year_from=2015,
        languages="por, eng",
    )

    assert payload["article_scope"] == ARTICLE_SCOPE_ALL
    assert payload["query"] == [
        "adesão alimentar",
        "competências alimentares",
        "guias alimentares",
    ]
    assert payload["year_from"] == 2015
    assert payload["languages"] == ["por", "eng"]


def test_unified_query_takes_precedence_over_legacy_picos_blocks():
    spec = parse_strategy(
        {
            "query": "adherence, food competence",
            "population": ["adults"],
            "outcome": ["weight loss"],
        }
    )

    assert len(spec.concepts) == 1
    assert spec.concepts[0].role == "query"
    assert spec.concepts[0].terms == ["adherence", "food competence"]


def test_same_global_field_is_rendered_for_every_provider():
    payload = unified_from_text("adherence; meal planning")
    grid = build_all(parse_strategy(payload))

    assert "adherence" in grid["pubmed"]["balanced"]
    assert '"meal planning"' in grid["pubmed"]["balanced"]
    assert "adherence" in grid["europepmc"]["balanced"]
    assert "adherence" in grid["crossref"]["balanced"]
    assert "adherence" in grid["openalex"]["balanced"]


def test_empty_global_field_does_not_create_a_strategy():
    assert unified_from_text("  \n ; , ") == {}


def test_unified_terms_are_deduplicated_case_insensitively():
    payload = unified_from_text("Adherence; adherence; ADHERENCE\nmeal planning")
    assert payload["query"] == ["Adherence", "meal planning"]
