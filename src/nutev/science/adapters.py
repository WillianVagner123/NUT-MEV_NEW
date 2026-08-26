"""Adapters from the current Reference Engine into scientific domain objects."""

from __future__ import annotations

from typing import Any, Mapping

from nutev.reference_identity import canonical_identity, normalize_doi, normalize_pmid

from .models import DocumentCandidate, EvidenceRecord


def _provider(row: Mapping[str, Any]) -> str:
    return str(
        row.get("source_provider")
        or row.get("source")
        or row.get("reference_provider")
        or ""
    ).strip()


def _year(row: Mapping[str, Any]) -> int | None:
    raw = row.get("year")
    if raw in (None, ""):
        raw = row.get("reference_year")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def reference_to_scientific_objects(
    row: Mapping[str, Any],
    *,
    source_run_id: str | None = None,
    origin_sha256: str | None = None,
) -> tuple[DocumentCandidate, EvidenceRecord]:
    """Bridge one traceable Reference Engine row into the scientific layer.

    This adapter preserves identity/provenance and deliberately does not create
    claims, eligibility decisions, quality judgments, or recommendations.
    """

    materialized = dict(row)
    identity = canonical_identity(materialized)
    if not identity:
        raise ValueError("reference row has no canonical traceable identity")

    provider = _provider(materialized)
    if not provider:
        raise ValueError("reference row has no source provider")

    title = str(materialized.get("title") or "").strip()
    if not title:
        raise ValueError("reference row has no title")

    document_id = identity
    record_id = f"evidence:{identity}"

    taxonomy_values: list[str] = []
    primary = materialized.get("taxonomy_primary")
    if primary:
        taxonomy_values.append(str(primary))
    secondary = materialized.get("taxonomy_secondary") or []
    if isinstance(secondary, (list, tuple)):
        taxonomy_values.extend(str(item) for item in secondary if item)

    document = DocumentCandidate(
        id=document_id,
        source_provider=provider,
        title=title,
        doi=normalize_doi(materialized.get("doi") or materialized.get("doi_normalized")) or None,
        pmid=normalize_pmid(materialized.get("pmid") or materialized.get("pmid_normalized")) or None,
        url=str(materialized.get("url") or materialized.get("url_normalized") or "").strip() or None,
        year=_year(materialized),
        metadata={
            "reference_rank": materialized.get("reference_rank"),
            "reference_score": materialized.get("reference_score"),
            "reference_tier": materialized.get("reference_tier"),
            "audit_traceability": materialized.get("audit_traceability"),
        },
    )

    evidence = EvidenceRecord(
        id=record_id,
        document_id=document_id,
        source_provider=provider,
        source_run_id=source_run_id or materialized.get("audit_source_run_id"),
        origin_sha256=origin_sha256 or materialized.get("audit_origin_sha256"),
        taxonomy=tuple(dict.fromkeys(taxonomy_values)),
        metadata={
            "audit_source_manifest_path": materialized.get("audit_source_manifest_path"),
            "audit_source_master_sha256": materialized.get("audit_source_master_sha256"),
        },
    )

    return document, evidence
