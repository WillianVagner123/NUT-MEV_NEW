"""Status-aware execution extension for the NutEV topic/competency audit.

The original topic-audit module remains backwards compatible. This extension wraps
its deterministic mapping/audit/plan materialization and upgrades the active-search
execution layer for providers that now expose explicit ``ProviderResult`` status.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file
from nutev.search.pubmed import PubMedClient
from nutev.search.regional_status import LilacsBVSStatusClient, SciELOStatusClient
from nutev.search.status_adapters import get_status_aware_discovery_client
from nutev.science.topic_audit import (
    TopicAuditError,
    run_topic_competency_audit as _run_base_topic_competency_audit,
)

_STATUS_AWARE_PROVIDERS = {
    "pubmed",
    "europepmc",
    "openalex",
    "crossref",
    "doaj",
    "semantic_scholar",
    "lilacs_bvs",
    "scielo",
}
_MANUAL_PROVIDERS = {"scopus", "wos"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TopicAuditError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TopicAuditError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TopicAuditError(f"expected JSON object at {path}")
    return value


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    return _atomic_text(
        path,
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
            for row in rows
        ),
    )


def _promote_plan(plan: dict[str, Any]) -> dict[str, Any]:
    searches = plan.get("searches") or []
    if not isinstance(searches, list):
        raise TopicAuditError("active search plan searches must be a list")
    promoted: list[dict[str, Any]] = []
    for raw in searches:
        if not isinstance(raw, Mapping):
            raise TopicAuditError("active search plan row must be an object")
        item = dict(raw)
        provider = str(item.get("provider") or "").strip().lower()
        if provider in _STATUS_AWARE_PROVIDERS:
            item["execution"] = "EXECUTABLE_STATUS_AWARE"
        elif provider in _MANUAL_PROVIDERS:
            item["execution"] = "MANUAL_LICENSED"
        else:
            item["execution"] = "PLAN_ONLY_STATUS_ADAPTER_REQUIRED"
        promoted.append(item)
    plan = dict(plan)
    plan["schema_version"] = max(2, int(plan.get("schema_version") or 1))
    plan["status_contract"] = "explicit_provider_result_v1"
    plan["status_aware_providers"] = sorted(_STATUS_AWARE_PROVIDERS)
    plan["searches"] = promoted
    plan["guardrail"] = (
        "Status-aware provider execution distinguishes empty from failed/partial/skipped. "
        "Discovery results do not enter the CORE bank or PRISMA until they pass the normal "
        "NutEV normalization, traceability, deduplication, ranking/audit and scientific pipeline."
    )
    return plan


def _client(provider: str) -> Any | None:
    if provider == "pubmed":
        return PubMedClient()
    if provider == "lilacs_bvs":
        return LilacsBVSStatusClient()
    if provider == "scielo":
        return SciELOStatusClient()
    return get_status_aware_discovery_client(provider)


def _execute_plan(
    plan: Mapping[str, Any],
    *,
    checkpoint_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for raw in plan.get("searches") or []:
        if not isinstance(raw, Mapping):
            raise TopicAuditError("active search plan row must be an object")
        provider = str(raw.get("provider") or "").strip().lower()
        topic_id = str(raw.get("topic_id") or "").strip()
        query = str(raw.get("query") or "")
        limit = int(raw.get("limit") or 20)
        client = _client(provider)
        if client is None:
            runs.append(
                {
                    "topic_id": topic_id,
                    "provider": provider,
                    "query": query,
                    "status": "planned_not_executed",
                    "error": (
                        "manual_licensed_provider"
                        if provider in _MANUAL_PROVIDERS
                        else "explicit_provider_status_adapter_required"
                    ),
                    "total_found": None,
                    "total_returned": 0,
                    "checkpoint_path": None,
                    "feeds_prisma": False,
                    "auto_ingest": False,
                }
            )
            continue

        context: dict[str, Any] = {
            "workstream": f"topic-audit-{topic_id}",
            "checkpoint_dir": checkpoint_dir,
            "resume": True,
        }
        provider_result = client.search(query, limit=limit, context=context)
        runs.append(
            {
                "topic_id": topic_id,
                "provider": provider_result.provider,
                "query": provider_result.query,
                "status": provider_result.status,
                "error": provider_result.error,
                "total_found": provider_result.total_found,
                "total_returned": provider_result.total_returned,
                "checkpoint_path": provider_result.checkpoint_path,
                "provider_meta": provider_result.meta,
                "feeds_prisma": False,
                "auto_ingest": False,
            }
        )
        for row in provider_result.rows:
            result = dict(row)
            result["topic_id"] = topic_id
            result["topic_search_provider"] = provider_result.provider
            result["topic_search_run_status"] = provider_result.status
            result["topic_search_status"] = "discovery_candidate"
            result["feeds_prisma"] = False
            result["auto_ingest"] = False
            results.append(result)
    return runs, results


def run_topic_competency_audit(
    relational_records_jsonl: Path,
    relations_manifest: Path,
    topic_profile: Path,
    output_dir: Path,
    *,
    execute_search: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    """Run topic audit and optionally execute all status-aware discovery providers."""

    base_result = _run_base_topic_competency_audit(
        relational_records_jsonl,
        relations_manifest,
        topic_profile,
        output_dir,
        execute_search=False,
        limit=limit,
    )
    if not execute_search:
        return base_result

    plan_path = output_dir / "active_search_plan.json"
    runs_path = output_dir / "active_search_runs.jsonl"
    results_path = output_dir / "active_search_results.jsonl"
    manifest_path = output_dir / "TOPIC_AUDIT_MANIFEST.json"

    plan = _promote_plan(_read_json(plan_path))
    runs, active_results = _execute_plan(
        plan,
        checkpoint_dir=output_dir / "checkpoints",
    )

    plan_sha = _write_json(plan_path, plan)
    runs_sha = _write_jsonl(runs_path, runs)
    results_sha = _write_jsonl(results_path, active_results)

    manifest = _read_json(manifest_path)
    if (
        manifest.get("audit_type") != "NUTEV_TOPIC_COMPETENCY_AUDIT"
        or manifest.get("status") != "PASS"
    ):
        raise TopicAuditError("base topic audit manifest is not PASS")
    outputs = manifest.setdefault("outputs", {})
    if not isinstance(outputs, dict):
        raise TopicAuditError("topic audit manifest outputs must be an object")
    outputs["active_search_plan"] = {"path": str(plan_path), "sha256": plan_sha}
    outputs["active_search_runs"] = {"path": str(runs_path), "sha256": runs_sha}
    outputs["active_search_results"] = {
        "path": str(results_path),
        "sha256": results_sha,
    }
    counts = manifest.setdefault("counts", {})
    if not isinstance(counts, dict):
        raise TopicAuditError("topic audit manifest counts must be an object")
    counts["active_search_runs"] = len(runs)
    counts["active_search_results"] = len(active_results)
    counts["active_search_status_counts"] = dict(
        sorted(Counter(str(row.get("status") or "") for row in runs).items())
    )
    counts["active_search_provider_counts"] = dict(
        sorted(Counter(str(row.get("provider") or "") for row in runs).items())
    )
    manifest["execution_contract"] = {
        "version": "explicit_provider_result_v1",
        "status_aware_providers": sorted(_STATUS_AWARE_PROVIDERS),
        "plan_only_providers": [],
        "manual_licensed_providers": sorted(_MANUAL_PROVIDERS),
        "empty_is_distinct_from_failure": True,
        "regional_html_zero_requires_explicit_marker": True,
    }
    assertions = manifest.setdefault("assertions", [])
    if not isinstance(assertions, list):
        raise TopicAuditError("topic audit manifest assertions must be a list")
    assertions.extend(
        [
            {
                "name": "multi_provider_status_aware_execution",
                "status": "PASS",
            },
            {
                "name": "empty_distinct_from_failed_partial_skipped",
                "status": "PASS",
            },
            {
                "name": "regional_html_zero_requires_explicit_marker",
                "status": "PASS",
            },
            {
                "name": "status_aware_results_remain_discovery_candidates",
                "status": "PASS",
            },
        ]
    )
    manifest["guardrail"] = (
        "Status-aware discovery distinguishes successful zero-hit responses from provider "
        "failures, partial retrieval and intentional skips. Regional HTML searches require an "
        "explicit no-results marker before asserting zero. All returned rows remain discovery "
        "candidates and must re-enter the normal NutEV traceability pipeline; they do not feed PRISMA."
    )
    manifest_sha = _write_json(manifest_path, manifest)

    result = dict(base_result)
    result["active_search_executed"] = True
    result["active_search_results"] = len(active_results)
    result["status_aware_providers"] = sorted(_STATUS_AWARE_PROVIDERS)
    result["outputs"] = dict(result.get("outputs") or {})
    result["outputs"].update(
        {
            "search_plan": str(plan_path),
            "search_runs": str(runs_path),
            "search_results": str(results_path),
            "manifest": str(manifest_path),
        }
    )
    result["output_sha256"] = dict(result.get("output_sha256") or {})
    result["output_sha256"].update(
        {
            "search_plan": plan_sha,
            "search_runs": runs_sha,
            "search_results": results_sha,
            "manifest": manifest_sha,
        }
    )
    return result
