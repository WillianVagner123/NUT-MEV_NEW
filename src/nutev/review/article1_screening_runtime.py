"""Canonical two-reviewer FORMAL screening runtime for Article 1.

This is additive to the existing Search Registry SQLite: it does not create a
second review database. R1/R2 submissions are append-only per reviewer slot,
original decisions are never overwritten, and consensus/adjudication is stored
as a separate record. The runtime uses the immutable FORMAL corpus build as its
source of document identity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.article1_runtime import (
    article1_reviewer_assignment,
    initialize_article1_runtime,
    set_article1_reviewer_assignment,
)
from nutev.review.article_screening import effective_master_records, ensure_screening_session
from nutev.review.evidence_matrix_core import SLOTS, _db, _j, _loads, _now
from nutev.review.screening import (
    EXCLUSION_REASONS,
    normalize_decision,
    reconcile_full_text,
    reconcile_title_abstract,
)
from nutev.search.strategy_registry import default_registry_path

ARTICLE1_FORMAL_PROTOCOL_VERSION = "article1-formal-v1"
PHASES = ("TITLE_ABSTRACT", "FULL_TEXT")
FINAL_DECISIONS = ("INCLUDE", "EXCLUDE")


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalize_phase(value: object) -> str:
    phase = _clean(value).upper().replace("-", "_").replace(" ", "_")
    aliases = {"TITLEABSTRACT": "TITLE_ABSTRACT", "FULLTEXT": "FULL_TEXT"}
    phase = aliases.get(phase, phase)
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {PHASES}")
    return phase


def _normalize_slot(value: object) -> str:
    slot = _clean(value).upper()
    slot = {"R1": "REVIEWER_1", "R2": "REVIEWER_2"}.get(slot, slot)
    if slot not in SLOTS:
        raise ValueError(f"reviewer_slot must be one of {SLOTS}")
    return slot


def initialize_article1_screening_runtime(db_path: Path) -> None:
    initialize_article1_runtime(db_path)
    with _db(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS article1_screening_submissions(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              phase TEXT NOT NULL CHECK(phase IN ('TITLE_ABSTRACT','FULL_TEXT')),
              reviewer_slot TEXT NOT NULL CHECK(reviewer_slot IN ('REVIEWER_1','REVIEWER_2')),
              reviewer_name TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              decision TEXT NOT NULL CHECK(decision IN ('INCLUDE','EXCLUDE','DOUBT')),
              exclusion_reason TEXT NOT NULL DEFAULT '',
              family TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              revision INTEGER NOT NULL,
              submitted_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,phase,reviewer_slot,revision));
            CREATE INDEX IF NOT EXISTS idx_article1_screening_latest
              ON article1_screening_submissions(
                session_id,phase,document_id,reviewer_slot,revision DESC);

            CREATE TABLE IF NOT EXISTS article1_screening_adjudications(
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              document_id TEXT NOT NULL,
              phase TEXT NOT NULL CHECK(phase IN ('TITLE_ABSTRACT','FULL_TEXT')),
              reviewer_1_json TEXT NOT NULL,
              reviewer_2_json TEXT NOT NULL,
              final_decision TEXT NOT NULL CHECK(final_decision IN ('INCLUDE','EXCLUDE')),
              final_family TEXT NOT NULL DEFAULT '',
              adjudicator_name TEXT NOT NULL,
              adjudicator_role TEXT NOT NULL,
              rationale TEXT NOT NULL,
              revision INTEGER NOT NULL,
              decided_at TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES screening_sessions(session_id),
              UNIQUE(session_id,document_id,phase,revision));
            CREATE INDEX IF NOT EXISTS idx_article1_screening_adj_latest
              ON article1_screening_adjudications(
                session_id,phase,document_id,revision DESC);
            """
        )


def _load_latest_formal_summary(project_root: Path) -> dict[str, Any]:
    path = Path(project_root) / "12_play" / "latest_summary.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(value, dict):
        return {}
    scientific = value.get("scientific_state") or {}
    if str(scientific.get("search_type") or "").upper() != "FORMAL":
        return {}
    if not bool(scientific.get("formal_freeze_authorized")):
        return {}
    return value


def _inherit_assignment_if_available(db_path: Path, session_id: str) -> dict[str, Any] | None:
    current = article1_reviewer_assignment(db_path, session_id)
    if current:
        return current
    initialize_article1_screening_runtime(db_path)
    with _db(db_path) as con:
        row = con.execute(
            """SELECT * FROM article1_reviewer_assignments
               WHERE session_id<>? AND gf07_resolved=1
               ORDER BY recorded_at DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    source = dict(row)
    return set_article1_reviewer_assignment(
        db_path,
        session_id=session_id,
        reviewer_1_name=str(source["reviewer_1_name"]),
        reviewer_2_name=str(source["reviewer_2_name"]),
        adjudicator_name=str(source["adjudicator_name"]),
        notes=(
            "Inherited real reviewer identities from prior GF-07 session "
            f"{source['session_id']}; no screening decision was copied."
        ),
    )


def ensure_formal_screening_context(project_root: Path) -> dict[str, Any]:
    """Create/reuse the screening session attached to the immutable FORMAL corpus."""
    root = Path(project_root)
    summary = _load_latest_formal_summary(root)
    if not summary:
        raise ValueError("a completed authorized FORMAL summary is required")
    build_id = _clean((summary.get("corpus") or {}).get("build_id"))
    if not build_id:
        raise ValueError("FORMAL summary does not contain corpus build_id")
    db_path = default_registry_path(root)
    session = ensure_screening_session(
        db_path,
        build_id=build_id,
        protocol_version=ARTICLE1_FORMAL_PROTOCOL_VERSION,
        created_by="NutEV Engine",
        notes=(
            "Automatically attached to the immutable FORMAL corpus. "
            "Human decisions remain independent and are never inferred."
        ),
    )
    initialize_article1_screening_runtime(db_path)
    assignment = _inherit_assignment_if_available(db_path, str(session["session_id"]))
    return {
        "db_path": str(db_path),
        "session_id": str(session["session_id"]),
        "build_id": build_id,
        "reviewer_assignment_present": bool(assignment),
        "assignment": assignment,
    }


def _expected_reviewer(db_path: Path, session_id: str, slot: str) -> tuple[str, str]:
    assignment = article1_reviewer_assignment(db_path, session_id)
    if not assignment or not bool(assignment.get("gf07_resolved")):
        raise ValueError("FORMAL screening is blocked until real R1/R2/adjudicator identities are assigned")
    if slot == "REVIEWER_1":
        return str(assignment["reviewer_1_name"]), "reviewer_1"
    return str(assignment["reviewer_2_name"]), "reviewer_2"


def _latest_submissions(
    db_path: Path,
    *,
    session_id: str,
    phase: str | None = None,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    initialize_article1_screening_runtime(db_path)
    clauses = ["s.session_id=?"]
    params: list[object] = [session_id]
    if phase:
        clauses.append("s.phase=?")
        params.append(_normalize_phase(phase))
    if document_id:
        clauses.append("s.document_id=?")
        params.append(document_id)
    with _db(db_path) as con:
        rows = con.execute(
            f"""SELECT s.* FROM article1_screening_submissions s JOIN(
                 SELECT session_id,document_id,phase,reviewer_slot,MAX(revision) revision
                 FROM article1_screening_submissions
                 GROUP BY session_id,document_id,phase,reviewer_slot) x
               ON x.session_id=s.session_id AND x.document_id=s.document_id
               AND x.phase=s.phase AND x.reviewer_slot=s.reviewer_slot
               AND x.revision=s.revision
               WHERE {' AND '.join(clauses)}""",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _latest_adjudication(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    phase: str,
) -> dict[str, Any] | None:
    initialize_article1_screening_runtime(db_path)
    normalized_phase = _normalize_phase(phase)
    with _db(db_path) as con:
        row = con.execute(
            """SELECT * FROM article1_screening_adjudications
               WHERE session_id=? AND document_id=? AND phase=?
               ORDER BY revision DESC LIMIT 1""",
            (session_id, document_id, normalized_phase),
        ).fetchone()
    if not row:
        return None
    out = dict(row)
    out["reviewer_1"] = _loads(out["reviewer_1_json"], {})
    out["reviewer_2"] = _loads(out["reviewer_2_json"], {})
    return out


def _technical_queue(project_root: Path) -> dict[str, dict[str, Any]]:
    path = Path(project_root) / "06_review" / "formal_screening_queue.jsonl"
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and _clean(value.get("document_id")):
            rows[_clean(value["document_id"])] = value
    return rows


def _eligible_ids(db_path: Path, session_id: str, phase: str) -> set[str]:
    records, _ = effective_master_records(db_path, session_id=session_id)
    if phase == "TITLE_ABSTRACT":
        return {_clean(row["document_id"]) for row in records}
    return {
        _clean(row["document_id"])
        for row in title_abstract_queue(db_path, session_id=session_id)
        if row["final_action"] == "ADVANCE"
    }


def submit_screening_decision(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    phase: str,
    reviewer_slot: str,
    reviewer_name: str,
    decision: str,
    exclusion_reason: str = "",
    family: str = "",
    notes: str = "",
) -> dict[str, Any]:
    initialize_article1_screening_runtime(db_path)
    normalized_phase = _normalize_phase(phase)
    slot = _normalize_slot(reviewer_slot)
    expected_name, reviewer_role = _expected_reviewer(db_path, session_id, slot)
    if _clean(reviewer_name).casefold() != expected_name.casefold():
        raise ValueError("reviewer identity does not match the GF-07 reviewer slot")
    if document_id not in _eligible_ids(db_path, session_id, normalized_phase):
        raise ValueError("document is not eligible for this screening phase")
    normalized_decision = normalize_decision(decision)
    reason = _clean(exclusion_reason).lower()
    if normalized_decision == "EXCLUDE":
        if reason not in EXCLUSION_REASONS:
            raise ValueError(f"exclusion_reason must be one of {EXCLUSION_REASONS}")
    elif reason:
        raise ValueError("exclusion_reason is only allowed for EXCLUDE")
    normalized_family = _clean(family).upper()
    if normalized_phase == "FULL_TEXT" and normalized_decision == "INCLUDE" and not normalized_family:
        raise ValueError("FULL_TEXT INCLUDE requires document family classification")
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_screening_submissions
                   WHERE session_id=? AND document_id=? AND phase=? AND reviewer_slot=?""",
                (session_id, document_id, normalized_phase, slot),
            ).fetchone()[0]
        )
        row_id = f"article1_screen_{uuid4().hex}"
        con.execute(
            """INSERT INTO article1_screening_submissions(
                 id,session_id,document_id,phase,reviewer_slot,reviewer_name,
                 reviewer_role,decision,exclusion_reason,family,notes,revision,submitted_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row_id,
                session_id,
                document_id,
                normalized_phase,
                slot,
                expected_name,
                reviewer_role,
                normalized_decision,
                reason,
                normalized_family,
                notes.strip(),
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_screening_submissions WHERE id=?", (row_id,)
        ).fetchone()
    return dict(row)


def screening_record_resolution(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    phase: str,
) -> dict[str, Any]:
    normalized_phase = _normalize_phase(phase)
    by_slot = {
        row["reviewer_slot"]: row
        for row in _latest_submissions(
            db_path,
            session_id=session_id,
            phase=normalized_phase,
            document_id=document_id,
        )
    }
    r1, r2 = by_slot.get("REVIEWER_1"), by_slot.get("REVIEWER_2")
    if not r1 or not r2:
        return {
            "document_id": document_id,
            "phase": normalized_phase,
            "status": "PENDING_REVIEWERS",
            "reviewer_1": r1,
            "reviewer_2": r2,
            "requires_adjudication": False,
            "final_decision": None,
            "final_action": None,
            "final_family": "",
        }

    if normalized_phase == "TITLE_ABSTRACT":
        reconciled = reconcile_title_abstract(r1["decision"], r2["decision"])
        if reconciled["resolution"] == "ADVANCE":
            return {
                "document_id": document_id,
                "phase": normalized_phase,
                "status": "RESOLVED_ADVANCE",
                "reviewer_1": r1,
                "reviewer_2": r2,
                "requires_adjudication": False,
                "final_decision": "INCLUDE",
                "final_action": "ADVANCE",
                "final_family": "",
            }
        if reconciled["resolution"] == "EXCLUDE":
            return {
                "document_id": document_id,
                "phase": normalized_phase,
                "status": "RESOLVED_EXCLUDE",
                "reviewer_1": r1,
                "reviewer_2": r2,
                "requires_adjudication": False,
                "final_decision": "EXCLUDE",
                "final_action": "EXCLUDE",
                "final_family": "",
            }
    else:
        reconciled = reconcile_full_text(r1["decision"], r2["decision"])
        same_family = _clean(r1.get("family")).casefold() == _clean(r2.get("family")).casefold()
        if reconciled["resolution"] == "INCLUDE" and same_family and _clean(r1.get("family")):
            return {
                "document_id": document_id,
                "phase": normalized_phase,
                "status": "RESOLVED_INCLUDE",
                "reviewer_1": r1,
                "reviewer_2": r2,
                "requires_adjudication": False,
                "final_decision": "INCLUDE",
                "final_action": "INCLUDE",
                "final_family": _clean(r1["family"]).upper(),
            }
        if reconciled["resolution"] == "EXCLUDE":
            return {
                "document_id": document_id,
                "phase": normalized_phase,
                "status": "RESOLVED_EXCLUDE",
                "reviewer_1": r1,
                "reviewer_2": r2,
                "requires_adjudication": False,
                "final_decision": "EXCLUDE",
                "final_action": "EXCLUDE",
                "final_family": "",
            }

    adjudication = _latest_adjudication(
        db_path,
        session_id=session_id,
        document_id=document_id,
        phase=normalized_phase,
    )
    if adjudication:
        final_decision = str(adjudication["final_decision"])
        return {
            "document_id": document_id,
            "phase": normalized_phase,
            "status": f"ADJUDICATED_{final_decision}",
            "reviewer_1": r1,
            "reviewer_2": r2,
            "requires_adjudication": False,
            "final_decision": final_decision,
            "final_action": (
                "ADVANCE"
                if normalized_phase == "TITLE_ABSTRACT" and final_decision == "INCLUDE"
                else final_decision
            ),
            "final_family": str(adjudication.get("final_family") or ""),
            "adjudication": adjudication,
        }
    return {
        "document_id": document_id,
        "phase": normalized_phase,
        "status": "PENDING_ADJUDICATION",
        "reviewer_1": r1,
        "reviewer_2": r2,
        "requires_adjudication": True,
        "final_decision": None,
        "final_action": None,
        "final_family": "",
    }


def adjudicate_screening(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    phase: str,
    final_decision: str,
    adjudicator_name: str,
    rationale: str,
    final_family: str = "",
) -> dict[str, Any]:
    normalized_phase = _normalize_phase(phase)
    current = screening_record_resolution(
        db_path,
        session_id=session_id,
        document_id=document_id,
        phase=normalized_phase,
    )
    if current["status"] != "PENDING_ADJUDICATION":
        raise ValueError("only unresolved reviewer disagreement/doubt requires adjudication")
    assignment = article1_reviewer_assignment(db_path, session_id)
    if not assignment or _clean(adjudicator_name).casefold() != _clean(assignment.get("adjudicator_name")).casefold():
        raise ValueError("adjudicator identity does not match the GF-07 assignment")
    decision = _clean(final_decision).upper()
    if decision not in FINAL_DECISIONS:
        raise ValueError(f"final_decision must be one of {FINAL_DECISIONS}")
    if not _clean(rationale):
        raise ValueError("adjudication requires rationale")
    family = _clean(final_family).upper()
    if normalized_phase == "FULL_TEXT" and decision == "INCLUDE" and not family:
        raise ValueError("FULL_TEXT INCLUDE adjudication requires final_family")
    with _db(db_path) as con:
        revision = int(
            con.execute(
                """SELECT COALESCE(MAX(revision),0)+1
                   FROM article1_screening_adjudications
                   WHERE session_id=? AND document_id=? AND phase=?""",
                (session_id, document_id, normalized_phase),
            ).fetchone()[0]
        )
        row_id = f"article1_screen_adj_{uuid4().hex}"
        con.execute(
            """INSERT INTO article1_screening_adjudications(
                 id,session_id,document_id,phase,reviewer_1_json,reviewer_2_json,
                 final_decision,final_family,adjudicator_name,adjudicator_role,
                 rationale,revision,decided_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row_id,
                session_id,
                document_id,
                normalized_phase,
                _j(current["reviewer_1"]),
                _j(current["reviewer_2"]),
                decision,
                family,
                str(assignment["adjudicator_name"]),
                "external_reviewer",
                rationale.strip(),
                revision,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM article1_screening_adjudications WHERE id=?", (row_id,)
        ).fetchone()
    return dict(row)


def title_abstract_queue(db_path: Path, *, session_id: str) -> list[dict[str, Any]]:
    records, _ = effective_master_records(db_path, session_id=session_id)
    output = []
    for record in records:
        document_id = _clean(record["document_id"])
        resolution = screening_record_resolution(
            db_path,
            session_id=session_id,
            document_id=document_id,
            phase="TITLE_ABSTRACT",
        )
        output.append({**record, **resolution})
    return output


def full_text_queue(
    db_path: Path,
    *,
    session_id: str,
    project_root: Path | None = None,
) -> list[dict[str, Any]]:
    records, _ = effective_master_records(db_path, session_id=session_id)
    by_id = {_clean(row["document_id"]): row for row in records}
    technical = _technical_queue(project_root) if project_root else {}
    output = []
    for title_row in title_abstract_queue(db_path, session_id=session_id):
        if title_row["final_action"] != "ADVANCE":
            continue
        document_id = _clean(title_row["document_id"])
        resolution = screening_record_resolution(
            db_path,
            session_id=session_id,
            document_id=document_id,
            phase="FULL_TEXT",
        )
        technical_row = technical.get(document_id) or {}
        output.append(
            {
                **by_id[document_id],
                "full_text_path": technical_row.get("full_text_path", ""),
                "screen_flag": technical_row.get("screen_flag", ""),
                "quality_note": technical_row.get("quality_note", ""),
                **resolution,
            }
        )
    return output


def formal_screening_status(
    db_path: Path,
    *,
    session_id: str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    initialize_article1_screening_runtime(db_path)
    assignment = article1_reviewer_assignment(db_path, session_id)
    title = title_abstract_queue(db_path, session_id=session_id)
    title_pending = [row for row in title if not row.get("final_action")]
    full = full_text_queue(
        db_path,
        session_id=session_id,
        project_root=project_root,
    ) if not title_pending else []
    full_pending = [row for row in full if not row.get("final_action")]
    included = [row for row in full if row.get("final_decision") == "INCLUDE"]
    if not assignment:
        phase = "SCREENING_REVIEWER_ASSIGNMENT"
    elif title_pending:
        phase = "TITLE_ABSTRACT_HUMAN_REVIEW"
    elif full_pending:
        phase = "FULLTEXT_HUMAN_REVIEW"
    else:
        phase = "SCREENING_COMPLETE"
    return {
        "session_id": session_id,
        "phase": phase,
        "reviewer_assignment_present": bool(assignment),
        "title_abstract": {
            "total": len(title),
            "resolved": len(title) - len(title_pending),
            "pending": len(title_pending),
            "pending_adjudication": sum(row.get("requires_adjudication", False) for row in title),
        },
        "full_text": {
            "total": len(full),
            "resolved": len(full) - len(full_pending),
            "pending": len(full_pending),
            "pending_adjudication": sum(row.get("requires_adjudication", False) for row in full),
        },
        "included_documents": len(included),
        "human_decision_inferred": False,
    }


def canonical_article1_included(db_path: Path, session_id: str) -> list[dict[str, Any]]:
    """Return final FORMAL Article 1 included documents from the dual-review ledger."""
    full = full_text_queue(db_path, session_id=session_id, project_root=Path(db_path).parent.parent)
    included_by_id = {
        _clean(row["document_id"]): row
        for row in full
        if row.get("final_decision") == "INCLUDE"
    }
    records, _ = effective_master_records(db_path, session_id=session_id)
    output: list[dict[str, Any]] = []
    for record in records:
        document_id = _clean(record["document_id"])
        final = included_by_id.get(document_id)
        if not final:
            continue
        output.append(
            {
                **record,
                "article_id": "article_1",
                "family": final.get("final_family", ""),
                "document_family": final.get("final_family", ""),
                "retrieval_artifact_path": final.get("full_text_path", ""),
                "retrieval_artifact_sha256": "",
                "screening_basis": "ARTICLE1_DUAL_REVIEW",
            }
        )
    return output


__all__ = [
    "ARTICLE1_FORMAL_PROTOCOL_VERSION",
    "adjudicate_screening",
    "canonical_article1_included",
    "ensure_formal_screening_context",
    "formal_screening_status",
    "full_text_queue",
    "initialize_article1_screening_runtime",
    "screening_record_resolution",
    "submit_screening_decision",
    "title_abstract_queue",
]
