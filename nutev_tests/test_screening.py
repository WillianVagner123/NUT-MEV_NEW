"""Canonical two-reviewer Article 1 screening tests."""
from __future__ import annotations

import pytest

from nutev.review.screening import (
    adjudicate,
    blind_reviewer_view,
    build_screening_queue,
    cohen_kappa,
    export_blocked_reason,
    final_decision,
    full_text_calibration_metrics,
    is_export_ready,
    reconcile_full_text,
    reconcile_record,
    reconcile_title_abstract,
    screening_agreement,
    title_abstract_action,
    title_abstract_calibration_metrics,
    validate_formal_reviewer_assignment,
)


def _d(reviewer, decision, phase="full_text"):
    return {"reviewer": reviewer, "decision": decision, "phase": phase}


def test_formal_reviewer_gate_requires_three_real_distinct_people():
    assignment = validate_formal_reviewer_assignment("R1 Pessoa", "R2 Pessoa", "Adjudicador")
    assert assignment.reviewer_1 == "R1 Pessoa"
    with pytest.raises(ValueError):
        validate_formal_reviewer_assignment("R1", "", "A")
    with pytest.raises(ValueError):
        validate_formal_reviewer_assignment("Pessoa", "Pessoa", "A")


def test_title_abstract_doubt_advances_without_rewriting_original_state():
    assert title_abstract_action("DOUBT") == "ADVANCE"
    result = reconcile_title_abstract("DOUBT", "INCLUDE")
    assert result["r1_decision"] == "DOUBT"
    assert result["resolution"] == "ADVANCE"
    assert result["operational_agreement"] is True


def test_title_abstract_doubt_vs_exclude_is_conflict():
    assert reconcile_title_abstract("DOUBT", "EXCLUDE")["resolution"] == "CONFLICT"
    result = reconcile_record([_d("R1", "uncertain", "title_abstract"), _d("R2", "include", "title_abstract")], "title_abstract")
    assert result["status"] == "agree_advance"


def test_full_text_doubt_blocks_closure_even_when_both_are_doubt():
    for pair in (("DOUBT", "DOUBT"), ("INCLUDE", "DOUBT"), ("EXCLUDE", "DOUBT")):
        assert reconcile_full_text(*pair)["resolution"] == "UNRESOLVED_DOUBT"
    result = reconcile_record([_d("R1", "include"), _d("R2", "uncertain")], "full_text")
    assert result["status"] == "unresolved_doubt"


def test_full_text_agreement_conflict_and_export_gate():
    assert reconcile_record([_d("R1", "include")], "full_text")["status"] == "needs_second_reviewer"
    assert reconcile_record([_d("R1", "include"), _d("R2", "include")], "full_text")["status"] == "agree_include"
    assert reconcile_record([_d("R1", "exclude"), _d("R2", "exclude")], "full_text")["status"] == "agree_exclude"
    assert reconcile_record([_d("R1", "include"), _d("R2", "exclude")], "full_text")["status"] == "conflict"
    assert is_export_ready([_d("R1", "include"), _d("R2", "include")]) is True
    assert is_export_ready([_d("R1", "include"), _d("R2", "uncertain")]) is False


def test_conflict_resolved_by_adjudication_preserves_original_decisions():
    decs = [_d("R1", "include"), _d("R2", "exclude")]
    assert final_decision(decs)["decision"] == "pending"
    adj = adjudicate("doc1", "full_text", "advisor", "include", "in scope")
    assert final_decision(decs, [adj])["decision"] == "include"
    assert decs[0]["decision"] == "include" and decs[1]["decision"] == "exclude"


def test_adjudication_requires_rationale_and_binary_resolution():
    with pytest.raises(ValueError):
        adjudicate("d", "full_text", "advisor", "include", "")
    with pytest.raises(ValueError):
        adjudicate("d", "full_text", "advisor", "uncertain", "because")


def test_title_abstract_calibration_uses_advance_vs_exclude_and_gf07():
    rows = [
        {"r1_decision": "INCLUDE", "r2_decision": "DOUBT"},
        {"r1_decision": "EXCLUDE", "r2_decision": "EXCLUDE"},
        {"r1_decision": "DOUBT", "r2_decision": "EXCLUDE"},
        {"r1_decision": "INCLUDE", "r2_decision": "INCLUDE"},
        {"r1_decision": "DOUBT", "r2_decision": "DOUBT"},
    ]
    metrics = title_abstract_calibration_metrics(rows, expected_units=5, gf07_resolved=True)
    assert metrics["completeness"] == 1.0
    assert metrics["advance_exclude_raw_agreement"] == pytest.approx(0.8)
    assert metrics["r1_doubt_count"] == 2
    assert metrics["release_signal"] is True
    assert title_abstract_calibration_metrics(rows, expected_units=5, gf07_resolved=False)["release_signal"] is False


def test_recurrent_rule_contradiction_blocks_title_abstract_release():
    rows = [{"r1_decision": "INCLUDE", "r2_decision": "INCLUDE"}]
    metrics = title_abstract_calibration_metrics(rows, expected_units=1, gf07_resolved=True, recurrent_rule_contradiction=True)
    assert metrics["advance_exclude_raw_agreement"] == 1.0
    assert metrics["release_signal"] is False


def test_full_text_calibration_preserves_doubt_and_family_denominator():
    rows = [
        {"r1_decision": "INCLUDE", "r2_decision": "INCLUDE", "r1_family": "F1", "r2_family": "F1"},
        {"r1_decision": "EXCLUDE", "r2_decision": "EXCLUDE"},
        {"r1_decision": "DOUBT", "r2_decision": "DOUBT"},
    ]
    metrics = full_text_calibration_metrics(rows, expected_units=3, gf07_resolved=True)
    assert metrics["eligibility_denominator"] == 3
    assert metrics["eligibility_raw_agreement"] == 1.0
    assert metrics["unresolved_doubt_pairs"] == 1
    assert metrics["family_denominator"] == 1
    assert metrics["release_signal"] is False


def test_full_text_release_thresholds_when_no_doubt():
    rows = [
        {"r1_decision": "INCLUDE", "r2_decision": "INCLUDE", "r1_family": "A", "r2_family": "A"},
        {"r1_decision": "INCLUDE", "r2_decision": "INCLUDE", "r1_family": "B", "r2_family": "B"},
        {"r1_decision": "EXCLUDE", "r2_decision": "EXCLUDE"},
        {"r1_decision": "EXCLUDE", "r2_decision": "EXCLUDE"},
        {"r1_decision": "INCLUDE", "r2_decision": "EXCLUDE"},
    ]
    metrics = full_text_calibration_metrics(rows, expected_units=5, gf07_resolved=True)
    assert metrics["eligibility_raw_agreement"] == pytest.approx(0.8)
    assert metrics["family_raw_agreement"] == 1.0
    assert metrics["release_signal"] is True


def test_blind_view_hides_other_reviewer_until_unblinded():
    row = {"document_id": "D1", "r1_decision": "INCLUDE", "r2_decision": "EXCLUDE"}
    assert blind_reviewer_view(row, reviewer_slot="R1", own_submitted=True)["r2_decision"] is None
    assert blind_reviewer_view(row, reviewer_slot="R2", own_submitted=True)["r1_decision"] is None
    assert blind_reviewer_view(row, reviewer_slot="R1", own_submitted=True, pair_unblinded=True)["r2_decision"] == "EXCLUDE"


def test_cohen_kappa_is_descriptive_only():
    assert cohen_kappa([("include", "include"), ("exclude", "exclude")]) == 1.0
    report = screening_agreement([
        {"reviewer_1_decision": "include", "reviewer_2_decision": "include", "screen_flag": "ready_to_screen", "export_ready": False}
    ])
    assert report["cohen_kappa"] == 1.0
    assert "substantial" not in report["note"].lower()
    assert "near-perfect" not in report["note"].lower()


def test_screening_queue_flags_no_full_text_and_never_autovalidates():
    q = build_screening_queue([
        {"name": "ok guide", "extraction_status": "ok"},
        {"name": "scanned", "extraction_status": "pdf_needs_ocr_setup"},
        {"name": "blocked", "extraction_status": "junk_or_blocked"},
    ])
    flags = {r["name"]: r["screen_flag"] for r in q}
    assert flags == {"ok guide": "ready_to_screen", "scanned": "poor_ocr", "blocked": "no_full_text"}
    assert all(r["export_ready"] is False for r in q)
    assert "not validated" in export_blocked_reason([_d("R1", "include")])
