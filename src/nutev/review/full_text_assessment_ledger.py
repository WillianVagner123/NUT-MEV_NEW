"""Append-only ledger for full-text retrieval and article eligibility decisions."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.review.article_screening_ledger import (
    ARTICLE_IDS,
    get_screening_session,
    initialize_article_screening_ledger,
)
from nutev.review.human_review import REVIEWER_ROLES

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RETRIEVAL_STATUSES = ("AVAILABLE", "REQUESTED", "NOT_FOUND", "PAYWALLED", "FAILED")
TERMINAL_NOT_RETRIEVED = ("NOT_FOUND", "PAYWALLED", "FAILED")
FULL_TEXT_DECISIONS = ("INCLUDE", "EXCLUDE", "MAYBE")
FULL_TEXT_EXCLUSION_REASONS = (
    "WRONG_POPULATION",
    "WRONG_CONCEPT",
    "WRONG_CONTEXT",
    "WRONG_DOCUMENT_TYPE",
    "WRONG_STUDY_DESIGN",
    "WRONG_OUTCOME",
    "NOT_PRIMARY_SOURCE",
    "DUPLICATE_PUBLICATION",
    "NO_USABLE_DATA",
    "WRONG_PUBLICATION_DATE",
    "WRONG_LANGUAGE",
    "OTHER",
)


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _connect(db_path: Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_full_text_assessment_ledger(db_path: Path) -> None:
    """Create additive full-text tables without changing prior screening data."""
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS full_text_retrieval_reviews (
                retrieval_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('AVAILABLE', 'REQUESTED', 'NOT_FOUND', 'PAYWALLED', 'FAILED')
                ),
                source_url TEXT NOT NULL DEFAULT '',
                artifact_path TEXT NOT NULL DEFAULT '',
                artifact_sha256 TEXT NOT NULL DEFAULT '',
                content_type TEXT NOT NULL DEFAULT '',
                reviewer_name TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL CHECK (revision > 0),
                decided_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id),
                UNIQUE (session_id, document_id, revision)
            );

            CREATE INDEX IF NOT EXISTS idx_full_text_retrieval_latest
                ON full_text_retrieval_reviews(session_id, document_id, revision DESC);

            CREATE TABLE IF NOT EXISTS full_text_eligibility_decisions (
                decision_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('INCLUDE', 'EXCLUDE', 'MAYBE')),
                exclusion_reason TEXT NOT NULL DEFAULT '',
                reviewer_name TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL CHECK (revision > 0),
                decided_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id),
                FOREIGN KEY (article_id) REFERENCES screening_article_catalog(article_id),
                UNIQUE (session_id, document_id, article_id, revision)
            );

            CREATE INDEX IF NOT EXISTS idx_full_text_eligibility_latest
                ON full_text_eligibility_decisions(
                    session_id, article_id, document_id, revision DESC
                );

            CREATE TABLE IF NOT EXISTS full_text_exports (
                export_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                distinct_reports_sought INTEGER NOT NULL CHECK (distinct_reports_sought >= 0),
                distinct_reports_retrieved INTEGER NOT NULL CHECK (distinct_reports_retrieved >= 0),
                distinct_reports_not_retrieved INTEGER NOT NULL
                    CHECK (distinct_reports_not_retrieved >= 0),
                article_inclusions INTEGER NOT NULL CHECK (article_inclusions >= 0),
                retrieval_csv_path TEXT NOT NULL,
                eligibility_csv_path TEXT NOT NULL,
                queue_csv_path TEXT NOT NULL,
                included_csv_path TEXT NOT NULL,
                prisma_csv_path TEXT NOT NULL,
                prisma_json_path TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_full_text_exports_session
                ON full_text_exports(session_id, created_at DESC);
            """
        )


def _validate_reviewer(reviewer_name: str, reviewer_role: str) -> tuple[str, str]:
    name = reviewer_name.strip()
    role = reviewer_role.strip()
    if not name:
        raise ValueError("reviewer_name is required")
    if role not in REVIEWER_ROLES:
        raise ValueError(f"reviewer_role must be one of {sorted(REVIEWER_ROLES)}")
    return name, role


def _require_open_session(db_path: Path, session_id: str) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    if session["status"] != "OPEN":
        raise ValueError("screening session is completed")
    return session


def record_full_text_retrieval(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    status: str,
    reviewer_name: str,
    reviewer_role: str,
    source_url: str = "",
    artifact_path: str = "",
    artifact_sha256: str = "",
    content_type: str = "",
    notes: str = "",
    decided_at: str | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().upper()
    name, role = _validate_reviewer(reviewer_name, reviewer_role)
    if not document_id.strip():
        raise ValueError("document_id is required")
    if normalized_status not in RETRIEVAL_STATUSES:
        raise ValueError(f"status must be one of {RETRIEVAL_STATUSES}")
    if normalized_status == "AVAILABLE" and not (source_url.strip() or artifact_path.strip()):
        raise ValueError("AVAILABLE requires source_url or artifact_path")
    if normalized_status in TERMINAL_NOT_RETRIEVED and not notes.strip():
        raise ValueError(f"notes are required for {normalized_status}")
    if artifact_sha256.strip() and not artifact_path.strip():
        raise ValueError("artifact_sha256 requires artifact_path")

    initialize_full_text_assessment_ledger(db_path)
    _require_open_session(db_path, session_id)
    timestamp = decided_at or _now_iso()
    with _connect(db_path) as connection:
        revision = int(
            connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM full_text_retrieval_reviews
                WHERE session_id = ? AND document_id = ?
                """,
                (session_id, document_id.strip()),
            ).fetchone()[0]
        )
        retrieval_id = f"full_text_retrieval_{uuid4().hex}"
        connection.execute(
            """
            INSERT INTO full_text_retrieval_reviews (
                retrieval_id, session_id, document_id, status, source_url,
                artifact_path, artifact_sha256, content_type, reviewer_name,
                reviewer_role, notes, revision, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                retrieval_id,
                session_id,
                document_id.strip(),
                normalized_status,
                source_url.strip(),
                artifact_path.strip(),
                artifact_sha256.strip(),
                content_type.strip(),
                name,
                role,
                notes.strip(),
                revision,
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM full_text_retrieval_reviews WHERE retrieval_id = ?",
            (retrieval_id,),
        ).fetchone()
    return dict(row)


def list_latest_full_text_retrievals(
    db_path: Path,
    *,
    session_id: str,
) -> list[dict[str, Any]]:
    initialize_full_text_assessment_ledger(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT r.*
            FROM full_text_retrieval_reviews r
            JOIN (
                SELECT session_id, document_id, MAX(revision) AS max_revision
                FROM full_text_retrieval_reviews
                WHERE session_id = ?
                GROUP BY session_id, document_id
            ) latest
              ON latest.session_id = r.session_id
             AND latest.document_id = r.document_id
             AND latest.max_revision = r.revision
            WHERE r.session_id = ?
            ORDER BY r.document_id
            """,
            (session_id, session_id),
        ).fetchall()
    return [dict(row) for row in rows]


def record_full_text_eligibility_decision(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    exclusion_reason: str = "",
    notes: str = "",
    decided_at: str | None = None,
) -> dict[str, Any]:
    normalized_article = article_id.strip().lower()
    normalized_decision = decision.strip().upper()
    normalized_reason = exclusion_reason.strip().upper()
    name, role = _validate_reviewer(reviewer_name, reviewer_role)
    if not document_id.strip():
        raise ValueError("document_id is required")
    if normalized_article not in ARTICLE_IDS:
        raise ValueError(f"article_id must be one of {ARTICLE_IDS}")
    if normalized_decision not in FULL_TEXT_DECISIONS:
        raise ValueError(f"decision must be one of {FULL_TEXT_DECISIONS}")
    if normalized_decision == "EXCLUDE":
        if normalized_reason not in FULL_TEXT_EXCLUSION_REASONS:
            raise ValueError(
                "exclusion_reason must be one of "
                f"{FULL_TEXT_EXCLUSION_REASONS}"
            )
        if normalized_reason == "OTHER" and not notes.strip():
            raise ValueError("notes are required when exclusion_reason is OTHER")
    elif normalized_reason:
        raise ValueError("exclusion_reason is only allowed for EXCLUDE decisions")

    initialize_full_text_assessment_ledger(db_path)
    _require_open_session(db_path, session_id)
    timestamp = decided_at or _now_iso()
    with _connect(db_path) as connection:
        revision = int(
            connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM full_text_eligibility_decisions
                WHERE session_id = ? AND document_id = ? AND article_id = ?
                """,
                (session_id, document_id.strip(), normalized_article),
            ).fetchone()[0]
        )
        decision_id = f"full_text_decision_{uuid4().hex}"
        connection.execute(
            """
            INSERT INTO full_text_eligibility_decisions (
                decision_id, session_id, document_id, article_id, decision,
                exclusion_reason, reviewer_name, reviewer_role, notes,
                revision, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                session_id,
                document_id.strip(),
                normalized_article,
                normalized_decision,
                normalized_reason,
                name,
                role,
                notes.strip(),
                revision,
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM full_text_eligibility_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    return dict(row)


def list_latest_full_text_eligibility_decisions(
    db_path: Path,
    *,
    session_id: str,
    article_id: str | None = None,
) -> list[dict[str, Any]]:
    initialize_full_text_assessment_ledger(db_path)
    clauses = ["d.session_id = ?"]
    params: list[object] = [session_id]
    if article_id:
        clauses.append("d.article_id = ?")
        params.append(article_id.strip().lower())
    where = " AND ".join(clauses)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT d.*
            FROM full_text_eligibility_decisions d
            JOIN (
                SELECT session_id, document_id, article_id, MAX(revision) AS max_revision
                FROM full_text_eligibility_decisions
                GROUP BY session_id, document_id, article_id
            ) latest
              ON latest.session_id = d.session_id
             AND latest.document_id = d.document_id
             AND latest.article_id = d.article_id
             AND latest.max_revision = d.revision
            WHERE {where}
            ORDER BY d.article_id, d.document_id
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def record_full_text_export(
    db_path: Path,
    *,
    session_id: str,
    distinct_reports_sought: int,
    distinct_reports_retrieved: int,
    distinct_reports_not_retrieved: int,
    article_inclusions: int,
    paths: dict[str, str],
    manifest_sha256: str,
    export_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    counts = (
        distinct_reports_sought,
        distinct_reports_retrieved,
        distinct_reports_not_retrieved,
        article_inclusions,
    )
    if any(int(value) < 0 for value in counts):
        raise ValueError("full-text export counts cannot be negative")
    required = (
        "retrieval_csv_path",
        "eligibility_csv_path",
        "queue_csv_path",
        "included_csv_path",
        "prisma_csv_path",
        "prisma_json_path",
        "manifest_path",
    )
    missing = [key for key in required if not str(paths.get(key) or "").strip()]
    if missing:
        raise ValueError(f"missing export paths: {', '.join(missing)}")
    if not manifest_sha256.strip():
        raise ValueError("manifest_sha256 is required")

    initialize_full_text_assessment_ledger(db_path)
    if get_screening_session(db_path, session_id) is None:
        raise ValueError(f"unknown session_id: {session_id}")
    resolved = export_id or f"full_text_export_{uuid4().hex}"
    timestamp = created_at or _now_iso()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO full_text_exports (
                export_id, session_id, created_at, distinct_reports_sought,
                distinct_reports_retrieved, distinct_reports_not_retrieved,
                article_inclusions, retrieval_csv_path, eligibility_csv_path,
                queue_csv_path, included_csv_path, prisma_csv_path,
                prisma_json_path, manifest_path, manifest_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved,
                session_id,
                timestamp,
                int(distinct_reports_sought),
                int(distinct_reports_retrieved),
                int(distinct_reports_not_retrieved),
                int(article_inclusions),
                paths["retrieval_csv_path"],
                paths["eligibility_csv_path"],
                paths["queue_csv_path"],
                paths["included_csv_path"],
                paths["prisma_csv_path"],
                paths["prisma_json_path"],
                paths["manifest_path"],
                manifest_sha256.strip(),
            ),
        )
        row = connection.execute(
            "SELECT * FROM full_text_exports WHERE export_id = ?",
            (resolved,),
        ).fetchone()
    return dict(row)


def list_full_text_exports(
    db_path: Path,
    *,
    session_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    initialize_full_text_assessment_ledger(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM full_text_exports
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, safe_limit),
        ).fetchall()
    return [dict(row) for row in rows]
