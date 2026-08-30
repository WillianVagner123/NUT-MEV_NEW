"""Audited Bank NutEV priority extension for the Article Workbench.

This module attaches the persisted bank ranking (rank/score/operational tier) to
an already-built Workbench without rerunning CORE, semantic extraction, or
excerpts. It writes a new SQLite database and switches the Workbench manifest
only after integrity and hash checks pass.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Iterable
from uuid import uuid4

from nutev.audit_guardrails import sha256_file
from nutev.reference_identity import canonical_identity


class WorkbenchPriorityError(RuntimeError):
    """Raised when bank priority cannot be attached with proven integrity."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkbenchPriorityError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkbenchPriorityError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkbenchPriorityError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise WorkbenchPriorityError(f"missing ranking JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WorkbenchPriorityError(
                    f"invalid ranking JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise WorkbenchPriorityError(
                    f"non-object ranking row at {path}:{line_number}"
                )
            rows.append(value)
    if not rows:
        raise WorkbenchPriorityError("ranking JSONL is empty")
    return rows


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256_file(path)


def _verified_ranking(output_root: Path, search_id: str) -> tuple[Path, str, list[dict[str, Any]]]:
    bank_root = output_root / "bank" / "searches" / search_id
    ranking_path = bank_root / "reference_ranking.jsonl"
    audit_path = bank_root / "AUDIT_MANIFEST.json"
    audit = _read_json(audit_path)
    if audit.get("audit_type") != "REFERENCE_RANKING_AUDIT" or audit.get("status") != "PASS":
        raise WorkbenchPriorityError("reference ranking audit is not PASS")
    expected = str(
        (((audit.get("outputs") or {}).get("ranking_jsonl") or {}).get("sha256")) or ""
    ).strip().lower()
    actual = sha256_file(ranking_path)
    if not expected or actual != expected:
        raise WorkbenchPriorityError(
            f"ranking SHA-256 mismatch: expected {expected or '(missing)'}, got {actual}"
        )
    return ranking_path, actual, _read_jsonl(ranking_path)


def _resolve_active_database(workbench_root: Path, manifest: dict[str, Any]) -> tuple[Path, str]:
    if manifest.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1":
        raise WorkbenchPriorityError("unexpected Workbench manifest type")
    if manifest.get("status") != "PASS":
        raise WorkbenchPriorityError("Workbench manifest is not PASS")
    output = (manifest.get("outputs") or {}).get("database") or {}
    expected = str(output.get("sha256") or "").strip().lower()
    raw = str(output.get("path") or "").strip()
    database = Path(raw) if raw else workbench_root / "evidence_workbench.sqlite"
    if not database.is_absolute():
        candidate = workbench_root / database.name
        database = candidate if candidate.is_file() else database.resolve()
    if not database.is_file() or not expected:
        raise WorkbenchPriorityError("active Workbench database or SHA-256 is missing")
    actual = sha256_file(database)
    if actual != expected:
        raise WorkbenchPriorityError(
            f"Workbench database SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return database, actual


def _tier(row: dict[str, Any]) -> str:
    direct = str(row.get("bank_processing_tier") or "").strip().upper()
    if direct in {"A", "B", "C", "D"}:
        return direct
    label = str(row.get("reference_tier") or "").strip().upper()
    for tier in ("A", "B", "C", "D"):
        if label == f"BANK_{tier}_PROCESSING_PRIORITY":
            return tier
    raise WorkbenchPriorityError("ranking row lacks a valid operational bank tier")


def _priority_rows(rows: Iterable[dict[str, Any]]) -> list[tuple[int, float | None, str, str]]:
    output: list[tuple[int, float | None, str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        document_id = canonical_identity(row)
        if not document_id:
            raise WorkbenchPriorityError(f"ranking row {index} has no canonical identity")
        if document_id in seen:
            raise WorkbenchPriorityError(f"duplicate ranking identity: {document_id}")
        seen.add(document_id)
        try:
            rank = int(row.get("reference_rank") or index)
        except (TypeError, ValueError) as exc:
            raise WorkbenchPriorityError(f"invalid reference_rank at row {index}") from exc
        if rank <= 0:
            raise WorkbenchPriorityError(f"invalid non-positive reference_rank at row {index}")
        raw_score = row.get("reference_score")
        try:
            score = float(raw_score) if raw_score not in (None, "") else None
        except (TypeError, ValueError):
            score = None
        tier = _tier(row)
        output.append((rank, score, f"BANK_{tier}_PROCESSING_PRIORITY", document_id))
    return output


def _update_pipeline_manifest(
    output_root: Path,
    search_id: str,
    *,
    database: Path,
    database_sha: str,
    workbench_manifest: Path,
    workbench_manifest_sha: str,
    extension: dict[str, Any],
) -> tuple[str | None, str | None]:
    path = output_root / "bank" / "searches" / search_id / "BANK_PIPELINE_MANIFEST.json"
    if not path.is_file():
        return None, None
    payload = _read_json(path)
    stages = payload.get("stages")
    if isinstance(stages, dict):
        workbench = stages.get("workbench")
        if isinstance(workbench, dict):
            workbench["database"] = str(database)
            workbench["manifest"] = str(workbench_manifest)
            hashes = workbench.get("output_sha256")
            if isinstance(hashes, dict):
                hashes["database"] = database_sha
                hashes["manifest"] = workbench_manifest_sha
    extensions = payload.setdefault("extensions", {})
    if isinstance(extensions, dict):
        extensions["bank_priority"] = extension
    return str(path), _atomic_json(path, payload)


def augment_workbench_priority(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
) -> dict[str, Any]:
    """Attach bank rank/score/tier to the Workbench in an atomic audited switch."""

    output_root = output_root.resolve()
    ranking_path, ranking_sha, ranking_rows = _verified_ranking(output_root, search_id)
    priorities = _priority_rows(ranking_rows)

    workbench_root = output_root / "scientific" / "workbench"
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest = _read_json(manifest_path)
    active_database, source_database_sha = _resolve_active_database(workbench_root, manifest)

    target_database = workbench_root / "evidence_workbench_priority.sqlite"
    tmp_database = workbench_root / f".evidence_workbench_priority.{uuid4().hex}.tmp.sqlite"
    shutil.copy2(active_database, tmp_database)

    matched = 0
    article_count = 0
    try:
        with sqlite3.connect(tmp_database) as connection:
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(article_cards)").fetchall()
            }
            if "reference_rank" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN reference_rank INTEGER")
            if "reference_score" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN reference_score REAL")
            if "reference_tier" not in columns:
                connection.execute("ALTER TABLE article_cards ADD COLUMN reference_tier TEXT")

            connection.execute(
                "UPDATE article_cards SET reference_rank=NULL, reference_score=NULL, reference_tier=NULL"
            )
            connection.executemany(
                """
                UPDATE article_cards
                SET reference_rank=?, reference_score=?, reference_tier=?
                WHERE document_id=?
                """,
                priorities,
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_reference_rank ON article_cards(reference_rank)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_reference_tier ON article_cards(reference_tier)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_reference_score ON article_cards(reference_score DESC)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO workbench_meta(key,value) VALUES (?,?)",
                ("bank_priority_search_id", search_id),
            )
            connection.execute(
                "INSERT OR REPLACE INTO workbench_meta(key,value) VALUES (?,?)",
                ("bank_priority_ranking_sha256", ranking_sha),
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise WorkbenchPriorityError("priority Workbench SQLite integrity_check failed")
            article_count = int(connection.execute("SELECT COUNT(*) FROM article_cards").fetchone()[0])
            matched = int(
                connection.execute(
                    "SELECT COUNT(*) FROM article_cards WHERE reference_rank IS NOT NULL"
                ).fetchone()[0]
            )
    except Exception:
        tmp_database.unlink(missing_ok=True)
        raise

    if matched != article_count or matched != len(priorities):
        tmp_database.unlink(missing_ok=True)
        raise WorkbenchPriorityError(
            "priority join is incomplete: "
            f"articles={article_count}, ranking={len(priorities)}, matched={matched}"
        )

    database_sha = sha256_file(tmp_database)
    tmp_database.replace(target_database)

    extension = {
        "status": "PASS",
        "created_at": _now(),
        "search_id": search_id,
        "ranking_jsonl": str(ranking_path),
        "ranking_sha256": ranking_sha,
        "source_database_sha256": source_database_sha,
        "records": len(priorities),
        "matched_articles": matched,
        "fields": ["reference_rank", "reference_score", "reference_tier"],
        "semantics": (
            "Operational reading/processing priority only; not eligibility, quality, "
            "risk of bias, certainty, or recommendation."
        ),
    }
    manifest.setdefault("extensions", {})["bank_priority"] = extension
    manifest["outputs"]["database"] = {
        "path": str(target_database),
        "sha256": database_sha,
    }
    manifest_sha = _atomic_json(manifest_path, manifest)

    pipeline_path, pipeline_sha = _update_pipeline_manifest(
        output_root,
        search_id,
        database=target_database,
        database_sha=database_sha,
        workbench_manifest=manifest_path,
        workbench_manifest_sha=manifest_sha,
        extension=extension,
    )

    return {
        "mode": "NUTEV_WORKBENCH_BANK_PRIORITY",
        "status": "COMPLETE",
        "search_id": search_id,
        "articles": article_count,
        "matched_articles": matched,
        "database": str(target_database),
        "database_sha256": database_sha,
        "workbench_manifest": str(manifest_path),
        "workbench_manifest_sha256": manifest_sha,
        "bank_pipeline_manifest": pipeline_path,
        "bank_pipeline_manifest_sha256": pipeline_sha,
        "ranking_sha256": ranking_sha,
        "guardrail": extension["semantics"],
    }
