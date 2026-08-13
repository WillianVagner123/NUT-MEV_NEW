"""Execute immutable search-strategy versions through canonical providers.

The executor is the execution boundary: PILOT versions remain auditable and
non-PRISMA; FORMAL/PRISMA-eligible versions cannot start unless persisted gates
and an immutable freeze authorize the exact strategy, Git SHA, and config digest.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.base import ProviderResult
from nutev.search.formal_execution_guard import require_formal_execution_authorization
from nutev.search.provider_orchestrator import search_provider
from nutev.search.strategy_builder import BREADTHS
from nutev.search.strategy_execution_ledger import (
    create_search_run,
    finish_search_run,
    record_execution_artifact,
)
from nutev.search.strategy_registry import (
    default_registry_path,
    get_strategy_version,
    record_search_execution,
)

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
EXECUTABLE_PROVIDERS = ("pubmed", "europepmc", "crossref", "openalex")


def default_raw_search_root(project_root: Path) -> Path:
    return Path(project_root) / "03_corpus" / "search_raw"


def parse_provider_expression(provider: str, expression: str) -> tuple[str, str]:
    clean_provider = provider.strip().lower()
    clean_expression = expression.strip()
    if not clean_expression:
        raise ValueError("provider expression cannot be blank")
    if clean_provider in {"crossref", "openalex"}:
        if not clean_expression.startswith("query="):
            raise ValueError(f"{clean_provider} expression must start with 'query='")
        body = clean_expression.removeprefix("query=")
        query, separator, filter_value = body.partition(" | filter=")
        clean_query = query.strip()
        if not clean_query:
            raise ValueError(f"{clean_provider} query cannot be blank")
        return clean_query, filter_value.strip() if separator else ""
    return clean_expression, ""


def _safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    temporary.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _registry_status(provider_status: str) -> str:
    if provider_status in {"completed", "empty", "partial"}:
        return "SUCCEEDED"
    if provider_status == "skipped":
        return "CANCELLED"
    return "FAILED"


def _run_status(provider_statuses: list[str]) -> str:
    if not provider_statuses:
        return "CANCELLED"
    successes = sum(status in {"completed", "empty"} for status in provider_statuses)
    partials = sum(status == "partial" for status in provider_statuses)
    failures = sum(status == "failed" for status in provider_statuses)
    skipped = sum(status == "skipped" for status in provider_statuses)
    if successes == len(provider_statuses):
        return "SUCCEEDED"
    if failures == len(provider_statuses):
        return "FAILED"
    if skipped == len(provider_statuses):
        return "CANCELLED"
    if successes or partials:
        return "PARTIAL"
    return "FAILED"


def execute_strategy_version(
    project_root: Path,
    *,
    version_id: str,
    breadth: str = "specific",
    providers: list[str] | tuple[str, ...] | None = None,
    limit: int = 100,
    resume: bool = False,
    registry_path: Path | None = None,
    search_fn: Callable[..., ProviderResult] = search_provider,
    run_id: str | None = None,
    started_at: str | None = None,
    authorization_git_sha: str | None = None,
    authorization_config_digest: str | None = None,
) -> dict[str, Any]:
    """Execute one immutable strategy version after required scientific gates."""
    root = Path(project_root)
    db_path = Path(registry_path) if registry_path else default_registry_path(root)
    version = get_strategy_version(db_path, version_id)
    if version is None:
        raise ValueError(f"unknown strategy version: {version_id}")

    authorization = require_formal_execution_authorization(
        root,
        version,
        current_git_sha=authorization_git_sha,
        current_config_digest=authorization_config_digest,
    )

    normalized_breadth = breadth.strip().lower()
    if normalized_breadth not in BREADTHS:
        raise ValueError(f"breadth must be one of {BREADTHS}")
    safe_limit = int(limit)
    if safe_limit <= 0 or safe_limit > 10000:
        raise ValueError("limit must be between 1 and 10000")

    provider_grid = version.get("providers") or {}
    available = [
        provider
        for provider in EXECUTABLE_PROVIDERS
        if provider in provider_grid
        and str((provider_grid.get(provider) or {}).get(normalized_breadth) or "").strip()
    ]
    requested = list(providers) if providers is not None else available
    requested = list(dict.fromkeys(str(provider).strip().lower() for provider in requested))
    if not requested:
        raise ValueError("select at least one executable provider")
    unsupported = [provider for provider in requested if provider not in available]
    if unsupported:
        raise ValueError(
            "providers unavailable for this version/breadth: " + ", ".join(unsupported)
        )

    timestamp = started_at or datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")
    resolved_run_id = run_id or (
        "search_run_"
        + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
        + "_"
        + uuid4().hex[:10]
    )
    create_search_run(
        db_path,
        version_id=version_id,
        breadth=normalized_breadth,
        provider_limit=safe_limit,
        resume_enabled=resume,
        run_id=resolved_run_id,
        started_at=timestamp,
    )

    run_dir = default_raw_search_root(root) / _safe_component(version_id) / _safe_component(resolved_run_id)
    checkpoint_dir = root / "07_logs" / "checkpoints" / "search_registry"
    logs_dir = root / "07_logs"
    provider_summaries: list[dict[str, Any]] = []
    provider_statuses: list[str] = []
    errors: list[str] = []

    for provider in requested:
        expression = str(provider_grid[provider][normalized_breadth]).strip()
        provider_query, provider_filter = parse_provider_expression(provider, expression)
        result: ProviderResult
        try:
            result = search_fn(
                provider=provider,
                query=provider_query,
                workstream=f"search_registry_{version_id}",
                limit=safe_limit,
                checkpoint_dir=checkpoint_dir,
                resume=resume,
                run_id=resolved_run_id,
                logs_dir=logs_dir,
                context={
                    "provider_filter": provider_filter,
                    "strategy_version_id": version_id,
                    "exact_expression": expression,
                },
            )
            if not isinstance(result, ProviderResult):
                raise TypeError("search provider returned an invalid result object")
        except Exception as exc:
            result = ProviderResult(
                provider=provider,
                query=provider_query,
                status="failed",
                error=str(exc),
            )

        provider_statuses.append(result.status)
        if result.error:
            errors.append(f"{provider}: {result.error}")

        snapshot_path = run_dir / f"{_safe_component(provider)}.jsonl"
        snapshot_sha256 = _write_jsonl_atomic(snapshot_path, list(result.rows or []))
        registry_status = _registry_status(result.status)
        records_found = int(result.total_found) if result.total_found is not None else int(result.total_returned)
        execution = record_search_execution(
            db_path,
            version_id=version_id,
            provider=provider,
            breadth=normalized_breadth,
            expression=expression,
            status=registry_status,
            records_found=records_found,
            error_message=result.error or "",
            started_at=timestamp,
        )
        artifact = record_execution_artifact(
            db_path,
            run_id=resolved_run_id,
            execution_id=execution["execution_id"],
            version_id=version_id,
            provider=provider,
            breadth=normalized_breadth,
            exact_expression=expression,
            provider_query=provider_query,
            provider_filter=provider_filter,
            provider_status=result.status,
            records_returned=int(result.total_returned),
            total_found=int(result.total_found) if result.total_found is not None else None,
            snapshot_path=str(snapshot_path),
            snapshot_sha256=snapshot_sha256,
            checkpoint_path=result.checkpoint_path or "",
            metadata=dict(result.meta or {}),
            created_at=timestamp,
        )
        provider_summaries.append(artifact)

    records_identified = sum(item["records_returned"] for item in provider_summaries)
    provider_reported_total_found = sum(
        item["total_found"] if item["total_found"] is not None else item["records_returned"]
        for item in provider_summaries
    )
    prisma_records_identified = records_identified if version["prisma_eligible"] else 0
    terminal_status = _run_status(provider_statuses)

    manifest_path = run_dir / "run_manifest.json"
    manifest = {
        "run_id": resolved_run_id,
        "strategy_id": version["strategy_id"],
        "version_id": version_id,
        "version": version["version"],
        "search_type": version["search_type"],
        "prisma_eligible": bool(version["prisma_eligible"]),
        "formal_authorization": authorization,
        "breadth": normalized_breadth,
        "provider_limit": safe_limit,
        "resume_enabled": bool(resume),
        "started_at": timestamp,
        "status": terminal_status,
        "records_identified_before_deduplication": records_identified,
        "provider_reported_total_found": provider_reported_total_found,
        "prisma_records_identified": prisma_records_identified,
        "providers": provider_summaries,
        "errors": errors,
    }
    manifest_sha256 = _write_json_atomic(manifest_path, manifest)
    finished = finish_search_run(
        db_path,
        run_id=resolved_run_id,
        status=terminal_status,
        records_identified=records_identified,
        provider_reported_total_found=provider_reported_total_found,
        prisma_records_identified=prisma_records_identified,
        manifest_path=str(manifest_path),
        error_message="; ".join(errors),
    )

    return {
        **finished,
        "strategy_id": version["strategy_id"],
        "version": version["version"],
        "search_type": version["search_type"],
        "prisma_eligible": bool(version["prisma_eligible"]),
        "formal_authorization": authorization,
        "records_identified_before_deduplication": records_identified,
        "provider_reported_total_found": provider_reported_total_found,
        "prisma_records_identified": prisma_records_identified,
        "providers": provider_summaries,
        "manifest_sha256": manifest_sha256,
    }
