from __future__ import annotations

from pathlib import Path

import pytest

from nutev.review import article1_screening_runtime as screening
from nutev.review.article1_runtime import set_article1_reviewer_assignment
from nutev.review.article_screening import ensure_screening_session
from nutev.search.base import ProviderResult
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import default_registry_path, save_strategy_version


def _context(tmp_path: Path, *, suffix: str = "dual") -> tuple[Path, str, list[str]]:
    registry = default_registry_path(tmp_path)
    version = save_strategy_version(
        registry,
        title=f"Article 1 dual screening {suffix}",
        query_text="lifestyle nutrition",
        strategy_payload={
            "article_scope": "all_articles",
            "query": ["lifestyle nutrition"],
            "filters": {},
            "providers": {"pubmed": {"specific": "lifestyle nutrition[tiab]"}},
        },
        search_type="PILOT",
        created_by="test",
    )

    records = [
        {
            "title": "Guideline one",
            "pmid": "9001",
            "year": 2025,
            "abstract": "Lifestyle nutrition guideline for clinical care.",
        },
        {
            "title": "Guideline two",
            "pmid": "9002",
            "year": 2024,
            "abstract": "Nutrition and lifestyle recommendations.",
        },
    ]

    def fake_search(**kwargs):
        return ProviderResult(
            provider="pubmed",
            query=kwargs["query"],
            rows=records,
            total_found=len(records),
            total_returned=len(records),
            status="completed",
        )

    run_id = f"screen_runtime_{suffix}"
    execute_strategy_version(
        tmp_path,
        registry_path=registry,
        version_id=version.version_id,
        breadth="specific",
        providers=["pubmed"],
        limit=10,
        search_fn=fake_search,
        run_id=run_id,
    )
    build = build_corpus_from_search_run(
        tmp_path,
        registry_path=registry,
        run_id=run_id,
        build_id=f"build_{suffix}",
    )
    session = ensure_screening_session(
        registry,
        build_id=build["build_id"],
        protocol_version=screening.ARTICLE1_FORMAL_PROTOCOL_VERSION,
        created_by="test",
    )
    screening.initialize_article1_screening_runtime(registry)
    set_article1_reviewer_assignment(
        registry,
        session_id=session["session_id"],
        reviewer_1_name="Reviewer One",
        reviewer_2_name="Reviewer Two",
        adjudicator_name="Adjudicator",
    )
    document_ids = [row["document_id"] for row in screening.title_abstract_queue(registry, session_id=session["session_id"])]
    return registry, str(session["session_id"]), document_ids


def test_title_abstract_preserves_doubt_but_advances_when_both_operationally_advance(tmp_path: Path) -> None:
    db, session_id, documents = _context(tmp_path, suffix="doubt")
    document_id = documents[0]

    screening.submit_screening_decision(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
        reviewer_slot="REVIEWER_1",
        reviewer_name="Reviewer One",
        decision="INCLUDE",
    )
    screening.submit_screening_decision(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
        reviewer_slot="REVIEWER_2",
        reviewer_name="Reviewer Two",
        decision="DOUBT",
    )

    result = screening.screening_record_resolution(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
    )
    assert result["status"] == "RESOLVED_ADVANCE"
    assert result["final_action"] == "ADVANCE"
    assert result["reviewer_1"]["decision"] == "INCLUDE"
    assert result["reviewer_2"]["decision"] == "DOUBT"
    assert result["requires_adjudication"] is False


def test_title_conflict_requires_real_adjudication_and_identity(tmp_path: Path) -> None:
    db, session_id, documents = _context(tmp_path, suffix="title_conflict")
    document_id = documents[0]
    for slot, reviewer, decision in (
        ("REVIEWER_1", "Reviewer One", "INCLUDE"),
        ("REVIEWER_2", "Reviewer Two", "EXCLUDE"),
    ):
        screening.submit_screening_decision(
            db,
            session_id=session_id,
            document_id=document_id,
            phase="TITLE_ABSTRACT",
            reviewer_slot=slot,
            reviewer_name=reviewer,
            decision=decision,
            exclusion_reason="out_of_scope" if decision == "EXCLUDE" else "",
        )
    before = screening.screening_record_resolution(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
    )
    assert before["status"] == "PENDING_ADJUDICATION"
    assert before["requires_adjudication"] is True
    with pytest.raises(ValueError, match="adjudicator identity"):
        screening.adjudicate_screening(
            db,
            session_id=session_id,
            document_id=document_id,
            phase="TITLE_ABSTRACT",
            final_decision="INCLUDE",
            adjudicator_name="Wrong person",
            rationale="No",
        )
    screening.adjudicate_screening(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
        final_decision="INCLUDE",
        adjudicator_name="Adjudicator",
        rationale="Scope resolved against the protocol.",
    )
    after = screening.screening_record_resolution(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="TITLE_ABSTRACT",
    )
    assert after["status"] == "ADJUDICATED_INCLUDE"
    assert after["final_action"] == "ADVANCE"


def test_full_text_family_divergence_requires_adjudication_and_final_inclusion(tmp_path: Path) -> None:
    db, session_id, documents = _context(tmp_path, suffix="family")
    document_id = documents[0]
    # First resolve title/abstract for this document.
    for slot, reviewer in (("REVIEWER_1", "Reviewer One"), ("REVIEWER_2", "Reviewer Two")):
        screening.submit_screening_decision(
            db,
            session_id=session_id,
            document_id=document_id,
            phase="TITLE_ABSTRACT",
            reviewer_slot=slot,
            reviewer_name=reviewer,
            decision="INCLUDE",
        )
    # FULL_TEXT INCLUDE agrees on eligibility but not documentary family.
    screening.submit_screening_decision(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="FULL_TEXT",
        reviewer_slot="REVIEWER_1",
        reviewer_name="Reviewer One",
        decision="INCLUDE",
        family="GUIDELINE",
    )
    screening.submit_screening_decision(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="FULL_TEXT",
        reviewer_slot="REVIEWER_2",
        reviewer_name="Reviewer Two",
        decision="INCLUDE",
        family="CONSENSUS",
    )
    pending = screening.screening_record_resolution(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="FULL_TEXT",
    )
    assert pending["status"] == "PENDING_ADJUDICATION"

    screening.adjudicate_screening(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="FULL_TEXT",
        final_decision="INCLUDE",
        final_family="GUIDELINE",
        adjudicator_name="Adjudicator",
        rationale="Document family resolved from the issuing body and document type.",
    )
    resolved = screening.screening_record_resolution(
        db,
        session_id=session_id,
        document_id=document_id,
        phase="FULL_TEXT",
    )
    assert resolved["final_decision"] == "INCLUDE"
    assert resolved["final_family"] == "GUIDELINE"

    included = screening.canonical_article1_included(db, session_id)
    assert [row["document_id"] for row in included] == [document_id]
    assert included[0]["family"] == "GUIDELINE"
    assert included[0]["screening_basis"] == "ARTICLE1_DUAL_REVIEW"


def test_reviewer_slot_cannot_be_impersonated_and_status_remains_human(tmp_path: Path) -> None:
    db, session_id, documents = _context(tmp_path, suffix="identity")
    with pytest.raises(ValueError, match="reviewer identity"):
        screening.submit_screening_decision(
            db,
            session_id=session_id,
            document_id=documents[0],
            phase="TITLE_ABSTRACT",
            reviewer_slot="REVIEWER_1",
            reviewer_name="Reviewer Two",
            decision="INCLUDE",
        )
    status = screening.formal_screening_status(db, session_id=session_id)
    assert status["phase"] == "TITLE_ABSTRACT_HUMAN_REVIEW"
    assert status["title_abstract"]["pending"] == 2
    assert status["human_decision_inferred"] is False
