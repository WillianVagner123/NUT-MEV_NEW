"""Selective, resumable full-text deepening for the NutEV scientific bank.

Deepening is an operational retrieval/extraction stage. It uses the existing bank
priority only to decide processing order; it does not create scientific inclusion,
quality, risk-of-bias, certainty, or recommendation judgments.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file
from nutev.reference_identity import canonical_identity
from nutev.science.core import run_core_bank_export
from nutev.science.enrichment import run_document_enrichment
from nutev.science.excerpts import run_evidence_excerpt_extraction
from nutev.science.export import run_scientific_export
from nutev.science.semantic import run_semantic_deconstruction
from nutev.science.workbench_deepening import overlay_workbench_deepening


class BankDeepeningError(RuntimeError):
    """Raised when a selective deepening run cannot prove source integrity."""


ProgressCallback = Callable[[dict[str, Any]], None]
_TIERS = {"A", "B", "C", "D"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(callback: ProgressCallback | None, stage: str, **payload: Any) -> None:
    if callback is None:
        return
    try:
        callback({"stage": stage, "at": _now(), **payload})
    except Exception:
        return


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BankDeepeningError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BankDeepeningError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BankDeepeningError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise BankDeepeningError(f"missing {label}: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BankDeepeningError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise BankDeepeningError(f"non-object {label} row at {path}:{line_number}")
            rows.append(value)
    if not rows:
        raise BankDeepeningError(f"{label} is empty: {path}")
    return rows


def _atomic_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    return _atomic_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> str:
    return _atomic_text(
        path,
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True, default=str) + "\n"
            for row in rows
        ),
    )


def _bank_ranking(output_root: Path, search_id: str) -> tuple[list[dict[str, Any]], Path, str]:
    bank_root = output_root / "bank" / "searches" / search_id
    ranking_path = bank_root / "reference_ranking.jsonl"
    audit_path = bank_root / "AUDIT_MANIFEST.json"
    audit = _read_json(audit_path)
    if audit.get("audit_type") != "REFERENCE_RANKING_AUDIT" or audit.get("status") != "PASS":
        raise BankDeepeningError("bank ranking audit is not PASS")
    expected = str(
        (((audit.get("outputs") or {}).get("ranking_jsonl") or {}).get("sha256")) or ""
    ).strip().lower()
    if not expected:
        raise BankDeepeningError("bank ranking audit has no ranking SHA-256")
    actual = sha256_file(ranking_path)
    if actual != expected:
        raise BankDeepeningError(
            f"bank ranking SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return _read_jsonl(ranking_path, label="bank ranking"), ranking_path, actual


def _tier(row: Mapping[str, Any]) -> str:
    direct = str(row.get("bank_processing_tier") or "").strip().upper()
    if direct in _TIERS:
        return direct
    label = str(row.get("reference_tier") or "").strip().upper()
    for tier in sorted(_TIERS):
        if label == f"BANK_{tier}_PROCESSING_PRIORITY":
            return tier
    return ""


def _rank(row: Mapping[str, Any]) -> int:
    try:
        value = int(row.get("reference_rank") or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        raise BankDeepeningError("bank row lacks positive reference_rank")
    return value


def _lookup_url(row: Mapping[str, Any]) -> str | None:
    pmcid = str(row.get("pmcid") or row.get("pmc_id") or "").strip()
    if pmcid:
        normalized = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{normalized}/"
    for key in ("pdf_url", "full_text_url", "open_access_url", "oa_url", "url", "url_normalized"):
        value = str(row.get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    doi = str(row.get("doi") or row.get("doi_normalized") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"
    pmid = str(row.get("pmid") or row.get("pmid_normalized") or "").strip()
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    return None


def _asset_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    document_id = canonical_identity(dict(row))
    if not document_id:
        raise BankDeepeningError("selected bank row has no canonical document identity")
    url = _lookup_url(row)
    if not url:
        return None
    scope: str | None = None
    lower = url.casefold()
    if lower.endswith(".pdf") or "/pdf" in lower or "pmc.ncbi.nlm.nih.gov/articles/" in lower:
        scope = "full_text"
    elif str(row.get("full_text_url") or "").strip() == url:
        scope = "full_text"
    payload: dict[str, Any] = {"document_id": document_id, "url": url}
    if scope:
        payload["scope"] = scope
    return payload


def _prepare_batch_inputs(
    batch_rows: list[dict[str, Any]],
    *,
    batch_root: Path,
    source_ranking_sha: str,
    source_ranking_path: Path,
    search_id: str,
    tier: str,
) -> tuple[Path, Path, Path | None, str]:
    input_root = batch_root / "input"
    materialized: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    for raw in batch_rows:
        row = dict(raw)
        if not str(row.get("url") or row.get("url_normalized") or "").strip():
            lookup = _lookup_url(row)
            if lookup:
                row["url"] = lookup
                row["deepening_lookup_url_materialized"] = True
        materialized.append(row)
        asset = _asset_row(row)
        if asset is not None:
            assets.append(asset)

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
            "selection_semantics": "operational deepening order only; not scientific eligibility",
        },
        "outputs": {
            "ranking_jsonl": {"path": str(ranking_path), "sha256": ranking_sha},
        },
        "guardrails": {
            "tier_is_not_scientific_inclusion": True,
            "rank_is_not_evidence_quality": True,
            "deepening_is_not_prisma_screening": True,
        },
    }
    _write_json(audit_path, audit)
    assets_path: Path | None = None
    if assets:
        assets_path = input_root / "full_text_assets.jsonl"
        _write_jsonl(assets_path, assets)
    return ranking_path, audit_path, assets_path, ranking_sha


def _workbench_has_batch(workbench_root: Path, batch_id: str) -> bool:
    try:
        manifest = _read_json(workbench_root / "WORKBENCH_MANIFEST.json")
    except BankDeepeningError:
        return False
    batches = ((((manifest.get("extensions") or {}).get("deepening") or {}).get("batches")) or {})
    return isinstance(batches, dict) and isinstance(batches.get(batch_id), dict) and batches[batch_id].get("status") == "PASS"


def _batch_complete(batch_root: Path, workbench_root: Path, batch_id: str, source_ranking_sha: str) -> bool:
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
    )


def _artifact_status_counts(path: Path) -> dict[str, int]:
    rows = _read_jsonl(path, label="full-text artifacts")
    counts = Counter(str(row.get("retrieval_status") or "unknown") for row in rows)
    return dict(sorted(counts.items()))


def _summarize_batches(root: Path) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.glob("batches/*/BATCH_MANIFEST.json")):
        try:
            value = _read_json(path)
        except BankDeepeningError:
            continue
        if value.get("status") == "PASS":
            manifests.append(value)
    retrieval: Counter[str] = Counter()
    extraction: Counter[str] = Counter()
    processed = 0
    ocr = 0
    for manifest in manifests:
        processed += int(manifest.get("documents") or 0)
        ocr += int(manifest.get("ocr_used") or 0)
        retrieval.update({str(k): int(v) for k, v in (manifest.get("retrieval_status_counts") or {}).items()})
        extraction.update({str(k): int(v) for k, v in (manifest.get("extraction_method_counts") or {}).items()})
    return {
        "completed_batches": len(manifests),
        "processed_documents": processed,
        "ocr_used": ocr,
        "retrieval_status_counts": dict(sorted(retrieval.items())),
        "extraction_method_counts": dict(sorted(extraction.items())),
    }


def run_selective_bank_deepening(
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
    """Deepen one bank tier in resumable batches and overlay each completed batch."""

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
    )

    completed_this_run = 0
    skipped_this_run = 0
    for offset in range(0, len(selected), batch_size):
        batch_rows = selected[offset : offset + batch_size]
        first_rank = _rank(batch_rows[0])
        last_rank = _rank(batch_rows[-1])
        batch_id = f"tier-{tier}-rank-{first_rank:06d}-{last_rank:06d}"
        batch_root = tier_root / "batches" / batch_id
        if _batch_complete(batch_root, workbench_root, batch_id, ranking_sha):
            skipped_this_run += 1
            _emit(on_progress, "batch_skipped_complete", batch_id=batch_id, documents=len(batch_rows))
            continue

        _emit(
            on_progress,
            "batch_start",
            batch_id=batch_id,
            documents=len(batch_rows),
            first_rank=first_rank,
            last_rank=last_rank,
        )
        ranking_subset, audit_subset, assets_path, subset_sha = _prepare_batch_inputs(
            batch_rows,
            batch_root=batch_root,
            source_ranking_sha=ranking_sha,
            source_ranking_path=ranking_path,
            search_id=search_id,
            tier=tier,
        )

        export_root = batch_root / "export"
        _emit(on_progress, "scientific_export", batch_id=batch_id)
        export = run_scientific_export(ranking_subset, audit_subset, export_root)

        enrichment_root = batch_root / "enrichment"
        _emit(on_progress, "full_text_enrichment", batch_id=batch_id, allow_network=allow_network)
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
            "retrieval_status_counts": _artifact_status_counts(
                enrichment_root / "full_text_artifacts.jsonl"
            ),
            "extraction_method_counts": dict(sorted(extraction_counts.items())),
            "ocr_used": int((enrichment_manifest.get("counts") or {}).get("ocr_used") or 0),
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
            ocr_used=batch_manifest["ocr_used"],
        )

        summary = _summarize_batches(tier_root)
        overall = {
            "schema_version": 1,
            "deepening_type": "NUTEV_SELECTIVE_BANK_DEEPENING",
            "status": "PASS_IN_PROGRESS",
            "updated_at": _now(),
            "search_id": search_id,
            "tier": tier,
            "source_bank_ranking": str(ranking_path),
            "source_bank_ranking_sha256": ranking_sha,
            "network_fetch_enabled": allow_network,
            "summary": summary,
            "target_tier_records": sum(1 for row in ranking_rows if _tier(row) == tier),
            "guardrail": (
                "Deepening means retrieval/extraction and richer machine candidates only; it is not "
                "eligibility, evidence quality, risk of bias, certainty, or recommendation."
            ),
        }
        _write_json(tier_root / "DEEPENING_MANIFEST.json", overall)

    summary = _summarize_batches(tier_root)
    target_tier_records = sum(1 for row in ranking_rows if _tier(row) == tier)
    overall_status = "COMPLETE" if summary["processed_documents"] >= target_tier_records else "PARTIAL"
    overall = {
        "schema_version": 1,
        "deepening_type": "NUTEV_SELECTIVE_BANK_DEEPENING",
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
    )
    return {
        "mode": "NUTEV_SELECTIVE_BANK_DEEPENING",
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
