"""Article 1 export safety and compatibility tests."""
from __future__ import annotations

import pytest

from nutev.analysis.article1_abcd import ABCD_CODES
from nutev.export.article1_exports import (
    abcd_34_matrix_rows,
    abcd_matrix_rows,
    prisma_counts,
    prisma_diagram_mermaid,
)


def _closed_long_rows(document_id="DOC1"):
    rows = []
    for i, code in enumerate(ABCD_CODES):
        if i % 2:
            rows.append({"document_id": document_id, "code": code, "presence": "NO", "depth": 0, "family": "F1"})
        else:
            rows.append({"document_id": document_id, "code": code, "presence": "YES", "depth": 2, "family": "F1"})
    return rows


def test_legacy_matrix_is_explicitly_non_scoring():
    rows = [{
        "name": "Guia", "country": "brazil", "reference": "MoH. 2014.",
        "domain_A_state": "RECOMMENDED", "domain_A_intensity": 2,
        "domain_B_state": "OPERATIONALIZED", "domain_B_intensity": 3,
        "domain_C_state": "MENTIONED", "domain_C_intensity": 1,
        "domain_D_state": "NOT_ASSESSED", "domain_D_intensity": "",
    }]
    matrix = abcd_matrix_rows(rows)
    assert matrix[0]["A_state"] == "RECOMMENDED"
    assert "n_domains_positive" not in matrix[0]
    assert "profile" not in matrix[0]


def test_canonical_abcd_export_has_34_presence_depth_pairs_and_no_global_score():
    row = abcd_34_matrix_rows(_closed_long_rows())[0]
    assert row["document_id"] == "DOC1"
    for code in ABCD_CODES:
        assert f"{code}_presence" in row
        assert f"{code}_depth" in row
    for forbidden in ("n_domains_positive", "profile", "abcd_score", "mean_depth", "maturity_score"):
        assert forbidden not in row


def test_canonical_abcd_export_blocks_incomplete_document():
    with pytest.raises(ValueError, match="cannot close"):
        abcd_34_matrix_rows(_closed_long_rows()[:-1])


def test_prisma_counts_included_is_pending():
    registries = {"file_assets": [1, 2, 3], "versions": [1, 2], "families": [1]}
    queue = [{"screen_flag": "ready_to_screen"}, {"screen_flag": "ready_to_screen"}, {"screen_flag": "no_full_text"}]
    counts = prisma_counts(registries, queue)
    assert counts["identified_file_assets"] == 3
    assert counts["ready_to_screen"] == 2
    assert counts["included"] == "pending"


def test_prisma_diagram_is_pending_human_validation():
    md = prisma_diagram_mermaid(prisma_counts({"file_assets": [1], "versions": [1], "families": [1]}, []))
    assert md.startswith("```mermaid")
    assert "PENDENTE" in md
