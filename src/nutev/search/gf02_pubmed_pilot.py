from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import csv
import hashlib
import json
from pathlib import Path
import random
import subprocess
from typing import Any, Callable
from zoneinfo import ZoneInfo

from nutev.search.base import ProviderResult
from nutev.search.gf02_evidence import (
    NoiseSampleRecord,
    SentinelRecord,
    save_json,
    save_jsonl,
    validate_gf02_pilot_strategy,
    validate_sentinel_registry,
)
from nutev.search.pubmed import PubMedClient

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
_REQUIRED_MECHANISM_LINES = ("#3", "#6", "#7")
_FORBIDDEN_RESCUE_CONDITION_TOKENS = (
    "cardiovascular",
    "cardiac",
    "coronary",
    "hypertension",
    "dyslipid",
    "hypercholesterol",
    "diabetes",
    "prediabet",
    "obes",
    "overweight",
    "cancer",
    "neoplasm",
    "autoimmune",
    "celiac",
    "coeliac",
    "crohn",
    "colitis",
    "inflammatory bowel",
    "irritable bowel",
    "gastrointestinal",
    "digestive",
    "chronic obstructive pulmonary",
    "copd",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _hash_file(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repo_root),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def _clean_query(value: object, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} cannot be blank")
    return text


def _resolve_line_expression(
    config: dict[str, Any],
    line_id: str,
    *,
    stack: tuple[str, ...] = (),
) -> str:
    lines = config.get("lines") or {}
    if line_id not in lines:
        raise ValueError(f"unknown GF-02 PubMed line: {line_id}")
    if line_id in stack:
        raise ValueError(f"cyclic GF-02 PubMed line definition: {' -> '.join(stack + (line_id,))}")
    node = lines[line_id]
    if not isinstance(node, dict):
        raise ValueError(f"GF-02 PubMed line {line_id} must be an object")
    if "query" in node:
        return _clean_query(node.get("query"), field=f"{line_id}.query")
    combine = node.get("combine")
    if not isinstance(combine, dict):
        raise ValueError(f"GF-02 PubMed line {line_id} must define query or combine")
    left = str(combine.get("left") or "").strip()
    right = str(combine.get("right") or "").strip()
    operator = str(combine.get("operator") or "").strip().upper()
    if operator not in {"AND", "OR", "NOT"}:
        raise ValueError(f"unsupported GF-02 PubMed operator for {line_id}: {operator}")
    if not left or not right:
        raise ValueError(f"GF-02 PubMed line {line_id} requires left and right references")
    next_stack = stack + (line_id,)
    left_query = _resolve_line_expression(config, left, stack=next_stack)
    right_query = _resolve_line_expression(config, right, stack=next_stack)
    return f"({left_query}) {operator} ({right_query})"


def resolved_line_expressions(config: dict[str, Any]) -> dict[str, str]:
    lines = config.get("lines") or {}
    return {line_id: _resolve_line_expression(config, line_id) for line_id in lines}


def _resolve_binary_expression(config: dict[str, Any], spec: dict[str, Any]) -> str:
    left = str(spec.get("left") or "").strip()
    right = str(spec.get("right") or "").strip()
    operator = str(spec.get("operator") or "").strip().upper()
    if operator not in {"AND", "OR", "NOT"}:
        raise ValueError(f"unsupported GF-02 PubMed binary operator: {operator}")
    if not left or not right:
        raise ValueError("GF-02 PubMed binary expression requires left and right")
    return (
        f"({_resolve_line_expression(config, left)}) {operator} "
        f"({_resolve_line_expression(config, right)})"
    )


def load_candidate_config(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_gf02_pilot_strategy(data)
    if int(data.get("schema_version") or 0) < 2:
        raise ValueError("GF-02 PubMed config schema_version 2 is required")
    if str(data.get("route_id") or "").strip() != "B-NORM-PUBMED":
        raise ValueError("GF-02 PubMed config must target B-NORM-PUBMED")
    if str(data.get("current_candidate") or "").strip() != "v0.4":
        raise ValueError("GF-02 PubMed current candidate must be v0.4")
    final_line = str(data.get("final_line") or "").strip()
    if final_line != "#7":
        raise ValueError("GF-02 PubMed v0.4 final line must be #7")
    required_count_lines = [str(item).strip() for item in data.get("required_count_lines") or []]
    if required_count_lines != ["#1", "#2", "#3", "#4", "#6", "#7"]:
        raise ValueError("GF-02 PubMed v0.4 requires counts for #1,#2,#3,#4,#6,#7")
    expressions = resolved_line_expressions(data)
    for required in required_count_lines:
        if required not in expressions:
            raise ValueError(f"missing required GF-02 PubMed line: {required}")
    rescue = expressions.get("#4", "").casefold()
    leaked = [token for token in _FORBIDDEN_RESCUE_CONDITION_TOKENS if token in rescue]
    if leaked:
        raise ValueError("GF-02 PubMed v0.4 rescue is not condition-neutral: " + ", ".join(leaked))
    rescue_only = data.get("rescue_only")
    if not isinstance(rescue_only, dict):
        raise ValueError("GF-02 PubMed v0.4 rescue_only specification is required")
    _resolve_binary_expression(data, rescue_only)
    sample = data.get("rescue_sample") or {}
    minimum = int(sample.get("minimum") or 0)
    maximum = int(sample.get("maximum") or 0)
    default = int(sample.get("default") or 0)
    if not (10 <= minimum <= default <= maximum <= 20):
        raise ValueError("GF-02 PubMed rescue sample must remain within 10-20 records")
    for version, payload in (data.get("superseded_candidates") or {}).items():
        if bool((payload or {}).get("execution_allowed")):
            raise ValueError(f"superseded GF-02 candidate cannot remain executable: {version}")
    return data


def load_sentinel_registry(path: Path) -> list[SentinelRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SentinelRecord(**item) for item in data.get("sentinels", [])]


def _write_noise_csv(path: Path, records: list[NoiseSampleRecord]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(NoiseSampleRecord.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return path


def _sample_rows(rows: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    if size <= 0 or not rows:
        return []
    ordered = sorted(
        rows,
        key=lambda row: (
            str(row.get("pmid") or ""),
            str(row.get("doi") or ""),
            str(row.get("title") or ""),
        ),
    )
    if len(ordered) <= size:
        return ordered
    rng = random.Random(seed)
    positions = sorted(rng.sample(range(len(ordered)), size))
    return [ordered[pos] for pos in positions]


def _default_search(query: str, limit: int, context: dict[str, Any]) -> ProviderResult:
    return PubMedClient().search(query, limit=limit, context=context)


def _run_query(
    *,
    query: str,
    fetch_limit: int,
    workstream: str,
    checkpoint_dir: Path,
    search_fn: Callable[[str, int, dict[str, Any]], ProviderResult],
    retrieval_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        result = search_fn(
            query,
            fetch_limit,
            {
                "workstream": workstream,
                "checkpoint_dir": checkpoint_dir,
                "resume": False,
            },
        )
        if not isinstance(result, ProviderResult):
            raise TypeError("GF-02 PubMed search returned an invalid result object")
    except Exception as exc:
        result = ProviderResult("pubmed", query, status="failed", error=str(exc))
    rows = list(result.rows or [])
    total_found = int(result.total_found) if result.total_found is not None else None
    returned = int(result.total_returned or len(rows))
    meta = dict(result.meta or {})
    audit = {
        "provider": "pubmed",
        "exact_query": query,
        "query_sha256": _sha256_text(query),
        "retrieval_mode": retrieval_mode,
        "fetch_limit": fetch_limit,
        "total_found": total_found,
        "records_returned": returned,
        "rows_capped": bool(total_found is not None and total_found > returned),
        "status": result.status,
        "error": result.error or "",
        "ncbi_query_translation": str(
            meta.get("query_translation") or meta.get("querytranslation") or ""
        ),
        "provider_meta": meta,
    }
    return audit, rows


def _probe_sentinel(
    *,
    expression: str,
    sentinel: SentinelRecord,
    line_id: str,
    checkpoint_dir: Path,
    search_fn: Callable[[str, int, dict[str, Any]], ProviderResult],
) -> dict[str, Any]:
    if not sentinel.pmid:
        return {
            "sentinel_id": sentinel.sentinel_id,
            "line_id": line_id,
            "status": "NOT_PROBED_NO_PMID",
            "recovered": False,
            "query": "",
            "query_sha256": "",
            "total_found": None,
            "error": "priority PubMed mechanism probe requires PMID",
        }
    probe_query = f"({expression}) AND {sentinel.pmid}[pmid]"
    audit, rows = _run_query(
        query=probe_query,
        fetch_limit=1,
        workstream=f"gf02_probe_{line_id.replace('#', 'line_')}_{sentinel.sentinel_id}",
        checkpoint_dir=checkpoint_dir,
        search_fn=search_fn,
        retrieval_mode="SENTINEL_PROBE",
    )
    return {
        "sentinel_id": sentinel.sentinel_id,
        "line_id": line_id,
        "status": audit["status"],
        "recovered": bool(rows or (audit["total_found"] or 0) > 0),
        "query": probe_query,
        "query_sha256": audit["query_sha256"],
        "total_found": audit["total_found"],
        "error": audit["error"],
    }


def run_gf02_pubmed_pilot(
    repo_root: Path,
    *,
    project_root: Path,
    limit: int = 10000,
    noise_sample_size: int | None = None,
    noise_seed: int = 20260812,
    search_fn: Callable[[str, int, dict[str, Any]], ProviderResult] | None = None,
    started_at: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the current B-NORM-PUBMED v0.4 PILOT package; never FORMAL/PRISMA."""
    repo = Path(repo_root)
    project = Path(project_root)
    config_path = repo / "config" / "gf02_pubmed_candidates.json"
    sentinel_path = repo / "config" / "article1_sentinel_registry.json"
    config = load_candidate_config(config_path)
    sentinels = load_sentinel_registry(sentinel_path)
    validate_sentinel_registry(sentinels)
    sentinel_map = {record.sentinel_id: record for record in sentinels}
    priority_ids = list((config.get("priority_expectations") or {}).keys())
    missing_priority = [sentinel_id for sentinel_id in priority_ids if sentinel_id not in sentinel_map]
    if missing_priority:
        raise ValueError("priority sentinel identity missing from registry: " + ", ".join(missing_priority))

    safe_limit = int(limit)
    if safe_limit <= 0 or safe_limit > 10000:
        raise ValueError("GF-02 PubMed limit must be between 1 and 10000")
    sample_config = config.get("rescue_sample") or {}
    sample_size = int(noise_sample_size if noise_sample_size is not None else sample_config["default"])
    if not int(sample_config["minimum"]) <= sample_size <= int(sample_config["maximum"]):
        raise ValueError("GF-02 PubMed rescue-only sample size must be between 10 and 20")

    search_fn = search_fn or _default_search
    timestamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")
    resolved_run_id = run_id or (
        "gf02_pubmed_v04_" + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
    )
    run_dir = project / "07_logs" / "gf02" / "pubmed" / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = run_dir / "checkpoints"

    expressions = resolved_line_expressions(config)
    line_audits: dict[str, dict[str, Any]] = {}
    final_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    final_line = str(config["final_line"])

    for line_id in config["required_count_lines"]:
        fetch_limit = safe_limit if line_id == final_line else 1
        retrieval_mode = "FULL_CAPPED" if line_id == final_line else "COUNT_ONLY"
        audit, rows = _run_query(
            query=expressions[line_id],
            fetch_limit=fetch_limit,
            workstream=f"gf02_v04_{line_id.replace('#', 'line_')}",
            checkpoint_dir=checkpoint_dir,
            search_fn=search_fn,
            retrieval_mode=retrieval_mode,
        )
        line_audits[line_id] = {
            "label": str((config["lines"][line_id] or {}).get("label") or ""),
            **audit,
        }
        save_json(run_dir / f"{line_id.replace('#', 'line_')}.audit.json", line_audits[line_id])
        if line_id == final_line:
            final_rows = rows
            final_snapshot = save_jsonl(run_dir / "v0_4_final.rows.jsonl", final_rows)
            line_audits[line_id]["row_snapshot_path"] = str(final_snapshot)
            line_audits[line_id]["row_snapshot_sha256"] = _hash_file(final_snapshot)
        if audit["status"] not in {"completed", "empty"}:
            errors.append(f"{line_id}:{audit['status']}:{audit['error']}")

    rescue_only_query = _resolve_binary_expression(config, config["rescue_only"])
    rescue_audit, rescue_rows = _run_query(
        query=rescue_only_query,
        fetch_limit=safe_limit,
        workstream="gf02_v04_rescue_only",
        checkpoint_dir=checkpoint_dir,
        search_fn=search_fn,
        retrieval_mode="RESCUE_ONLY_FULL_CAPPED",
    )
    rescue_snapshot = save_jsonl(run_dir / "v0_4_rescue_only.rows.jsonl", rescue_rows)
    rescue_audit["row_snapshot_path"] = str(rescue_snapshot)
    rescue_audit["row_snapshot_sha256"] = _hash_file(rescue_snapshot)
    save_json(run_dir / "v0_4_rescue_only.audit.json", rescue_audit)
    if rescue_audit["status"] not in {"completed", "empty"}:
        errors.append(f"rescue_only:{rescue_audit['status']}:{rescue_audit['error']}")

    sampled = _sample_rows(rescue_rows, sample_size, noise_seed)
    sample_records = [
        NoiseSampleRecord(
            sample_id=f"GF02-RESCUE-{idx:03d}",
            provider="PUBMED",
            strategy_version="B-NORM-PUBMED-v0.4-rescue-only",
            record_id=str(row.get("pmid") or row.get("doi") or ""),
            title=str(row.get("title") or ""),
            doi=str(row.get("doi") or ""),
            pmid=str(row.get("pmid") or ""),
            sampling_rule=(
                f"deterministic seed={noise_seed}; sorted PMID/DOI/title; sample={sample_size}; "
                f"source=(#6 NOT #3); rescue_only_total={rescue_audit['total_found']}; "
                f"returned={rescue_audit['records_returned']}; "
                f"capped={str(rescue_audit['rows_capped']).lower()}"
            ),
        )
        for idx, row in enumerate(sampled, start=1)
    ]
    sample_path = _write_noise_csv(run_dir / "rescue_only_sample_v0_4.csv", sample_records)

    mechanism: dict[str, dict[str, bool]] = {sentinel_id: {} for sentinel_id in priority_ids}
    probe_records: list[dict[str, Any]] = []
    for sentinel_id in priority_ids:
        sentinel = sentinel_map[sentinel_id]
        for line_id in _REQUIRED_MECHANISM_LINES:
            probe = _probe_sentinel(
                expression=expressions[line_id],
                sentinel=sentinel,
                line_id=line_id,
                checkpoint_dir=checkpoint_dir,
                search_fn=search_fn,
            )
            probe_records.append(probe)
            mechanism[sentinel_id][line_id] = bool(probe["recovered"])
            if probe["status"] not in {"completed", "empty"}:
                errors.append(
                    f"probe:{sentinel_id}:{line_id}:{probe['status']}:{probe['error']}"
                )
    save_jsonl(run_dir / "priority_sentinel_probes.jsonl", probe_records)

    final_audit = line_audits[final_line]
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "run_id": resolved_run_id,
        "route_id": config["route_id"],
        "candidate_version": config["current_candidate"],
        "candidate_status": config["candidate_status"],
        "search_type": "PILOT",
        "formal_execution_authorized": False,
        "prisma_eligible": False,
        "started_at": timestamp,
        "software_git_sha": _git_sha(repo),
        "candidate_config_path": str(config_path),
        "candidate_config_sha256": _hash_file(config_path),
        "sentinel_registry_path": str(sentinel_path),
        "sentinel_registry_sha256": _hash_file(sentinel_path),
        "methodology_decisions": list(config.get("methodology_decisions") or []),
        "canonical_operational_source": str(config.get("canonical_operational_source") or ""),
        "line_expressions": expressions,
        "line_audits": line_audits,
        "line_counts": {
            line_id: line_audits[line_id]["total_found"]
            for line_id in config["required_count_lines"]
        },
        "final_line": final_line,
        "final_total_found": final_audit["total_found"],
        "final_records_returned": final_audit["records_returned"],
        "final_rows_capped": final_audit["rows_capped"],
        "final_ncbi_query_translation": final_audit["ncbi_query_translation"],
        "pubmed_advanced_search_details_required": True,
        "rescue_only": rescue_audit,
        "rescue_only_sample": str(sample_path),
        "rescue_only_sample_sha256": _hash_file(sample_path),
        "rescue_only_sampling_rule": {
            "seed": noise_seed,
            "requested_size": sample_size,
            "actual_size": len(sample_records),
            "minimum_required": int(sample_config["minimum"]),
            "maximum_allowed": int(sample_config["maximum"]),
            "human_classification_required": True,
        },
        "priority_sentinel_mechanism": mechanism,
        "priority_sentinel_probe_records": probe_records,
        "errors": errors,
        "status": "SUCCEEDED" if not errors else "FAILED",
        "scientific_interpretation_allowed": False,
        "press_approved": False,
        "freeze_authorized": False,
    }
    save_json(run_dir / "run_manifest.json", manifest)
    return manifest


__all__ = [
    "load_candidate_config",
    "load_sentinel_registry",
    "resolved_line_expressions",
    "run_gf02_pubmed_pilot",
]
