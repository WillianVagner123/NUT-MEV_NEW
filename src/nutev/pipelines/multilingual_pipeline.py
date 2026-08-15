"""Resumable non-destructive multilingual enrichment for FORMAL documents."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.language import normalize_language_code
from nutev.translation_service import (
    translate_metadata_record,
    translate_text_artifact,
    translation_configuration,
    write_translation_manifest,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not Path(path).is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return _sha256_file(path)


def _completed_text_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    output: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if str(row.get("status") or "").upper() != "COMPLETED":
            continue
        path = Path(str(row.get("translated_text_path") or ""))
        if not path.is_file():
            continue
        expected = str(row.get("translated_sha256") or "")
        if not expected or _sha256_file(path) != expected:
            continue
        key = (
            str(row.get("document_id") or ""),
            str(row.get("original_sha256") or ""),
            str(row.get("target_language") or ""),
            str(row.get("translator") or ""),
        )
        output[key] = row
    return output


def run_multilingual_enrichment(
    project_root: Path,
    *,
    master_rows: list[dict[str, Any]],
    extraction_rows: list[dict[str, Any]],
    target_language: str | None = None,
) -> dict[str, Any]:
    """Translate metadata/text when configured, preserving all originals.

    Missing translation credentials are a transparent SKIPPED state, not a false
    success and not a scientific blocker. Completed translations are reused only
    when source hash, target language and translated artifact hash still match.
    """
    root = Path(project_root)
    config = translation_configuration()
    target = normalize_language_code(target_language or config.get("target_language") or "pt") or "pt"
    formal_dir = root / "12_play" / "formal"
    text_manifest_path = formal_dir / "translation_manifest.jsonl"
    metadata_manifest_path = formal_dir / "metadata_translation_manifest.jsonl"
    summary_path = formal_dir / "translation_summary.json"
    translation_dir = root / "04_ocr_text" / "translations" / target

    existing_text = _read_jsonl(text_manifest_path)
    completed = _completed_text_index(existing_text)
    master_by_id = {str(row.get("document_id") or ""): row for row in master_rows}
    text_rows: list[dict[str, Any]] = []

    for extracted in extraction_rows:
        document_id = str(extracted.get("document_id") or "").strip()
        text_path = Path(str(extracted.get("text_path") or ""))
        if not document_id or not text_path.is_file():
            continue
        original_sha = _sha256_file(text_path)
        source = normalize_language_code(
            extracted.get("language_detected")
            or extracted.get("language_original")
            or (master_by_id.get(document_id) or {}).get("language_original")
            or (master_by_id.get(document_id) or {}).get("language")
        ) or "und"
        provider_name = str(config.get("provider") or "")
        matching = next(
            (
                value
                for key, value in completed.items()
                if key[0] == document_id
                and key[1] == original_sha
                and key[2] == target
                and (not provider_name or key[3].startswith(provider_name) or provider_name in key[3])
            ),
            None,
        )
        if matching:
            text_rows.append(dict(matching))
            continue
        text_rows.append(
            translate_text_artifact(
                document_id,
                text_path,
                translation_dir / document_id,
                source_language=source,
                target_language=target,
            )
        )

    metadata_rows = [
        translate_metadata_record(
            str(row.get("document_id") or ""),
            row,
            target_language=target,
        )
        for row in master_rows
        if str(row.get("document_id") or "").strip()
    ]

    text_sha = write_translation_manifest(text_manifest_path, text_rows)
    metadata_sha = write_translation_manifest(metadata_manifest_path, metadata_rows)
    summary = {
        "schema_version": 1,
        "configured": bool(config.get("configured")),
        "provider": config.get("provider"),
        "configuration_reason": config.get("reason"),
        "target_language": target,
        "documents_with_text": len(text_rows),
        "text_completed": sum(str(row.get("status") or "").upper() == "COMPLETED" for row in text_rows),
        "text_skipped": sum(str(row.get("status") or "").upper() == "SKIPPED" for row in text_rows),
        "text_failed": sum(str(row.get("status") or "").upper() == "FAILED" for row in text_rows),
        "metadata_records": len(metadata_rows),
        "metadata_completed": sum(str(row.get("status") or "").upper() == "COMPLETED" for row in metadata_rows),
        "metadata_skipped": sum(str(row.get("status") or "").upper() == "SKIPPED" for row in metadata_rows),
        "metadata_failed": sum(str(row.get("status") or "").upper() == "FAILED" for row in metadata_rows),
        "originals_preserved": True,
        "text_manifest_path": str(text_manifest_path),
        "text_manifest_sha256": text_sha,
        "metadata_manifest_path": str(metadata_manifest_path),
        "metadata_manifest_sha256": metadata_sha,
        "scientific_decision_inferred": False,
    }
    summary_sha = _atomic_json(summary_path, summary)
    return {
        **summary,
        "summary_path": str(summary_path),
        "summary_sha256": summary_sha,
        "translation_rows": text_rows,
        "metadata_translation_rows": metadata_rows,
    }


__all__ = ["run_multilingual_enrichment"]
