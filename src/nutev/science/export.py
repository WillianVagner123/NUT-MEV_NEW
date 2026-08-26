"""Audited export from Reference Engine ranking into the scientific object layer."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from nutev.audit_guardrails import sha256_file

from .adapters import reference_to_scientific_objects
from .models import ScientificEvent, derive_prisma_counts


class ScientificExportError(RuntimeError):
    """Raised when a scientific export cannot prove its input integrity."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ScientificExportError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScientificExportError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScientificExportError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ScientificExportError(f"missing ranking JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ScientificExportError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ScientificExportError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows:
        raise ScientificExportError(f"ranking JSONL is empty: {path}")
    return rows


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _verified_ranking_sha(ranking_jsonl: Path, audit_manifest: Path) -> str:
    manifest = _read_json(audit_manifest)
    if manifest.get("audit_type") != "REFERENCE_RANKING_AUDIT":
        raise ScientificExportError(
            f"unexpected audit_type in {audit_manifest}: {manifest.get('audit_type')!r}"
        )
    if manifest.get("status") != "PASS":
        raise ScientificExportError(
            f"reference ranking audit is not PASS: {manifest.get('status')!r}"
        )
    expected = str(
        (((manifest.get("outputs") or {}).get("ranking_jsonl") or {}).get("sha256")) or ""
    ).strip().lower()
    if not expected:
        raise ScientificExportError(
            f"ranking_jsonl SHA-256 missing from audit manifest: {audit_manifest}"
        )
    actual = sha256_file(ranking_jsonl)
    if actual != expected:
        raise ScientificExportError(
            f"ranking SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def run_scientific_export(
    ranking_jsonl: Path,
    audit_manifest: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Export audited ranking rows into traceable scientific objects.

    The export creates document/evidence objects only. It does not infer
    eligibility, claims, evidence quality, synthesis, or recommendations.
    """

    ranking_sha = _verified_ranking_sha(ranking_jsonl, audit_manifest)
    source_manifest_sha = sha256_file(audit_manifest)
    rows = _read_jsonl(ranking_jsonl)

    documents: list[dict[str, Any]] = []
    evidence_records: list[dict[str, Any]] = []
    events: list[ScientificEvent] = []
    document_ids: set[str] = set()
    record_ids: set[str] = set()

    for index, row in enumerate(rows, start=1):
        if row.get("audit_quarantined"):
            raise ScientificExportError(
                f"ranked row {index} is marked quarantined and cannot enter scientific layer"
            )
        try:
            document, evidence = reference_to_scientific_objects(row)
        except ValueError as exc:
            raise ScientificExportError(f"invalid ranked row {index}: {exc}") from exc

        if document.id in document_ids:
            raise ScientificExportError(f"duplicate document identity in ranking: {document.id}")
        if evidence.id in record_ids:
            raise ScientificExportError(f"duplicate evidence identity in ranking: {evidence.id}")
        document_ids.add(document.id)
        record_ids.add(evidence.id)

        documents.append(asdict(document))
        evidence_records.append(asdict(evidence))
        events.append(
            ScientificEvent(
                id=f"science-ingest:{index}",
                entity_type="document",
                entity_id=document.id,
                action="entered_scientific_layer",
                metadata={
                    "reference_rank": row.get("reference_rank"),
                    "source_ranking_sha256": ranking_sha,
                },
            )
        )

    event_rows = [asdict(event) for event in events]
    prisma = derive_prisma_counts(events)

    output_dir.mkdir(parents=True, exist_ok=True)
    documents_path = output_dir / "document_candidates.jsonl"
    evidence_path = output_dir / "evidence_records.jsonl"
    events_path = output_dir / "scientific_events.jsonl"
    manifest_path = output_dir / "SCIENTIFIC_EXPORT_MANIFEST.json"

    documents_sha = _write_jsonl(documents_path, documents)
    evidence_sha = _write_jsonl(evidence_path, evidence_records)
    events_sha = _write_jsonl(events_path, event_rows)

    manifest = {
        "schema_version": 1,
        "export_type": "NUTEV_SCIENTIFIC_OBJECT_EXPORT",
        "created_at": _now(),
        "status": "PASS",
        "source": {
            "ranking_jsonl": str(ranking_jsonl),
            "ranking_sha256": ranking_sha,
            "reference_audit_manifest": str(audit_manifest),
            "reference_audit_manifest_sha256": source_manifest_sha,
        },
        "counts": {
            "ranking_rows": len(rows),
            "document_candidates": len(documents),
            "evidence_records": len(evidence_records),
            "evidence_claims": 0,
            "claim_evaluations": 0,
            "recommendation_candidates": 0,
            "human_validations": 0,
        },
        "prisma_from_explicit_events": asdict(prisma),
        "outputs": {
            "document_candidates": {
                "path": str(documents_path),
                "sha256": documents_sha,
            },
            "evidence_records": {
                "path": str(evidence_path),
                "sha256": evidence_sha,
            },
            "scientific_events": {
                "path": str(events_path),
                "sha256": events_sha,
            },
        },
        "assertions": [
            {"name": "reference_ranking_hash_verified", "status": "PASS"},
            {"name": "reference_audit_manifest_passed", "status": "PASS"},
            {"name": "ranked_quarantine_excluded", "status": "PASS"},
            {"name": "scientific_claims_not_inferred", "status": "PASS"},
            {"name": "prisma_not_inferred_from_ranking", "status": "PASS"},
        ],
        "interpretation_guardrail": (
            "This export is an audited handoff from reference ranking into scientific-domain "
            "objects. Presence in this export is not scientific inclusion, certainty of evidence, "
            "or a clinical recommendation."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "SCIENTIFIC_OBJECT_EXPORT",
        "status": "COMPLETE",
        "created_at": manifest["created_at"],
        "records": len(rows),
        "outputs": {
            "documents": str(documents_path),
            "evidence_records": str(evidence_path),
            "events": str(events_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "documents": documents_sha,
            "evidence_records": evidence_sha,
            "events": events_sha,
            "manifest": manifest_sha,
        },
    }
