"""Additive SQLite ledger for saved-strategy search runs and artifacts.

This module extends the versioned search registry without altering its existing
schema. A run groups one or more provider executions for a frozen strategy
version. Provider artifacts record immutable result snapshots and exact query
metadata so identification counts can be reproduced and audited.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.strategy_registry import initialize_registry

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RUN_STATUSES = ("RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED")


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


def initialize_execution_ledger(db_path: Path) -> None:
    """Create additive run/artifact tables in the registry database."""
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_runs (
                run_id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL,
                breadth TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'CANCELLED')),
                provider_limit INTEGER NOT NULL CHECK (provider_limit > 0),
                resume_enabled INTEGER NOT NULL CHECK (resume_enabled IN (0, 1)),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                records_identified INTEGER NOT NULL DEFAULT 0
                    CHECK (records_identified >= 0),
                provider_reported_total_found INTEGER NOT NULL DEFAULT 0
                    CHECK (provider_reported_total_found >= 0),
                prisma_records_identified INTEGER NOT NULL DEFAULT 0
                    CHECK (prisma_records_identified >= 0),
                manifest_path TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (version_id) REFERENCES search_strategy_versions(version_id)
            );

            CREATE INDEX IF NOT EXISTS idx_search_runs_version
                ON search_runs(version_id, started_at DESC);

            CREATE TABLE IF NOT EXISTS search_execution_artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                breadth TEXT NOT NULL,
                exact_expression TEXT NOT NULL,
                provider_query TEXT NOT NULL,
                provider_filter TEXT NOT NULL DEFAULT '',
                provider_status TEXT NOT NULL,
                records_returned INTEGER NOT NULL DEFAULT 0
                    CHECK (records_returned >= 0),
                total_found INTEGER CHECK (total_found IS NULL OR total_found >= 0),
                snapshot_path TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL,
                checkpoint_path TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES search_runs(run_id),
                FOREIGN KEY (execution_id) REFERENCES search_executions(execution_id),
                FOREIGN KEY (version_id) REFERENCES search_strategy_versions(version_id),
                UNIQUE (run_id, provider)
            );

            CREATE INDEX IF NOT EXISTS idx_search_execution_artifacts_run
                ON search_execution_artifacts(run_id, provider);
            """
        )


def create_search_run(
    db_path: Path,
    *,
    version_id: str,
    breadth: str,
    provider_limit: int,
    resume_enabled: bool,
    run_id: str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    """Create a RUNNING group for one frozen strategy-version execution."""
    if not version_id.strip():
        raise ValueError("version_id is required")
    if not breadth.strip():
        raise ValueError("breadth is required")
    if int(provider_limit) <= 0:
        raise ValueError("provider_limit must be greater than zero")

    initialize_execution_ledger(db_path)
    resolved_run_id = run_id or f"search_run_{uuid4().hex}"
    timestamp = started_at or _now_iso()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO search_runs (
                run_id, version_id, breadth, status, provider_limit,
                resume_enabled, started_at
            ) VALUES (?, ?, ?, 'RUNNING', ?, ?, ?)
            """,
            (
                resolved_run_id,
                version_id.strip(),
                breadth.strip(),
                int(provider_limit),
                int(bool(resume_enabled)),
                timestamp,
            ),
        )
    return {
        "run_id": resolved_run_id,
        "version_id": version_id.strip(),
        "breadth": breadth.strip(),
        "status": "RUNNING",
        "provider_limit": int(provider_limit),
        "resume_enabled": bool(resume_enabled),
        "started_at": timestamp,
    }


def finish_search_run(
    db_path: Path,
    *,
    run_id: str,
    status: str,
    records_identified: int,
    provider_reported_total_found: int,
    prisma_records_identified: int,
    manifest_path: str,
    error_message: str = "",
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Finalize one run after every requested provider has been attempted."""
    normalized_status = status.strip().upper()
    if normalized_status not in RUN_STATUSES or normalized_status == "RUNNING":
        raise ValueError("terminal run status must be SUCCEEDED, PARTIAL, FAILED, or CANCELLED")
    for label, value in (
        ("records_identified", records_identified),
        ("provider_reported_total_found", provider_reported_total_found),
        ("prisma_records_identified", prisma_records_identified),
    ):
        if int(value) < 0:
            raise ValueError(f"{label} cannot be negative")

    initialize_execution_ledger(db_path)
    completed_at = finished_at or _now_iso()
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE search_runs
            SET status = ?, finished_at = ?, records_identified = ?,
                provider_reported_total_found = ?, prisma_records_identified = ?,
                manifest_path = ?, error_message = ?
            WHERE run_id = ?
            """,
            (
                normalized_status,
                completed_at,
                int(records_identified),
                int(provider_reported_total_found),
                int(prisma_records_identified),
                manifest_path.strip(),
                error_message.strip(),
                run_id,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown run_id: {run_id}")
    return get_search_run(db_path, run_id) or {}


def record_execution_artifact(
    db_path: Path,
    *,
    run_id: str,
    execution_id: str,
    version_id: str,
    provider: str,
    breadth: str,
    exact_expression: str,
    provider_query: str,
    provider_filter: str,
    provider_status: str,
    records_returned: int,
    total_found: int | None,
    snapshot_path: str,
    snapshot_sha256: str,
    checkpoint_path: str = "",
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Link an immutable provider snapshot to its registry execution row."""
    required = {
        "run_id": run_id,
        "execution_id": execution_id,
        "version_id": version_id,
        "provider": provider,
        "breadth": breadth,
        "exact_expression": exact_expression,
        "provider_query": provider_query,
        "provider_status": provider_status,
        "snapshot_path": snapshot_path,
        "snapshot_sha256": snapshot_sha256,
    }
    missing = [name for name, value in required.items() if not str(value).strip()]
    if missing:
        raise ValueError(f"required artifact fields are blank: {', '.join(missing)}")
    if int(records_returned) < 0:
        raise ValueError("records_returned cannot be negative")
    if total_found is not None and int(total_found) < 0:
        raise ValueError("total_found cannot be negative")

    initialize_execution_ledger(db_path)
    artifact_id = f"search_artifact_{uuid4().hex}"
    timestamp = created_at or _now_iso()
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO search_execution_artifacts (
                artifact_id, run_id, execution_id, version_id, provider, breadth,
                exact_expression, provider_query, provider_filter, provider_status,
                records_returned, total_found, snapshot_path, snapshot_sha256,
                checkpoint_path, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                run_id.strip(),
                execution_id.strip(),
                version_id.strip(),
                provider.strip(),
                breadth.strip(),
                exact_expression.strip(),
                provider_query.strip(),
                provider_filter.strip(),
                provider_status.strip(),
                int(records_returned),
                int(total_found) if total_found is not None else None,
                snapshot_path.strip(),
                snapshot_sha256.strip(),
                checkpoint_path.strip(),
                metadata_json,
                timestamp,
            ),
        )
    return {
        "artifact_id": artifact_id,
        "run_id": run_id.strip(),
        "execution_id": execution_id.strip(),
        "version_id": version_id.strip(),
        "provider": provider.strip(),
        "breadth": breadth.strip(),
        "exact_expression": exact_expression.strip(),
        "provider_query": provider_query.strip(),
        "provider_filter": provider_filter.strip(),
        "provider_status": provider_status.strip(),
        "records_returned": int(records_returned),
        "total_found": int(total_found) if total_found is not None else None,
        "snapshot_path": snapshot_path.strip(),
        "snapshot_sha256": snapshot_sha256.strip(),
        "checkpoint_path": checkpoint_path.strip(),
        "metadata": metadata or {},
        "created_at": timestamp,
    }


def _decode_run(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    out["resume_enabled"] = bool(out["resume_enabled"])
    return out


def _decode_artifact(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    out["metadata"] = json.loads(out.pop("metadata_json") or "{}")
    return out


def get_search_run(db_path: Path, run_id: str) -> dict[str, Any] | None:
    initialize_execution_ledger(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM search_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    return _decode_run(row) if row is not None else None


def list_search_runs(
    db_path: Path,
    *,
    version_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    initialize_execution_ledger(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    params: list[object] = []
    where = ""
    if version_id:
        where = "WHERE version_id = ?"
        params.append(version_id)
    params.append(safe_limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM search_runs
            {where}
            ORDER BY started_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_decode_run(row) for row in rows]


def list_execution_artifacts(
    db_path: Path,
    *,
    run_id: str | None = None,
    version_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    initialize_execution_ledger(db_path)
    safe_limit = max(1, min(int(limit), 5000))
    clauses: list[str] = []
    params: list[object] = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if version_id:
        clauses.append("version_id = ?")
        params.append(version_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(safe_limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM search_execution_artifacts
            {where}
            ORDER BY created_at DESC, provider ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_decode_artifact(row) for row in rows]
