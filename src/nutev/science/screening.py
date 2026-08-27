"""Translate final scientific screening decisions into explicit lifecycle events."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from nutev.audit_guardrails import sha256_file

from .models import (
    DocumentState,
    ScientificEvent,
    ScreeningDecision,
    ScreeningDecisionValue,
    ScreeningStage,
    derive_prisma_counts,
)


class ScreeningImportError(RuntimeError):
    """Raised when final screening decisions cannot be safely imported."""


def events_from_screening_decision(decision: ScreeningDecision) -> tuple[ScientificEvent, ...]:
    """Return PRISMA-relevant events for one final resolved screening decision.

    Individual reviewer votes must not be passed here. This function represents
    the final resolved decision for one document/stage so PRISMA counts are not
    multiplied by the number of reviewers.
    """

    if decision.decision is ScreeningDecisionValue.EXCLUDE and not str(
        decision.reason or ""
    ).strip():
        raise ValueError("final exclusion decision requires an explicit reason")

    common_metadata = {
        "screening_decision_id": decision.id,
        "stage": decision.stage.value,
        "decision": decision.decision.value,
        "adjudicator": decision.adjudicator,
        **dict(decision.metadata),
    }

    if decision.stage is ScreeningStage.TITLE_ABSTRACT:
        events: list[ScientificEvent] = [
            ScientificEvent(
                id=f"{decision.id}:screened",
                entity_type="document",
                entity_id=decision.document_id,
                action="screened",
                to_state=DocumentState.SCREENED.value,
                occurred_at=decision.decided_at,
                metadata=common_metadata,
            )
        ]
        if decision.decision is ScreeningDecisionValue.EXCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:excluded_screening",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="excluded_screening",
                    to_state=DocumentState.EXCLUDED.value,
                    reason=decision.reason,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        return tuple(events)

    if decision.stage is ScreeningStage.FULL_TEXT:
        events = [
            ScientificEvent(
                id=f"{decision.id}:assessed_for_eligibility",
                entity_type="document",
                entity_id=decision.document_id,
                action="assessed_for_eligibility",
                occurred_at=decision.decided_at,
                metadata=common_metadata,
            )
        ]
        if decision.decision is ScreeningDecisionValue.EXCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:excluded_full_text",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="excluded_full_text",
                    to_state=DocumentState.EXCLUDED.value,
                    reason=decision.reason,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        elif decision.decision is ScreeningDecisionValue.INCLUDE:
            events.append(
                ScientificEvent(
                    id=f"{decision.id}:included",
                    entity_type="document",
                    entity_id=decision.document_id,
                    action="included",
                    to_state=DocumentState.INCLUDED.value,
                    occurred_at=decision.decided_at,
                    metadata=common_metadata,
                )
            )
        return tuple(events)

    raise ValueError(f"unsupported screening stage: {decision.stage!r}")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ScreeningImportError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScreeningImportError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScreeningImportError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ScreeningImportError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ScreeningImportError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ScreeningImportError(
                    f"non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
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


def _verify_document_export(documents_jsonl: Path, science_manifest: Path) -> str:
    manifest = _read_json(science_manifest)
    if manifest.get("export_type") != "NUTEV_SCIENTIFIC_OBJECT_EXPORT":
        raise ScreeningImportError(
            f"unexpected export_type in {science_manifest}: {manifest.get('export_type')!r}"
        )
    if manifest.get("status") != "PASS":
        raise ScreeningImportError(
            f"scientific export manifest is not PASS: {manifest.get('status')!r}"
        )
    expected = str(
        (((manifest.get("outputs") or {}).get("document_candidates") or {}).get("sha256"))
        or ""
    ).strip().lower()
    if not expected:
        raise ScreeningImportError(
            f"document_candidates SHA-256 missing from scientific manifest: {science_manifest}"
        )
    actual = sha256_file(documents_jsonl)
    if actual != expected:
        raise ScreeningImportError(
            f"document_candidates SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def _verify_reviewer_dossiers(
    dossiers_jsonl: Path,
    enrichment_manifest: Path,
) -> tuple[set[str], str]:
    manifest = _read_json(enrichment_manifest)
    if manifest.get("enrichment_type") != "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT":
        raise ScreeningImportError(
            "unexpected enrichment_type in "
            f"{enrichment_manifest}: {manifest.get('enrichment_type')!r}"
        )
    if manifest.get("status") != "PASS":
        raise ScreeningImportError(
            f"enrichment manifest is not PASS: {manifest.get('status')!r}"
        )
    expected = str(
        (((manifest.get("outputs") or {}).get("reviewer_dossiers") or {}).get("sha256"))
        or ""
    ).strip().lower()
    if not expected:
        raise ScreeningImportError(
            f"reviewer_dossiers SHA-256 missing from enrichment manifest: {enrichment_manifest}"
        )
    actual = sha256_file(dossiers_jsonl)
    if actual != expected:
        raise ScreeningImportError(
            f"reviewer_dossiers SHA-256 mismatch: expected {expected}, got {actual}"
        )

    rows = _read_jsonl(dossiers_jsonl, label="reviewer dossiers")
    ids: set[str] = set()
    for line_number, row in enumerate(rows, start=1):
        document_id = str(row.get("document_id") or "").strip()
        if not document_id:
            raise ScreeningImportError(
                f"reviewer dossier line {line_number} missing document_id"
            )
        guardrails = row.get("guardrails") or {}
        if not isinstance(guardrails, dict):
            raise ScreeningImportError(
                f"reviewer dossier line {line_number} guardrails must be an object"
            )
        if guardrails.get("blind_to_nutev_rank") is not True:
            raise ScreeningImportError(
                f"reviewer dossier line {line_number} is not rank-blind"
            )
        if guardrails.get("blind_to_nutev_taxonomy") is not True:
            raise ScreeningImportError(
                f"reviewer dossier line {line_number} is not taxonomy-blind"
            )
        ids.add(document_id)
    return ids, actual


def _parse_decision(row: dict[str, Any], line_number: int) -> ScreeningDecision:
    required = ("id", "document_id", "stage", "decision", "decided_at")
    missing = [key for key in required if not str(row.get(key) or "").strip()]
    if missing:
        raise ScreeningImportError(
            f"screening decision line {line_number} missing required fields: {', '.join(missing)}"
        )
    try:
        stage = ScreeningStage(str(row["stage"]))
        decision_value = ScreeningDecisionValue(str(row["decision"]))
    except ValueError as exc:
        raise ScreeningImportError(
            f"screening decision line {line_number} has invalid stage/decision"
        ) from exc
    metadata = row.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ScreeningImportError(
            f"screening decision line {line_number} metadata must be an object"
        )
    return ScreeningDecision(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        stage=stage,
        decision=decision_value,
        adjudicator=str(row.get("adjudicator") or "").strip() or None,
        reason=str(row.get("reason") or "").strip() or None,
        decided_at=str(row["decided_at"]),
        metadata=metadata,
    )


def run_screening_import(
    documents_jsonl: Path,
    science_manifest: Path,
    decisions_jsonl: Path,
    output_dir: Path,
    *,
    dossiers_jsonl: Path | None = None,
    enrichment_manifest: Path | None = None,
    require_enrichment: bool = False,
) -> dict[str, Any]:
    """Import final resolved screening decisions and emit auditable PRISMA events."""

    documents_sha = _verify_document_export(documents_jsonl, science_manifest)
    decisions_sha = sha256_file(decisions_jsonl) if decisions_jsonl.is_file() else ""
    document_rows = _read_jsonl(documents_jsonl, label="document candidates")
    decision_rows = _read_jsonl(decisions_jsonl, label="screening decisions")
    if not decision_rows:
        raise ScreeningImportError(f"screening decisions JSONL is empty: {decisions_jsonl}")

    dossier_ids: set[str] = set()
    dossiers_sha: str | None = None
    if require_enrichment:
        if dossiers_jsonl is None or enrichment_manifest is None:
            raise ScreeningImportError(
                "pre-screening enrichment is required: provide reviewer dossiers and enrichment manifest"
            )
        dossier_ids, dossiers_sha = _verify_reviewer_dossiers(
            dossiers_jsonl, enrichment_manifest
        )

    document_ids = {str(row.get("id") or "") for row in document_rows if row.get("id")}
    if not document_ids:
        raise ScreeningImportError("document candidates contain no document IDs")

    decisions: list[ScreeningDecision] = []
    seen_keys: set[tuple[str, ScreeningStage]] = set()
    seen_ids: set[str] = set()
    for line_number, row in enumerate(decision_rows, start=1):
        decision = _parse_decision(row, line_number)
        if decision.document_id not in document_ids:
            raise ScreeningImportError(
                f"screening decision references unknown document: {decision.document_id}"
            )
        if require_enrichment and decision.document_id not in dossier_ids:
            raise ScreeningImportError(
                "screening decision has no verified reviewer dossier: "
                f"{decision.document_id}"
            )
        if decision.id in seen_ids:
            raise ScreeningImportError(f"duplicate screening decision id: {decision.id}")
        key = (decision.document_id, decision.stage)
        if key in seen_keys:
            raise ScreeningImportError(
                "multiple final decisions for the same document/stage are not allowed: "
                f"{decision.document_id} / {decision.stage.value}"
            )
        seen_ids.add(decision.id)
        seen_keys.add(key)
        decisions.append(decision)

    events: list[ScientificEvent] = []
    for decision in decisions:
        try:
            events.extend(events_from_screening_decision(decision))
        except ValueError as exc:
            raise ScreeningImportError(
                f"invalid final screening decision {decision.id}: {exc}"
            ) from exc

    normalized_decisions = [asdict(decision) for decision in decisions]
    event_rows = [asdict(event) for event in events]
    prisma = derive_prisma_counts(events)

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = output_dir / "screening_decisions.jsonl"
    events_path = output_dir / "screening_events.jsonl"
    prisma_path = output_dir / "PRISMA_COUNTS.json"
    manifest_path = output_dir / "SCREENING_IMPORT_MANIFEST.json"

    normalized_sha = _write_jsonl(normalized_path, normalized_decisions)
    events_sha = _write_jsonl(events_path, event_rows)
    prisma_sha = _write_json(prisma_path, asdict(prisma))

    assertions = [
        {"name": "document_export_hash_verified", "status": "PASS"},
        {"name": "decisions_reference_known_documents", "status": "PASS"},
        {"name": "one_final_decision_per_document_stage", "status": "PASS"},
        {"name": "exclusions_require_reason", "status": "PASS"},
        {"name": "prisma_derived_from_final_decisions_only", "status": "PASS"},
    ]
    if require_enrichment:
        assertions.extend(
            [
                {"name": "reviewer_dossier_hash_verified", "status": "PASS"},
                {"name": "decisions_have_verified_reviewer_dossiers", "status": "PASS"},
                {"name": "reviewer_dossiers_rank_and_taxonomy_blind", "status": "PASS"},
            ]
        )

    manifest = {
        "schema_version": 2,
        "import_type": "NUTEV_FINAL_SCREENING_IMPORT",
        "status": "PASS",
        "source": {
            "document_candidates": str(documents_jsonl),
            "document_candidates_sha256": documents_sha,
            "scientific_export_manifest": str(science_manifest),
            "scientific_export_manifest_sha256": sha256_file(science_manifest),
            "screening_decisions_input": str(decisions_jsonl),
            "screening_decisions_input_sha256": decisions_sha,
            "reviewer_dossiers": str(dossiers_jsonl) if dossiers_jsonl else None,
            "reviewer_dossiers_sha256": dossiers_sha,
            "enrichment_manifest": str(enrichment_manifest) if enrichment_manifest else None,
            "enrichment_manifest_sha256": (
                sha256_file(enrichment_manifest) if enrichment_manifest else None
            ),
            "pre_screening_enrichment_required": require_enrichment,
        },
        "counts": {
            "document_candidates": len(document_rows),
            "verified_reviewer_dossiers": len(dossier_ids) if require_enrichment else 0,
            "final_screening_decisions": len(decisions),
            "scientific_events": len(events),
        },
        "prisma_from_explicit_events": asdict(prisma),
        "outputs": {
            "screening_decisions": {
                "path": str(normalized_path),
                "sha256": normalized_sha,
            },
            "screening_events": {"path": str(events_path), "sha256": events_sha},
            "prisma_counts": {"path": str(prisma_path), "sha256": prisma_sha},
        },
        "assertions": assertions,
        "interpretation_guardrail": (
            "This import records externally resolved final scientific screening decisions. "
            "NutEV does not generate the include/exclude decision. When enrichment is required, "
            "every decision must reference a verified rank- and taxonomy-blind reviewer dossier."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)

    return {
        "mode": "FINAL_SCREENING_IMPORT",
        "status": "COMPLETE",
        "decisions": len(decisions),
        "events": len(events),
        "pre_screening_enrichment_required": require_enrichment,
        "prisma": asdict(prisma),
        "outputs": {
            "decisions": str(normalized_path),
            "events": str(events_path),
            "prisma": str(prisma_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "decisions": normalized_sha,
            "events": events_sha,
            "prisma": prisma_sha,
            "manifest": manifest_sha,
        },
    }
