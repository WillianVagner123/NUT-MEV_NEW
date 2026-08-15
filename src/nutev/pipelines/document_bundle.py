"""Canonical document bundle index for original/OCR/translation/version assets."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


def _clean(value: object) -> str:
    return str(value or "").strip()


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _asset(row: dict[str, Any], *, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": _clean(row.get("path") or row.get("file") or row.get("text_path")),
        "sha256": _clean(row.get("sha256") or row.get("source_artifact_sha256")),
        "status": _clean(row.get("status") or row.get("extraction_status") or row.get("fulltext_status")),
        "used_ocr": bool(row.get("used_ocr")),
        "language": _clean(row.get("detected_language") or row.get("language") or row.get("language_original")),
    }


def build_document_bundle_index(
    project_root: Path,
    *,
    master_rows: Iterable[dict[str, Any]],
    fulltext_rows: Iterable[dict[str, Any]] = (),
    download_manifest: Iterable[dict[str, Any]] = (),
    extraction_manifest: Iterable[dict[str, Any]] = (),
    translation_manifest: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Unify every representation of one document under its canonical document_id.

    This is an organizational/audit index only. It never merges distinct document
    identities or changes dedup decisions; it points at artifacts already created
    by the existing corpus/full-text/OCR/translation layers.
    """
    root = Path(project_root)
    bundles: dict[str, dict[str, Any]] = {}
    for row in master_rows:
        document_id = _clean(row.get("document_id"))
        if not document_id:
            continue
        bundles[document_id] = {
            "document_id": document_id,
            "title": _clean(row.get("title")),
            "doi": _clean(row.get("doi")),
            "pmid": _clean(row.get("pmid")),
            "pmcid": _clean(row.get("pmcid")),
            "year": _clean(row.get("year")),
            "source_providers": sorted({
                _clean(row.get("source_provider")),
                *[_clean(item) for item in (row.get("source_providers") or [])],
            } - {""}),
            "language_original": _clean(row.get("language_original") or row.get("language")),
            "language_detected": _clean(row.get("language_detected")),
            "metadata": dict(row),
            "fulltext_routes": [],
            "original_artifacts": [],
            "extractions": [],
            "translations": [],
        }

    unmatched = {"fulltext": 0, "download": 0, "extraction": 0, "translation": 0}

    for row in fulltext_rows:
        document_id = _clean(row.get("document_id"))
        if document_id not in bundles:
            unmatched["fulltext"] += 1
            continue
        bundles[document_id]["fulltext_routes"].append({
            "status": _clean(row.get("fulltext_status")),
            "url": _clean(row.get("fulltext_url") or row.get("oa_url") or row.get("url")),
            "route": _clean(row.get("fulltext_route") or row.get("source")),
        })

    for row in download_manifest:
        document_id = _clean(row.get("document_id"))
        if document_id not in bundles:
            unmatched["download"] += 1
            continue
        bundles[document_id]["original_artifacts"].append(_asset(row, kind="original_download"))

    for row in extraction_manifest:
        document_id = _clean(row.get("document_id"))
        if document_id not in bundles:
            unmatched["extraction"] += 1
            continue
        kind = "ocr_text" if bool(row.get("used_ocr")) else "native_text"
        bundles[document_id]["extractions"].append(_asset(row, kind=kind))

    for row in translation_manifest:
        document_id = _clean(row.get("document_id"))
        if document_id not in bundles:
            unmatched["translation"] += 1
            continue
        bundles[document_id]["translations"].append(dict(row))

    rows = [bundles[key] for key in sorted(bundles)]
    out_dir = root / "03_corpus" / "document_bundles"
    bundle_path = out_dir / "document_bundles.jsonl"
    bundle_sha256 = _atomic_jsonl(bundle_path, rows)
    summary = {
        "schema_version": 1,
        "bundle_count": len(rows),
        "documents_with_original_artifact": sum(bool(row["original_artifacts"]) for row in rows),
        "documents_with_extracted_text": sum(bool(row["extractions"]) for row in rows),
        "documents_with_translation": sum(bool(row["translations"]) for row in rows),
        "unmatched_artifacts": unmatched,
        "bundle_path": str(bundle_path),
        "bundle_sha256": bundle_sha256,
    }
    summary_path = out_dir / "document_bundles_summary.json"
    summary_sha256 = _atomic_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = summary_sha256
    return summary


__all__ = ["build_document_bundle_index"]
