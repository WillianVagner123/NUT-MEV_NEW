from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from nutev.analysis.article1_abcd import ABCD_CODES
from nutev.review import article1_runtime as runtime
from nutev.review.article_screening_ledger import get_or_create_screening_session
from nutev.search.corpus_build_ledger import create_corpus_build
from nutev.search.strategy_execution_ledger import create_search_run
from nutev.search.strategy_registry import save_strategy_version

R1_ROLE = "reviewer_1"
R2_ROLE = "reviewer_2"
ADJ_ROLE = "external_reviewer"


def _session(db: Path) -> str:
    version = save_strategy_version(
        db,
        title="Runtime calibration fixture",
        query_text="dietary guideline",
        strategy_payload={
            "query": ["dietary guideline"],
            "providers": {"pubmed": {"enabled": True}},
            "filters": {},
        },
        search_type="PILOT",
        created_by="test",
    )
    run = create_search_run(
        db,
        version_id=version.version_id,
        breadth="pilot",
        provider_limit=10,
        resume_enabled=False,
    )
    build = create_corpus_build(
        db,
        run_id=run["run_id"],
        version_id=version.version_id,
    )
    session = get_or_create_screening_session(
        db,
        build_id=build["build_id"],
        protocol_version="article1-runtime-test",
        created_by="test",
    )
    return str(session["session_id"])


def test_runtime_initializes_additive_mode_aware_tables(tmp_path: Path):
    db = tmp_path / "runtime.sqlite3"
    runtime.initialize_article1_runtime(db)
    with sqlite3.connect(db) as con:
        tables = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        abcd_columns = {
            row[1] for row in con.execute("PRAGMA table_info(article1_abcd_submissions)")
        }
        relation_columns = {
            row[1]
            for row in con.execute("PRAGMA table_info(article1_relation_review_status)")
        }
    assert {
        "article1_reviewer_assignments",
        "article1_abcd_submissions",
        "article1_abcd_adjudications",
        "article1_relation_submissions",
        "article1_relation_evidence_instances",
        "article1_relation_review_status",
        "article1_relation_adjudications",
        "article1_method_characterization",
        "article1_synthesis_snapshots",
    } <= tables
    assert "execution_mode" in abcd_columns
    assert "execution_mode" in relation_columns


def test_grid_modes_relation_and_prisma_guards():
    rows = runtime.instantiate_article1_abcd_grid("doc-1")
    assert len(rows) == 34
    assert [row["code"] for row in rows] == list(ABCD_CODES)
    assert all(row["presence"] is None and row["status"] == "UNASSESSED" for row in rows)
    assert runtime._normalize_mode("calibration") == "CALIBRATION"
    with pytest.raises(ValueError):
        runtime._normalize_mode("mixed")
    with pytest.raises(ValueError):
        runtime.normalize_relation(
            source_code="A1",
            target_code="B1",
            direction="NON_DIRECTIONAL",
            relation_type="CO_OCCURRENCE",
        )
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
    runtime.assert_article1_prisma_eligible(
        execution_mode="FORMAL",
        freeze_authorized=True,
        screening_calibration_released=True,
    )


def test_gf07_assignment_is_real_distinct_and_revisioned(tmp_path: Path):
    db = tmp_path / "assignment.sqlite3"
    session_id = _session(db)
    first = runtime.set_article1_reviewer_assignment(
        db,
        session_id=session_id,
        reviewer_1_name="Reviewer One",
        reviewer_2_name="Reviewer Two",
        adjudicator_name="Adjudicator",
        notes="first",
    )
    assert first["gf07_resolved"] == 1
    assert first["revision"] == 1
    assert runtime.article1_reviewer_assignment(db, session_id)["reviewer_2_name"] == "Reviewer Two"
    second = runtime.set_article1_reviewer_assignment(
        db,
        session_id=session_id,
        reviewer_1_name="Reviewer One",
        reviewer_2_name="Reviewer Two",
        adjudicator_name="Adjudicator",
        notes="updated",
    )
    assert second["revision"] == 2
    with pytest.raises(ValueError):
        runtime.set_article1_reviewer_assignment(
            db,
            session_id=session_id,
            reviewer_1_name="Same",
            reviewer_2_name="Same",
            adjudicator_name="Other",
        )
    with pytest.raises(ValueError, match="GF-07"):
        runtime._formal_guard(
            tmp_path / "empty.sqlite3",
            session_id="missing",
            execution_mode="FORMAL",
            reviewer_slot="REVIEWER_1",
            reviewer_name="R1",
        )
    runtime._formal_guard(
        db,
        session_id=session_id,
        execution_mode="CALIBRATION",
        reviewer_slot="REVIEWER_1",
        reviewer_name="Calibration reviewer",
    )


def test_abcd_calibration_persists_34_by_2_and_adjudicates(tmp_path: Path):
    db = tmp_path / "abcd.sqlite3"
    session_id = _session(db)
    document_id = "calibration-doc"

    for code in ABCD_CODES:
        for slot, name, role in (
            ("REVIEWER_1", "R1", R1_ROLE),
            ("REVIEWER_2", "R2", R2_ROLE),
        ):
            saved = runtime.submit_article1_abcd(
                db,
                session_id=session_id,
                document_id=document_id,
                reviewer_slot=slot,
                reviewer_name=name,
                reviewer_role=role,
                code=code,
                presence="NO",
                depth=0,
                execution_mode="CALIBRATION",
                locator="p. 1",
            )
            assert saved["execution_mode"] == "CALIBRATION"

    for slot, name, role, depth, evidence in (
        ("REVIEWER_1", "R1", R1_ROLE, 1, "Explicit adequacy objective."),
        ("REVIEWER_2", "R2", R2_ROLE, 2, "Actionable adequacy criterion."),
    ):
        revised = runtime.submit_article1_abcd(
            db,
            session_id=session_id,
            document_id=document_id,
            reviewer_slot=slot,
            reviewer_name=name,
            reviewer_role=role,
            code="A1",
            presence="YES",
            depth=depth,
            execution_mode="CALIBRATION",
            evidence=evidence,
            locator="p. 2",
            family="GUIDE",
        )
        assert revised["revision"] == 2

    comparison = runtime.compare_article1_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="CALIBRATION",
    )
    assert len(comparison) == 34
    assert next(row for row in comparison if row["code"] == "A1")["status"] == "DIVERGENT"
    assert all(row["status"] == "AGREED" for row in comparison if row["code"] != "A1")

    report = runtime.article1_abcd_calibration_report(
        db,
        session_id=session_id,
        document_ids=[document_id],
    )
    assert report["execution_mode"] == "CALIBRATION"
    assert report["completeness"] == 1.0
    assert report["presence_raw_agreement"] == 1.0
    assert report["depth_denominator_both_yes"] == 1
    assert report["exact_depth_agreement"] == 0.0
    assert report["depth_within_one_agreement"] == 1.0

    adjudication = runtime.adjudicate_article1_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        code="A1",
        final_presence="YES",
        final_depth=2,
        adjudicator_name="Calibration adjudicator",
        adjudicator_role=ADJ_ROLE,
        execution_mode="CALIBRATION",
        evidence="Resolved explicit adequacy criterion.",
        notes="calibration resolution",
    )
    assert adjudication["execution_mode"] == "CALIBRATION"
    final_rows = runtime.final_article1_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="CALIBRATION",
    )
    assert len(final_rows) == 34
    assert next(row for row in final_rows if row["code"] == "A1")["depth"] == 2


def test_relations_calibration_evidence_completion_and_adjudication(tmp_path: Path):
    db = tmp_path / "relations.sqlite3"
    session_id = _session(db)
    document_id = "relation-calibration-doc"

    for slot, name, role in (
        ("REVIEWER_1", "R1", R1_ROLE),
        ("REVIEWER_2", "R2", R2_ROLE),
    ):
        saved = runtime.submit_article1_relation(
            db,
            session_id=session_id,
            document_id=document_id,
            reviewer_slot=slot,
            reviewer_name=name,
            reviewer_role=role,
            source_code="A1",
            target_code="D5",
            direction="SOURCE_TO_TARGET",
            relation_type="MONITORS",
            evidence_instances=[
                {"locator": "p. 4", "evidence": "The objective is monitored at reassessment."},
                {"locator": "p. 7", "evidence": "Monitoring determines reassessment."},
            ],
            execution_mode="CALIBRATION",
            family="GUIDE",
        )
        assert len(saved["evidence_instances"]) == 2

    extra = runtime.submit_article1_relation(
        db,
        session_id=session_id,
        document_id=document_id,
        reviewer_slot="REVIEWER_1",
        reviewer_name="R1",
        reviewer_role=R1_ROLE,
        source_code="C8",
        target_code="D3",
        direction="SOURCE_TO_TARGET",
        relation_type="MODIFIES",
        evidence_instances=[
            {"locator": "p. 8", "evidence": "Execution burden modifies progression."}
        ],
        execution_mode="CALIBRATION",
    )
    assert extra["active"] is True

    for slot, name, role in (
        ("REVIEWER_1", "R1", R1_ROLE),
        ("REVIEWER_2", "R2", R2_ROLE),
    ):
        done = runtime.complete_article1_relation_review(
            db,
            session_id=session_id,
            document_id=document_id,
            reviewer_slot=slot,
            reviewer_name=name,
            reviewer_role=role,
            execution_mode="CALIBRATION",
        )
        assert done["complete"] is True

    comparison = runtime.compare_article1_relations(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="CALIBRATION",
    )
    agreed = next(row for row in comparison if row["relation_key"].startswith("A1|D5"))
    divergent = next(row for row in comparison if row["relation_key"].startswith("C8|D3"))
    assert agreed["final_status"] == "AGREED"
    assert len(agreed["final"]["evidence_instances"]) == 4
    assert divergent["final_status"] == "PENDING"

    report = runtime.article1_relation_calibration_report(
        db,
        session_id=session_id,
        document_ids=[document_id],
        conceptual_error_flags=["origin-target boundary"],
    )
    assert report["review_completeness"] == 1.0
    assert report["reviewer_1_relations"] == 2
    assert report["reviewer_2_relations"] == 1
    assert report["intersection"] == 1
    assert report["union"] == 2
    assert report["jaccard_descriptive"] == 0.5
    assert report["requires_rule_review"] is True

    adjudication = runtime.adjudicate_article1_relation(
        db,
        session_id=session_id,
        document_id=document_id,
        relation_key=divergent["relation_key"],
        final_decision="EXCLUDE",
        adjudicator_name="Calibration adjudicator",
        adjudicator_role=ADJ_ROLE,
        notes="R1 inferred more than the source states.",
        execution_mode="CALIBRATION",
    )
    assert adjudication["final_decision"] == "EXCLUDE"
    final = runtime.final_article1_relations(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="CALIBRATION",
    )
    assert len(final) == 1
    assert final[0]["relation_key"].startswith("A1|D5")


def test_execution_mode_isolation_keeps_staging_out_of_calibration(tmp_path: Path):
    db = tmp_path / "modes.sqlite3"
    session_id = _session(db)
    document_id = "mode-doc"
    runtime.submit_article1_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        reviewer_slot="REVIEWER_1",
        reviewer_name="R1",
        reviewer_role=R1_ROLE,
        code="A1",
        presence="NO",
        depth=0,
        execution_mode="CALIBRATION",
    )
    runtime.submit_article1_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        reviewer_slot="REVIEWER_1",
        reviewer_name="R1",
        reviewer_role=R1_ROLE,
        code="A1",
        presence="YES",
        depth=3,
        execution_mode="STAGING",
        evidence="Staging-only evidence.",
    )
    calibration = runtime._latest_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="CALIBRATION",
    )
    staging = runtime._latest_abcd(
        db,
        session_id=session_id,
        document_id=document_id,
        execution_mode="STAGING",
    )
    assert calibration[0]["presence"] == "NO"
    assert staging[0]["presence"] == "YES"


def test_synthesis_separates_components_cooccurrence_and_explicit_relations(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "_article1_included_documents",
        lambda *args, **kwargs: [
            {"document_id": "d1", "family": "GUIDE"},
            {"document_id": "d2", "family": "GUIDE"},
        ],
    )
    monkeypatch.setattr(
        runtime,
        "article1_runtime_status",
        lambda *args, **kwargs: {
            "session_id": "s",
            "execution_mode": "FORMAL",
            "included_documents": 2,
            "documents": [],
            "synthesis_ready": True,
            "codebook_version": "ABCD-v1.1-candidate",
        },
    )

    def fake_abcd(_db_path, *, session_id, document_id, execution_mode="FORMAL"):
        assert execution_mode == "FORMAL"
        rows = [{"code": code, "presence": "NO", "depth": 0} for code in ABCD_CODES]
        rows[0] = {"code": "A1", "presence": "YES", "depth": 2}
        if document_id == "d1":
            rows[5] = {"code": "B1", "presence": "YES", "depth": 1}
        return rows

    monkeypatch.setattr(runtime, "final_article1_abcd", fake_abcd)
    monkeypatch.setattr(
        runtime,
        "final_article1_relations",
        lambda _db_path, *, session_id, document_id, execution_mode="FORMAL": (
            [{
                "relation_key": "A1|B1|SOURCE_TO_TARGET|SUPPORTS",
                "source_code": "A1",
                "target_code": "B1",
                "direction": "SOURCE_TO_TARGET",
                "relation_type": "SUPPORTS",
            }]
            if document_id == "d1"
            else []
        ),
    )
    monkeypatch.setattr(runtime, "_latest_method_characterization", lambda *args, **kwargs: [])

    result = runtime.article1_synthesis(tmp_path / "unused.sqlite3", session_id="s")
    a1 = next(row for row in result["components"] if row["code"] == "A1")
    assert result["ready"] is True
    assert a1["yes"] == 2 and a1["depth_2"] == 2
    assert result["cooccurrence"] == [{
        "family": "GUIDE",
        "source_code": "A1",
        "target_code": "B1",
        "documents_with_cooccurrence": 1,
    }]
    assert result["explicit_relations"][0]["documents_with_explicit_relation"] == 1
    assert result["guardrails"]["global_abcd_score"] is False
    assert result["guardrails"]["cooccurrence_is_relation"] is False


def test_final_relation_set_requires_explicit_review_completion(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "_latest_relation_review_status",
        lambda *args, **kwargs: {"REVIEWER_1": True, "REVIEWER_2": False},
    )
    with pytest.raises(ValueError, match="both reviewers"):
        runtime.final_article1_relations(
            tmp_path / "unused.sqlite3",
            session_id="s",
            document_id="d",
        )
