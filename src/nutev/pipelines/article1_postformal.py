"""Post-FORMAL preparation that remains automatic and non-decisional."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nutev.pipelines.document_bundle import build_document_bundle_index
from nutev.pipelines.formal_review_queue import build_formal_review_queue
from nutev.pipelines.multilingual_pipeline import run_multilingual_enrichment


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def prepare_formal_human_review(project_root: Path, formal_summary: dict[str, Any]) -> dict[str, Any]:
    """Enrich FORMAL artifacts and create/rebuild the human screening queue."""
    root = Path(project_root)
    corpus = formal_summary.get("corpus") or {}
    artifacts = formal_summary.get("artifacts") or {}
    master_path = Path(str(corpus.get("master_jsonl_path") or ""))
    extraction_path = Path(str(artifacts.get("extraction_manifest_path") or ""))
    fulltext_path = Path(str(artifacts.get("fulltext_ledger_path") or ""))
    download_path = Path(str(artifacts.get("download_manifest_path") or ""))
    if not master_path.is_file():
        raise FileNotFoundError(f"formal master corpus not found: {master_path}")
    master_rows = _read_jsonl(master_path)
    extraction_rows = _read_jsonl(extraction_path) if extraction_path.is_file() else []
    fulltext_rows = _read_jsonl(fulltext_path) if fulltext_path.is_file() else []
    download_rows = _read_jsonl(download_path) if download_path.is_file() else []

    multilingual = run_multilingual_enrichment(
        root,
        master_rows=master_rows,
        extraction_rows=extraction_rows,
    )
    bundle = build_document_bundle_index(
        root,
        master_rows=master_rows,
        fulltext_rows=fulltext_rows,
        download_manifest=download_rows,
        extraction_manifest=extraction_rows,
        translation_manifest=multilingual.get("translation_rows") or [],
    )
    queue = build_formal_review_queue(
        root,
        master_rows=master_rows,
        extraction_manifest=extraction_rows,
    )
    return {
        **queue,
        "multilingual": {
            key: value
            for key, value in multilingual.items()
            if key not in {"translation_rows", "metadata_translation_rows"}
        },
        "document_bundle": bundle,
    }


__all__ = ["prepare_formal_human_review"]
