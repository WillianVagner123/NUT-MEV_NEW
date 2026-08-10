from __future__ import annotations

from nutev.global_watch.watch_scoring import (
    _apply_terms,
    _has_nutmev_scope_signal,
    score_watch_item,
)


def test_ckm_long_form_is_a_nutmev_scope_signal() -> None:
    assert _has_nutmev_scope_signal(
        "cardiovascular-kidney-metabolic scientific statement for risk management"
    )


def test_ckm_scientific_statement_is_not_demoted_as_out_of_scope() -> None:
    item = {
        "title": "Cardiovascular-kidney-metabolic scientific statement",
        "abstract": "Integrated CKM risk management in adults.",
        "source_provider": "official_sources",
        "relevance_score": 0,
    }

    assert score_watch_item(item) >= 0


def test_term_matching_does_not_penalize_newsletter_as_letter() -> None:
    assert _apply_terms(0.0, "nutrition newsletter", (("letter", -30.0),)) == 0.0
    assert _apply_terms(0.0, "letter to the editor", (("letter", -30.0),)) == -30.0


def test_hyphen_and_space_scope_variants_are_equivalent() -> None:
    assert _has_nutmev_scope_signal("plant-based dietary intervention")
    assert _has_nutmev_scope_signal("plant based dietary intervention")
