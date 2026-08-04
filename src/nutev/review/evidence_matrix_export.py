"""Auditable final evidence-matrix summaries and exports."""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.review.article_screening_ledger import (
    ARTICLE_IDS,
    get_screening_session,
    list_article_catalog,
)
from nutev.review.evidence_matrix_core import _db, _j, _now
from nutev.review.evidence_matrix_extraction import (
    _included,
    _latest_extractions,
    compare_extractions,
    final_extraction,
    list_schema,
)
from nutev.review.evidence_matrix_quality import final_quality
from nutev.search.corpus_build_ledger import get_corpus_build


def summarize(db_path: Path, session_id: str) -> dict[str, Any]:
    included = _included(db_path, session_id)
    articles: list[dict[str, Any]] = []
    for catalog in list_article_catalog(db_path, active_only=True):
        rows = [
            row for row in included if row["article_id"] == catalog["article_id"]
        ]
        extraction = [
            final_extraction(
                db_path,
                session_id,
                row["document_id"],
                row["article_id"],
            )
            for row in rows
        ]
        quality = [
            final_quality(
                db_path,
                session_id,
                row["document_id"],
                row["article_id"],
            )
            for row in rows
        ]
        articles.append(
            {
                "article_id": catalog["article_id"],
                "article_label": catalog["label"],
                "included_documents": len(rows),
                "extraction_complete": sum(
                    bool(row["extraction_complete"]) for row in extraction
                ),
                "extraction_pending": sum(
                    not bool(row["extraction_complete"]) for row in extraction
                ),
                "quality_complete": sum(
                    bool(row["quality_complete"]) for row in quality
                ),
                "quality_pending": sum(
                    not bool(row["quality_complete"]) for row in quality
                ),
            }
        )
    return {
        "session_id": session_id,
        "included_article_documents": len(included),
        "distinct_included_documents": len(
            {row["document_id"] for row in included}
        ),
        "extraction_complete": sum(
            int(row["extraction_complete"]) for row in articles
        ),
        "quality_complete": sum(int(row["quality_complete"]) for row in articles),
        "articles": articles,
    }


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    fields = sorted({key for row in rows for key in row}) or ["status"]
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            [
                {
                    key: _j(value) if isinstance(value, (dict, list)) else value
                    for key, value in row.items()
                }
                for row in rows
            ]
        )
    temporary.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def export_snapshot(
    db_path: Path,
    session_id: str,
    export_id: str | None = None,
) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if not session:
        raise ValueError("unknown session")
    build = get_corpus_build(db_path, session["build_id"])
    if not build:
        raise ValueError("missing corpus build")

    included = _included(db_path, session_id)
    schemas = [
        {"article_id": article, **field}
        for article in ARTICLE_IDS
        for field in list_schema(db_path, article)
    ]
    submissions = _latest_extractions(db_path, session_id)
    comparisons: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    for row in included:
        article = row["article_id"]
        document = row["document_id"]
        comparisons.extend(
            {
                "document_id": document,
                "article_id": article,
                **item,
            }
            for item in compare_extractions(
                db_path,
                session_id=session_id,
                document_id=document,
                article_id=article,
            )
        )
        evidence.append(final_extraction(db_path, session_id, document, article))
        quality.append(final_quality(db_path, session_id, document, article))

    summary_data = summarize(db_path, session_id)
    resolved_export_id = export_id or f"matrix_{uuid4().hex}"
    folder = (
        Path(build["manifest_path"]).parent
        / "evidence_matrix"
        / session_id
        / resolved_export_id
    )
    paths = {
        "schema": folder / "extraction_schema.csv",
        "submissions": folder / "extraction_submissions.csv",
        "comparison": folder / "extraction_comparison.csv",
        "evidence": folder / "final_evidence_matrix.csv",
        "quality": folder / "final_quality_matrix.csv",
    }
    datasets = (schemas, submissions, comparisons, evidence, quality)
    hashes = {
        key: _atomic_csv(path, rows)
        for (key, path), rows in zip(paths.items(), datasets)
    }

    summary_path = folder / "extraction_quality_summary.json"
    hashes["summary"] = _atomic_json(summary_path, summary_data)
    manifest_path = folder / "evidence_matrix_manifest.json"
    manifest = {
        "export_id": resolved_export_id,
        "session_id": session_id,
        "created_at": _now(),
        "summary": summary_data,
        "inputs": {
            "corpus_manifest_path": build["manifest_path"],
            "corpus_manifest_sha256": build["manifest_sha256"],
        },
        "outputs": {
            **{f"{key}_path": str(path) for key, path in paths.items()},
            "summary_path": str(summary_path),
            "hashes": hashes,
        },
        "governance": {
            "double_extraction": True,
            "field_adjudication": True,
            "configurable_quality": True,
            "quality_adjudication": True,
            "append_only": True,
            "artifact_integrity_checked": True,
        },
    }
    manifest_sha = _atomic_json(manifest_path, manifest)
    stored_paths = {
        **{key: str(path) for key, path in paths.items()},
        "summary": str(summary_path),
        "manifest": str(manifest_path),
    }
    with _db(db_path) as con:
        con.execute(
            "INSERT INTO evidence_matrix_exports VALUES(?,?,?,?,?,?,?,?)",
            (
                resolved_export_id,
                session_id,
                _now(),
                len(included),
                summary_data["extraction_complete"],
                summary_data["quality_complete"],
                _j(stored_paths),
                manifest_sha,
            ),
        )
    return {
        "export_id": resolved_export_id,
        "paths": stored_paths,
        "summary": summary_data,
        "manifest_sha256": manifest_sha,
    }
