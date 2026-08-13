from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import subprocess
from typing import Any, Callable
from zoneinfo import ZoneInfo

from nutev.search.base import ProviderResult
from nutev.search.gf02_evidence import SentinelRecord, validate_gf02_pilot_strategy, validate_sentinel_registry
from nutev.search.pubmed import PubMedClient

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
_MECHANISM_LINES = ("#3", "#6", "#7")
_ALLOWED_RESCUE_WORDS = {
    "guideline", "guidelines", "practice", "clinical", "consensus", "statement",
    "statements", "position", "scientific", "professional", "standards", "standard",
    "of", "care", "pt", "ti", "or",
}


def _hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def _git_sha(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNKNOWN"


def _line(config: dict[str, Any], line_id: str, stack: tuple[str, ...] = ()) -> str:
    lines = config.get("lines") or {}
    if line_id not in lines or line_id in stack:
        raise ValueError(f"invalid GF-02 PubMed line: {line_id}")
    node = lines[line_id]
    if "query" in node:
        query = str(node.get("query") or "").strip()
        if not query:
            raise ValueError(f"{line_id}.query cannot be blank")
        return query
    spec = node.get("combine") or {}
    left, right = str(spec.get("left") or ""), str(spec.get("right") or "")
    op = str(spec.get("operator") or "").upper()
    if not left or not right or op not in {"AND", "OR", "NOT"}:
        raise ValueError(f"invalid GF-02 PubMed combination: {line_id}")
    next_stack = stack + (line_id,)
    return f"({_line(config, left, next_stack)}) {op} ({_line(config, right, next_stack)})"


def resolved_line_expressions(config: dict[str, Any]) -> dict[str, str]:
    return {line_id: _line(config, line_id) for line_id in (config.get("lines") or {})}


def _binary(config: dict[str, Any], spec: dict[str, Any]) -> str:
    op = str(spec.get("operator") or "").upper()
    left, right = str(spec.get("left") or ""), str(spec.get("right") or "")
    if not left or not right or op not in {"AND", "OR", "NOT"}:
        raise ValueError("invalid GF-02 PubMed binary expression")
    return f"({_line(config, left)}) {op} ({_line(config, right)})"


def load_candidate_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_gf02_pilot_strategy(data)
    if int(data.get("schema_version") or 0) < 2 or data.get("route_id") != "B-NORM-PUBMED":
        raise ValueError("GF-02 PubMed schema 2 / B-NORM-PUBMED is required")
    if data.get("current_candidate") != "v0.4" or data.get("final_line") != "#7":
        raise ValueError("GF-02 PubMed current candidate must be v0.4 with final line #7")
    expected_counts = ["#1", "#2", "#3", "#4", "#6", "#7"]
    if data.get("required_count_lines") != expected_counts:
        raise ValueError("GF-02 PubMed v0.4 requires counts for #1,#2,#3,#4,#6,#7")
    expressions = resolved_line_expressions(data)
    if any(line_id not in expressions for line_id in expected_counts):
        raise ValueError("GF-02 PubMed v0.4 required line missing")
    unexpected = sorted(set(re.findall(r"[a-z]+", expressions["#4"].casefold())) - _ALLOWED_RESCUE_WORDS)
    if unexpected:
        raise ValueError("GF-02 PubMed v0.4 rescue is not condition-neutral: " + ", ".join(unexpected))
    _binary(data, data.get("rescue_only") or {})
    sample = data.get("rescue_sample") or {}
    minimum, maximum, default = int(sample.get("minimum") or 0), int(sample.get("maximum") or 0), int(sample.get("default") or 0)
    if not (10 <= minimum <= default <= maximum <= 20):
        raise ValueError("GF-02 PubMed rescue sample must remain within 10-20 records")
    for version, payload in (data.get("superseded_candidates") or {}).items():
        if bool((payload or {}).get("execution_allowed")):
            raise ValueError(f"superseded GF-02 candidate cannot remain executable: {version}")
    return data


def load_sentinel_registry(path: Path) -> list[SentinelRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SentinelRecord(**item) for item in data.get("sentinels", [])]


def _search(query: str, limit: int, context: dict[str, Any]) -> ProviderResult:
    return PubMedClient().search(query, limit=limit, context=context)


def _run(query: str, limit: int, workstream: str, checkpoint_dir: Path, search_fn: Callable[[str, int, dict[str, Any]], ProviderResult], mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        result = search_fn(query, limit, {"workstream": workstream, "checkpoint_dir": checkpoint_dir, "resume": False})
        if not isinstance(result, ProviderResult):
            raise TypeError("invalid PubMed result")
    except Exception as exc:
        result = ProviderResult("pubmed", query, status="failed", error=str(exc))
    rows = list(result.rows or [])
    total = int(result.total_found) if result.total_found is not None else None
    returned = int(result.total_returned or len(rows))
    meta = dict(result.meta or {})
    return ({
        "provider": "pubmed", "exact_query": query, "query_sha256": _hash_text(query),
        "retrieval_mode": mode, "fetch_limit": limit, "total_found": total,
        "records_returned": returned, "rows_capped": bool(total is not None and total > returned),
        "status": result.status, "error": result.error or "",
        "ncbi_query_translation": str(meta.get("query_translation") or meta.get("querytranslation") or ""),
        "provider_meta": meta,
    }, rows)


def _write_sample(path: Path, rows: list[dict[str, Any]], size: int, seed: int, total: int | None, returned: int, capped: bool) -> tuple[Path, int]:
    ordered = sorted(rows, key=lambda row: (str(row.get("pmid") or ""), str(row.get("doi") or ""), str(row.get("title") or "")))
    if len(ordered) > size:
        positions = sorted(random.Random(seed).sample(range(len(ordered)), size))
        ordered = [ordered[pos] for pos in positions]
    rule = f"deterministic seed={seed}; sorted PMID/DOI/title; sample={size}; source=(#6 NOT #3); rescue_only_total={total}; returned={returned}; capped={str(capped).lower()}"
    fields = ["sample_id", "record_id", "pmid", "doi", "title", "provider", "strategy_version", "sampling_rule", "classification", "reviewer", "note"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for idx, row in enumerate(ordered, 1):
            writer.writerow({
                "sample_id": f"GF02-RESCUE-{idx:03d}", "record_id": str(row.get("pmid") or row.get("doi") or ""),
                "pmid": str(row.get("pmid") or ""), "doi": str(row.get("doi") or ""), "title": str(row.get("title") or ""),
                "provider": "PUBMED", "strategy_version": "B-NORM-PUBMED-v0.4-rescue-only", "sampling_rule": rule,
                "classification": "", "reviewer": "", "note": "",
            })
    return path, len(ordered)


def run_gf02_pubmed_pilot(repo_root: Path, *, project_root: Path, limit: int = 10000, noise_sample_size: int | None = None, noise_seed: int = 20260812, search_fn: Callable[[str, int, dict[str, Any]], ProviderResult] | None = None, started_at: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    repo, project = Path(repo_root), Path(project_root)
    config_path, sentinel_path = repo / "config/gf02_pubmed_candidates.json", repo / "config/article1_sentinel_registry.json"
    config, sentinels = load_candidate_config(config_path), load_sentinel_registry(sentinel_path)
    validate_sentinel_registry(sentinels)
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
    search_fn = search_fn or _search
    stamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")
    resolved_run_id = run_id or "gf02_pubmed_v04_" + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
    run_dir, checkpoint_dir = project / "07_logs/gf02/pubmed" / resolved_run_id, project / "07_logs/gf02/pubmed" / resolved_run_id / "checkpoints"
    run_dir.mkdir(parents=True, exist_ok=True)
    expressions, audits, errors = resolved_line_expressions(config), {}, []
    for line_id in config["required_count_lines"]:
        fetch_limit, mode = (int(limit), "FULL_CAPPED") if line_id == "#7" else (1, "COUNT_ONLY")
        audit, rows = _run(expressions[line_id], fetch_limit, f"gf02_v04_{line_id.replace('#', 'line_')}", checkpoint_dir, search_fn, mode)
        audits[line_id] = {"label": str(config["lines"][line_id].get("label") or ""), **audit}
        _write_json(run_dir / f"{line_id.replace('#', 'line_')}.audit.json", audits[line_id])
        if line_id == "#7":
            snap = _write_jsonl(run_dir / "v0_4_final.rows.jsonl", rows)
            audits[line_id].update(row_snapshot_path=str(snap), row_snapshot_sha256=_hash_file(snap))
        if audit["status"] not in {"completed", "empty"}:
            errors.append(f"{line_id}:{audit['status']}:{audit['error']}")
    rescue_query = _binary(config, config["rescue_only"])
    rescue, rescue_rows = _run(rescue_query, int(limit), "gf02_v04_rescue_only", checkpoint_dir, search_fn, "RESCUE_ONLY_FULL_CAPPED")
    rescue_snap = _write_jsonl(run_dir / "v0_4_rescue_only.rows.jsonl", rescue_rows)
    rescue.update(row_snapshot_path=str(rescue_snap), row_snapshot_sha256=_hash_file(rescue_snap))
    _write_json(run_dir / "v0_4_rescue_only.audit.json", rescue)
    if rescue["status"] not in {"completed", "empty"}:
        errors.append(f"rescue_only:{rescue['status']}:{rescue['error']}")
    sample_path, actual_sample = _write_sample(run_dir / "rescue_only_sample_v0_4.csv", rescue_rows, sample_size, noise_seed, rescue["total_found"], rescue["records_returned"], rescue["rows_capped"])
    mechanism, probes = {sentinel_id: {} for sentinel_id in priority_ids}, []
    for sentinel_id in priority_ids:
        sentinel = sentinel_map[sentinel_id]
        for line_id in _MECHANISM_LINES:
            query = f"({expressions[line_id]}) AND {sentinel.pmid}[pmid]" if sentinel.pmid else ""
            if not query:
                probe = {"sentinel_id": sentinel_id, "line_id": line_id, "status": "NOT_PROBED_NO_PMID", "recovered": False, "query": "", "query_sha256": "", "total_found": None, "error": "priority PubMed mechanism probe requires PMID"}
            else:
                audit, rows = _run(query, 1, f"gf02_probe_{line_id.replace('#', 'line_')}_{sentinel_id}", checkpoint_dir, search_fn, "SENTINEL_PROBE")
                probe = {"sentinel_id": sentinel_id, "line_id": line_id, "status": audit["status"], "recovered": bool(rows or (audit["total_found"] or 0) > 0), "query": query, "query_sha256": audit["query_sha256"], "total_found": audit["total_found"], "error": audit["error"]}
            probes.append(probe)
            mechanism[sentinel_id][line_id] = bool(probe["recovered"])
            if probe["status"] not in {"completed", "empty"}:
                errors.append(f"probe:{sentinel_id}:{line_id}:{probe['status']}:{probe['error']}")
    _write_jsonl(run_dir / "priority_sentinel_probes.jsonl", probes)
    final = audits["#7"]
    manifest = {
        "schema_version": 2, "run_id": resolved_run_id, "route_id": config["route_id"], "candidate_version": "v0.4",
        "candidate_status": config["candidate_status"], "search_type": "PILOT", "formal_execution_authorized": False, "prisma_eligible": False,
        "started_at": stamp, "software_git_sha": _git_sha(repo), "candidate_config_path": str(config_path), "candidate_config_sha256": _hash_file(config_path),
        "sentinel_registry_path": str(sentinel_path), "sentinel_registry_sha256": _hash_file(sentinel_path), "methodology_decisions": list(config.get("methodology_decisions") or []),
        "canonical_operational_source": str(config.get("canonical_operational_source") or ""), "line_expressions": expressions, "line_audits": audits,
        "line_counts": {line_id: audits[line_id]["total_found"] for line_id in config["required_count_lines"]}, "final_line": "#7", "final_total_found": final["total_found"],
        "final_records_returned": final["records_returned"], "final_rows_capped": final["rows_capped"], "final_ncbi_query_translation": final["ncbi_query_translation"],
        "pubmed_advanced_search_details_required": True, "rescue_only": rescue, "rescue_only_sample": str(sample_path), "rescue_only_sample_sha256": _hash_file(sample_path),
        "rescue_only_sampling_rule": {"seed": noise_seed, "requested_size": sample_size, "actual_size": actual_sample, "minimum_required": int(sample_cfg["minimum"]), "maximum_allowed": int(sample_cfg["maximum"]), "human_classification_required": True},
        "priority_sentinel_mechanism": mechanism, "priority_sentinel_probe_records": probes, "errors": errors, "status": "SUCCEEDED" if not errors else "FAILED",
        "scientific_interpretation_allowed": False, "press_approved": False, "freeze_authorized": False,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    return manifest


__all__ = ["load_candidate_config", "load_sentinel_registry", "resolved_line_expressions", "run_gf02_pubmed_pilot"]
