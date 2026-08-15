from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from nutev.search.base import ProviderResult
from nutev.search.gf02_evidence import validate_sentinel_registry
from nutev.search.gf02_pubmed_current import (
    LOCAL_TIMEZONE,
    _MECHANISM_LINES,
    _binary,
    _boolean_semantics_warning,
    _git_sha,
    _hash_file,
    _hash_text,
    _run,
    _search,
    _version_slug,
    _write_json,
    _write_sample,
    load_candidate_config,
    load_sentinel_registry,
    resolved_line_expressions,
)
from nutev.search.pubmed import _request_json

ProgressFn = Callable[[str], None]
SearchFn = Callable[[str, int, dict[str, Any]], ProviderResult]


def _emit(progress_fn: ProgressFn | None, message: str) -> None:
    if progress_fn is not None:
        progress_fn(message)


def _direct_count(query: str, *, mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run one PubMed ESearch count without downloading record summaries."""
    try:
        payload = _request_json(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "retmode": "json",
                "term": query,
                "retmax": 0,
            },
        )
        esearch = payload.get("esearchresult", {})
        total = int(esearch.get("count") or 0)
        meta = {
            "querytranslation": str(esearch.get("querytranslation") or ""),
            "translationset": esearch.get("translationset") or [],
            "warninglist": esearch.get("warninglist") or {},
            "errorlist": esearch.get("errorlist") or {},
            "count_only": True,
        }
        errorlist = meta["errorlist"]
        status = "empty" if total == 0 else "completed"
        error = ""
        if errorlist:
            status = "failed"
            error = f"PubMed ESearch errorlist: {errorlist}"
    except Exception as exc:
        total = None
        meta = {"count_only": True}
        status = "failed"
        error = str(exc)

    return (
        {
            "provider": "pubmed",
            "exact_query": query,
            "query_sha256": _hash_text(query),
            "retrieval_mode": mode,
            "fetch_limit": 0,
            "total_found": total,
            "records_returned": 0,
            "rows_capped": bool(total),
            "status": status,
            "error": error,
            "ncbi_query_translation": str(meta.get("querytranslation") or ""),
            "provider_meta": meta,
        },
        [],
    )


def _count_or_injected(
    query: str,
    *,
    mode: str,
    workstream: str,
    checkpoint_dir: Path,
    search_fn: SearchFn | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if search_fn is None:
        return _direct_count(query, mode=mode)
    return _run(query, 1, workstream, checkpoint_dir, search_fn, mode)


def run_gf02_pubmed_pilot(
    repo_root: Path,
    *,
    project_root: Path,
    limit: int = 10000,
    noise_sample_size: int | None = None,
    noise_seed: int = 20260812,
    search_fn: SearchFn | None = None,
    started_at: str | None = None,
    run_id: str | None = None,
    progress_fn: ProgressFn | None = None,
) -> dict[str, Any]:
    """Execute the current GF-02 PubMed PILOT with a fast count-first plan.

    Scientific semantics are unchanged: all required lines are counted, Boolean
    warnings are audited, priority sentinels are probed, and the rescue-only
    sample remains human-classification-only. The optimization is operational:
    counts use ESearch retmax=0 and only the 10-20 rescue records needed for the
    human sample are downloaded.
    """
    repo = Path(repo_root)
    project = Path(project_root)
    config_path = repo / "config/gf02_pubmed_candidates.json"
    sentinel_path = repo / "config/article1_sentinel_registry.json"
    config = load_candidate_config(config_path)
    sentinels = load_sentinel_registry(sentinel_path)
    validate_sentinel_registry(sentinels)

    candidate_version = str(config["current_candidate"])
    version_slug = _version_slug(candidate_version)
    sentinel_map = {row.sentinel_id: row for row in sentinels}
    priority_ids = list((config.get("priority_expectations") or {}).keys())
    missing = [sentinel_id for sentinel_id in priority_ids if sentinel_id not in sentinel_map]
    if missing:
        raise ValueError("priority sentinel identity missing from registry: " + ", ".join(missing))
    if not 1 <= int(limit) <= 10000:
        raise ValueError("GF-02 PubMed limit must be between 1 and 10000")

    sample_cfg = config["rescue_sample"]
    sample_size = int(noise_sample_size if noise_sample_size is not None else sample_cfg["default"])
    if not int(sample_cfg["minimum"]) <= sample_size <= int(sample_cfg["maximum"]):
        raise ValueError("GF-02 PubMed rescue-only sample size must be between 10 and 20")

    stamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")
    resolved_run_id = run_id or f"gf02_pubmed_{version_slug}_" + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
    run_dir = project / "07_logs/gf02/pubmed" / resolved_run_id
    checkpoint_dir = run_dir / "checkpoints"
    run_dir.mkdir(parents=True, exist_ok=True)

    expressions = resolved_line_expressions(config)
    audits: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    count_lines = list(config["required_count_lines"])

    _emit(progress_fn, f"GF-02 {candidate_version}: iniciando PILOT PubMed.")
    for index, line_id in enumerate(count_lines, start=1):
        _emit(progress_fn, f"Contando {line_id} ({index}/{len(count_lines)})...")
        audit, _ = _count_or_injected(
            expressions[line_id],
            mode="COUNT_ONLY",
            workstream=f"gf02_{version_slug}_{line_id.replace('#', 'line_')}",
            checkpoint_dir=checkpoint_dir,
            search_fn=search_fn,
        )
        audits[line_id] = {
            "label": str(config["lines"][line_id].get("label") or ""),
            **audit,
        }
        _write_json(run_dir / f"{line_id.replace('#', 'line_')}.audit.json", audits[line_id])
        _emit(progress_fn, f"{line_id}: {audit['total_found']} registros.")

        semantic_warning = _boolean_semantics_warning(audit["provider_meta"])
        if semantic_warning:
            errors.append(f"{line_id}:BOOLEAN_SEMANTICS_WARNING:{semantic_warning}")
        if audit["status"] not in {"completed", "empty"}:
            errors.append(f"{line_id}:{audit['status']}:{audit['error']}")

    rescue_query = _binary(config, config["rescue_only"])
    _emit(progress_fn, f"Baixando somente {sample_size} registros do rescue-only para revisão humana...")
    rescue_search = search_fn or _search
    rescue, rescue_rows = _run(
        rescue_query,
        sample_size,
        f"gf02_{version_slug}_rescue_only",
        checkpoint_dir,
        rescue_search,
        "RESCUE_ONLY_SAMPLE",
    )
    _write_json(run_dir / f"{version_slug}_rescue_only.audit.json", rescue)
    rescue_semantic_warning = _boolean_semantics_warning(rescue["provider_meta"])
    if rescue_semantic_warning:
        errors.append("rescue_only:BOOLEAN_SEMANTICS_WARNING:" + rescue_semantic_warning)
    if rescue["status"] not in {"completed", "empty"}:
        errors.append(f"rescue_only:{rescue['status']}:{rescue['error']}")

    sample_path, actual_sample = _write_sample(
        run_dir / f"rescue_only_sample_{version_slug}.csv",
        rescue_rows,
        sample_size,
        noise_seed,
        rescue["total_found"],
        rescue["records_returned"],
        rescue["rows_capped"],
        candidate_version=candidate_version,
    )
    _emit(progress_fn, f"Amostra rescue-only pronta: {actual_sample} registros.")

    mechanism = {sentinel_id: {} for sentinel_id in priority_ids}
    probes: list[dict[str, Any]] = []
    total_probes = len(priority_ids) * len(_MECHANISM_LINES)
    probe_index = 0
    for sentinel_id in priority_ids:
        sentinel = sentinel_map[sentinel_id]
        for line_id in _MECHANISM_LINES:
            probe_index += 1
            _emit(progress_fn, f"Sentinela {sentinel_id} em {line_id} ({probe_index}/{total_probes})...")
            query = f"({expressions[line_id]}) AND {sentinel.pmid}[pmid]" if sentinel.pmid else ""
            if not query:
                probe = {
                    "sentinel_id": sentinel_id,
                    "line_id": line_id,
                    "status": "NOT_PROBED_NO_PMID",
                    "recovered": False,
                    "query": "",
                    "query_sha256": "",
                    "total_found": None,
                    "error": "priority PubMed mechanism probe requires PMID",
                }
            else:
                audit, rows = _count_or_injected(
                    query,
                    mode="SENTINEL_COUNT_ONLY",
                    workstream=f"gf02_probe_{line_id.replace('#', 'line_')}_{sentinel_id}",
                    checkpoint_dir=checkpoint_dir,
                    search_fn=search_fn,
                )
                probe = {
                    "sentinel_id": sentinel_id,
                    "line_id": line_id,
                    "status": audit["status"],
                    "recovered": bool(rows or (audit["total_found"] or 0) > 0),
                    "query": query,
                    "query_sha256": audit["query_sha256"],
                    "total_found": audit["total_found"],
                    "error": audit["error"],
                }
            probes.append(probe)
            mechanism[sentinel_id][line_id] = bool(probe["recovered"])
            if probe["status"] not in {"completed", "empty"}:
                errors.append(f"probe:{sentinel_id}:{line_id}:{probe['status']}:{probe['error']}")

    from nutev.search.gf02_pubmed_current import _write_jsonl

    _write_jsonl(run_dir / "priority_sentinel_probes.jsonl", probes)
    final = audits["#7"]
    manifest = {
        "schema_version": 4,
        "run_id": resolved_run_id,
        "route_id": config["route_id"],
        "candidate_version": candidate_version,
        "candidate_status": config["candidate_status"],
        "search_type": "PILOT",
        "formal_execution_authorized": False,
        "prisma_eligible": False,
        "started_at": stamp,
        "software_git_sha": _git_sha(repo),
        "candidate_config_path": str(config_path),
        "candidate_config_sha256": _hash_file(config_path),
        "sentinel_registry_path": str(sentinel_path),
        "sentinel_registry_sha256": _hash_file(sentinel_path),
        "methodology_decisions": list(config.get("methodology_decisions") or []),
        "canonical_operational_source": str(config.get("canonical_operational_source") or ""),
        "execution_plan": "COUNT_FIRST_SAMPLE_ONLY",
        "line_expressions": expressions,
        "line_audits": audits,
        "line_counts": {line_id: audits[line_id]["total_found"] for line_id in count_lines},
        "final_line": "#7",
        "final_total_found": final["total_found"],
        "final_records_returned": 0,
        "final_rows_capped": bool(final["total_found"]),
        "final_ncbi_query_translation": final["ncbi_query_translation"],
        "final_pubmed_provider_meta": final["provider_meta"],
        "pubmed_advanced_search_details_required": True,
        "rescue_only": rescue,
        "rescue_only_sample": str(sample_path),
        "rescue_only_sample_sha256": _hash_file(sample_path),
        "rescue_only_sampling_rule": {
            "seed": noise_seed,
            "requested_size": sample_size,
            "actual_size": actual_sample,
            "minimum_required": int(sample_cfg["minimum"]),
            "maximum_allowed": int(sample_cfg["maximum"]),
            "human_classification_required": True,
            "representative_of_full_rescue_only": False,
            "note": "PILOT retrieves only the deterministic human-review slice; it does not claim representativeness of the full rescue-only set.",
        },
        "priority_sentinel_mechanism": mechanism,
        "priority_sentinel_probe_records": probes,
        "errors": errors,
        "status": "SUCCEEDED" if not errors else "FAILED",
        "scientific_interpretation_allowed": False,
        "ready_for_press_inferred": False,
        "press_approved": False,
        "freeze_authorized": False,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    _emit(progress_fn, f"GF-02 {candidate_version}: {manifest['status']}.")
    return manifest


__all__ = [
    "load_candidate_config",
    "load_sentinel_registry",
    "resolved_line_expressions",
    "run_gf02_pubmed_pilot",
]
