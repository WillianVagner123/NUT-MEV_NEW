from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from nutev.review.article_screening import (
    ensure_screening_session,
    save_article_screening_decision,
)
from nutev.review.full_text_assessment import (
    export_full_text_snapshot,
    full_text_assessment_queue,
    full_text_retrieval_queue,
    save_full_text_eligibility_decision,
    save_full_text_retrieval,
    summarize_full_text_assessment,
)
from nutev.review.full_text_assessment_ledger import (
    list_latest_full_text_eligibility_decisions,
    list_latest_full_text_retrievals,
)
from nutev.search.base import ProviderResult
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import default_registry_path, save_strategy_version


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food competence"],
        "filters": {},
        "providers": {
            "pubmed": {"specific": "food competence[tiab]"},
        },
    }


def _build_session(tmp_path: Path, *, search_type: str = "FORMAL") -> tuple[str, list[dict]]:
    registry = default_registry_path(tmp_path)
    version = save_strategy_version(
        registry,
        title=f"Full text {search_type}",
        query_text="food competence",
        strategy_payload=_payload(),
        search_type=search_type,
        created_by="Researcher",
        created_at="2026-08-04T20:00:00-03:00",
    )

    rows = [
        {
            "title": "Competence paper",
            "doi": "10.1000/competence",
            "pmid": "12345",
            "url": "https://example.org/competence",
            "year": 2024,
            "abstract": "A study about food competence and outcomes.",
        },
        {
            "title": "Second paper",
            "doi": "10.1000/second",
            "url": "https://example.org/second",
            "year": 2023,
            "abstract": "A second potentially eligible report.",
        },
    ]

    def fake_search(**kwargs):
        return ProviderResult(
            provider=kwargs["provider"],
            query=kwargs["query"],
            rows=rows,
            total_found=len(rows),
            total_returned=len(rows),
            status="completed",
        )

    execute_strategy_version(
        tmp_path,
        registry_path=registry,
        version_id=version.version_id,
        breadth="specific",
        providers=["pubmed"],
        limit=20,
        resume=False,
        search_fn=fake_search,
        run_id=f"run_full_text_{search_type.lower()}",
        started_at="2026-08-04T20:05:00-03:00",
    )
    build = build_corpus_from_search_run(
        tmp_path,
        registry_path=registry,
        run_id=f"run_full_text_{search_type.lower()}",
        build_id=f"build_full_text_{search_type.lower()}",
        started_at="2026-08-04T20:10:00-03:00",
    )
    session = ensure_screening_session(
        registry,
        build_id=str(build["build_id"]),
        protocol_version="v1",
        created_by="Researcher",
    )
    master_rows = [
        json.loads(line)
        for line in Path(build["master_jsonl_path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    return str(session["session_id"]), master_rows


def _screen(
    tmp_path: Path,
    session_id: str,
    document_id: str,
    article_id: str,
    decision: str = "INCLUDE",
) -> None:
    save_article_screening_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
        decision=decision,
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        stage="TITLE_ABSTRACT",
    )


def test_retrieval_once_and_independent_eligibility_per_article(tmp_path):
    session_id, rows = _build_session(tmp_path)
    document_id = str(rows[0]["document_id"])
    _screen(tmp_path, session_id, document_id, "article_1", "INCLUDE")
    _screen(tmp_path, session_id, document_id, "article_2", "MAYBE")

    queue = full_text_retrieval_queue(
        default_registry_path(tmp_path),
        session_id=session_id,
    )
    assert len(queue) == 1
    assert set(queue[0]["target_article_ids"].split("|")) == {
        "article_1",
        "article_2",
    }

    artifact = tmp_path / "paper.pdf"
    artifact.write_bytes(b"%PDF-1.4\nsynthetic test artifact\n")
    retrieval = save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="AVAILABLE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        artifact_path=str(artifact),
        source_url="https://example.org/competence.pdf",
    )
    assert retrieval["revision"] == 1
    assert retrieval["artifact_sha256"]

    first = save_full_text_eligibility_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    second = save_full_text_eligibility_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id="article_2",
        decision="EXCLUDE",
        exclusion_reason="WRONG_OUTCOME",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="The outcome does not answer Article 2.",
    )
    assert first["decision"] == "INCLUDE"
    assert second["decision"] == "EXCLUDE"

    summary = summarize_full_text_assessment(
        default_registry_path(tmp_path),
        session_id=session_id,
    )
    assert summary["distinct_reports_sought"] == 1
    assert summary["distinct_reports_retrieved"] == 1
    assert summary["distinct_documents_included"] == 1
    by_article = {row["article_id"]: row for row in summary["articles"]}
    assert by_article["article_1"]["reports_included"] == 1
    assert by_article["article_2"]["reports_excluded_at_full_text"] == 1
    assert by_article["article_2"]["full_text_exclusion_reasons"] == {
        "WRONG_OUTCOME": 1
    }

    exported = export_full_text_snapshot(
        default_registry_path(tmp_path),
        session_id=session_id,
        export_id="full_text_export_test",
        created_at="2026-08-04T20:30:00-03:00",
    )
    assert Path(exported["manifest_path"]).exists()
    assert Path(exported["included_csv_path"]).exists()


def test_not_retrieved_counts_and_blocks_eligibility(tmp_path):
    session_id, rows = _build_session(tmp_path)
    document_id = str(rows[0]["document_id"])
    _screen(tmp_path, session_id, document_id, "article_1")

    save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="PAYWALLED",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Institutional access and author contact were unsuccessful.",
    )
    queue = full_text_assessment_queue(
        default_registry_path(tmp_path),
        session_id=session_id,
        article_id="article_1",
    )
    assert queue[0]["full_text_status"] == "NOT_RETRIEVED"
    with pytest.raises(ValueError, match="AVAILABLE"):
        save_full_text_eligibility_decision(
            default_registry_path(tmp_path),
            session_id=session_id,
            document_id=document_id,
            article_id="article_1",
            decision="INCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )

    summary = summarize_full_text_assessment(
        default_registry_path(tmp_path),
        session_id=session_id,
    )
    article = next(row for row in summary["articles"] if row["article_id"] == "article_1")
    assert article["reports_sought_for_retrieval"] == 1
    assert article["reports_not_retrieved"] == 1
    assert article["reports_assessed_for_eligibility"] == 0


def test_revisions_are_append_only_and_other_requires_notes(tmp_path):
    session_id, rows = _build_session(tmp_path)
    document_id = str(rows[0]["document_id"])
    _screen(tmp_path, session_id, document_id, "article_1")

    requested = save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="REQUESTED",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Requested from the corresponding author.",
    )
    available = save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="AVAILABLE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        source_url="https://example.org/full-text",
    )
    assert requested["revision"] == 1
    assert available["revision"] == 2
    latest = list_latest_full_text_retrievals(
        default_registry_path(tmp_path),
        session_id=session_id,
    )
    assert latest[0]["status"] == "AVAILABLE"
    assert latest[0]["revision"] == 2

    with pytest.raises(ValueError, match="notes are required"):
        save_full_text_eligibility_decision(
            default_registry_path(tmp_path),
            session_id=session_id,
            document_id=document_id,
            article_id="article_1",
            decision="EXCLUDE",
            exclusion_reason="OTHER",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )

    first = save_full_text_eligibility_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        decision="EXCLUDE",
        exclusion_reason="WRONG_STUDY_DESIGN",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Editorial rather than empirical study.",
    )
    second = save_full_text_eligibility_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Revised after adjudication.",
    )
    assert first["revision"] == 1
    assert second["revision"] == 2
    latest_decisions = list_latest_full_text_eligibility_decisions(
        default_registry_path(tmp_path),
        session_id=session_id,
        article_id="article_1",
    )
    assert latest_decisions[0]["decision"] == "INCLUDE"
    assert latest_decisions[0]["revision"] == 2

    with sqlite3.connect(default_registry_path(tmp_path)) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM full_text_eligibility_decisions WHERE session_id = ?",
            (session_id,),
        ).fetchone()[0]
    assert count == 2


def test_tampered_local_artifact_blocks_decision_and_export(tmp_path):
    session_id, rows = _build_session(tmp_path)
    document_id = str(rows[0]["document_id"])
    _screen(tmp_path, session_id, document_id, "article_1")
    artifact = tmp_path / "tamper.pdf"
    artifact.write_bytes(b"original")
    save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="AVAILABLE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        artifact_path=str(artifact),
    )
    artifact.write_bytes(b"modified")

    with pytest.raises(ValueError, match="integrity is mismatch"):
        save_full_text_eligibility_decision(
            default_registry_path(tmp_path),
            session_id=session_id,
            document_id=document_id,
            article_id="article_1",
            decision="INCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )
    with pytest.raises(ValueError, match="integrity is mismatch"):
        export_full_text_snapshot(
            default_registry_path(tmp_path),
            session_id=session_id,
        )


def test_pilot_full_text_is_auditable_but_prisma_columns_are_zero(tmp_path):
    session_id, rows = _build_session(tmp_path, search_type="PILOT")
    document_id = str(rows[0]["document_id"])
    _screen(tmp_path, session_id, document_id, "article_1")
    save_full_text_retrieval(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        status="AVAILABLE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        source_url="https://example.org/full-text",
    )
    save_full_text_eligibility_decision(
        default_registry_path(tmp_path),
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    summary = summarize_full_text_assessment(
        default_registry_path(tmp_path),
        session_id=session_id,
    )
    article = next(row for row in summary["articles"] if row["article_id"] == "article_1")
    assert article["reports_included"] == 1
    assert article["prisma_reports_sought_for_retrieval"] == 0
    assert article["prisma_studies_included"] == 0
