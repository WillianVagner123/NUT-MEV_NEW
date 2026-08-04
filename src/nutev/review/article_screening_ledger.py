"""Additive SQLite ledger for duplicate review and article-level screening."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.review.human_review import REVIEWER_ROLES
from nutev.search.corpus_build_ledger import initialize_corpus_build_ledger

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
ARTICLE_IDS = tuple(f"article_{number}" for number in range(1, 6))
SCREENING_STAGES = ("TITLE_ABSTRACT", "FULL_TEXT")
SCREENING_DECISIONS = ("INCLUDE", "EXCLUDE", "MAYBE")
DUPLICATE_REVIEW_DECISIONS = ("CONFIRMED_DUPLICATE", "REJECTED")
SESSION_STATUSES = ("OPEN", "COMPLETED")
EXCLUSION_REASONS = (
    "NOT_RELEVANT_TO_ARTICLE",
    "WRONG_POPULATION",
    "WRONG_CONCEPT",
    "WRONG_CONTEXT",
    "WRONG_DOCUMENT_TYPE",
    "WRONG_OUTCOME",
    "WRONG_PUBLICATION_DATE",
    "WRONG_LANGUAGE",
    "INSUFFICIENT_METADATA",
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


def initialize_article_screening_ledger(db_path: Path) -> None:
    """Create the article-screening schema without modifying prior tables."""
    initialize_corpus_build_ledger(db_path)
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS screening_article_catalog (
                article_id TEXT PRIMARY KEY,
                article_number INTEGER NOT NULL UNIQUE CHECK (article_number > 0),
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS screening_sessions (
                session_id TEXT PRIMARY KEY,
                build_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('OPEN', 'COMPLETED')),
                protocol_version TEXT NOT NULL DEFAULT 'v1',
                created_by TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (build_id) REFERENCES search_corpus_builds(build_id),
                UNIQUE (build_id, protocol_version)
            );

            CREATE INDEX IF NOT EXISTS idx_screening_sessions_build
                ON screening_sessions(build_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS article_screening_decisions (
                decision_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                stage TEXT NOT NULL CHECK (stage IN ('TITLE_ABSTRACT', 'FULL_TEXT')),
                decision TEXT NOT NULL CHECK (decision IN ('INCLUDE', 'EXCLUDE', 'MAYBE')),
                exclusion_reason TEXT NOT NULL DEFAULT '',
                reviewer_name TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL CHECK (revision > 0),
                decided_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id),
                FOREIGN KEY (article_id) REFERENCES screening_article_catalog(article_id),
                UNIQUE (session_id, document_id, article_id, stage, revision)
            );

            CREATE INDEX IF NOT EXISTS idx_article_screening_latest
                ON article_screening_decisions(
                    session_id, article_id, stage, document_id, revision DESC
                );

            CREATE TABLE IF NOT EXISTS duplicate_candidate_reviews (
                review_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                decision TEXT NOT NULL
                    CHECK (decision IN ('CONFIRMED_DUPLICATE', 'REJECTED')),
                retained_document_id TEXT NOT NULL DEFAULT '',
                removed_document_id TEXT NOT NULL DEFAULT '',
                reviewer_name TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL CHECK (revision > 0),
                decided_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id),
                FOREIGN KEY (candidate_id) REFERENCES search_duplicate_candidates(candidate_id),
                UNIQUE (session_id, candidate_id, revision)
            );

            CREATE INDEX IF NOT EXISTS idx_duplicate_reviews_latest
                ON duplicate_candidate_reviews(session_id, candidate_id, revision DESC);

            CREATE TABLE IF NOT EXISTS screening_exports (
                export_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                effective_documents INTEGER NOT NULL CHECK (effective_documents >= 0),
                human_duplicates_removed INTEGER NOT NULL
                    CHECK (human_duplicates_removed >= 0),
                decisions_csv_path TEXT NOT NULL,
                duplicate_reviews_csv_path TEXT NOT NULL,
                queue_csv_path TEXT NOT NULL,
                prisma_csv_path TEXT NOT NULL,
                prisma_json_path TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES screening_sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_screening_exports_session
                ON screening_exports(session_id, created_at DESC);
            """
        )
        timestamp = _now_iso()
        connection.executemany(
            """
            INSERT OR IGNORE INTO screening_article_catalog (
                article_id, article_number, label, description, active, updated_at
            ) VALUES (?, ?, ?, '', 1, ?)
            """,
            [
                (article_id, number, f"Artigo {number}", timestamp)
                for number, article_id in enumerate(ARTICLE_IDS, start=1)
            ],
        )


def list_article_catalog(
    db_path: Path,
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    where = "WHERE active = 1" if active_only else ""
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM screening_article_catalog
            {where}
            ORDER BY article_number
            """
        ).fetchall()
    output = [dict(row) for row in rows]
    for row in output:
        row["active"] = bool(row["active"])
    return output


def update_article_catalog(
    db_path: Path,
    *,
    article_id: str,
    label: str,
    description: str = "",
    active: bool = True,
) -> dict[str, Any]:
    normalized_article = article_id.strip().lower()
    if normalized_article not in ARTICLE_IDS:
        raise ValueError(f"article_id must be one of {ARTICLE_IDS}")
    if not label.strip():
        raise ValueError("article label is required")
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE screening_article_catalog
            SET label = ?, description = ?, active = ?, updated_at = ?
            WHERE article_id = ?
            """,
            (
                label.strip(),
                description.strip(),
                int(bool(active)),
                _now_iso(),
                normalized_article,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown article_id: {article_id}")
        row = connection.execute(
            "SELECT * FROM screening_article_catalog WHERE article_id = ?",
            (normalized_article,),
        ).fetchone()
    output = dict(row)
    output["active"] = bool(output["active"])
    return output


def get_or_create_screening_session(
    db_path: Path,
    *,
    build_id: str,
    protocol_version: str = "v1",
    created_by: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if not build_id.strip():
        raise ValueError("build_id is required")
    if not protocol_version.strip():
        raise ValueError("protocol_version is required")
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        existing = connection.execute(
            """
            SELECT * FROM screening_sessions
            WHERE build_id = ? AND protocol_version = ?
            """,
            (build_id.strip(), protocol_version.strip()),
        ).fetchone()
        if existing is not None:
            return dict(existing)

        session_id = f"screening_session_{uuid4().hex}"
        timestamp = _now_iso()
        connection.execute(
            """
            INSERT INTO screening_sessions (
                session_id, build_id, status, protocol_version,
                created_by, notes, created_at
            ) VALUES (?, ?, 'OPEN', ?, ?, ?, ?)
            """,
            (
                session_id,
                build_id.strip(),
                protocol_version.strip(),
                created_by.strip(),
                notes.strip(),
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM screening_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row)


def get_screening_session(
    db_path: Path,
    session_id: str,
) -> dict[str, Any] | None:
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM screening_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_screening_sessions(
    db_path: Path,
    *,
    build_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    params: list[object] = []
    where = ""
    if build_id:
        where = "WHERE build_id = ?"
        params.append(build_id)
    params.append(safe_limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM screening_sessions
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def set_screening_session_status(
    db_path: Path,
    *,
    session_id: str,
    status: str,
) -> dict[str, Any]:
    normalized = status.strip().upper()
    if normalized not in SESSION_STATUSES:
        raise ValueError(f"status must be one of {SESSION_STATUSES}")
    initialize_article_screening_ledger(db_path)
    completed_at = _now_iso() if normalized == "COMPLETED" else None
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE screening_sessions
            SET status = ?, completed_at = ?
            WHERE session_id = ?
            """,
            (normalized, completed_at, session_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown session_id: {session_id}")
    return get_screening_session(db_path, session_id) or {}


def _validate_reviewer(reviewer_name: str, reviewer_role: str) -> tuple[str, str]:
    name = reviewer_name.strip()
    role = reviewer_role.strip()
    if not name:
        raise ValueError("reviewer_name is required")
    if role not in REVIEWER_ROLES:
        raise ValueError(f"reviewer_role must be one of {sorted(REVIEWER_ROLES)}")
    return name, role


def record_article_screening_decision(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    stage: str = "TITLE_ABSTRACT",
    exclusion_reason: str = "",
    notes: str = "",
    decided_at: str | None = None,
) -> dict[str, Any]:
    normalized_article = article_id.strip().lower()
    normalized_stage = stage.strip().upper()
    normalized_decision = decision.strip().upper()
    normalized_reason = exclusion_reason.strip().upper()
    name, role = _validate_reviewer(reviewer_name, reviewer_role)
    if not document_id.strip():
        raise ValueError("document_id is required")
    if normalized_article not in ARTICLE_IDS:
        raise ValueError(f"article_id must be one of {ARTICLE_IDS}")
    if normalized_stage not in SCREENING_STAGES:
        raise ValueError(f"stage must be one of {SCREENING_STAGES}")
    if normalized_decision not in SCREENING_DECISIONS:
        raise ValueError(f"decision must be one of {SCREENING_DECISIONS}")
    if normalized_decision == "EXCLUDE":
        if normalized_reason not in EXCLUSION_REASONS:
            raise ValueError(
                f"exclusion_reason must be one of {EXCLUSION_REASONS}"
            )
        if normalized_reason == "OTHER" and not notes.strip():
            raise ValueError("notes are required when exclusion_reason is OTHER")
    elif normalized_reason:
        raise ValueError("exclusion_reason is only allowed for EXCLUDE decisions")

    initialize_article_screening_ledger(db_path)
    timestamp = decided_at or _now_iso()
    with _connect(db_path) as connection:
        session = connection.execute(
            "SELECT status FROM screening_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            raise ValueError(f"unknown session_id: {session_id}")
        if session["status"] != "OPEN":
            raise ValueError("screening session is completed")
        revision = int(
            connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM article_screening_decisions
                WHERE session_id = ? AND document_id = ?
                    AND article_id = ? AND stage = ?
                """,
                (
                    session_id,
                    document_id.strip(),
                    normalized_article,
                    normalized_stage,
                ),
            ).fetchone()[0]
        )
        decision_id = f"screening_decision_{uuid4().hex}"
        connection.execute(
            """
            INSERT INTO article_screening_decisions (
                decision_id, session_id, document_id, article_id, stage,
                decision, exclusion_reason, reviewer_name, reviewer_role,
                notes, revision, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                session_id,
                document_id.strip(),
                normalized_article,
                normalized_stage,
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
            "SELECT * FROM article_screening_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    return dict(row)


def list_latest_article_screening_decisions(
    db_path: Path,
    *,
    session_id: str,
    article_id: str | None = None,
    stage: str | None = None,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    clauses = ["d.session_id = ?"]
    params: list[object] = [session_id]
    if article_id:
        clauses.append("d.article_id = ?")
        params.append(article_id.strip().lower())
    if stage:
        clauses.append("d.stage = ?")
        params.append(stage.strip().upper())
    where = " AND ".join(clauses)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT d.*
            FROM article_screening_decisions d
            JOIN (
                SELECT session_id, document_id, article_id, stage,
                       MAX(revision) AS max_revision
                FROM article_screening_decisions
                GROUP BY session_id, document_id, article_id, stage
            ) latest
              ON latest.session_id = d.session_id
             AND latest.document_id = d.document_id
             AND latest.article_id = d.article_id
             AND latest.stage = d.stage
             AND latest.max_revision = d.revision
            WHERE {where}
            ORDER BY d.article_id, d.document_id, d.stage
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def list_duplicate_candidates_with_latest_review(
    db_path: Path,
    *,
    session_id: str,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        session = connection.execute(
            "SELECT build_id FROM screening_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            raise ValueError(f"unknown session_id: {session_id}")
        rows = connection.execute(
            """
            SELECT c.*,
                   r.review_id,
                   r.decision AS review_decision,
                   r.retained_document_id,
                   r.removed_document_id,
                   r.reviewer_name,
                   r.reviewer_role,
                   r.notes AS review_notes,
                   r.revision AS review_revision,
                   r.decided_at
            FROM search_duplicate_candidates c
            LEFT JOIN duplicate_candidate_reviews r
              ON r.review_id = (
                    SELECT r2.review_id
                    FROM duplicate_candidate_reviews r2
                    WHERE r2.session_id = ?
                      AND r2.candidate_id = c.candidate_id
                    ORDER BY r2.revision DESC
                    LIMIT 1
                 )
            WHERE c.build_id = ?
            ORDER BY c.created_at, c.candidate_id
            """,
            (session_id, session["build_id"]),
        ).fetchall()
    return [dict(row) for row in rows]


def record_duplicate_candidate_review(
    db_path: Path,
    *,
    session_id: str,
    candidate_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    retained_document_id: str = "",
    removed_document_id: str = "",
    notes: str = "",
    decided_at: str | None = None,
) -> dict[str, Any]:
    normalized_decision = decision.strip().upper()
    name, role = _validate_reviewer(reviewer_name, reviewer_role)
    if normalized_decision not in DUPLICATE_REVIEW_DECISIONS:
        raise ValueError(
            f"decision must be one of {DUPLICATE_REVIEW_DECISIONS}"
        )
    initialize_article_screening_ledger(db_path)
    timestamp = decided_at or _now_iso()
    with _connect(db_path) as connection:
        session = connection.execute(
            "SELECT build_id, status FROM screening_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            raise ValueError(f"unknown session_id: {session_id}")
        if session["status"] != "OPEN":
            raise ValueError("screening session is completed")
        candidate = connection.execute(
            """
            SELECT * FROM search_duplicate_candidates
            WHERE candidate_id = ? AND build_id = ?
            """,
            (candidate_id, session["build_id"]),
        ).fetchone()
        if candidate is None:
            raise ValueError("candidate does not belong to this screening session")

        pair = {
            str(candidate["left_document_id"]),
            str(candidate["right_document_id"]),
        }
        retained = retained_document_id.strip()
        removed = removed_document_id.strip()
        if normalized_decision == "CONFIRMED_DUPLICATE":
            if {retained, removed} != pair or retained == removed:
                raise ValueError(
                    "retained_document_id and removed_document_id must match the candidate pair"
                )
            current_decisions = connection.execute(
                """
                SELECT 1 FROM article_screening_decisions
                WHERE session_id = ? AND document_id = ?
                LIMIT 1
                """,
                (session_id, removed),
            ).fetchone()
            if current_decisions is not None:
                raise ValueError(
                    "resolve duplicate candidates before screening the document to be removed"
                )

            latest_confirmed = connection.execute(
                """
                SELECT r.*
                FROM duplicate_candidate_reviews r
                JOIN (
                    SELECT candidate_id, MAX(revision) AS max_revision
                    FROM duplicate_candidate_reviews
                    WHERE session_id = ? AND candidate_id <> ?
                    GROUP BY candidate_id
                ) latest
                  ON latest.candidate_id = r.candidate_id
                 AND latest.max_revision = r.revision
                WHERE r.session_id = ?
                  AND r.decision = 'CONFIRMED_DUPLICATE'
                """,
                (session_id, candidate_id, session_id),
            ).fetchall()
            removed_ids = {str(row["removed_document_id"]) for row in latest_confirmed}
            retained_ids = {str(row["retained_document_id"]) for row in latest_confirmed}
            if retained in removed_ids:
                raise ValueError("the retained document was already removed by another review")
            if removed in removed_ids:
                raise ValueError("the removed document was already removed by another review")
            if removed in retained_ids:
                raise ValueError(
                    "the document selected for removal is retained by another confirmed pair"
                )
        else:
            retained = ""
            removed = ""

        revision = int(
            connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM duplicate_candidate_reviews
                WHERE session_id = ? AND candidate_id = ?
                """,
                (session_id, candidate_id),
            ).fetchone()[0]
        )
        review_id = f"duplicate_review_{uuid4().hex}"
        connection.execute(
            """
            INSERT INTO duplicate_candidate_reviews (
                review_id, session_id, candidate_id, decision,
                retained_document_id, removed_document_id,
                reviewer_name, reviewer_role, notes, revision, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                session_id,
                candidate_id,
                normalized_decision,
                retained,
                removed,
                name,
                role,
                notes.strip(),
                revision,
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM duplicate_candidate_reviews WHERE review_id = ?",
            (review_id,),
        ).fetchone()
    return dict(row)


def list_latest_duplicate_reviews(
    db_path: Path,
    *,
    session_id: str,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT r.*
            FROM duplicate_candidate_reviews r
            JOIN (
                SELECT session_id, candidate_id, MAX(revision) AS max_revision
                FROM duplicate_candidate_reviews
                WHERE session_id = ?
                GROUP BY session_id, candidate_id
            ) latest
              ON latest.session_id = r.session_id
             AND latest.candidate_id = r.candidate_id
             AND latest.max_revision = r.revision
            WHERE r.session_id = ?
            ORDER BY r.candidate_id
            """,
            (session_id, session_id),
        ).fetchall()
    return [dict(row) for row in rows]


def record_screening_export(
    db_path: Path,
    *,
    session_id: str,
    effective_documents: int,
    human_duplicates_removed: int,
    paths: dict[str, str],
    manifest_sha256: str,
    export_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if int(effective_documents) < 0 or int(human_duplicates_removed) < 0:
        raise ValueError("export counts cannot be negative")
    required_paths = (
        "decisions_csv_path",
        "duplicate_reviews_csv_path",
        "queue_csv_path",
        "prisma_csv_path",
        "prisma_json_path",
        "manifest_path",
    )
    missing = [key for key in required_paths if not paths.get(key, "").strip()]
    if missing:
        raise ValueError(f"missing export paths: {', '.join(missing)}")
    if not manifest_sha256.strip():
        raise ValueError("manifest_sha256 is required")
    initialize_article_screening_ledger(db_path)
    resolved_export_id = export_id or f"screening_export_{uuid4().hex}"
    timestamp = created_at or _now_iso()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO screening_exports (
                export_id, session_id, created_at, effective_documents,
                human_duplicates_removed, decisions_csv_path,
                duplicate_reviews_csv_path, queue_csv_path, prisma_csv_path,
                prisma_json_path, manifest_path, manifest_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_export_id,
                session_id,
                timestamp,
                int(effective_documents),
                int(human_duplicates_removed),
                paths["decisions_csv_path"],
                paths["duplicate_reviews_csv_path"],
                paths["queue_csv_path"],
                paths["prisma_csv_path"],
                paths["prisma_json_path"],
                paths["manifest_path"],
                manifest_sha256.strip(),
            ),
        )
        row = connection.execute(
            "SELECT * FROM screening_exports WHERE export_id = ?",
            (resolved_export_id,),
        ).fetchone()
    return dict(row)


def list_screening_exports(
    db_path: Path,
    *,
    session_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    initialize_article_screening_ledger(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM screening_exports
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, safe_limit),
        ).fetchall()
    return [dict(row) for row in rows]
