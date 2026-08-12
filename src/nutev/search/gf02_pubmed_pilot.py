"""Reproducible PubMed runner for the Article 1 GF-02 PILOT gate.

This module executes the exact frozen v0.2/v0.3 PubMed candidate strings from
``config/gf02_pubmed_candidates.json`` and preserves validation evidence under
``07_logs/gf02``. It is deliberately PILOT-only and never creates PRISMA counts,
PRESS approval, or FORMAL authorization.
"""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import random
import subprocess
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.base import ProviderResult
from nutev.search.gf02_evidence import SentinelRecord, sentinel_matches_row
from nutev.search.pubmed import PubMedClient

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
PRIORITY_SENTINEL_IDS = ("NORM-035", "NORM-063")


def load_candidate_config(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if str(data.get("search_type") or "").upper() != "PILOT":
        raise ValueError("GF-02 PubMed candidates must be PILOT")
    if bool(data.get("prisma_eligible")):
        raise ValueError("GF-02 PubMed candidates must not be PRISMA-eligible")
    candidates = data.get("candidates") or {}
    for version in ("v0.2", "v0.3"):
        if not str(candidates.get(version) or "").strip():
            raise ValueError(f"missing exact PubMed candidate: {version}")
    return data


def load_priority_sentinels(path: Path) -> list[SentinelRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    by_id = {str(row.get("sentinel_id") or ""): row for row in data.get("sentinels") or []}
    records: list[SentinelRecord] = []
    for sentinel_id in PRIORITY_SENTINEL_IDS:
        row = by_id.get(sentinel_id)
        if not row:
            raise ValueError(f"priority sentinel missing from registry: {sentinel_id}")
        if str(row.get("identity_status") or "").upper() != "RESOLVED":
            raise ValueError(f"priority sentinel identity unresolved: {sentinel_id}")
        records.append(
            SentinelRecord(
                sentinel_id=sentinel_id,
                canonical_title=str(row.get("canonical_title") or ""),
                doi=str(row.get("doi") or ""),
                pmid=str(row.get("pmid") or ""),
                pmcid=str(row.get("pmcid") or ""),
                issuer=str(row.get("issuer") or ""),
                version_year=str(row.get("version_year") or ""),
                document_unit_rule=str(row.get("document_unit_rule") or ""),
                relationship_notes=str(row.get("relationship_notes") or ""),
                expected_routes=tuple(row.get("expected_routes") or ()),
                identity_status="RESOLVED",
                allow_title_match=bool(row.get("allow_title_match", False)),
            )
        )
    return records


def _sha256_path(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _sha256_path(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return _sha256_path(path)


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def _probe_query(exact_query: str, sentinel: SentinelRecord) -> str:
    if sentinel.pmid.strip():
        return f"({exact_query}) AND {sentinel.pmid.strip()}[pmid]"
    if sentinel.doi.strip():
        return f'({exact_query}) AND "{sentinel.doi.strip()}"[doi]'
    raise ValueError(f"priority sentinel lacks PMID/DOI probe identity: {sentinel.sentinel_id}")


def _execute(
    search_fn: Callable[[str, int, dict[str, Any]], ProviderResult],
    query: str,
    *,
    limit: int,
    context: dict[str, Any],
) -> ProviderResult:
    result = search_fn(query, limit, context)
    if not isinstance(result, ProviderResult):
        raise TypeError("GF-02 PubMed search function returned invalid result")
    return result


def _default_search(query: str, limit: int, context: dict[str, Any]) -> ProviderResult:
    return PubMedClient().search(query, limit=limit, context=context)


def _sample_rows(rows: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0:
        return []
    ordered = sorted(rows, key=lambda row: (str(row.get("pmid") or ""), str(row.get("title") or "")))
    if sample_size >= len(ordered):
        return ordered
    rng = random.Random(seed)
    indexes = sorted(rng.sample(range(len(ordered)), sample_size))
    return [ordered[index] for index in indexes]


def _write_noise_template(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    strategy_version: str,
    sample_size: int,
    seed: int,
    truncated: bool,
) -> str:
    sample = _sample_rows(rows, min(sample_size, len(rows)), seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sample_id",
        "record_id",
        "pmid",
        "doi",
        "title",
        "strategy_version",
        "sampling_rule",
        "classification",
        "reviewer",
        "note",
    ]
    rule = (
        f"seeded random sample (seed={seed}) from rows returned by exact {strategy_version} PILOT"
        + ("; source retrieval truncated at configured limit" if truncated else "; complete returned set")
    )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for idx, row in enumerate(sample, start=1):
            writer.writerow(
                {
                    "sample_id": f"GF02-{strategy_version}-noise",
                    "record_id": idx,
                    "pmid": row.get("pmid", ""),
                    "doi": row.get("doi", ""),
                    "title": row.get("title", ""),
                    "strategy_version": strategy_version,
                    "sampling_rule": rule,
                    "classification": "",
                    "reviewer": "",
                    "note": "",
                }
            )
    return _sha256_path(path)


def run_gf02_pubmed_pilot(
    repo_root: Path,
    *,
    project_root: Path,
    limit: int = 10000,
    noise_sample_size: int = 20,
    noise_seed: int = 20260812,
    search_fn: Callable[[str, int, dict[str, Any]], ProviderResult] = _default_search,
    started_at: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute v0.2/v0.3 and sentinel probes, preserving PILOT-only evidence."""
    repo = Path(repo_root)
    project = Path(project_root)
    if limit <= 0 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")
    if noise_sample_size < 0:
        raise ValueError("noise_sample_size cannot be negative")

    candidates_path = repo / "config" / "gf02_pubmed_candidates.json"
    sentinel_path = repo / "config" / "article1_sentinel_registry.json"
    candidates = load_candidate_config(candidates_path)
    sentinels = load_priority_sentinels(sentinel_path)

    timestamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")
    resolved_run_id = run_id or (
        "gf02_pubmed_" + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z") + "_" + uuid4().hex[:8]
    )
    run_dir = project / "07_logs" / "gf02" / "pubmed" / resolved_run_id
    checkpoint_dir = project / "07_logs" / "checkpoints" / "gf02_pubmed"
    run_dir.mkdir(parents=True, exist_ok=True)

    versions: dict[str, Any] = {}
    overall_status = "SUCCEEDED"
    for version in ("v0.2", "v0.3"):
        exact_query = str(candidates["candidates"][version])
        context = {
            "workstream": f"gf02_{version.replace('.', '_')}",
            "checkpoint_dir": checkpoint_dir,
            "resume": False,
        }
        result = _execute(search_fn, exact_query, limit=limit, context=context)
        if result.status not in {"completed", "empty"}:
            overall_status = "FAILED" if not result.rows else "PARTIAL"

        rows = list(result.rows or [])
        rows_path = run_dir / f"pubmed_{version.replace('.', '_')}_rows.jsonl"
        rows_sha = _write_jsonl(rows_path, rows)
        total_found = int(result.total_found) if result.total_found is not None else None
        truncated = total_found is not None and total_found > len(rows)

        probes: dict[str, Any] = {}
        for sentinel in sentinels:
            probe = _probe_query(exact_query, sentinel)
            probe_result = _execute(
                search_fn,
                probe,
                limit=1,
                context={
                    "workstream": f"gf02_{version.replace('.', '_')}_{sentinel.sentinel_id.lower()}",
                    "checkpoint_dir": checkpoint_dir,
                    "resume": False,
                },
            )
            probe_rows = list(probe_result.rows or [])
            recovered = any(sentinel_matches_row(sentinel, row) for row in probe_rows)
            probes[sentinel.sentinel_id] = {
                "sentinel_id": sentinel.sentinel_id,
                "canonical_pmid": sentinel.pmid,
                "probe_query": probe,
                "status": probe_result.status,
                "total_found": probe_result.total_found,
                "rows_returned": probe_result.total_returned,
                "recovered": recovered,
                "error": probe_result.error or "",
            }
            if probe_result.status not in {"completed", "empty"}:
                overall_status = "FAILED" if not rows else "PARTIAL"

        version_payload = {
            "strategy_version": version,
            "exact_query": exact_query,
            "provider": "pubmed",
            "search_type": "PILOT",
            "prisma_eligible": False,
            "started_at": timestamp,
            "status": result.status,
            "error": result.error or "",
            "total_found": total_found,
            "rows_returned": int(result.total_returned),
            "limit": limit,
            "truncated": truncated,
            "rows_snapshot": str(rows_path),
            "rows_snapshot_sha256": rows_sha,
            "sentinel_probes": probes,
        }
        evidence_path = run_dir / f"pubmed_{version.replace('.', '_')}_evidence.json"
        version_payload["evidence_sha256"] = _write_json(evidence_path, version_payload)
        versions[version] = version_payload

    v03 = versions["v0.3"]
    noise_path = run_dir / "pubmed_v0_3_noise_sample.csv"
    noise_sha = _write_noise_template(
        noise_path,
        list(json.loads(line) for line in Path(v03["rows_snapshot"]).read_text(encoding="utf-8").splitlines() if line),
        strategy_version="v0.3",
        sample_size=noise_sample_size,
        seed=noise_seed,
        truncated=bool(v03["truncated"]),
    )

    comparison = {
        sentinel_id: {
            "v0.2": bool(versions["v0.2"]["sentinel_probes"][sentinel_id]["recovered"]),
            "v0.3": bool(versions["v0.3"]["sentinel_probes"][sentinel_id]["recovered"]),
        }
        for sentinel_id in PRIORITY_SENTINEL_IDS
    }
    manifest = {
        "schema_version": 1,
        "run_id": resolved_run_id,
        "gate": "GF-02",
        "route_id": candidates.get("route_id"),
        "search_type": "PILOT",
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "started_at": timestamp,
        "software_sha": _git_sha(repo),
        "candidate_config": str(candidates_path),
        "candidate_config_sha256": _sha256_path(candidates_path),
        "sentinel_registry": str(sentinel_path),
        "sentinel_registry_sha256": _sha256_path(sentinel_path),
        "status": overall_status,
        "versions": versions,
        "priority_sentinel_comparison": comparison,
        "noise_sample": str(noise_path),
        "noise_sample_sha256": noise_sha,
        "noise_sample_requires_human_classification": True,
        "notes": "This manifest is GF-02 PILOT evidence only and must not enter formal PRISMA identification counts.",
    }
    manifest_path = run_dir / "run_manifest.json"
    manifest["manifest_sha256"] = _write_json(manifest_path, manifest)
    return manifest
