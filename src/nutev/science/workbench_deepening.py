"""Atomic overlay of selectively deepened article evidence into the NutEV Workbench.

A deepening batch replaces only the affected article cards/excerpts/result bundles
inside a copy of the active Workbench. The active manifest is switched only after
source-hash verification and SQLite integrity checks pass.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


class WorkbenchDeepeningError(RuntimeError):
    """Raised when a selective deepening overlay cannot be proven safe."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkbenchDeepeningError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkbenchDeepeningError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkbenchDeepeningError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        raise WorkbenchDeepeningError(f"missing {label}: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WorkbenchDeepeningError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise WorkbenchDeepeningError(
                    f"non-object {label} row at {path}:{line_number}"
                )
            rows.append(value)
    if not rows and not allow_empty:
        raise WorkbenchDeepeningError(f"{label} is empty: {path}")
    return rows


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256_file(path)


def _manifest_output_sha(manifest: Mapping[str, Any], key: str, *, label: str) -> str:
    value = str((((manifest.get("outputs") or {}).get(key) or {}).get("sha256")) or "").strip().lower()
    if not value:
        raise WorkbenchDeepeningError(f"{label} missing SHA-256 for {key}")
    return value


def _verify_file(path: Path, expected: str, *, label: str) -> str:
    if not path.is_file():
        raise WorkbenchDeepeningError(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise WorkbenchDeepeningError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def _verify_sources(
    article_cards_jsonl: Path,
    evidence_excerpts_jsonl: Path,
    result_bundles_jsonl: Path,
    excerpt_manifest_path: Path,
    enrichments_jsonl: Path,
    enrichment_manifest_path: Path,
) -> dict[str, str]:
    excerpt_manifest = _read_json(excerpt_manifest_path)
    if excerpt_manifest.get("excerpt_type") != "NUTEV_EVIDENCE_EXCERPTS_RESULTS":
        raise WorkbenchDeepeningError("unexpected excerpt manifest type")
    if excerpt_manifest.get("status") != "PASS":
        raise WorkbenchDeepeningError("excerpt manifest is not PASS")

    enrichment_manifest = _read_json(enrichment_manifest_path)
    if enrichment_manifest.get("enrichment_type") != "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT":
        raise WorkbenchDeepeningError("unexpected enrichment manifest type")
    if enrichment_manifest.get("status") != "PASS":
        raise WorkbenchDeepeningError("enrichment manifest is not PASS")

    return {
        "article_cards": _verify_file(
            article_cards_jsonl,
            _manifest_output_sha(excerpt_manifest, "article_evidence_cards", label="excerpt manifest"),
            label="article evidence cards",
        ),
        "evidence_excerpts": _verify_file(
            evidence_excerpts_jsonl,
            _manifest_output_sha(excerpt_manifest, "evidence_excerpts", label="excerpt manifest"),
            label="evidence excerpts",
        ),
        "result_bundles": _verify_file(
            result_bundles_jsonl,
            _manifest_output_sha(excerpt_manifest, "result_bundles", label="excerpt manifest"),
            label="result bundles",
        ),
        "enrichments": _verify_file(
            enrichments_jsonl,
            _manifest_output_sha(enrichment_manifest, "document_enrichments", label="enrichment manifest"),
            label="document enrichments",
        ),
        "excerpt_manifest": sha256_file(excerpt_manifest_path),
        "enrichment_manifest": sha256_file(enrichment_manifest_path),
    }


def _active_database(workbench_root: Path, manifest: Mapping[str, Any]) -> tuple[Path, str]:
    if manifest.get("workbench_type") != "NUTEV_ARTICLE_WORKBENCH_V1" or manifest.get("status") != "PASS":
        raise WorkbenchDeepeningError("active Workbench manifest is not a passing v1 manifest")
    output = (manifest.get("outputs") or {}).get("database") or {}
    raw = str(output.get("path") or "").strip()
    expected = str(output.get("sha256") or "").strip().lower()
    database = Path(raw) if raw else workbench_root / "evidence_workbench.sqlite"
    if not database.is_absolute():
        candidate = workbench_root / database.name
        database = candidate if candidate.is_file() else database.resolve()
    if not expected:
        raise WorkbenchDeepeningError("active Workbench database SHA-256 missing")
    return database, _verify_file(database, expected, label="active Workbench database")


def _search_text(card: Mapping[str, Any]) -> str:
    identity = card.get("identity") or {}
    reference = card.get("reference") or {}
    snapshot = card.get("study_snapshot") or {}
    parts: list[str] = []
    if isinstance(identity, Mapping):
        parts.extend(str(identity.get(key) or "") for key in ("title", "doi", "pmid", "source_provider"))
    if isinstance(reference, Mapping):
        parts.extend(str(reference.get(key) or "") for key in ("authors", "journal", "reference_stub"))
    if isinstance(snapshot, Mapping):
        for values in snapshot.values():
            if isinstance(values, list):
                parts.extend(str(value) for value in values)
            elif values:
                parts.append(str(values))
    return " ".join(" ".join(parts).casefold().split())[:20000]


def _index_unique(rows: Iterable[dict[str, Any]], *, key: str, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            raise WorkbenchDeepeningError(f"{label} row missing {key}")
        if value in indexed:
            raise WorkbenchDeepeningError(f"duplicate {label} {key}: {value}")
        indexed[value] = row
    return indexed


def overlay_workbench_deepening(
    *,
    workbench_root: Path,
    batch_id: str,
    search_id: str,
    tier: str,
    article_cards_jsonl: Path,
    evidence_excerpts_jsonl: Path,
    result_bundles_jsonl: Path,
    excerpt_manifest: Path,
    enrichments_jsonl: Path,
    enrichment_manifest: Path,
) -> dict[str, Any]:
    """Atomically overlay one verified selective-deepening batch into the Workbench."""

    tier = str(tier or "").strip().upper()
    if tier not in {"A", "B", "C", "D"}:
        raise WorkbenchDeepeningError(f"invalid bank tier: {tier}")
    source_shas = _verify_sources(
        article_cards_jsonl,
        evidence_excerpts_jsonl,
        result_bundles_jsonl,
        excerpt_manifest,
        enrichments_jsonl,
        enrichment_manifest,
    )
    cards = _read_jsonl(article_cards_jsonl, label="article cards")
    excerpts = _read_jsonl(evidence_excerpts_jsonl, label="evidence excerpts", allow_empty=True)
    bundles = _read_jsonl(result_bundles_jsonl, label="result bundles", allow_empty=True)
    enrichments = _read_jsonl(enrichments_jsonl, label="document enrichments")
    cards_by_doc = _index_unique(cards, key="document_id", label="article card")
    enrichments_by_doc = _index_unique(enrichments, key="document_id", label="enrichment")
    if set(cards_by_doc) != set(enrichments_by_doc):
        raise WorkbenchDeepeningError("deepening cards and enrichments do not contain the same document IDs")
    batch_documents = set(cards_by_doc)
    for label, rows in (("excerpt", excerpts), ("result bundle", bundles)):
        seen: set[str] = set()
        for row in rows:
            row_id = str(row.get("id") or "").strip()
            document_id = str(row.get("document_id") or "").strip()
            if not row_id or row_id in seen:
                raise WorkbenchDeepeningError(f"invalid/duplicate {label} id: {row_id or '<missing>'}")
            if document_id not in batch_documents:
                raise WorkbenchDeepeningError(f"{label} references document outside deepening batch: {document_id}")
            seen.add(row_id)

    workbench_root = workbench_root.resolve()
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest = _read_json(manifest_path)
    active_database, source_database_sha = _active_database(workbench_root, manifest)
    target_database = workbench_root / "evidence_workbench_deepened.sqlite"
    tmp_database = workbench_root / f".evidence_workbench_deepened.{uuid4().hex}.tmp.sqlite"
    shutil.copy2(active_database, tmp_database)

    now = _now()
    try:
        with sqlite3.connect(tmp_database) as connection:
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(article_cards)")}
            additions = {
                "deepening_status": "TEXT",
                "extraction_method": "TEXT",
                "ocr_used": "INTEGER",
                "text_chars": "INTEGER",
                "deepened_at": "TEXT",
            }
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE article_cards ADD COLUMN {name} {sql_type}")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_deepening_status ON article_cards(deepening_status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_article_extraction_method ON article_cards(extraction_method)"
            )

            existing = {
                str(row[0])
                for row in connection.execute(
                    "SELECT document_id FROM article_cards WHERE document_id IN (%s)"
                    % ",".join("?" for _ in batch_documents),
                    sorted(batch_documents),
                ).fetchall()
            }
            if existing != batch_documents:
                missing = sorted(batch_documents - existing)
                raise WorkbenchDeepeningError(
                    f"deepening batch contains documents missing from Workbench: {missing[:5]}"
                )

            for document_id in sorted(batch_documents):
                card = dict(cards_by_doc[document_id])
                enrichment = enrichments_by_doc[document_id]
                metadata = enrichment.get("metadata") or {}
                if not isinstance(metadata, Mapping):
                    metadata = {}
                card["deepening"] = {
                    "status": "deepened",
                    "batch_id": batch_id,
                    "search_id": search_id,
                    "tier": tier,
                    "extraction_method": enrichment.get("extraction_method"),
                    "ocr_used": bool(enrichment.get("ocr_used")),
                    "ocr_engine": enrichment.get("ocr_engine"),
                    "text_chars": int(enrichment.get("text_chars") or 0),
                    "text_sha256": enrichment.get("text_sha256"),
                    "full_text_status": card.get("full_text_status") or metadata.get("full_text_status"),
                    "warnings": list(enrichment.get("warnings") or []),
                    "deepened_at": now,
                    "semantics": "retrieval/extraction status only; not scientific inclusion or quality",
                }
                identity = card.get("identity") or {}
                reference = card.get("reference") or {}
                if not isinstance(identity, Mapping):
                    identity = {}
                if not isinstance(reference, Mapping):
                    reference = {}
                year = identity.get("year")
                try:
                    year_value = int(year) if year not in (None, "") else None
                except (TypeError, ValueError):
                    year_value = None
                connection.execute(
                    """
                    UPDATE article_cards
                    SET record_id=?, title=?, year=?, doi=?, pmid=?, source_provider=?,
                        document_class=?, full_text_status=?, cache_key=?, reference_stub=?,
                        llm_context_chars=?, search_text=?, card_json=?, deepening_status=?,
                        extraction_method=?, ocr_used=?, text_chars=?, deepened_at=?
                    WHERE document_id=?
                    """,
                    (
                        card.get("record_id"),
                        identity.get("title"),
                        year_value,
                        identity.get("doi"),
                        identity.get("pmid"),
                        identity.get("source_provider"),
                        card.get("document_class"),
                        card.get("full_text_status"),
                        str(card.get("cache_key") or ""),
                        reference.get("reference_stub"),
                        int(card.get("llm_context_chars") or 0),
                        _search_text(card),
                        json.dumps(card, ensure_ascii=False, sort_keys=True, default=str),
                        "deepened",
                        enrichment.get("extraction_method"),
                        1 if enrichment.get("ocr_used") else 0,
                        int(enrichment.get("text_chars") or 0),
                        now,
                        document_id,
                    ),
                )
                connection.execute("DELETE FROM evidence_excerpts WHERE document_id=?", (document_id,))
                connection.execute("DELETE FROM result_bundles WHERE document_id=?", (document_id,))

            for excerpt in excerpts:
                connection.execute(
                    """
                    INSERT INTO evidence_excerpts(
                        excerpt_id, document_id, kind, section, locator, priority_score,
                        verbatim_excerpt, excerpt_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        excerpt["id"], excerpt["document_id"], excerpt["kind"], excerpt.get("section"),
                        excerpt.get("locator"), float(excerpt.get("priority_score") or 0.0),
                        excerpt["verbatim_excerpt"],
                        json.dumps(excerpt, ensure_ascii=False, sort_keys=True, default=str),
                    ),
                )
            for bundle in bundles:
                connection.execute(
                    """
                    INSERT INTO result_bundles(
                        result_id, document_id, result_kind, priority_score, result_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        bundle["id"], bundle["document_id"], bundle["result_kind"],
                        float(bundle.get("priority_score") or 0.0),
                        json.dumps(bundle, ensure_ascii=False, sort_keys=True, default=str),
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO workbench_meta(key,value) VALUES (?,?)",
                ("last_deepening_batch", batch_id),
            )
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise WorkbenchDeepeningError("deepened Workbench SQLite integrity_check failed")
            counts = {
                "articles": int(connection.execute("SELECT COUNT(*) FROM article_cards").fetchone()[0]),
                "evidence_excerpts": int(connection.execute("SELECT COUNT(*) FROM evidence_excerpts").fetchone()[0]),
                "result_bundles": int(connection.execute("SELECT COUNT(*) FROM result_bundles").fetchone()[0]),
                "deepened_articles": int(
                    connection.execute("SELECT COUNT(*) FROM article_cards WHERE deepening_status='deepened'").fetchone()[0]
                ),
            }
            retrieval_counts = Counter(
                str(row[0] or "unknown")
                for row in connection.execute(
                    "SELECT full_text_status FROM article_cards WHERE deepening_status='deepened'"
                ).fetchall()
            )
            extraction_counts = Counter(
                str(row[0] or "unknown")
                for row in connection.execute(
                    "SELECT extraction_method FROM article_cards WHERE deepening_status='deepened'"
                ).fetchall()
            )
            ocr_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM article_cards WHERE deepening_status='deepened' AND ocr_used=1"
                ).fetchone()[0]
            )
    except Exception:
        tmp_database.unlink(missing_ok=True)
        raise

    database_sha = sha256_file(tmp_database)
    tmp_database.replace(target_database)

    extensions = manifest.setdefault("extensions", {})
    if not isinstance(extensions, dict):
        extensions = {}
        manifest["extensions"] = extensions
    deepening_extension = extensions.setdefault("deepening", {})
    if not isinstance(deepening_extension, dict):
        deepening_extension = {}
        extensions["deepening"] = deepening_extension
    batches = deepening_extension.setdefault("batches", {})
    if not isinstance(batches, dict):
        batches = {}
        deepening_extension["batches"] = batches
    batches[batch_id] = {
        "status": "PASS",
        "search_id": search_id,
        "tier": tier,
        "documents": len(batch_documents),
        "created_at": now,
        "source_sha256": source_shas,
    }
    deepening_extension.update(
        {
            "status": "PASS",
            "updated_at": now,
            "search_id": search_id,
            "deepened_articles": counts["deepened_articles"],
            "retrieval_status_counts": dict(sorted(retrieval_counts.items())),
            "extraction_method_counts": dict(sorted(extraction_counts.items())),
            "ocr_used": ocr_count,
            "semantics": "selective retrieval/extraction overlay; not scientific inclusion, quality, certainty, or recommendation",
        }
    )
    manifest["counts"] = {
        **dict(manifest.get("counts") or {}),
        "articles": counts["articles"],
        "evidence_excerpts": counts["evidence_excerpts"],
        "result_bundles": counts["result_bundles"],
    }
    manifest["outputs"]["database"] = {"path": str(target_database), "sha256": database_sha}
    manifest_sha = _atomic_json(manifest_path, manifest)

    return {
        "mode": "NUTEV_WORKBENCH_SELECTIVE_DEEPENING",
        "status": "COMPLETE",
        "batch_id": batch_id,
        "search_id": search_id,
        "tier": tier,
        "batch_documents": len(batch_documents),
        "deepened_articles": counts["deepened_articles"],
        "articles": counts["articles"],
        "evidence_excerpts": counts["evidence_excerpts"],
        "result_bundles": counts["result_bundles"],
        "retrieval_status_counts": dict(sorted(retrieval_counts.items())),
        "extraction_method_counts": dict(sorted(extraction_counts.items())),
        "ocr_used": ocr_count,
        "source_database_sha256": source_database_sha,
        "database": str(target_database),
        "database_sha256": database_sha,
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha,
    }
