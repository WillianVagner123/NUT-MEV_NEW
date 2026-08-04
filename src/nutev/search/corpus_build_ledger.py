"""Additive SQLite ledger for normalization and deduplication builds."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.strategy_execution_ledger import initialize_execution_ledger

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
BUILD_STATUSES = ("RUNNING", "SUCCEEDED", "FAILED")
DECISION_STATUSES = ("RETAINED", "AUTO_DUPLICATE")
CANDIDATE_STATUSES = ("PENDING_HUMAN_REVIEW", "CONFIRMED_DUPLICATE", "REJECTED")


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


def initialize_corpus_build_ledger(db_path: Path) -> None:
    initialize_execution_ledger(db_path)
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_corpus_builds (
                build_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                input_records INTEGER NOT NULL DEFAULT 0 CHECK (input_records >= 0),
                unique_records INTEGER NOT NULL DEFAULT 0 CHECK (unique_records >= 0),
                duplicates_removed INTEGER NOT NULL DEFAULT 0 CHECK (duplicates_removed >= 0),
                possible_duplicates INTEGER NOT NULL DEFAULT 0 CHECK (possible_duplicates >= 0),
                prisma_records_identified INTEGER NOT NULL DEFAULT 0 CHECK (prisma_records_identified >= 0),
                prisma_duplicates_removed INTEGER NOT NULL DEFAULT 0 CHECK (prisma_duplicates_removed >= 0),
                prisma_records_after_deduplication INTEGER NOT NULL DEFAULT 0 CHECK (prisma_records_after_deduplication >= 0),
                normalized_jsonl_path TEXT NOT NULL DEFAULT '',
                master_jsonl_path TEXT NOT NULL DEFAULT '',
                metadata_csv_path TEXT NOT NULL DEFAULT '',
                decisions_csv_path TEXT NOT NULL DEFAULT '',
                candidates_csv_path TEXT NOT NULL DEFAULT '',
                prisma_summary_path TEXT NOT NULL DEFAULT '',
                manifest_path TEXT NOT NULL DEFAULT '',
                manifest_sha256 TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (run_id) REFERENCES search_runs(run_id),
                FOREIGN KEY (version_id) REFERENCES search_strategy_versions(version_id)
            );

            CREATE INDEX IF NOT EXISTS idx_search_corpus_builds_run
                ON search_corpus_builds(run_id, started_at DESC);

            CREATE TABLE IF NOT EXISTS search_dedup_decisions (
                decision_id TEXT PRIMARY KEY,
                build_id TEXT NOT NULL,
                source_record_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                source_row_number INTEGER NOT NULL CHECK (source_row_number > 0),
                master_document_id TEXT NOT NULL,
                decision_status TEXT NOT NULL CHECK (decision_status IN ('RETAINED', 'AUTO_DUPLICATE')),
                match_type TEXT NOT NULL,
                match_value TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (build_id) REFERENCES search_corpus_builds(build_id),
                UNIQUE (build_id, source_record_id)
            );

            CREATE INDEX IF NOT EXISTS idx_search_dedup_decisions_build
                ON search_dedup_decisions(build_id, master_document_id);

            CREATE TABLE IF NOT EXISTS search_duplicate_candidates (
                candidate_id TEXT PRIMARY KEY,
                build_id TEXT NOT NULL,
                left_document_id TEXT NOT NULL,
                right_document_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                match_value TEXT NOT NULL,
                confidence TEXT NOT NULL,
                review_status TEXT NOT NULL
                    CHECK (review_status IN ('PENDING_HUMAN_REVIEW', 'CONFIRMED_DUPLICATE', 'REJECTED')),
                created_at TEXT NOT NULL,
                FOREIGN KEY (build_id) REFERENCES search_corpus_builds(build_id),
                UNIQUE (build_id, left_document_id, right_document_id, match_type, match_value)
            );
            """
        )


def create_corpus_build(
    db_path: Path,
    *,
    run_id: str,
    version_id: str,
    build_id: str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    if not run_id.strip() or not version_id.strip():
        raise ValueError("run_id and version_id are required")
    initialize_corpus_build_ledger(db_path)
    resolved = build_id or f"corpus_build_{uuid4().hex}"
    timestamp = started_at or _now_iso()
    with _connect(db_path) as connection:
        connection.execute(
            "INSERT INTO search_corpus_builds (build_id, run_id, version_id, status, started_at) VALUES (?, ?, ?, 'RUNNING', ?)",
            (resolved, run_id.strip(), version_id.strip(), timestamp),
        )
    return {
        "build_id": resolved,
        "run_id": run_id.strip(),
        "version_id": version_id.strip(),
        "status": "RUNNING",
        "started_at": timestamp,
    }


def record_dedup_decisions(
    db_path: Path,
    *,
    build_id: str,
    rows: list[dict[str, Any]],
) -> None:
    initialize_corpus_build_ledger(db_path)
    timestamp = _now_iso()
    payload = []
    for row in rows:
        status = str(row["decision_status"]).upper()
        if status not in DECISION_STATUSES:
            raise ValueError(f"invalid decision_status: {status}")
        payload.append(
            (
                f"dedup_decision_{uuid4().hex}",
                build_id,
                str(row["source_record_id"]),
                str(row["provider"]),
                int(row["source_row_number"]),
                str(row["master_document_id"]),
                status,
                str(row["match_type"]),
                str(row["match_value"]),
                str(row["confidence"]),
                timestamp,
            )
        )
    with _connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO search_dedup_decisions (
                decision_id, build_id, source_record_id, provider, source_row_number,
                master_document_id, decision_status, match_type, match_value,
                confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )


def record_duplicate_candidates(
    db_path: Path,
    *,
    build_id: str,
    rows: list[dict[str, Any]],
) -> None:
    initialize_corpus_build_ledger(db_path)
    timestamp = _now_iso()
    payload = []
    for row in rows:
        status = str(row.get("review_status") or "PENDING_HUMAN_REVIEW").upper()
        if status not in CANDIDATE_STATUSES:
            raise ValueError(f"invalid review_status: {status}")
        left, right = sorted(
            (str(row["left_document_id"]), str(row["right_document_id"]))
        )
        payload.append(
            (
                f"duplicate_candidate_{uuid4().hex}",
                build_id,
                left,
                right,
                str(row["match_type"]),
                str(row["match_value"]),
                str(row["confidence"]),
                status,
                timestamp,
            )
        )
    with _connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO search_duplicate_candidates (
                candidate_id, build_id, left_document_id, right_document_id,
                match_type, match_value, confidence, review_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )


def finish_corpus_build(
    db_path: Path,
    *,
    build_id: str,
    status: str,
    metrics: dict[str, int],
    paths: dict[str, str],
    manifest_sha256: str = "",
    error_message: str = "",
    finished_at: str | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().upper()
    if normalized_status not in {"SUCCEEDED", "FAILED"}:
        raise ValueError("terminal status must be SUCCEEDED or FAILED")
    completed = finished_at or _now_iso()
    values = {
        "input_records": int(metrics.get("input_records", 0)),
        "unique_records": int(metrics.get("unique_records", 0)),
        "duplicates_removed": int(metrics.get("duplicates_removed", 0)),
        "possible_duplicates": int(metrics.get("possible_duplicates", 0)),
        "prisma_records_identified": int(
            metrics.get("prisma_records_identified", 0)
        ),
        "prisma_duplicates_removed": int(
            metrics.get("prisma_duplicates_removed", 0)
        ),
        "prisma_records_after_deduplication": int(
            metrics.get("prisma_records_after_deduplication", 0)
        ),
    }
    if any(value < 0 for value in values.values()):
        raise ValueError("corpus metrics cannot be negative")
    initialize_corpus_build_ledger(db_path)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE search_corpus_builds SET
                status = ?, finished_at = ?, input_records = ?, unique_records = ?,
                duplicates_removed = ?, possible_duplicates = ?,
                prisma_records_identified = ?, prisma_duplicates_removed = ?,
                prisma_records_after_deduplication = ?, normalized_jsonl_path = ?,
                master_jsonl_path = ?, metadata_csv_path = ?, decisions_csv_path = ?,
                candidates_csv_path = ?, prisma_summary_path = ?, manifest_path = ?,
                manifest_sha256 = ?, error_message = ? WHERE build_id = ?
            """,
            (
                normalized_status,
                completed,
                values["input_records"],
                values["unique_records"],
                values["duplicates_removed"],
                values["possible_duplicates"],
                values["prisma_records_identified"],
                values["prisma_duplicates_removed"],
                values["prisma_records_after_deduplication"],
                paths.get("normalized_jsonl_path", ""),
                paths.get("master_jsonl_path", ""),
                paths.get("metadata_csv_path", ""),
                paths.get("decisions_csv_path", ""),
                paths.get("candidates_csv_path", ""),
                paths.get("prisma_summary_path", ""),
                paths.get("manifest_path", ""),
                manifest_sha256,
                error_message.strip(),
                build_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown build_id: {build_id}")
    return get_corpus_build(db_path, build_id) or {}


def get_corpus_build(db_path: Path, build_id: str) -> dict[str, Any] | None:
    initialize_corpus_build_ledger(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM search_corpus_builds WHERE build_id = ?",
            (build_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_corpus_builds(
    db_path: Path,
    *,
    run_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    initialize_corpus_build_ledger(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    params: list[object] = []
    where = ""
    if run_id:
        where = "WHERE run_id = ?"
        params.append(run_id)
    params.append(safe_limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM search_corpus_builds {where} ORDER BY started_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def export_decisions_json(
    db_path: Path,
    *,
    build_id: str,
) -> dict[str, list[dict[str, Any]]]:
    initialize_corpus_build_ledger(db_path)
    with _connect(db_path) as connection:
        decisions = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM search_dedup_decisions WHERE build_id = ? ORDER BY master_document_id, source_row_number",
                (build_id,),
            ).fetchall()
        ]
        candidates = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM search_duplicate_candidates WHERE build_id = ? ORDER BY left_document_id, right_document_id",
                (build_id,),
            ).fetchall()
        ]
    return {"decisions": decisions, "candidates": candidates}
