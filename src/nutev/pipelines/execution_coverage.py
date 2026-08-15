"""Auditable inventory of what Article 1 did and did not search."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from nutev.search.provider_orchestrator import implemented_search_providers
from nutev.search.strategy_execution_ledger import list_execution_artifacts
from nutev.search.strategy_registry import default_registry_path


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    fields = [
        "provider", "method_track", "implemented", "default_enabled",
        "attempted", "search_completed", "status", "reason",
        "exact_expression", "records_returned", "total_found", "evidence_path",
    ]
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _source_registry(repo_root: Path) -> dict[str, Any]:
    return _load_json(Path(repo_root) / "config" / "source_registry.json")


def _latest_play(project_root: Path) -> dict[str, Any]:
    return _load_json(Path(project_root) / "12_play" / "latest_summary.json")


def _play_artifacts(project_root: Path, play: dict[str, Any]) -> dict[str, dict[str, Any]]:
    run_id = str((play.get("search") or {}).get("run_id") or "").strip()
    if not run_id:
        return {}
    try:
        rows = list_execution_artifacts(default_registry_path(project_root), run_id=run_id)
    except Exception:
        return {}
    return {str(row.get("provider") or "").strip().lower(): row for row in rows}


def _status_from_artifact(row: dict[str, Any]) -> tuple[str, bool, bool]:
    status = str(row.get("provider_status") or "").lower()
    if status in {"completed", "empty"}:
        return "EXECUTED", True, True
    if status == "partial":
        return "EXECUTED_PARTIAL", True, False
    if status == "failed":
        return "FAILED", True, False
    if status == "skipped":
        return "SKIPPED", True, False
    return "UNKNOWN_ATTEMPT", bool(status), False


def write_search_coverage_ledger(
    repo_root: Path,
    project_root: Path,
    *,
    scientific_status: dict[str, Any],
) -> dict[str, Any]:
    """Persist a route-by-route ledger including negative coverage statements.

    ``attempted`` and ``search_completed`` are separate on purpose: a timeout or
    credential failure proves an attempt occurred, but must never be represented
    as a completed zero-result search.
    """
    repo = Path(repo_root)
    project = Path(project_root)
    registry = _source_registry(repo)
    play = _latest_play(project)
    artifacts = _play_artifacts(project, play)
    implemented = set(implemented_search_providers())
    gf02 = scientific_status.get("gf02") or {}
    gf02_manifest_path = Path(str(gf02.get("latest_manifest") or ""))
    gf02_manifest = _load_json(gf02_manifest_path) if gf02_manifest_path.is_file() else {}

    rows: list[dict[str, Any]] = []
    providers = registry.get("providers") or {}
    for provider, meta in sorted(providers.items(), key=lambda item: int((item[1] or {}).get("priority") or 999)):
        meta = meta or {}
        artifact = artifacts.get(provider)
        status = "NOT_EXECUTED_CURRENT_PHASE"
        attempted = False
        completed = False
        reason = "No execution evidence exists for this provider in the current project output."
        expression = ""
        returned: int | str = ""
        total: int | str = ""
        evidence = ""
        if artifact:
            status, attempted, completed = _status_from_artifact(artifact)
            reason = str(artifact.get("error") or artifact.get("provider_status") or status)
            expression = str(artifact.get("exact_expression") or "")
            returned = int(artifact.get("records_returned") or 0)
            total_value = artifact.get("total_found")
            total = int(total_value) if total_value is not None else ""
            evidence = str(artifact.get("snapshot_path") or "")
        elif provider == "pubmed" and bool(gf02.get("pubmed_pilot_complete")) and gf02_manifest:
            status = "PILOT_EXECUTED"
            attempted = True
            completed = True
            expression = str((gf02_manifest.get("line_expressions") or {}).get("#7") or "")
            total_value = gf02_manifest.get("final_total_found")
            total = int(total_value) if total_value is not None else ""
            returned = int(gf02_manifest.get("final_records_returned") or 0)
            evidence = str(gf02_manifest_path)
            reason = "Current canonical GF-02 PubMed PILOT completed; this is not a FORMAL/PRISMA search."
        elif provider not in implemented:
            status = "NOT_IMPLEMENTED"
            reason = "Declared in source registry but no executable connector is currently registered."
        elif not bool(meta.get("default_enabled", False)):
            status = "AVAILABLE_NOT_SELECTED"
            reason = "Connector exists but this source is not selected by the current default/methodological route."

        rows.append({
            "provider": provider,
            "method_track": str(meta.get("method_track") or ""),
            "implemented": provider in implemented,
            "default_enabled": bool(meta.get("default_enabled", False)),
            "attempted": attempted,
            "search_completed": completed,
            "status": status,
            "reason": reason,
            "exact_expression": expression,
            "records_returned": returned,
            "total_found": total,
            "evidence_path": evidence,
            "coverage_note": str(meta.get("coverage_note") or ""),
        })

    # Licensed routes are explicit even though they are not executable providers.
    for provider in ("scopus", "web_of_science"):
        rows.append({
            "provider": provider,
            "method_track": "indexed_database_licensed",
            "implemented": False,
            "default_enabled": False,
            "attempted": False,
            "search_completed": False,
            "status": "LICENSED_MANUAL_ROUTE",
            "reason": "Requires real licensed/manual execution evidence; another provider is never treated as equivalent.",
            "exact_expression": "",
            "records_returned": "",
            "total_found": "",
            "evidence_path": "",
            "coverage_note": "POST_PRESS route governed by D-096 for Article 1.",
        })

    out_dir = project / "07_logs" / "engine"
    json_path = out_dir / "search_coverage_ledger.json"
    csv_path = out_dir / "search_coverage_ledger.csv"
    payload = {
        "schema_version": 1,
        "article1_phase": str(scientific_status.get("article1_current_phase") or ""),
        "source_registry_version": str(registry.get("version") or ""),
        "rows": rows,
        "summary": {
            "routes_total": len(rows),
            "attempted": sum(bool(row["attempted"]) for row in rows),
            "completed": sum(bool(row["search_completed"]) for row in rows),
            "failed_or_partial": sum(row["status"] in {"FAILED", "EXECUTED_PARTIAL"} for row in rows),
        },
        "semantics": {
            "attempted_is_not_completed": True,
            "failure_is_not_zero_results": True,
            "pilot_is_not_formal": True,
        },
    }
    _atomic_json(json_path, payload)
    _atomic_csv(csv_path, rows)
    return {**payload["summary"], "json_path": str(json_path), "csv_path": str(csv_path)}


__all__ = ["write_search_coverage_ledger"]
