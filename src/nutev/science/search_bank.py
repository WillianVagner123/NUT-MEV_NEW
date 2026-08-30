"""Bridge persisted NutEV web-search runs into the reusable scientific bank.

The first bank pass is intentionally low-cost: it processes every deduplicated
reference using metadata/abstracts only. It does not perform network full-text
retrieval and it makes no external LLM calls. Operational A/B/C/D tiers are
recorded for later selective deepening; they are not eligibility decisions.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable
from uuid import uuid4

from nutev.audit_guardrails import sha256_file
from nutev.science.core import run_core_bank_export
from nutev.science.enrichment import run_document_enrichment
from nutev.science.excerpts import run_evidence_excerpt_extraction
from nutev.science.export import run_scientific_export
from nutev.science.semantic import run_semantic_deconstruction
from nutev.science.workbench import run_workbench_index


class SearchBankError(RuntimeError):
    """Raised when a persisted search cannot safely enter the NutEV bank."""


_SEARCH_ID_RE = re.compile(r"^web_[A-Za-z0-9+_-]+$")
ProgressCallback = Callable[[dict[str, Any]], None]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return _atomic_text(
        path,
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
            for row in rows
        ),
    )


def _emit(callback: ProgressCallback | None, stage: str, **payload: Any) -> None:
    if callback is None:
        return
    try:
        callback({"stage": stage, "at": _now(), **payload})
    except Exception:
        return


def _safe_search_id(search_id: str) -> str:
    value = str(search_id or "").strip()
    if not _SEARCH_ID_RE.fullmatch(value):
        raise SearchBankError("search_id inválido")
    return value


def _search_path(output_root: Path, search_id: str) -> Path:
    return output_root / "15_web_searches" / _safe_search_id(search_id) / "result.json"


def latest_search_id(output_root: Path) -> str:
    candidates = sorted(
        output_root.glob("15_web_searches/web_*/result.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SearchBankError("nenhuma busca web persistida foi encontrada")
    return candidates[0].parent.name


def _load_search(output_root: Path, search_id: str) -> tuple[dict[str, Any], Path, str]:
    path = _search_path(output_root, search_id)
    if not path.is_file():
        raise SearchBankError(f"busca persistida não encontrada: {search_id}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SearchBankError(f"result.json inválido: {exc}") from exc
    if not isinstance(value, dict):
        raise SearchBankError("result.json precisa ser um objeto")
    if str(value.get("search_id") or "") != search_id:
        raise SearchBankError("search_id do arquivo não corresponde ao diretório")
    status = str(value.get("status") or "")
    if not status.startswith("COMPLETE"):
        raise SearchBankError(f"busca ainda não está concluída: {status or 'sem status'}")
    rows = value.get("results")
    if not isinstance(rows, list) or not rows:
        raise SearchBankError("busca concluída não contém resultados para importar")
    returned = value.get("returned_records")
    if returned is not None and int(returned) != len(rows):
        raise SearchBankError(
            f"returned_records diverge de results: {returned} != {len(rows)}"
        )
    return value, path, sha256_file(path)


def tier_boundaries(total: int) -> dict[str, int]:
    """Return cumulative deterministic processing cutoffs.

    A = top 2%, B = next 8%, C = next 30%, D = remainder. For tiny corpora,
    every non-empty tier is allowed to collapse naturally; no scientific meaning
    is attached to these operational buckets.
    """
    if total <= 0:
        return {"A": 0, "B": 0, "C": 0, "D": 0}
    a_end = min(total, max(1, math.ceil(total * 0.02)))
    b_end = min(total, max(a_end, math.ceil(total * 0.10)))
    c_end = min(total, max(b_end, math.ceil(total * 0.40)))
    return {"A": a_end, "B": b_end, "C": c_end, "D": total}


def _tier_for_position(position: int, boundaries: dict[str, int]) -> str:
    if position <= boundaries["A"]:
        return "A"
    if position <= boundaries["B"]:
        return "B"
    if position <= boundaries["C"]:
        return "C"
    return "D"


def _materialize_ranking_row(
    raw: dict[str, Any],
    *,
    position: int,
    tier: str,
    search_id: str,
    search_sha: str,
    source_path: Path,
) -> dict[str, Any]:
    row = dict(raw)
    row["reference_rank"] = position
    row["source_reference_tier"] = row.get("reference_tier")
    row["reference_tier"] = f"BANK_{tier}_PROCESSING_PRIORITY"
    row["bank_processing_tier"] = tier
    row["bank_processing_policy"] = "rank_percentile_operational_not_eligibility"
    row["reference_provider"] = (
        row.get("reference_provider") or row.get("source_provider") or row.get("source")
    )
    row["reference_year"] = row.get("reference_year") or row.get("year")
    row["audit_traceability"] = row.get("audit_traceability") or "WEB_SEARCH_PERSISTED_RESULT"
    row["audit_quarantined"] = False
    row["audit_origin_sha256"] = search_sha
    row["audit_source_run_id"] = search_id
    row["audit_source_master_sha256"] = search_sha
    row["audit_source_manifest_path"] = str(source_path)
    return row


def prepare_search_for_bank(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
) -> dict[str, Any]:
    """Tier and audit every deduplicated record from a persisted web search."""
    output_root = output_root.resolve()
    search_id = _safe_search_id(search_id)
    search, source_path, source_sha = _load_search(output_root, search_id)
    rows = [dict(item) for item in search["results"] if isinstance(item, dict)]
    if len(rows) != len(search["results"]):
        raise SearchBankError("results contém item que não é objeto")

    boundaries = tier_boundaries(len(rows))
    prepared: list[dict[str, Any]] = []
    for position, raw in enumerate(rows, start=1):
        title = str(raw.get("title") or "").strip()
        provider = str(raw.get("source_provider") or raw.get("source") or "").strip()
        if not title or not provider:
            raise SearchBankError(
                f"registro {position} sem título ou provider não pode entrar no banco"
            )
        tier = _tier_for_position(position, boundaries)
        prepared.append(
            _materialize_ranking_row(
                raw,
                position=position,
                tier=tier,
                search_id=search_id,
                search_sha=source_sha,
                source_path=source_path,
            )
        )

    bank_root = output_root / "bank" / "searches" / search_id
    ranking_path = bank_root / "reference_ranking.jsonl"
    audit_path = bank_root / "AUDIT_MANIFEST.json"
    import_manifest_path = bank_root / "BANK_IMPORT_MANIFEST.json"
    ranking_sha = _write_jsonl(ranking_path, prepared)

    tier_counts = Counter(str(row["bank_processing_tier"]) for row in prepared)
    audit_manifest = {
        "schema_version": 1,
        "audit_type": "REFERENCE_RANKING_AUDIT",
        "status": "PASS",
        "created_at": _now(),
        "source": {
            "search_id": search_id,
            "result_json": str(source_path),
            "result_json_sha256": source_sha,
            "search_status": search.get("status"),
            "search_mode": search.get("search_mode"),
        },
        "outputs": {
            "ranking_jsonl": {"path": str(ranking_path), "sha256": ranking_sha}
        },
        "guardrails": {
            "tiers_are_operational_not_eligibility": True,
            "ranking_is_not_quality": True,
            "formal_search_not_inferred": True,
            "prisma_event_not_created": True,
        },
    }
    audit_sha = _write_json(audit_path, audit_manifest)

    provider_gaps = sorted(
        set(
            list(search.get("failed_providers") or [])
            + list(search.get("unavailable_providers") or [])
            + list(search.get("non_exhaustive_providers") or [])
        )
    )
    import_manifest = {
        "schema_version": 1,
        "import_type": "NUTEV_WEB_SEARCH_TO_BANK",
        "status": "PASS",
        "created_at": _now(),
        "search_id": search_id,
        "source_result_sha256": source_sha,
        "records": len(prepared),
        "tier_policy": {
            "A": "top 2% by existing NutEV reading-priority rank",
            "B": "2-10%",
            "C": "10-40%",
            "D": "40-100%",
            "semantics": "operational processing priority only; not inclusion, quality, certainty, or recommendation",
        },
        "tier_counts": {tier: int(tier_counts.get(tier, 0)) for tier in ("A", "B", "C", "D")},
        "provider_gaps_preserved": provider_gaps,
        "deepening_candidates": ["A", "B"],
        "initial_materialization": {
            "network_full_text_retrieval": False,
            "external_llm_calls": 0,
            "abstract_fallback_allowed": True,
        },
        "outputs": {
            "ranking_jsonl": {"path": str(ranking_path), "sha256": ranking_sha},
            "audit_manifest": {"path": str(audit_path), "sha256": audit_sha},
        },
    }
    import_sha = _write_json(import_manifest_path, import_manifest)
    return {
        "status": "PREPARED",
        "search_id": search_id,
        "records": len(prepared),
        "tier_counts": import_manifest["tier_counts"],
        "provider_gaps": provider_gaps,
        "ranking_jsonl": str(ranking_path),
        "audit_manifest": str(audit_path),
        "bank_import_manifest": str(import_manifest_path),
        "bank_import_manifest_sha256": import_sha,
    }


def run_search_bank_pipeline(
    search_id: str,
    *,
    output_root: Path = Path("project_output_reference"),
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Materialize one saved search into the low-token Article Workbench.

    This pass intentionally disables network full-text retrieval. All references
    can therefore enter the operational library using available abstracts or
    metadata, while A/B tiers remain explicitly marked for later deepening.
    """
    output_root = output_root.resolve()
    search_id = _safe_search_id(search_id)

    _emit(on_progress, "preparing", search_id=search_id)
    prepared = prepare_search_for_bank(search_id, output_root=output_root)

    scientific = output_root / "scientific"
    ranking = Path(str(prepared["ranking_jsonl"]))
    audit = Path(str(prepared["audit_manifest"]))

    _emit(on_progress, "scientific_export", records=prepared["records"])
    export = run_scientific_export(ranking, audit, scientific)

    _emit(on_progress, "enrichment_abstract_only", records=prepared["records"])
    enrichment = run_document_enrichment(
        scientific / "document_candidates.jsonl",
        scientific / "SCIENTIFIC_EXPORT_MANIFEST.json",
        scientific / "enrichment",
        allow_network=False,
    )

    _emit(on_progress, "core", records=prepared["records"])
    core = run_core_bank_export(
        scientific / "document_candidates.jsonl",
        scientific / "evidence_records.jsonl",
        scientific / "SCIENTIFIC_EXPORT_MANIFEST.json",
        scientific / "enrichment" / "full_text_artifacts.jsonl",
        scientific / "enrichment" / "document_enrichments.jsonl",
        scientific / "enrichment" / "reviewer_dossiers.jsonl",
        scientific / "enrichment" / "ENRICHMENT_MANIFEST.json",
        scientific / "core",
    )

    _emit(on_progress, "semantic", records=prepared["records"])
    semantic = run_semantic_deconstruction(
        scientific / "core" / "nutev_core_records.jsonl",
        scientific / "core" / "CORE_MANIFEST.json",
        scientific / "enrichment" / "document_enrichments.jsonl",
        scientific / "enrichment" / "ENRICHMENT_MANIFEST.json",
        scientific / "semantic",
    )

    _emit(on_progress, "excerpts", records=prepared["records"])
    excerpts = run_evidence_excerpt_extraction(
        scientific / "semantic" / "nutev_core_records_semantic.jsonl",
        scientific / "semantic" / "semantic_fact_candidates.jsonl",
        scientific / "semantic" / "SEMANTIC_MANIFEST.json",
        scientific / "excerpts",
    )

    _emit(on_progress, "workbench_index", records=prepared["records"])
    workbench = run_workbench_index(
        scientific / "excerpts" / "evidence_excerpts.jsonl",
        scientific / "excerpts" / "result_bundles.jsonl",
        scientific / "excerpts" / "article_evidence_cards.jsonl",
        scientific / "excerpts" / "EXCERPT_MANIFEST.json",
        scientific / "workbench",
    )

    completion = {
        "schema_version": 1,
        "run_type": "NUTEV_SEARCH_BANK_MATERIALIZATION",
        "status": "COMPLETE",
        "created_at": _now(),
        "search_id": search_id,
        "records": prepared["records"],
        "tier_counts": prepared["tier_counts"],
        "provider_gaps_preserved": prepared["provider_gaps"],
        "cost_policy": {
            "network_full_text_retrieval": False,
            "external_llm_calls": 0,
            "full_text_deepening": "deferred_to_explicit_A_or_B_stage",
        },
        "stages": {
            "scientific_export": export,
            "enrichment": enrichment,
            "core": core,
            "semantic": semantic,
            "excerpts": excerpts,
            "workbench": workbench,
        },
        "guardrails": {
            "bank_presence_is_not_scientific_inclusion": True,
            "tiers_are_not_quality_or_risk_of_bias": True,
            "no_prisma_events_inferred": True,
            "provider_gaps_not_recoded_as_zero_coverage": True,
        },
    }
    completion_path = output_root / "bank" / "searches" / search_id / "BANK_PIPELINE_MANIFEST.json"
    completion_sha = _write_json(completion_path, completion)
    _emit(on_progress, "complete", records=prepared["records"])
    return {
        "status": "COMPLETE",
        "search_id": search_id,
        "records": prepared["records"],
        "tier_counts": prepared["tier_counts"],
        "provider_gaps": prepared["provider_gaps"],
        "workbench": workbench,
        "manifest": str(completion_path),
        "manifest_sha256": completion_sha,
    }
