from __future__ import annotations

import pytest

from nutev.analysis.article1_abcd import (
    ABCD_CODES,
    ABCD_COMPONENTS,
    ABCD_VERSION,
    assert_article1_export_schema_is_safe,
    assert_document_can_close,
    calibration_metrics,
    codebook_rows,
    document_completion,
    validate_component_decision,
)


def _closed_rows():
    rows = []
    for index, code in enumerate(ABCD_CODES):
        if index % 3 == 0:
            rows.append({"code": code, "presence": "YES", "depth": (index % 3) + 1})
        else:
            rows.append({"code": code, "presence": "NO", "depth": 0})
    return rows


def test_codebook_has_exactly_34_unique_components_in_canonical_order():
    assert ABCD_VERSION == "v1.1-candidata"
    assert len(ABCD_CODES) == 34
    assert len(set(ABCD_CODES)) == 34
    assert ABCD_CODES[:5] == ("A1", "A2", "A3", "A4", "A5")
    assert ABCD_CODES[5:14] == tuple(f"B{i}" for i in range(1, 10))
    assert ABCD_CODES[14:24] == tuple(f"C{i}" for i in range(1, 11))
    assert ABCD_CODES[24:] == tuple(f"D{i}" for i in range(1, 11))
    assert set(ABCD_COMPONENTS) == set(ABCD_CODES)
    assert len(codebook_rows()) == 34


def test_yes_requires_depth_1_to_3():
    assert validate_component_decision(code="A1", presence="SIM", depth=1) == ("A1", "YES", 1)
    with pytest.raises(ValueError, match="YES requires depth 1-3"):
        validate_component_decision(code="A1", presence="YES", depth=0)
    with pytest.raises(ValueError, match="YES requires depth 1-3"):
        validate_component_decision(code="A1", presence="YES", depth="")


def test_no_requires_depth_zero():
    assert validate_component_decision(code="C9", presence="NÃO", depth=0) == ("C9", "NO", 0)
    with pytest.raises(ValueError, match="NO requires depth 0"):
        validate_component_decision(code="C9", presence="NO", depth=1)


def test_doubt_is_real_open_state_but_never_a_closed_state():
    assert validate_component_decision(code="D10", presence="DÚVIDA", depth="", final=False) == ("D10", "DOUBT", None)
    with pytest.raises(ValueError, match="DOUBT must keep depth blank"):
        validate_component_decision(code="D10", presence="DOUBT", depth=1, final=False)
    with pytest.raises(ValueError, match="cannot remain"):
        validate_component_decision(code="D10", presence="DOUBT", depth="", final=True)


def test_blank_and_na_are_not_absence():
    for invalid in ("", None, "N/A", "NA", "NOT_APPLICABLE"):
        with pytest.raises(ValueError, match="blank and N/A are not valid"):
            validate_component_decision(code="A2", presence=invalid, depth=0)


def test_document_closes_only_with_34_valid_unique_final_decisions():
    rows = _closed_rows()
    status = document_completion(rows)
    assert status["closed"] is True
    assert status["evaluated_unique_components"] == 34
    assert_document_can_close(rows)

    missing = rows[:-1]
    status = document_completion(missing)
    assert status["closed"] is False
    assert status["missing_codes"] == ["D10"]
    with pytest.raises(ValueError, match="cannot close"):
        assert_document_can_close(missing)


def test_duplicate_code_blocks_document_closure():
    rows = _closed_rows()
    rows.append({"code": "A1", "presence": "NO", "depth": 0})
    status = document_completion(rows)
    assert status["closed"] is False
    assert status["duplicate_codes"] == ["A1"]


def test_d102_presence_denominator_includes_doubt_as_observed_state():
    pairs = [
        {"code": "A1", "r1_presence": "YES", "r1_depth": 2, "r2_presence": "YES", "r2_depth": 2},
        {"code": "A2", "r1_presence": "DOUBT", "r1_depth": "", "r2_presence": "DOUBT", "r2_depth": ""},
        {"code": "A3", "r1_presence": "YES", "r1_depth": 1, "r2_presence": "DOUBT", "r2_depth": ""},
        {"code": "A4", "r1_presence": "NO", "r1_depth": 0, "r2_presence": "NO", "r2_depth": 0},
    ]
    metrics = calibration_metrics(pairs, expected_units=4)
    assert metrics["presence_denominator"] == 4
    assert metrics["presence_exact_matches"] == 3
    assert metrics["presence_raw_agreement"] == pytest.approx(0.75)
    assert metrics["r1_doubt_count"] == 1
    assert metrics["r2_doubt_count"] == 2
    assert metrics["depth_denominator_both_yes"] == 1
    assert metrics["exact_depth_agreement"] == 1.0


def test_d102_depth_denominator_is_only_both_yes():
    pairs = [
        {"code": "B1", "r1_presence": "YES", "r1_depth": 1, "r2_presence": "YES", "r2_depth": 2},
        {"code": "B2", "r1_presence": "YES", "r1_depth": 3, "r2_presence": "NO", "r2_depth": 0},
        {"code": "B3", "r1_presence": "NO", "r1_depth": 0, "r2_presence": "NO", "r2_depth": 0},
    ]
    metrics = calibration_metrics(pairs, expected_units=3)
    assert metrics["presence_denominator"] == 3
    assert metrics["depth_denominator_both_yes"] == 1
    assert metrics["exact_depth_agreement"] == 0.0
    assert metrics["depth_within_one_agreement"] == 1.0


def test_calibration_cannot_signal_stability_before_100_percent_completeness():
    pairs = [{"code": "A1", "r1_presence": "YES", "r1_depth": 2, "r2_presence": "YES", "r2_depth": 2}]
    metrics = calibration_metrics(pairs, expected_units=2)
    assert metrics["completeness"] == 0.5
    assert metrics["stability_signal"] is False


def test_recurrent_critical_divergence_blocks_signal_even_if_metrics_pass():
    pairs = [
        {"code": "A1", "r1_presence": "YES", "r1_depth": 2, "r2_presence": "YES", "r2_depth": 2},
        {"code": "A2", "r1_presence": "YES", "r1_depth": 2, "r2_presence": "YES", "r2_depth": 2},
        {"code": "A3", "r1_presence": "NO", "r1_depth": 0, "r2_presence": "NO", "r2_depth": 0},
    ]
    metrics = calibration_metrics(pairs, expected_units=3, recurrent_critical_divergence=True)
    assert metrics["presence_raw_agreement"] == 1.0
    assert metrics["exact_depth_agreement"] == 1.0
    assert metrics["depth_within_one_agreement"] == 1.0
    assert metrics["stability_signal"] is False


def test_canonical_export_blocks_legacy_or_global_aggregation_fields():
    assert_article1_export_schema_is_safe(["document_id", "A1_presence", "A1_depth"])
    for forbidden in ("profile", "n_domains", "n_domains_positive", "abcd_score", "mean_depth", "maturity_score", "document_rank"):
        with pytest.raises(ValueError, match="forbidden"):
            assert_article1_export_schema_is_safe(["document_id", forbidden])
