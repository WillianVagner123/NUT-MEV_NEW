"""Human review events must stay operational, append-only and auditable.

REVIEWED means a human read the document. It is never inclusion, exclusion, eligibility,
screening, risk of bias, certainty, recommendation or a PRISMA event.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

import human_review_store as review_store


def test_empty_store_reports_not_started_without_creating_a_database(tmp_path: Path) -> None:
    status = review_store.store_status(root=tmp_path)

    assert status["events"] == 0
    assert status["database_present"] is False
    assert status["append_only"] is True
    assert review_store.document_states(root=tmp_path) == {}
    assert review_store.derive_document_state([])["status"] == "NOT_STARTED"


def test_review_event_is_recorded_with_human_provenance(tmp_path: Path) -> None:
    result = review_store.append_event(
        document_id="doi:10.1000/a",
        reviewer_id="ana",
        status="REVIEWED",
        decision="READ",
        route="B-NORM",
        reason_text="Documento normativo lido integralmente.",
        root=tmp_path,
    )

    event = result["event"]
    assert event["status"] == "REVIEWED"
    assert event["provenance"]["human_event"] is True
    assert event["provenance"]["machine_generated_decision"] is False
    assert "not inclusion" in result["guardrail"]

    state = review_store.document_states(root=tmp_path)["doi:10.1000/a"]
    assert state["status"] == "REVIEWED"
    assert state["reviewers"][0]["reviewer_id"] == "ana"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "INCLUDED"},
        {"status": "EXCLUDED"},
        {"status": "ELIGIBLE"},
        {"status": "SCREENED_IN"},
        {"status": "REVIEWED", "decision": "INCLUDE"},
        {"status": "REVIEWED", "decision": "EXCLUDE"},
        {"status": "REVIEWED", "reason_code": "eligible_population"},
        {"status": "REVIEWED", "reason_code": "prisma_screening"},
        {"status": "REVIEWED", "reason_code": "risk_of_bias_high"},
        {"status": "REVIEWED", "reason_code": "certainty_low"},
    ],
)
def test_eligibility_and_prisma_vocabulary_is_rejected(tmp_path: Path, kwargs: dict) -> None:
    with pytest.raises(review_store.HumanReviewError):
        review_store.append_event(
            document_id="doi:10.1000/a",
            reviewer_id="ana",
            root=tmp_path,
            **kwargs,
        )
    assert review_store.store_status(root=tmp_path)["events"] == 0


def test_review_status_never_becomes_an_inclusion_state(tmp_path: Path) -> None:
    for status in review_store.REVIEW_STATUSES:
        assert "INCLUD" not in status
        assert "EXCLUD" not in status
        assert "ELIGIB" not in status
    for decision in review_store.REVIEW_DECISIONS:
        assert "INCLUD" not in decision
        assert "EXCLUD" not in decision


def test_corrections_supersede_instead_of_overwriting(tmp_path: Path) -> None:
    first = review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="ana", status="IN_REVIEW", root=tmp_path
    )["event"]
    second = review_store.append_event(
        document_id="doi:10.1000/a",
        reviewer_id="ana",
        status="REVIEWED",
        decision="READ",
        supersedes=first["review_id"],
        root=tmp_path,
    )["event"]

    events = review_store.document_events("doi:10.1000/a", root=tmp_path)
    assert [event["review_id"] for event in events] == [first["review_id"], second["review_id"]]

    state = review_store.derive_document_state(events)
    assert state["status"] == "REVIEWED"
    assert state["events"] == 2
    assert state["superseded_events"] == 1


def test_supersedes_must_reference_a_real_event_on_the_same_document(tmp_path: Path) -> None:
    existing = review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="ana", status="IN_REVIEW", root=tmp_path
    )["event"]

    with pytest.raises(review_store.HumanReviewError):
        review_store.append_event(
            document_id="doi:10.1000/a",
            reviewer_id="ana",
            status="REVIEWED",
            supersedes="review:does-not-exist",
            root=tmp_path,
        )
    with pytest.raises(review_store.HumanReviewError):
        review_store.append_event(
            document_id="doi:10.1000/b",
            reviewer_id="ana",
            status="REVIEWED",
            supersedes=existing["review_id"],
            root=tmp_path,
        )


def test_independent_reviewers_produce_a_conflict_until_adjudicated(tmp_path: Path) -> None:
    review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="ana", status="REVIEWED",
        decision="READ", root=tmp_path,
    )
    review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="bruno", status="REVIEWED",
        decision="NEEDS_FULL_TEXT", root=tmp_path,
    )
    conflicted = review_store.document_states(root=tmp_path)["doi:10.1000/a"]
    assert conflicted["status"] == "CONFLICT"
    assert conflicted["conflict"] is True
    assert len(conflicted["reviewers"]) == 2

    review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="carla", status="RESOLVED",
        stage="adjudication", reason_text="Adjudicado: leitura confirmada.", root=tmp_path,
    )
    resolved = review_store.document_states(root=tmp_path)["doi:10.1000/a"]
    assert resolved["status"] == "RESOLVED"
    # Both original reviewer positions stay readable: provenance is never dropped.
    assert {item["reviewer_id"] for item in resolved["reviewers"]} == {"ana", "bruno", "carla"}


def test_store_issues_no_update_or_delete_statements() -> None:
    source = (WEB / "human_review_store.py").read_text(encoding="utf-8")
    upper = source.upper()

    assert "UPDATE REVIEW_EVENTS" not in upper
    assert "DELETE FROM" not in upper
    assert "DROP TABLE" not in upper
    assert "INSERT INTO REVIEW_EVENTS" in upper


def test_stored_rows_are_never_mutated_on_disk(tmp_path: Path) -> None:
    first = review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="ana", status="IN_REVIEW", root=tmp_path
    )["event"]
    review_store.append_event(
        document_id="doi:10.1000/a", reviewer_id="ana", status="REVIEWED",
        decision="READ", supersedes=first["review_id"], root=tmp_path,
    )

    database = tmp_path / review_store.DATABASE_NAME
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT review_id, status FROM review_events ORDER BY created_at, review_id"
        ).fetchall()
    assert (first["review_id"], "IN_REVIEW") in rows
    assert len(rows) == 2
