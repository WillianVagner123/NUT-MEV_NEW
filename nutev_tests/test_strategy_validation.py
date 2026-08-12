"""GF-02 support tests for global strategy input validation."""
from __future__ import annotations

import pytest

from nutev.search.strategy_builder import FILTER_SUPPORT, build_all, parse_strategy, unified_from_text


def test_year_range_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="Ano inicial não pode ser maior"):
        unified_from_text("nutrition", year_from=2025, year_to=2020)


def test_year_range_rejects_non_year_values_instead_of_silently_ignoring():
    with pytest.raises(ValueError, match="Ano inicial deve ser um ano inteiro"):
        unified_from_text("nutrition", year_from="abc")


def test_zero_year_still_means_no_filter():
    payload = unified_from_text("nutrition", year_from=0, year_to="0")
    assert "year_from" not in payload
    assert "year_to" not in payload


def test_languages_are_normalized_for_current_article1_workflow():
    payload = unified_from_text("nutrition", languages="English, português, es")
    assert payload["languages"] == ["eng", "por", "spa"]

    grid = build_all(parse_strategy(payload))
    pubmed_specific = grid["pubmed"]["specific"]
    openalex_specific = grid["openalex"]["specific"]

    assert "english[la]" in pubmed_specific
    assert "portuguese[la]" in pubmed_specific
    assert "spanish[la]" in pubmed_specific
    assert "language:en|pt|es" in openalex_specific


def test_unknown_language_is_rejected_explicitly():
    with pytest.raises(ValueError, match="Idioma não reconhecido"):
        unified_from_text("nutrition", languages="german")


def test_publication_types_are_normalized_and_only_rendered_where_supported():
    payload = unified_from_text(
        "nutrition",
        publication_types="guideline; systematic review; meta analysis",
    )
    assert payload["publication_types"] == [
        "Guideline",
        "Systematic Review",
        "Meta-Analysis",
    ]

    grid = build_all(parse_strategy(payload))
    assert "Guideline[pt]" in grid["pubmed"]["specific"]
    assert '"Systematic Review"[pt]' in grid["pubmed"]["specific"]
    assert '"Meta-Analysis"[pt]' in grid["pubmed"]["specific"]
    assert "Guideline" not in grid["europepmc"]["specific"]
    assert "Guideline" not in grid["crossref"]["specific"]
    assert "Guideline" not in grid["openalex"]["specific"]


def test_unknown_publication_type_is_rejected_explicitly():
    with pytest.raises(ValueError, match="Tipo de publicação não reconhecido"):
        unified_from_text("nutrition", publication_types="made-up type")


@pytest.mark.parametrize(
    "query",
    [
        "nutrition AND obesity",
        "nutrition[tiab]",
        "TITLE-ABS-KEY(nutrition)",
        "TS=nutrition",
        "PUB_YEAR:2025",
        "LANG:eng",
        "query=nutrition",
    ],
)
def test_global_field_rejects_manual_boolean_or_provider_syntax(query: str):
    with pytest.raises(ValueError):
        unified_from_text(query)


def test_wrapping_quotes_are_normalized_without_double_quoting_provider_output():
    payload = unified_from_text('"lifestyle medicine"; nutrition')
    assert payload["query"] == ["lifestyle medicine", "nutrition"]

    pubmed = build_all(parse_strategy(payload))["pubmed"]["balanced"]
    assert '"lifestyle medicine"[tiab]' in pubmed
    assert '""lifestyle medicine""' not in pubmed


def test_filter_support_matrix_is_explicit_and_matches_current_renderers():
    assert FILTER_SUPPORT["pubmed"] == {
        "year": True,
        "language": True,
        "publication_type": True,
    }
    assert FILTER_SUPPORT["europepmc"]["publication_type"] is False
    assert FILTER_SUPPORT["crossref"] == {
        "year": True,
        "language": False,
        "publication_type": False,
    }
    assert FILTER_SUPPORT["openalex"] == {
        "year": True,
        "language": True,
        "publication_type": False,
    }
