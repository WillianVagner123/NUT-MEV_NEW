"""Derived post-FORMAL Article 1 state from canonical persistent ledgers."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from nutev.review.article1_runtime import article1_runtime_status
from nutev.review.article1_screening_runtime import (
    ARTICLE1_FORMAL_PROTOCOL_VERSION,
    formal_screening_status,
)
from nutev.search.strategy_registry import default_registry_path


def _formal_session_id(db_path: Path, build_id: str) -> str | None:
    if not Path(db_path).is_file() or not build_id:
        return None
    try:
        con = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            row = con.execute(
                """SELECT session_id FROM screening_sessions
                   WHERE build_id=? AND protocol_version=?
                   ORDER BY created_at DESC LIMIT 1""",
                (build_id, ARTICLE1_FORMAL_PROTOCOL_VERSION),
            ).fetchone()
        finally:
            con.close()
    except (sqlite3.Error, OSError):
        return None
    return str(row["session_id"]) if row else None


def derive_postformal_status(project_root: Path, formal_summary: dict[str, Any]) -> dict[str, Any]:
    """Return the next legitimate phase after an authorized FORMAL corpus exists."""
    project = Path(project_root)
    build_id = str((formal_summary.get("corpus") or {}).get("build_id") or "").strip()
    db_path = default_registry_path(project)
    session_id = _formal_session_id(db_path, build_id)
    if not session_id:
        return {
            "phase": "SCREENING_INITIALIZATION",
            "next_action": "Initialize the canonical R1/R2 screening session for the frozen FORMAL corpus.",
            "session_id": None,
            "build_id": build_id,
            "human_decision_inferred": False,
        }

    screening = formal_screening_status(
        db_path,
        session_id=session_id,
        project_root=project,
    )
    screening_phase = str(screening.get("phase") or "")
    if screening_phase != "SCREENING_COMPLETE":
        action = {
            "SCREENING_REVIEWER_ASSIGNMENT": "Confirm real and distinct R1, R2 and adjudicator identities.",
            "TITLE_ABSTRACT_HUMAN_REVIEW": "Complete blinded R1/R2 title/abstract screening and adjudication.",
            "FULLTEXT_HUMAN_REVIEW": "Complete R1/R2 full-text eligibility, family classification and adjudication.",
        }.get(screening_phase, "Complete the pending human screening work.")
        return {
            "phase": screening_phase,
            "next_action": action,
            "session_id": session_id,
            "build_id": build_id,
            "screening": screening,
            "human_decision_inferred": False,
        }

    included = int(screening.get("included_documents") or 0)
    if included == 0:
        return {
            "phase": "SYNTHESIS_PRISMA",
            "next_action": "Generate the final zero-inclusion synthesis/PRISMA package from the resolved FORMAL lineage.",
            "session_id": session_id,
            "build_id": build_id,
            "screening": screening,
            "runtime": {"included_documents": 0, "synthesis_ready": True, "documents": []},
            "human_decision_inferred": False,
        }

    runtime = article1_runtime_status(db_path, session_id=session_id)
    documents = list(runtime.get("documents") or [])
    if any(not bool(row.get("abcd_closed")) for row in documents):
        phase = "ABCD_HUMAN_REVIEW"
        action = "Complete R1/R2 ABCD 34/34 coding and adjudicate unresolved component divergences."
    elif any(not bool(row.get("relations_closed")) for row in documents):
        phase = "RELATIONS_HUMAN_REVIEW"
        action = "Complete explicit relation review for R1/R2 and adjudicate unresolved relation-set divergences."
    else:
        phase = "SYNTHESIS_PRISMA"
        action = "Generate synthesis, audit bundle and PRISMA-eligible final outputs."

    return {
        "phase": phase,
        "next_action": action,
        "session_id": session_id,
        "build_id": build_id,
        "screening": screening,
        "runtime": runtime,
        "human_decision_inferred": False,
    }


__all__ = ["derive_postformal_status"]
