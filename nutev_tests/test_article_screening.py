from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nutev.review.article_screening import (
    article_screening_queue,
    duplicate_review_queue,
    effective_master_records,
    ensure_screening_session,
    export_screening_snapshot,
    save_article_screening_decision,
    save_duplicate_review,
    summarize_screening_session,
)
from nutev.review.article_screening_ledger import (
    list_article_catalog,
    list_latest_article_screening_decisions,
    list_screening_exports,
)
from nutev.search.base import ProviderResult
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import (
    default_registry_path,
    save_strategy_version,
)


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["lifestyle nutrition"],
        "filters": {},
        "providers": {
            "pubmed": {"specific": "lifestyle nutrition[tiab]"},
            "openalex": {"specific": 'query="lifestyle nutrition"'},
        },
    }


def _build(
    tmp_path: Path,
    *,
    rows_by_provider: dict[str, list[dict]],
    search_type: str = "FORMAL",
    suffix: str = "one",
):
    registry = default_registry_path(tmp_path)
    version = save_strategy_version(
        registry,
        title=f"Screening {suffix}",
        query_text="lifestyle nutrition",
        strategy_payload=_payload(),
        search_type=search_type,
        created_by="Researcher",
        created_at="2026-08-04T19:00:00-03:00",
    )

    def fake_search(**kwargs):
        rows = list(rows_by_provider.get(kwargs["provider"], []))
        return ProviderResult(
            provider=kwargs["provider"],
            query=kwargs["query"],
            rows=rows,
            total_found=len(rows),
            total_returned=len(rows),
            status="completed",
        )

    run_id = f"run_screening_{suffix}"
    execute_strategy_version(
        tmp_path,
        registry_path=registry,
        version_id=version.version_id,
        breadth="specific",
        providers=list(rows_by_provider),
        limit=50,
        search_fn=fake_search,
        run_id=run_id,
        started_at="2026-08-04T19:10:00-03:00",
    )
    build_id = f"build_screening_{suffix}"
    build = build_corpus_from_search_run(
        tmp_path,
        registry_path=registry,
        run_id=run_id,
        build_id=build_id,
        started_at="2026-08-04T19:20:00-03:00",
    )
    session = ensure_screening_session(
        registry,
        build_id=build_id,
        created_by="Researcher",
    )
    return registry, build, session


def test_catalog_has_five_articles_and_document_can_serve_multiple_articles(
    tmp_path,
):
    registry, _, session = _build(
        tmp_path,
        rows_by_provider={
            "pubmed": [
                {
                    "title": "Shared evidence",
                    "pmid": "101",
                    "year": 2025,
                    "abstract": "Relevant to more than one manuscript.",
                }
            ]
        },
        suffix="multi",
    )
    articles = list_article_catalog(registry)
    assert [row["article_id"] for row in articles] == [
        "article_1",
        "article_2",
        "article_3",
        "article_4",
        "article_5",
    ]
    document = article_screening_queue(
        registry,
        session_id=session["session_id"],
        article_id="article_1",
    )[0]
    for article_id in ("article_1", "article_3"):
        save_article_screening_decision(
            registry,
            session_id=session["session_id"],
            document_id=document["document_id"],
            article_id=article_id,
            decision="INCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )

    summary = summarize_screening_session(
        registry,
        session_id=session["session_id"],
    )
    by_article = {row["article_id"]: row for row in summary["articles"]}
    assert by_article["article_1"]["records_included"] == 1
    assert by_article["article_3"]["records_included"] == 1
    assert by_article["article_2"]["records_pending"] == 1


def test_exclusion_requires_reason_and_decisions_are_append_only_revisions(
    tmp_path,
):
    registry, _, session = _build(
        tmp_path,
        rows_by_provider={
            "pubmed": [{"title": "Candidate", "pmid": "102", "year": 2024}]
        },
        suffix="revisions",
    )
    document_id = article_screening_queue(
        registry,
        session_id=session["session_id"],
        article_id="article_2",
    )[0]["document_id"]

    with pytest.raises(ValueError, match="exclusion_reason"):
        save_article_screening_decision(
            registry,
            session_id=session["session_id"],
            document_id=document_id,
            article_id="article_2",
            decision="EXCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )
    with pytest.raises(ValueError, match="notes are required"):
        save_article_screening_decision(
            registry,
            session_id=session["session_id"],
            document_id=document_id,
            article_id="article_2",
            decision="EXCLUDE",
            exclusion_reason="OTHER",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )

    first = save_article_screening_decision(
        registry,
        session_id=session["session_id"],
        document_id=document_id,
        article_id="article_2",
        decision="EXCLUDE",
        exclusion_reason="WRONG_CONTEXT",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    second = save_article_screening_decision(
        registry,
        session_id=session["session_id"],
        document_id=document_id,
        article_id="article_2",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Revised after calibration.",
    )
    assert first["revision"] == 1
    assert second["revision"] == 2
    latest = list_latest_article_screening_decisions(
        registry,
        session_id=session["session_id"],
        article_id="article_2",
    )
    assert len(latest) == 1
    assert latest[0]["decision"] == "INCLUDE"
    assert latest[0]["revision"] == 2


def test_confirmed_human_duplicate_changes_effective_corpus_and_prisma(tmp_path):
    registry, _, session = _build(
        tmp_path,
        rows_by_provider={
            "openalex": [
                {
                    "title": "Same title candidate",
                    "url": "https://example.org/a",
                    "year": 2023,
                    "abstract": "A",
                },
                {
                    "title": "Same title candidate",
                    "url": "https://example.org/b",
                    "year": 2023,
                    "abstract": "B",
                },
            ]
        },
        suffix="human_dedup",
    )
    candidates = duplicate_review_queue(
        registry,
        session_id=session["session_id"],
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    retained = candidate["left_document_id"]
    save_duplicate_review(
        registry,
        session_id=session["session_id"],
        candidate_id=candidate["candidate_id"],
        decision="CONFIRMED_DUPLICATE",
        retained_document_id=retained,
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        notes="Same report with alternate landing pages.",
    )
    effective, mapping = effective_master_records(
        registry,
        session_id=session["session_id"],
    )
    assert len(effective) == 1
    assert list(mapping.values()) == [retained]

    save_article_screening_decision(
        registry,
        session_id=session["session_id"],
        document_id=retained,
        article_id="article_1",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    summary = summarize_screening_session(
        registry,
        session_id=session["session_id"],
    )
    article_1 = next(
        row for row in summary["articles"] if row["article_id"] == "article_1"
    )
    assert summary["human_duplicates_removed"] == 1
    assert summary["effective_documents"] == 1
    assert article_1["records_included"] == 1
    assert article_1["prisma_reports_sought_for_retrieval"] == 1

    exported = export_screening_snapshot(
        registry,
        session_id=session["session_id"],
        export_id="screening_export_test",
        created_at="2026-08-04T19:40:00-03:00",
    )
    assert Path(exported["paths"]["manifest_path"]).exists()
    with Path(exported["paths"]["queue_csv_path"]).open(
        encoding="utf-8", newline=""
    ) as handle:
        queue_rows = list(csv.DictReader(handle))
    assert len(queue_rows) == 5
    assert len(list_screening_exports(registry, session_id=session["session_id"])) == 1


def test_duplicate_must_be_resolved_before_screening_removed_document(tmp_path):
    registry, _, session = _build(
        tmp_path,
        rows_by_provider={
            "openalex": [
                {"title": "Pair", "url": "https://example.org/1", "year": 2022},
                {"title": "Pair", "url": "https://example.org/2", "year": 2022},
            ]
        },
        suffix="guard",
    )
    candidate = duplicate_review_queue(
        registry,
        session_id=session["session_id"],
    )[0]
    removed = candidate["right_document_id"]
    retained = candidate["left_document_id"]
    save_article_screening_decision(
        registry,
        session_id=session["session_id"],
        document_id=removed,
        article_id="article_1",
        decision="MAYBE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    with pytest.raises(ValueError, match="before screening"):
        save_duplicate_review(
            registry,
            session_id=session["session_id"],
            candidate_id=candidate["candidate_id"],
            decision="CONFIRMED_DUPLICATE",
            retained_document_id=retained,
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )


def test_pilot_screening_is_preserved_but_prisma_columns_are_zero(tmp_path):
    registry, _, session = _build(
        tmp_path,
        rows_by_provider={
            "pubmed": [{"title": "Pilot", "pmid": "103", "year": 2024}]
        },
        search_type="PILOT",
        suffix="pilot",
    )
    document_id = article_screening_queue(
        registry,
        session_id=session["session_id"],
        article_id="article_5",
    )[0]["document_id"]
    save_article_screening_decision(
        registry,
        session_id=session["session_id"],
        document_id=document_id,
        article_id="article_5",
        decision="INCLUDE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
    )
    summary = summarize_screening_session(
        registry,
        session_id=session["session_id"],
    )
    article_5 = next(
        row for row in summary["articles"] if row["article_id"] == "article_5"
    )
    assert summary["prisma_eligible"] is False
    assert article_5["records_included"] == 1
    assert article_5["prisma_records_screened"] == 0
    assert article_5["prisma_reports_sought_for_retrieval"] == 0


def test_tampered_master_corpus_blocks_screening_session(tmp_path):
    registry, build, session = _build(
        tmp_path,
        rows_by_provider={
            "pubmed": [{"title": "Integrity", "pmid": "104", "year": 2024}]
        },
        suffix="integrity",
    )
    master_path = Path(build["master_jsonl_path"])
    master_path.write_text(
        master_path.read_text(encoding="utf-8") + "{}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="master corpus checksum mismatch"):
        ensure_screening_session(
            registry,
            build_id=session["build_id"],
        )
