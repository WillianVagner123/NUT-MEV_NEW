from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from nutev.analysis.article1_abcd import ABCD_CODES
from nutev.review import article1_runtime as runtime


def test_runtime_initializes_additive_tables(tmp_path: Path):
    db = tmp_path / "runtime.sqlite3"
    runtime.initialize_article1_runtime(db)
    with sqlite3.connect(db) as con:
        tables = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {
        "article1_reviewer_assignments",
        "article1_abcd_submissions",
        "article1_abcd_adjudications",
        "article1_relation_submissions",
        "article1_relation_evidence_instances",
        "article1_relation_adjudications",
        "article1_method_characterization",
        "article1_synthesis_snapshots",
    } <= tables


def test_grid_is_exactly_34_and_unassessed():
    rows = runtime.instantiate_article1_abcd_grid("doc-1")
    assert len(rows) == 34
    assert [row["code"] for row in rows] == list(ABCD_CODES)
    assert all(row["presence"] is None and row["depth"] is None for row in rows)
    assert all(row["status"] == "UNASSESSED" for row in rows)


def test_relation_contract_rejects_cooccurrence_as_relation():
    with pytest.raises(ValueError):
        runtime.normalize_relation(
            source_code="A1",
            target_code="B1",
            direction="NON_DIRECTIONAL",
            relation_type="CO_OCCURRENCE",
        )


def test_relation_contract_normalizes_unique_key():
    key, source, target, direction, kind = runtime.normalize_relation(
        source_code="a1",
        target_code="d5",
        direction="source_to_target",
        relation_type="monitors",
    )
    assert key == "A1|D5|SOURCE_TO_TARGET|MONITORS"
    assert (source, target, direction, kind) == (
        "A1",
        "D5",
        "SOURCE_TO_TARGET",
        "MONITORS",
    )


def test_prisma_guard_blocks_nonformal_and_unfrozen():
    with pytest.raises(ValueError, match="zero formal PRISMA"):
        runtime.assert_article1_prisma_eligible(
            execution_mode="CALIBRATION",
            freeze_authorized=True,
            screening_calibration_released=True,
        )
    with pytest.raises(ValueError, match="GF-10"):
        runtime.assert_article1_prisma_eligible(
            execution_mode="FORMAL",
            freeze_authorized=False,
            screening_calibration_released=True,
        )


def test_prisma_guard_allows_only_resolved_formal_lineage():
    runtime.assert_article1_prisma_eligible(
        execution_mode="FORMAL",
        freeze_authorized=True,
        screening_calibration_released=True,
        unresolved_title_abstract=0,
        unresolved_full_text=0,
    )


def test_formal_guard_requires_real_assignment(tmp_path: Path):
    db = tmp_path / "guard.sqlite3"
    runtime.initialize_article1_runtime(db)
    with pytest.raises(ValueError, match="GF-07"):
        runtime._formal_guard(
            db,
            session_id="missing-session",
            execution_mode="FORMAL",
            reviewer_slot="REVIEWER_1",
            reviewer_name="R1",
        )


def test_relation_calibration_is_descriptive(monkeypatch, tmp_path: Path):
    def fake_latest(_db_path, *, session_id, document_id=None, reviewer_slot=None):
        rows = [
            {"reviewer_slot": "REVIEWER_1", "relation_key": "A1|D5|SOURCE_TO_TARGET|MONITORS"},
            {"reviewer_slot": "REVIEWER_2", "relation_key": "A1|D5|SOURCE_TO_TARGET|MONITORS"},
            {"reviewer_slot": "REVIEWER_1", "relation_key": "C8|D3|SOURCE_TO_TARGET|MODIFIES"},
        ]
        return rows

    monkeypatch.setattr(runtime, "_latest_relations", fake_latest)
    report = runtime.article1_relation_calibration_report(
        tmp_path / "unused.sqlite3",
        session_id="s",
        document_ids=["d1"],
    )
    assert report["reviewer_1_relations"] == 2
    assert report["reviewer_2_relations"] == 1
    assert report["intersection"] == 1
    assert report["union"] == 2
    assert report["jaccard_descriptive"] == 0.5
    assert "No Jaccard pass threshold" in report["interpretation"]
