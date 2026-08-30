"""SQLite index for high-scale NutEV article browsing.

The index is derived from hash-verified EvidenceExcerpt outputs. It keeps the
browser away from full JSONL corpora and allows server-side paging/filtering for
tens of thousands of article cards.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


WORKBENCH_SCHEMA = "NUTEV_ARTICLE_WORKBENCH_V1"


class WorkbenchIndexError(RuntimeError):
    """Raised when the Workbench index cannot prove input integrity."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise WorkbenchIndexError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkbenchIndexError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkbenchIndexError(f"expected JSON object at {path}")
    return value


def _read_jsonl(
    path: Path,
    *,
    label: str,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise WorkbenchIndexError(f"missing {label}: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WorkbenchIndexError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise WorkbenchIndexError(
                    f"non-object JSONL row at {path}:{line_number}"
                )
            rows.append(value)
    if not rows and not allow_empty:
        raise WorkbenchIndexError(f"{label} is empty: {path}")
    return rows


def _manifest_sha(manifest: Mapping[str, Any], key: str) -> str:
    value = str(
        (((manifest.get("outputs") or {}).get(key) or {}).get("sha256")) or ""
    ).strip().lower()
    if not value:
        raise WorkbenchIndexError(f"EXCERPT_MANIFEST missing SHA-256 for {key}")
    return value


def _verify_inputs(
    excerpts_jsonl: Path,
    result_bundles_jsonl: Path,
    article_cards_jsonl: Path,
    excerpt_manifest_path: Path,
) -> dict[str, str]:
    manifest = _read_json(excerpt_manifest_path)
    if manifest.get("excerpt_type") != "NUTEV_EVIDENCE_EXCERPTS_RESULTS":
        raise WorkbenchIndexError("unexpected excerpt manifest type")
    if manifest.get("status") != "PASS":
        raise WorkbenchIndexError("excerpt manifest is not PASS")
    paths = {
        "evidence_excerpts": excerpts_jsonl,
        "result_bundles": result_bundles_jsonl,
        "article_evidence_cards": article_cards_jsonl,
    }
    verified: dict[str, str] = {}
    for key, path in paths.items():
        actual = sha256_file(path)
        expected = _manifest_sha(manifest, key)
        if actual != expected:
            raise WorkbenchIndexError(
                f"{key} SHA-256 mismatch: expected {expected}, got {actual}"
            )
        verified[key] = actual
    verified["excerpt_manifest"] = sha256_file(excerpt_manifest_path)
    return verified


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256_file(path)


def _search_text(card: Mapping[str, Any]) -> str:
    identity = card.get("identity") or {}
    reference = card.get("reference") or {}
    snapshot = card.get("study_snapshot") or {}
    parts: list[str] = []
    if isinstance(identity, Mapping):
        parts.extend(
            str(identity.get(key) or "")
            for key in ("title", "doi", "pmid", "source_provider")
        )
    if isinstance(reference, Mapping):
        parts.extend(
            str(reference.get(key) or "")
            for key in ("authors", "journal", "reference_stub")
        )
    if isinstance(snapshot, Mapping):
        for values in snapshot.values():
            if isinstance(values, list):
                parts.extend(str(value) for value in values)
            elif values:
                parts.append(str(values))
    return " ".join(" ".join(parts).casefold().split())[:20000]


def _write_index(
    path: Path,
    cards: Iterable[dict[str, Any]],
    excerpts: Iterable[dict[str, Any]],
    bundles: Iterable[dict[str, Any]],
    source_shas: Mapping[str, str],
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    if tmp.exists():
        tmp.unlink()
    connection = sqlite3.connect(tmp)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=NORMAL;
            CREATE TABLE article_cards (
                document_id TEXT PRIMARY KEY,
                record_id TEXT,
                title TEXT,
                year INTEGER,
                doi TEXT,
                pmid TEXT,
                source_provider TEXT,
                document_class TEXT,
                full_text_status TEXT,
                cache_key TEXT NOT NULL,
                reference_stub TEXT,
                llm_context_chars INTEGER NOT NULL DEFAULT 0,
                search_text TEXT NOT NULL,
                card_json TEXT NOT NULL
            );
            CREATE INDEX idx_article_year ON article_cards(year DESC);
            CREATE INDEX idx_article_provider ON article_cards(source_provider);
            CREATE INDEX idx_article_class ON article_cards(document_class);
            CREATE INDEX idx_article_full_text ON article_cards(full_text_status);
            CREATE INDEX idx_article_doi ON article_cards(doi);
            CREATE INDEX idx_article_pmid ON article_cards(pmid);

            CREATE TABLE evidence_excerpts (
                excerpt_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                section TEXT,
                locator TEXT,
                priority_score REAL NOT NULL,
                verbatim_excerpt TEXT NOT NULL,
                excerpt_json TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES article_cards(document_id)
            );
            CREATE INDEX idx_excerpt_document ON evidence_excerpts(document_id);
            CREATE INDEX idx_excerpt_kind ON evidence_excerpts(kind);

            CREATE TABLE result_bundles (
                result_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                result_kind TEXT NOT NULL,
                priority_score REAL NOT NULL,
                result_json TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES article_cards(document_id)
            );
            CREATE INDEX idx_result_document ON result_bundles(document_id);
            CREATE INDEX idx_result_kind ON result_bundles(result_kind);

            CREATE TABLE workbench_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO workbench_meta(key, value) VALUES (?, ?)",
            ("schema", WORKBENCH_SCHEMA),
        )
        connection.execute(
            "INSERT INTO workbench_meta(key, value) VALUES (?, ?)",
            ("created_at", _now()),
        )
        connection.execute(
            "INSERT INTO workbench_meta(key, value) VALUES (?, ?)",
            ("source_sha256", json.dumps(dict(source_shas), sort_keys=True)),
        )

        for card in cards:
            document_id = str(card.get("document_id") or "").strip()
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
                INSERT INTO article_cards(
                    document_id, record_id, title, year, doi, pmid, source_provider,
                    document_class, full_text_status, cache_key, reference_stub,
                    llm_context_chars, search_text, card_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
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
                ),
            )

        for excerpt in excerpts:
            connection.execute(
                """
                INSERT INTO evidence_excerpts(
                    excerpt_id, document_id, kind, section, locator, priority_score,
                    verbatim_excerpt, excerpt_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    excerpt["id"],
                    excerpt["document_id"],
                    excerpt["kind"],
                    excerpt.get("section"),
                    excerpt.get("locator"),
                    float(excerpt.get("priority_score") or 0.0),
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
                    bundle["id"],
                    bundle["document_id"],
                    bundle["result_kind"],
                    float(bundle.get("priority_score") or 0.0),
                    json.dumps(bundle, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )
        connection.commit()
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise WorkbenchIndexError("SQLite integrity_check failed")
    finally:
        connection.close()
    tmp.replace(path)
    return sha256_file(path)


def run_workbench_index(
    excerpts_jsonl: Path,
    result_bundles_jsonl: Path,
    article_cards_jsonl: Path,
    excerpt_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Build the server-side article index used by the high-scale Workbench."""

    source_shas = _verify_inputs(
        excerpts_jsonl,
        result_bundles_jsonl,
        article_cards_jsonl,
        excerpt_manifest,
    )
    cards = _read_jsonl(article_cards_jsonl, label="article evidence cards")
    excerpts = _read_jsonl(
        excerpts_jsonl,
        label="evidence excerpts",
        allow_empty=True,
    )
    bundles = _read_jsonl(
        result_bundles_jsonl,
        label="result bundles",
        allow_empty=True,
    )
    known_documents: set[str] = set()
    for card in cards:
        document_id = str(card.get("document_id") or "").strip()
        if not document_id:
            raise WorkbenchIndexError("article evidence card missing document_id")
        if document_id in known_documents:
            raise WorkbenchIndexError(f"duplicate article card document_id: {document_id}")
        if not str(card.get("cache_key") or "").strip():
            raise WorkbenchIndexError(f"article card missing cache_key: {document_id}")
        known_documents.add(document_id)
    for label, rows in (("excerpt", excerpts), ("result bundle", bundles)):
        seen_ids: set[str] = set()
        for row in rows:
            row_id = str(row.get("id") or "").strip()
            document_id = str(row.get("document_id") or "").strip()
            if not row_id or row_id in seen_ids:
                raise WorkbenchIndexError(f"invalid/duplicate {label} id: {row_id or '<missing>'}")
            if document_id not in known_documents:
                raise WorkbenchIndexError(
                    f"{label} references unknown document_id: {document_id or '<missing>'}"
                )
            seen_ids.add(row_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "evidence_workbench.sqlite"
    manifest_path = output_dir / "WORKBENCH_MANIFEST.json"
    database_sha = _write_index(
        database_path,
        cards,
        excerpts,
        bundles,
        source_shas,
    )
    manifest = {
        "schema_version": 1,
        "workbench_type": WORKBENCH_SCHEMA,
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "excerpt_manifest": str(excerpt_manifest),
            "source_sha256": source_shas,
        },
        "counts": {
            "articles": len(cards),
            "evidence_excerpts": len(excerpts),
            "result_bundles": len(bundles),
        },
        "outputs": {
            "database": {
                "path": str(database_path),
                "sha256": database_sha,
            }
        },
        "performance_contract": {
            "browser_loads_full_corpus": False,
            "server_side_filtering": True,
            "page_limit_max": 100,
            "detail_loaded_on_demand": True,
        },
        "guardrail": (
            "The Workbench index is an operational projection of hash-verified machine candidates. "
            "It does not convert excerpts/results into accepted claims, eligibility, quality, certainty, "
            "causal interpretation, recommendation, or PRISMA decisions."
        ),
    }
    manifest_sha = _atomic_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_ARTICLE_WORKBENCH_INDEX",
        "status": "COMPLETE",
        "articles": len(cards),
        "evidence_excerpts": len(excerpts),
        "result_bundles": len(bundles),
        "database": str(database_path),
        "manifest": str(manifest_path),
        "output_sha256": {
            "database": database_sha,
            "manifest": manifest_sha,
        },
    }
