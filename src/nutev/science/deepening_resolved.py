"""Selective deepening with public/open-access URL resolution.

This module reuses the validated deepening stages and changes only the document
URL selection/checkpoint version. It exists as an incremental compatibility layer
so the original worker remains available while resolver-v2 is validated in
production.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from nutev.reference_identity import canonical_identity
from nutev.science.core import run_core_bank_export
from nutev.science.deepening import (
    BankDeepeningError,
    ProgressCallback,
    _artifact_status_counts,
    _bank_ranking,
    _emit,
    _lookup_url,
    _now,
    _rank,
    _read_json,
    _read_jsonl,
    _tier,
    _workbench_has_batch,
    _write_json,
    _write_jsonl,
)
from nutev.science.enrichment import run_document_enrichment
from nutev.science.excerpts import run_evidence_excerpt_extraction
from nutev.science.export import run_scientific_export
from nutev.science.full_text_resolver import resolve_full_text_candidates
from nutev.science.semantic import run_semantic_deconstruction
from nutev.science.workbench_deepening import overlay_workbench_deepening


DEEPENING_PIPELINE_VERSION = "oa_resolver_v2"
_TIERS = {"A", "B", "C", "D"}


def _resolved_asset_row(
    row: Mapping[str, Any],
    *,
    allow_network: bool,
) -> dict[str, Any] | None:
    document_id = canonical_identity(dict(row))
    if not document_id:
        raise BankDeepeningError("selected bank row has no canonical document identity")
    candidates = resolve_full_text_candidates(
        row,
        include_network_resolvers=allow_network,
    )
    if not candidates:
        return None
    selected = dict(candidates[0])
    payload: dict[str, Any] = {
        "document_id": document_id,
        "url": selected["url"],
        "scope": selected.get("scope") or "partial",
        "resolver_route": selected.get("resolver_route"),
        "resolver_source": selected.get("resolver_source"),
        "resolver_candidate_count": len(candidates),
        "resolver_candidates": candidates,
    }
    if selected.get("media_type"):
        payload["media_type"] = selected["media_type"]
    if selected.get("license"):
        payload["license"] = selected["license"]
    if selected.get("version"):
        payload["version"] = selected["version"]
    return payload


def _prepare_batch_inputs_resolved(
    batch_rows: list[dict[str, Any]],
    *,
    batch_root: Path,
    source_ranking_sha: str,
    source_ranking_path: Path,
    search_id: str,
    tier: str,
    allow_network: bool,
) -> tuple[Path, Path, Path | None, str, dict[str, int]]:
    input_root = batch_root / "input"
    materialized: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    resolver_routes: Counter[str] = Counter()
    for raw in batch_rows:
        row = dict(raw)
        if not str(row.get("url") or row.get("url_normalized") or "").strip():
            lookup = _lookup_url(row)
            if lookup:
                row["url"] = lookup
                row["deepening_lookup_url_materialized"] = True
        materialized.append(row)
        asset = _resolved_asset_row(row, allow_network=allow_network)
        if asset is not None:
            assets.append(asset)
            resolver_routes[str(asset.get("resolver_route") or "unknown")] += 1

    ranking_path = input_root / "reference_ranking.jsonl"
    ranking_sha = _write_jsonl(ranking_path, materialized)
    audit_path = input_root / "AUDIT_MANIFEST.json"
    audit = {
        "schema_version": 1,
        "audit_type": "REFERENCE_RANKING_AUDIT",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "search_id": search_id,
            "source_bank_ranking": str(source_ranking_path),
            "source_bank_ranking_sha256": source_ranking_sha,
            "tier": tier,
            "deepening_pipeline_version": DEEPENING_PIPELINE_VERSION,
            "selection_semantics": "operational deepening order only; not scientific eligibility",
        },
        "outputs": {
            "ranking_jsonl": {"path": str(ranking_path), "sha256": ranking_sha},
        },
        "guardrails": {
            "tier_is_not_scientific_inclusion": True,
            "rank_is_not_evidence_quality": True,
            "deepening_is_not_prisma_screening": True,
            "resolver_uses_public_or_open_access_candidates_only": True,
            "resolver_does_not_bypass_access_controls": True,
        },
    }
    _write_json(audit_path, audit)
    assets_path: Path | None = None
    if assets:
        assets_path = input_root / "full_text_assets.jsonl"
        _write_jsonl(assets_path, assets)
    return (
        ranking_path,
        audit_path,
        assets_path,
        ranking_sha,
        dict(sorted(resolver_routes.items())),
    )


def _batch_complete_resolved(
    batch_root: Path,
    workbench_root: Path,
    batch_id: str,
    source_ranking_sha: str,
) -> bool:
    path = batch_root / "BATCH_MANIFEST.json"
    if not path.is_file() or not _workbench_has_batch(workbench_root, batch_id):
        return False
    try:
        manifest = _read_json(path)
    except BankDeepeningError:
        return False
    return (
        manifest.get("status") == "PASS"
        and manifest.get("batch_id") == batch_id
        and manifest.get("source_bank_ranking_sha256") == source_ranking_sha
        and manifest.get("pipeline_version") == DEEPENING_PIPELINE_VERSION
    )


def _summarize_resolved_batches(root: Path) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.glob("batches/*/BATCH_MANIFEST.json")):
        try:
            value = _read_json(path)
        except BankDeepeningError:
            continue
        if (
            value.get("status") == "PASS"
            and value.get("pipeline_version") == DEEPENING_PIPELINE_VERSION
        ):
            manifests.append(value)
    retrieval: Counter[str] = Counter()
    extraction: Counter[str] = Counter()
    resolver_routes: Counter[str] = Counter()
    processed = 0
    ocr = 0
    for manifest in manifests:
        processed += int(manifest.get("documents") or 0)
        ocr += int(manifest.get("ocr_used") or 0)
        retrieval.update(
            {
                str(k): int(v)
                for k, v in (manifest.get("retrieval_status_counts") or {}).items()
            }
        )
        extraction.update(
            {
                str(k): int(v)
                for k, v in (manifest.get("extraction_method_counts") or {}).items()
            }
        )
        resolver_routes.update(
            {
                str(k): int(v)
                for k, v in (manifest.get("resolver_route_counts") or {}).items()
            }
        )
    return {
        "completed_batches": len(manifests),
        "processed_documents": processed,
        "ocr_used": ocr,
        "retrieval_status_counts": dict(sorted(retrieval.items())),
        "extraction_method_counts": dict(sorted(extraction.items())),
        "resolver_route_counts": dict(sorted(resolver_routes.items())),
    }


def run_selective_bank_deepening_resolved(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
    tier: str = "A",
    batch_size: int = 25,
    limit: int = 0,
    start_rank: int = 1,
    allow_network: bool = False,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Deepen a bank tier with OA resolution and versioned resumable batches."""

    output_root = output_root.resolve()
    tier = str(tier or "").strip().upper()
    if tier not in _TIERS:
        raise BankDeepeningError(f"invalid tier: {tier}")
    if batch_size < 1 or batch_size > 100:
        raise BankDeepeningError("batch_size must be between 1 and 100")
    if limit < 0 or start_rank < 1:
        raise BankDeepeningError("limit must be >= 0 and start_rank must be >= 1")

    ranking_rows, ranking_path, ranking_sha = _bank_ranking(output_root, search_id)
    selected = [
        dict(row)
        for row in ranking_rows
        if _tier(row) == tier and _rank(row) >= start_rank
    ]
    selected.sort(key=_rank)
    if limit:
        selected = selected[:limit]
    if not selected:
        raise BankDeepeningError("no bank records matched the requested deepening selection")

    tier_root = output_root / "scientific" / "deepening" / search_id / f"tier-{tier}"
    workbench_root = output_root / "scientific" / "workbench"
    _emit(
        on_progress,
        "selection_ready",
        search_id=search_id,
        tier=tier,
        selected=len(selected),
        first_rank=_rank(selected[0]),
        last_rank=_rank(selected[-1]),
        allow_network=allow_network,
        pipeline_version=DEEPENING_PIPELINE_VERSION,
    )

    completed_this_run = 0
    skipped_this_run = 0
    for offset in range(0, len(selected), batch_size):
        batch_rows = selected[offset : offset + batch_size]
        first_rank = _rank(batch_rows[0])
        last_rank = _rank(batch_rows[-1])
        batch_id = f"tier-{tier}-rank-{first_rank:06d}-{last_rank:06d}"
        batch_root = tier_root / "batches" / batch_id
        if _batch_complete_resolved(batch_root, workbench_root, batch_id, ranking_sha):
            skipped_this_run += 1
            _emit(
                on_progress,
                "batch_skipped_complete",
                batch_id=batch_id,
                documents=len(batch_rows),
            )
            continue

        _emit(
            on_progress,
            "batch_start",
            batch_id=batch_id,
            documents=len(batch_rows),
            first_rank=first_rank,
            last_rank=last_rank,
        )
        (
            ranking_subset,
            audit_subset,
            assets_path,
            subset_sha,
            resolver_route_counts,
        ) = _prepare_batch_inputs_resolved(
            batch_rows,
            batch_root=batch_root,
            source_ranking_sha=ranking_sha,
            source_ranking_path=ranking_path,
            search_id=search_id,
            tier=tier,
            allow_network=allow_network,
        )
        _emit(
            on_progress,
            "full_text_resolution",
            batch_id=batch_id,
            resolver_routes=resolver_route_counts,
        )

        export_root = batch_root / "export"
        _emit(on_progress, "scientific_export", batch_id=batch_id)
        export = run_scientific_export(ranking_subset, audit_subset, export_root)

        enrichment_root = batch_root / "enrichment"
        _emit(
            on_progress,
            "full_text_enrichment",
            batch_id=batch_id,
            allow_network=allow_network,
        )
        enrichment = run_document_enrichment(
            export_root / "document_candidates.jsonl",
            export_root / "SCIENTIFIC_EXPORT_MANIFEST.json",
            enrichment_root,
            assets_jsonl=assets_path,
            allow_network=allow_network,
        )

        core_root = batch_root / "core"
        _emit(on_progress, "core", batch_id=batch_id)
        core = run_core_bank_export(
            export_root / "document_candidates.jsonl",
            export_root / "evidence_records.jsonl",
            export_root / "SCIENTIFIC_EXPORT_MANIFEST.json",
            enrichment_root / "full_text_artifacts.jsonl",
            enrichment_root / "document_enrichments.jsonl",
            enrichment_root / "reviewer_dossiers.jsonl",
            enrichment_root / "ENRICHMENT_MANIFEST.json",
            core_root,
        )

        semantic_root = batch_root / "semantic"
        _emit(on_progress, "semantic", batch_id=batch_id)
        semantic = run_semantic_deconstruction(
            core_root / "nutev_core_records.jsonl",
            core_root / "CORE_MANIFEST.json",
            enrichment_root / "document_enrichments.jsonl",
            enrichment_root / "ENRICHMENT_MANIFEST.json",
            semantic_root,
        )

        excerpts_root = batch_root / "excerpts"
        _emit(on_progress, "excerpts", batch_id=batch_id)
        excerpts = run_evidence_excerpt_extraction(
            semantic_root / "nutev_core_records_semantic.jsonl",
            semantic_root / "semantic_fact_candidates.jsonl",
            semantic_root / "SEMANTIC_MANIFEST.json",
            excerpts_root,
        )

        _emit(on_progress, "workbench_overlay", batch_id=batch_id)
        overlay = overlay_workbench_deepening(
            workbench_root=workbench_root,
            batch_id=batch_id,
            search_id=search_id,
            tier=tier,
            article_cards_jsonl=excerpts_root / "article_evidence_cards.jsonl",
            evidence_excerpts_jsonl=excerpts_root / "evidence_excerpts.jsonl",
            result_bundles_jsonl=excerpts_root / "result_bundles.jsonl",
            excerpt_manifest=excerpts_root / "EXCERPT_MANIFEST.json",
            enrichments_jsonl=enrichment_root / "document_enrichments.jsonl",
            enrichment_manifest=enrichment_root / "ENRICHMENT_MANIFEST.json",
        )

        enrichment_manifest = _read_json(enrichment_root / "ENRICHMENT_MANIFEST.json")
        extraction_rows = _read_jsonl(
            enrichment_root / "document_enrichments.jsonl",
            label="document enrichments",
        )
        extraction_counts = Counter(
            str(row.get("extraction_method") or "unknown") for row in extraction_rows
        )
        batch_manifest = {
            "schema_version": 1,
            "deepening_type": "NUTEV_SELECTIVE_BANK_DEEPENING_BATCH",
            "pipeline_version": DEEPENING_PIPELINE_VERSION,
            "status": "PASS",
            "created_at": _now(),
            "batch_id": batch_id,
            "search_id": search_id,
            "tier": tier,
            "first_rank": first_rank,
            "last_rank": last_rank,
            "documents": len(batch_rows),
            "source_bank_ranking": str(ranking_path),
            "source_bank_ranking_sha256": ranking_sha,
            "subset_ranking_sha256": subset_sha,
            "network_fetch_enabled": allow_network,
            "resolver_route_counts": resolver_route_counts,
            "retrieval_status_counts": _artifact_status_counts(
                enrichment_root / "full_text_artifacts.jsonl"
            ),
            "extraction_method_counts": dict(sorted(extraction_counts.items())),
            "ocr_used": int(
                (enrichment_manifest.get("counts") or {}).get("ocr_used") or 0
            ),
            "stages": {
                "export": export,
                "enrichment": enrichment,
                "core": core,
                "semantic": semantic,
                "excerpts": excerpts,
                "workbench_overlay": overlay,
            },
            "guardrails": {
                "deepening_is_not_scientific_inclusion": True,
                "tier_is_operational_priority_only": True,
                "machine_candidates_are_not_evidence_claims": True,
                "copyrighted_full_text_is_private_execution_material": True,
                "resolver_does_not_bypass_access_controls": True,
            },
        }
        _write_json(batch_root / "BATCH_MANIFEST.json", batch_manifest)
        completed_this_run += 1
        _emit(
            on_progress,
            "batch_complete",
            batch_id=batch_id,
            documents=len(batch_rows),
            retrieval=batch_manifest["retrieval_status_counts"],
            resolver_routes=resolver_route_counts,
            ocr_used=batch_manifest["ocr_used"],
        )

        summary = _summarize_resolved_batches(tier_root)
        overall = {
            "schema_version": 1,
            "deepening_type": "NUTEV_SELECTIVE_BANK_DEEPENING",
            "pipeline_version": DEEPENING_PIPELINE_VERSION,
            "status": "PASS_IN_PROGRESS",
            "updated_at": _now(),
            "search_id": search_id,
            "tier": tier,
            "source_bank_ranking": str(ranking_path),
            "source_bank_ranking_sha256": ranking_sha,
            "network_fetch_enabled": allow_network,
            "summary": summary,
            "target_tier_records": sum(
                1 for row in ranking_rows if _tier(row) == tier
            ),
            "guardrail": (
                "Deepening means retrieval/extraction and richer machine candidates only; it is not "
                "eligibility, evidence quality, risk of bias, certainty, or recommendation."
            ),
        }
        _write_json(tier_root / "DEEPENING_MANIFEST.json", overall)

    summary = _summarize_resolved_batches(tier_root)
    target_tier_records = sum(1 for row in ranking_rows if _tier(row) == tier)
    overall_status = (
        "COMPLETE"
        if summary["processed_documents"] >= target_tier_records
        else "PARTIAL"
    )
    overall = {
        "schema_version": 1,
        "deepening_type": "NUTEV_SELECTIVE_BANK_DEEPENING",
        "pipeline_version": DEEPENING_PIPELINE_VERSION,
        "status": overall_status,
        "updated_at": _now(),
        "search_id": search_id,
        "tier": tier,
        "source_bank_ranking": str(ranking_path),
        "source_bank_ranking_sha256": ranking_sha,
        "network_fetch_enabled": allow_network,
        "target_tier_records": target_tier_records,
        "summary": summary,
        "guardrail": (
            "Deepening means retrieval/extraction and richer machine candidates only; it is not "
            "eligibility, evidence quality, risk of bias, certainty, or recommendation."
        ),
    }
    manifest_path = tier_root / "DEEPENING_MANIFEST.json"
    manifest_sha = _write_json(manifest_path, overall)
    _emit(
        on_progress,
        "complete",
        status=overall_status,
        tier=tier,
        processed_documents=summary["processed_documents"],
        target_tier_records=target_tier_records,
        pipeline_version=DEEPENING_PIPELINE_VERSION,
    )
    return {
        "mode": "NUTEV_SELECTIVE_BANK_DEEPENING",
        "pipeline_version": DEEPENING_PIPELINE_VERSION,
        "status": overall_status,
        "search_id": search_id,
        "tier": tier,
        "selected_this_run": len(selected),
        "completed_batches_this_run": completed_this_run,
        "skipped_batches_this_run": skipped_this_run,
        "target_tier_records": target_tier_records,
        **summary,
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "external_llm_calls": 0,
    }
