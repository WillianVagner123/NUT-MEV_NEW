"""Append-only human review event log for Article 1 reading queues.

This store records *human operational review state* only. It is deliberately incapable of
expressing scientific inclusion, exclusion, eligibility, screening, risk of bias, certainty or
PRISMA events: that vocabulary is rejected at write time.

The log is append-only. A correction is a new event whose ``supersedes`` points at the event it
replaces; the superseded row stays readable so provenance is never lost. The module issues no
``UPDATE`` and no ``DELETE``, and it never writes to the Workbench database.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_REVIEW_ROOT = (
    REPO_ROOT / "project_output_reference" / "scientific" / "human_review" / "article1"
)
DATABASE_NAME = "human_review_events.sqlite"
STORE_VERSION = "nutev_article1_human_review_events_v1"

#: Operational human review states. REVIEWED means "a human has read it", never "included".
REVIEW_STATUSES: tuple[str, ...] = (
    "NOT_STARTED",
    "IN_REVIEW",
    "REVIEWED",
    "CONFLICT",
    "ADJUDICATION_REQUIRED",
    "RESOLVED",
)
WRITABLE_STATUSES = frozenset(REVIEW_STATUSES) - {"NOT_STARTED"}

#: Operational reading outcomes. None of these is an eligibility or screening decision.
REVIEW_DECISIONS: tuple[str, ...] = (
    "READ",
    "NEEDS_FULL_TEXT",
    "NEEDS_SECOND_REVIEWER",
    "OPERATIONAL_SIGNAL_CONFIRMED",
    "NO_OPERATIONAL_SIGNAL",
    "DEFER",
)
REVIEW_STAGES: tuple[str, ...] = (
    "route_reading",
    "domain_check",
    "full_text_check",
    "adjudication",
)
REVIEW_ROUTES: tuple[str, ...] = ("B-NORM", "C-STRUCT", "unrouted")

#: Vocabulary that would turn an operational reading state into a scientific decision.
FORBIDDEN_VOCABULARY: tuple[str, ...] = (
    "include",
    "included",
    "exclude",
    "excluded",
    "inclusion",
    "exclusion",
    "eligible",
    "eligibility",
    "ineligible",
    "screen_in",
    "screened_in",
    "screen_out",
    "screened_out",
    "screening_decision",
    "prisma",
    "risk_of_bias",
    "rob_",
    "certainty",
    "grade_certainty",
    "recommendation",
)
_TOKEN = re.compile(r"[a-z0-9_]+")

GUARDRAIL = (
    "Human operational review state only. REVIEWED means a human has read the document; it is not "
    "inclusion, exclusion, eligibility, screening, risk of bias, certainty, recommendation or a "
    "PRISMA event."
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id TEXT NOT NULL UNIQUE,
  document_id TEXT NOT NULL,
  reviewer_id TEXT NOT NULL,
  route TEXT,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  decision TEXT,
  reason_code TEXT,
  reason_text TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  supersedes TEXT,
  provenance_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS review_events_document ON review_events(document_id);
CREATE INDEX IF NOT EXISTS review_events_reviewer ON review_events(reviewer_id);
CREATE INDEX IF NOT EXISTS review_events_created ON review_events(created_at);
"""


class HumanReviewError(ValueError):
    """Raised when an event would violate the append-only or guardrail contract."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _database_path(root: Path | None) -> Path:
    base = Path(root) if root is not None else DEFAULT_REVIEW_ROOT
    return base / DATABASE_NAME


def _connect(root: Path | None, *, write: bool) -> sqlite3.Connection:
    path = _database_path(root)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.executescript(_SCHEMA)
    else:
        if not path.is_file():
            connection = sqlite3.connect(":memory:")
            connection.executescript(_SCHEMA)
            connection.row_factory = sqlite3.Row
            return connection
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _assert_operational(field: str, value: str) -> None:
    """Reject any wording that would make an operational state read as a scientific decision."""
    lowered = str(value or "").casefold()
    for token in _TOKEN.findall(lowered):
        for forbidden in FORBIDDEN_VOCABULARY:
            if token == forbidden.strip("_") or token.startswith(forbidden):
                raise HumanReviewError(
                    f"{field} may not carry eligibility/screening/PRISMA vocabulary: {value!r}. "
                    "Operational review state is not scientific inclusion."
                )


def _clean(value: object, *, limit: int = 400) -> str:
    return " ".join(str(value or "").split())[:limit]


def append_event(
    *,
    document_id: str,
    reviewer_id: str,
    status: str,
    stage: str = "route_reading",
    route: str = "",
    decision: str = "",
    reason_code: str = "",
    reason_text: str = "",
    supersedes: str = "",
    provenance: Mapping[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Append one human review event. Never updates or deletes an existing row."""
    document_id = _clean(document_id, limit=300)
    reviewer_id = _clean(reviewer_id, limit=120)
    if not document_id:
        raise HumanReviewError("document_id is required")
    if not reviewer_id:
        raise HumanReviewError("reviewer_id is required")

    status = _clean(status, limit=60).upper()
    if status not in WRITABLE_STATUSES:
        raise HumanReviewError(
            f"unknown review status: {status!r}. Allowed: {', '.join(sorted(WRITABLE_STATUSES))}"
        )
    stage = _clean(stage, limit=60) or "route_reading"
    if stage not in REVIEW_STAGES:
        raise HumanReviewError(f"unknown review stage: {stage!r}")
    route = _clean(route, limit=40)
    if route and route not in REVIEW_ROUTES:
        raise HumanReviewError(f"unknown review route: {route!r}")
    decision = _clean(decision, limit=60).upper()
    if decision and decision not in REVIEW_DECISIONS:
        raise HumanReviewError(
            f"unknown review decision: {decision!r}. Allowed: {', '.join(REVIEW_DECISIONS)}"
        )
    reason_code = _clean(reason_code, limit=80)
    reason_text = _clean(reason_text, limit=1200)
    supersedes = _clean(supersedes, limit=80)

    for field, value in (
        ("status", status),
        ("decision", decision),
        ("reason_code", reason_code),
    ):
        _assert_operational(field, value)

    timestamp = _now()
    review_id = f"review:{uuid4().hex}"
    record = {
        "review_id": review_id,
        "document_id": document_id,
        "reviewer_id": reviewer_id,
        "route": route or None,
        "stage": stage,
        "status": status,
        "decision": decision or None,
        "reason_code": reason_code or None,
        "reason_text": reason_text or None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "supersedes": supersedes or None,
        "provenance_json": json.dumps(
            {
                "store_version": STORE_VERSION,
                "recorded_by": "nutev-web review control center",
                "human_event": True,
                "machine_generated_decision": False,
                **(dict(provenance) if provenance else {}),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    }

    with _connect(root, write=True) as connection:
        if supersedes:
            existing = connection.execute(
                "SELECT review_id, document_id FROM review_events WHERE review_id = ?",
                (supersedes,),
            ).fetchone()
            if existing is None:
                raise HumanReviewError(f"supersedes references an unknown event: {supersedes!r}")
            if str(existing["document_id"]) != document_id:
                raise HumanReviewError("supersedes must reference an event on the same document")
        connection.execute(
            """
            INSERT INTO review_events (
              review_id, document_id, reviewer_id, route, stage, status, decision,
              reason_code, reason_text, created_at, updated_at, supersedes, provenance_json
            ) VALUES (
              :review_id, :document_id, :reviewer_id, :route, :stage, :status, :decision,
              :reason_code, :reason_text, :created_at, :updated_at, :supersedes, :provenance_json
            )
            """,
            record,
        )
        connection.commit()

    stored = dict(record)
    stored["provenance"] = json.loads(stored.pop("provenance_json"))
    return {"status": "recorded", "event": stored, "guardrail": GUARDRAIL}


def document_events(document_id: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    with _connect(root, write=False) as connection:
        rows = connection.execute(
            "SELECT * FROM review_events WHERE document_id = ? ORDER BY sequence ASC",
            (str(document_id),),
        ).fetchall()
    return [_row_payload(row) for row in rows]


def _row_payload(row: sqlite3.Row) -> dict[str, Any]:
    payload = {key: row[key] for key in row.keys() if key != "provenance_json"}
    try:
        payload["provenance"] = json.loads(row["provenance_json"])
    except (json.JSONDecodeError, TypeError):
        payload["provenance"] = {}
    return payload


def _superseded_ids(events: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(event["supersedes"]) for event in events if event.get("supersedes")}


def derive_document_state(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Derive the human review state of one document from its (append-only) event history."""
    if not events:
        return {
            "status": "NOT_STARTED",
            "reviewers": [],
            "conflict": False,
            "adjudication_required": False,
            "events": 0,
            "last_event_at": None,
        }
    superseded = _superseded_ids(events)
    live = [event for event in events if str(event["review_id"]) not in superseded]
    latest_by_reviewer: dict[str, Mapping[str, Any]] = {}
    for event in live:
        latest_by_reviewer[str(event["reviewer_id"])] = event

    resolved = any(event["status"] == "RESOLVED" for event in live)
    adjudication = any(event["status"] == "ADJUDICATION_REQUIRED" for event in live)
    decisions = {
        str(event["decision"])
        for event in latest_by_reviewer.values()
        if event.get("decision")
    }
    flagged_conflict = any(event["status"] == "CONFLICT" for event in live)
    conflict = flagged_conflict or (len(latest_by_reviewer) > 1 and len(decisions) > 1)

    if resolved:
        status = "RESOLVED"
    elif adjudication:
        status = "ADJUDICATION_REQUIRED"
    elif conflict:
        status = "CONFLICT"
    elif latest_by_reviewer and all(
        event["status"] == "REVIEWED" for event in latest_by_reviewer.values()
    ):
        status = "REVIEWED"
    else:
        status = "IN_REVIEW"

    return {
        "status": status,
        "reviewers": [
            {
                "reviewer_id": reviewer_id,
                "status": event["status"],
                "decision": event.get("decision"),
                "reason_code": event.get("reason_code"),
                "reason_text": event.get("reason_text"),
                "route": event.get("route"),
                "stage": event.get("stage"),
                "updated_at": event.get("updated_at"),
                "review_id": event.get("review_id"),
            }
            for reviewer_id, event in sorted(latest_by_reviewer.items())
        ],
        "conflict": conflict,
        "adjudication_required": adjudication and not resolved,
        "events": len(events),
        "superseded_events": len(superseded),
        "last_event_at": str(events[-1]["created_at"]),
    }


def document_states(
    document_ids: Iterable[str] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Derived human review state for every document that has at least one event."""
    with _connect(root, write=False) as connection:
        rows = connection.execute(
            "SELECT * FROM review_events ORDER BY sequence ASC"
        ).fetchall()
    wanted = {str(value) for value in document_ids} if document_ids is not None else None
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        document_id = str(row["document_id"])
        if wanted is not None and document_id not in wanted:
            continue
        grouped.setdefault(document_id, []).append(_row_payload(row))
    return {
        document_id: derive_document_state(events) for document_id, events in grouped.items()
    }


def store_status(*, root: Path | None = None) -> dict[str, Any]:
    path = _database_path(root)
    with _connect(root, write=False) as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM review_events").fetchone()[0])
        reviewers = [
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT reviewer_id FROM review_events ORDER BY reviewer_id"
            ).fetchall()
        ]
    return {
        "store_version": STORE_VERSION,
        "database": str(path),
        "database_present": path.is_file(),
        "events": total,
        "reviewers": reviewers,
        "append_only": True,
        "statuses": list(REVIEW_STATUSES),
        "decisions": list(REVIEW_DECISIONS),
        "stages": list(REVIEW_STAGES),
        "guardrail": GUARDRAIL,
    }
