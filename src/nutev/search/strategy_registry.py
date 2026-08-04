"""Versioned SQLite registry for global NutEV search strategies.

The registry is intentionally small and dependency-free. It provides an
append-only audit trail for article-independent search strategies and their
executions while the broader platform migrates toward a full relational model.

A strategy is a stable identity (for example, "NutEV global search"). Every
save creates a new immutable version. Pilot searches are not PRISMA-eligible by
default; formal and supplementary searches are eligible unless explicitly
marked otherwise.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

ARTICLE_SCOPE_ALL = "all_articles"
SEARCH_TYPES = ("PILOT", "FORMAL", "SUPPLEMENTARY")
EXECUTION_STATUSES = ("PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED")
REGISTRY_SCHEMA_VERSION = 1
LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class StrategyVersionRecord:
    strategy_id: str
    version_id: str
    title: str
    version: int
    article_scope: str
    search_type: str
    prisma_eligible: bool
    query_text: str
    query_terms: list[str]
    filters: dict[str, Any]
    providers: dict[str, Any]
    notes: str
    created_at: str
    created_by: str
    checksum_sha256: str


def default_registry_path(project_root: Path) -> Path:
    """Return the canonical SQLite path inside a NutEV project output."""
    return Path(project_root) / "01_querypacks" / "search_registry.sqlite3"


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


def initialize_registry(db_path: Path) -> None:
    """Create the registry schema when it does not exist."""
    with _connect(db_path) as connection:
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > REGISTRY_SCHEMA_VERSION:
            raise RuntimeError(
                f"search registry schema {current_version} is newer than supported "
                f"version {REGISTRY_SCHEMA_VERSION}"
            )

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_strategies (
                strategy_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                article_scope TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_strategy_versions (
                version_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                version INTEGER NOT NULL CHECK (version > 0),
                search_type TEXT NOT NULL
                    CHECK (search_type IN ('PILOT', 'FORMAL', 'SUPPLEMENTARY')),
                prisma_eligible INTEGER NOT NULL CHECK (prisma_eligible IN (0, 1)),
                query_text TEXT NOT NULL,
                query_terms_json TEXT NOT NULL,
                filters_json TEXT NOT NULL,
                providers_json TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                checksum_sha256 TEXT NOT NULL,
                FOREIGN KEY (strategy_id) REFERENCES search_strategies(strategy_id),
                UNIQUE (strategy_id, version)
            );

            CREATE INDEX IF NOT EXISTS idx_search_strategy_versions_strategy
                ON search_strategy_versions(strategy_id, version DESC);

            CREATE TABLE IF NOT EXISTS search_executions (
                execution_id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                breadth TEXT NOT NULL,
                expression TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('PLANNED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                records_found INTEGER CHECK (records_found IS NULL OR records_found >= 0),
                error_message TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (version_id) REFERENCES search_strategy_versions(version_id)
            );

            CREATE INDEX IF NOT EXISTS idx_search_executions_version
                ON search_executions(version_id, started_at DESC);
            """
        )
        connection.execute(f"PRAGMA user_version = {REGISTRY_SCHEMA_VERSION}")


def _clean_terms(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = [str(item) for item in value]
    else:
        candidates = [str(value)]

    terms: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        term = candidate.strip()
        key = term.casefold()
        if term and key not in seen:
            terms.append(term)
            seen.add(key)
    return terms


def _canonical_strategy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("strategy_payload must be a dictionary")

    query_terms = _clean_terms(payload.get("query"))
    if not query_terms:
        raise ValueError("strategy_payload.query must contain at least one term")

    providers = payload.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("strategy_payload.providers must contain at least one provider")

    filters = payload.get("filters") or {}
    if not isinstance(filters, dict):
        raise TypeError("strategy_payload.filters must be a dictionary")

    return {
        "article_scope": str(payload.get("article_scope") or ARTICLE_SCOPE_ALL),
        "query": query_terms,
        "filters": filters,
        "providers": providers,
    }


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strategy_checksum(
    *,
    canonical_payload: dict[str, Any],
    search_type: str,
    prisma_eligible: bool,
) -> str:
    content = {
        "strategy": canonical_payload,
        "search_type": search_type,
        "prisma_eligible": prisma_eligible,
    }
    return sha256(_json_text(content).encode("utf-8")).hexdigest()


def save_strategy_version(
    db_path: Path,
    *,
    title: str,
    query_text: str,
    strategy_payload: dict[str, Any],
    search_type: str,
    created_by: str,
    notes: str = "",
    strategy_id: str | None = None,
    prisma_eligible: bool | None = None,
    created_at: str | None = None,
) -> StrategyVersionRecord:
    """Create a strategy or append an immutable version to an existing one."""
    clean_title = title.strip()
    clean_query_text = query_text.strip()
    clean_created_by = created_by.strip()
    normalized_type = search_type.strip().upper()

    if not clean_title:
        raise ValueError("title is required")
    if not clean_query_text:
        raise ValueError("query_text is required")
    if not clean_created_by:
        raise ValueError("created_by is required for auditability")
    if normalized_type not in SEARCH_TYPES:
        raise ValueError(f"search_type must be one of {SEARCH_TYPES}")

    canonical_payload = _canonical_strategy_payload(strategy_payload)
    if prisma_eligible is None:
        prisma_eligible = normalized_type != "PILOT"

    timestamp = created_at or _now_iso()
    resolved_strategy_id = strategy_id or f"strategy_{uuid4().hex}"
    version_id = f"strategy_version_{uuid4().hex}"
    checksum = _strategy_checksum(
        canonical_payload=canonical_payload,
        search_type=normalized_type,
        prisma_eligible=bool(prisma_eligible),
    )

    initialize_registry(db_path)
    with _connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT title, article_scope FROM search_strategies WHERE strategy_id = ?",
            (resolved_strategy_id,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO search_strategies
                    (strategy_id, title, article_scope, created_at, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    resolved_strategy_id,
                    clean_title,
                    canonical_payload["article_scope"],
                    timestamp,
                    clean_created_by,
                ),
            )
        else:
            if str(existing["title"]) != clean_title:
                raise ValueError("title cannot change when appending a strategy version")
            if str(existing["article_scope"]) != canonical_payload["article_scope"]:
                raise ValueError("article_scope cannot change when appending a strategy version")

        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version "
            "FROM search_strategy_versions WHERE strategy_id = ?",
            (resolved_strategy_id,),
        ).fetchone()
        next_version = int(row["next_version"])

        connection.execute(
            """
            INSERT INTO search_strategy_versions (
                version_id, strategy_id, version, search_type, prisma_eligible,
                query_text, query_terms_json, filters_json, providers_json,
                notes, created_at, created_by, checksum_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                resolved_strategy_id,
                next_version,
                normalized_type,
                int(bool(prisma_eligible)),
                clean_query_text,
                _json_text(canonical_payload["query"]),
                _json_text(canonical_payload["filters"]),
                _json_text(canonical_payload["providers"]),
                notes.strip(),
                timestamp,
                clean_created_by,
                checksum,
            ),
        )

    return StrategyVersionRecord(
        strategy_id=resolved_strategy_id,
        version_id=version_id,
        title=clean_title,
        version=next_version,
        article_scope=canonical_payload["article_scope"],
        search_type=normalized_type,
        prisma_eligible=bool(prisma_eligible),
        query_text=clean_query_text,
        query_terms=list(canonical_payload["query"]),
        filters=dict(canonical_payload["filters"]),
        providers=dict(canonical_payload["providers"]),
        notes=notes.strip(),
        created_at=timestamp,
        created_by=clean_created_by,
        checksum_sha256=checksum,
    )


def _decode_version_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "strategy_id": row["strategy_id"],
        "version_id": row["version_id"],
        "title": row["title"],
        "version": int(row["version"]),
        "article_scope": row["article_scope"],
        "search_type": row["search_type"],
        "prisma_eligible": bool(row["prisma_eligible"]),
        "query_text": row["query_text"],
        "query_terms": json.loads(row["query_terms_json"]),
        "filters": json.loads(row["filters_json"]),
        "providers": json.loads(row["providers_json"]),
        "notes": row["notes"],
        "created_at": row["created_at"],
        "created_by": row["created_by"],
        "checksum_sha256": row["checksum_sha256"],
    }


def list_strategies(db_path: Path) -> list[dict[str, Any]]:
    """Return one row per strategy, including its latest version metadata."""
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                s.strategy_id,
                s.title,
                s.article_scope,
                s.created_at,
                s.created_by,
                v.version AS latest_version,
                v.version_id AS latest_version_id,
                v.search_type AS latest_search_type,
                v.prisma_eligible AS latest_prisma_eligible,
                v.created_at AS updated_at
            FROM search_strategies AS s
            JOIN search_strategy_versions AS v
              ON v.strategy_id = s.strategy_id
             AND v.version = (
                 SELECT MAX(v2.version)
                 FROM search_strategy_versions AS v2
                 WHERE v2.strategy_id = s.strategy_id
             )
            ORDER BY v.created_at DESC, s.title ASC
            """
        ).fetchall()
    return [
        {
            **dict(row),
            "latest_version": int(row["latest_version"]),
            "latest_prisma_eligible": bool(row["latest_prisma_eligible"]),
        }
        for row in rows
    ]


def list_strategy_versions(
    db_path: Path,
    *,
    strategy_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return immutable strategy versions, newest first."""
    initialize_registry(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    params: list[object] = []
    where = ""
    if strategy_id:
        where = "WHERE v.strategy_id = ?"
        params.append(strategy_id)
    params.append(safe_limit)

    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                v.*,
                s.title,
                s.article_scope
            FROM search_strategy_versions AS v
            JOIN search_strategies AS s ON s.strategy_id = v.strategy_id
            {where}
            ORDER BY v.created_at DESC, v.version DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_decode_version_row(row) for row in rows]


def get_strategy_version(db_path: Path, version_id: str) -> dict[str, Any] | None:
    """Load one immutable strategy version by ID."""
    initialize_registry(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT v.*, s.title, s.article_scope
            FROM search_strategy_versions AS v
            JOIN search_strategies AS s ON s.strategy_id = v.strategy_id
            WHERE v.version_id = ?
            """,
            (version_id,),
        ).fetchone()
    return _decode_version_row(row) if row is not None else None


def record_search_execution(
    db_path: Path,
    *,
    version_id: str,
    provider: str,
    breadth: str,
    expression: str,
    status: str = "PLANNED",
    records_found: int | None = None,
    error_message: str = "",
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Append one execution event linked to a frozen strategy version."""
    normalized_status = status.strip().upper()
    if normalized_status not in EXECUTION_STATUSES:
        raise ValueError(f"status must be one of {EXECUTION_STATUSES}")
    if not provider.strip():
        raise ValueError("provider is required")
    if not breadth.strip():
        raise ValueError("breadth is required")
    if not expression.strip():
        raise ValueError("expression is required")
    if records_found is not None and records_found < 0:
        raise ValueError("records_found cannot be negative")

    initialize_registry(db_path)
    execution_id = f"search_execution_{uuid4().hex}"
    started = started_at or _now_iso()
    completed = normalized_status in {"SUCCEEDED", "FAILED", "CANCELLED"}
    finished = finished_at or (_now_iso() if completed else None)

    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO search_executions (
                execution_id, version_id, provider, breadth, expression, status,
                started_at, finished_at, records_found, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                version_id,
                provider.strip(),
                breadth.strip(),
                expression.strip(),
                normalized_status,
                started,
                finished,
                records_found,
                error_message.strip(),
            ),
        )

    return {
        "execution_id": execution_id,
        "version_id": version_id,
        "provider": provider.strip(),
        "breadth": breadth.strip(),
        "expression": expression.strip(),
        "status": normalized_status,
        "started_at": started,
        "finished_at": finished,
        "records_found": records_found,
        "error_message": error_message.strip(),
    }


def list_search_executions(
    db_path: Path,
    *,
    version_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return execution events, newest first."""
    initialize_registry(db_path)
    safe_limit = max(1, min(int(limit), 1000))
    params: list[object] = []
    where = ""
    if version_id:
        where = "WHERE e.version_id = ?"
        params.append(version_id)
    params.append(safe_limit)

    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT e.*
            FROM search_executions AS e
            {where}
            ORDER BY e.started_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def record_as_dict(record: StrategyVersionRecord) -> dict[str, Any]:
    """Serialize a saved strategy version for UI or JSON export."""
    return asdict(record)
