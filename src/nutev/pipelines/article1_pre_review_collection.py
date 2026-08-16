"""Real, resumable, non-FORMAL Article 1 collection before human PRESS review.

This module deliberately separates *collecting real provider data* from
*promoting a search to FORMAL/PRISMA*. It executes only persisted PILOT,
non-PRISMA expressions. If no Article 1 strategy-registry row exists yet, it may
materialize a deterministic operational mirror of the already-canonical GF-02
PubMed #7 expression; that mirror does not create or change scientific approval.

Every successfully completed provider is persisted immediately as an immutable
JSONL snapshot plus SHA-256 and ledger artifact. The collection state stores the
same search_run_id, so an interrupted dashboard run can resume later without
re-querying providers whose snapshots are already verified on disk.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.base import ProviderResult
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.gf02_pubmed_current import load_candidate_config, resolved_line_expressions
from nutev.search.provider_orchestrator import search_provider
from nutev.search.strategy_execution_ledger import (
    create_search_run,
    finish_search_run,
    get_search_run,
    list_execution_artifacts,
    record_execution_artifact,
)
from nutev.search.strategy_executor import (
    EXECUTABLE_PROVIDERS,
    default_raw_search_root,
    parse_provider_expression,
)
from nutev.search.strategy_registry import (
    default_registry_path,
    list_strategy_versions,
    record_search_execution,
    save_strategy_version,
)

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
ProgressFn = Callable[[str], None]
SearchFn = Callable[..., ProviderResult]
COLLECTION_SCHEMA_VERSION = 2
NATIVE_EXPORT_PROVIDERS = {"scielo_native", "lilacs_bvs"}
CORE_DISCOVERY_PROVIDERS = (
    "pubmed",
    "europepmc",
    "crossref",
    "openalex",
    "scielo_native",
    "lilacs_bvs",
)
_PROVIDER_SUCCESS = {"completed", "empty", "partial"}


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _state_path(project_root: Path) -> Path:
    return Path(project_root) / "07_logs" / "pre_review_collection" / "latest.json"


def _safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _canonical_gf02_query(repo_root: Path) -> tuple[str, str]:
    config = load_candidate_config(Path(repo_root) / "config" / "gf02_pubmed_candidates.json")
    final_line = str(config.get("final_line") or "#7")
    expressions = resolved_line_expressions(config)
    return str(config.get("current_candidate") or "UNKNOWN"), expressions[final_line]


def _matching_nonformal_version(project_root: Path, repo_root: Path) -> dict[str, Any] | None:
    _, canonical_query = _canonical_gf02_query(repo_root)
    versions = list_strategy_versions(default_registry_path(project_root), limit=1000)
    for version in versions:
        if str(version.get("search_type") or "").upper() != "PILOT" or bool(
            version.get("prisma_eligible")
        ):
            continue
        grid = version.get("providers") or {}
        pubmed_expression = str((grid.get("pubmed") or {}).get("specific") or "").strip()
        if pubmed_expression == canonical_query:
            return version
    return None


def _materialize_gf02_operational_mirror(project_root: Path, repo_root: Path) -> dict[str, Any]:
    candidate_version, query = _canonical_gf02_query(repo_root)
    record = save_strategy_version(
        default_registry_path(project_root),
        title="Article 1 GF-02 operational mirror",
        query_text=f"Canonical GF-02 PubMed {candidate_version} final line #7",
        strategy_payload={
            "query": [query],
            "filters": {},
            "providers": {"pubmed": {"specific": query}},
        },
        search_type="PILOT",
        prisma_eligible=False,
        created_by="SYSTEM_DETERMINISTIC_GF02_MIRROR",
        notes=(
            "article1_pre_review_candidate=true; deterministic operational mirror of "
            "config/gf02_pubmed_candidates.json; no scientific gate effect"
        ),
    )
    return asdict(record)


def _native_export_available(project_root: Path, expression: str) -> bool:
    _, marker, value = expression.partition(" | export=")
    if not marker or not value.strip():
        return False
    path = Path(value.strip())
    if not path.is_absolute():
        path = Path(project_root) / path
    return path.is_file()


def executable_collection_providers(
    project_root: Path,
    version: dict[str, Any],
    *,
    breadth: str = "specific",
) -> tuple[list[str], list[dict[str, str]]]:
    """Return real providers executable now and explicit deferred providers."""
    grid = version.get("providers") or {}
    executable: list[str] = []
    deferred: list[dict[str, str]] = []
    for provider in CORE_DISCOVERY_PROVIDERS:
        expression = str((grid.get(provider) or {}).get(breadth) or "").strip()
        if not expression:
            deferred.append(
                {"provider": provider, "reason": "no_exact_provider_expression_registered"}
            )
            continue
        if provider not in EXECUTABLE_PROVIDERS:
            deferred.append({"provider": provider, "reason": "provider_not_executable_in_play"})
            continue
        if provider in NATIVE_EXPORT_PROVIDERS and not _native_export_available(project_root, expression):
            deferred.append(
                {
                    "provider": provider,
                    "reason": "official_export_required_or_missing",
                }
            )
            continue
        executable.append(provider)

    deferred.extend(
        [
            {"provider": "official_web", "reason": "not_integrated_in_strategy_play"},
            {"provider": "scopus", "reason": "licensed_execution_required"},
            {"provider": "web_of_science", "reason": "licensed_execution_required"},
        ]
    )
    return executable, deferred


def _verified_artifacts(
    project_root: Path,
    *,
    run_id: str,
    requested: list[str],
) -> dict[str, dict[str, Any]]:
    db_path = default_registry_path(project_root)
    out: dict[str, dict[str, Any]] = {}
    for artifact in list_execution_artifacts(db_path, run_id=run_id, limit=5000):
        provider = str(artifact.get("provider") or "")
        if provider not in requested:
            continue
        snapshot_path = Path(str(artifact.get("snapshot_path") or ""))
        if not snapshot_path.is_file():
            raise RuntimeError(
                f"Autosave corrompido: snapshot de {provider} não existe: {snapshot_path}"
            )
        expected = str(artifact.get("snapshot_sha256") or "")
        actual = sha256(snapshot_path.read_bytes()).hexdigest()
        if not expected or actual != expected:
            raise RuntimeError(
                f"Autosave corrompido: SHA-256 do snapshot de {provider} não confere."
            )
        if str(artifact.get("provider_status") or "") not in _PROVIDER_SUCCESS:
            continue
        out[provider] = artifact
    return out


def _partial_payload(
    *,
    version: dict[str, Any],
    run_id: str,
    providers: list[str],
    deferred: list[dict[str, str]],
    artifacts: dict[str, dict[str, Any]],
    failure_history: list[dict[str, Any]],
    status: str,
    reason: str,
    started_at: str,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ordered = [artifacts[p] for p in providers if p in artifacts]
    records_saved = sum(int(item.get("records_returned") or 0) for item in ordered)
    total_found = sum(
        int(item.get("total_found"))
        if item.get("total_found") is not None
        else int(item.get("records_returned") or 0)
        for item in ordered
    )
    pending = [provider for provider in providers if provider not in artifacts]
    truncated = any(
        item.get("total_found") is not None
        and int(item.get("total_found") or 0) > int(item.get("records_returned") or 0)
        for item in ordered
    )
    payload: dict[str, Any] = {
        "schema_version": COLLECTION_SCHEMA_VERSION,
        "collection_type": "REAL_PRE_REVIEW_COLLECTION",
        "status": status,
        "reason": reason,
        "started_at": started_at,
        "updated_at": _now_iso(),
        "source_strategy_version_id": version.get("version_id"),
        "source_strategy_checksum_sha256": version.get("checksum_sha256"),
        "source_strategy_search_type": version.get("search_type"),
        "search_run_id": run_id,
        "providers_requested": providers,
        "providers_executed": [item.get("provider") for item in ordered],
        "providers_saved": [item.get("provider") for item in ordered],
        "providers_pending": pending,
        "providers_deferred": deferred,
        "records_returned": records_saved,
        "records_saved_partial": records_saved,
        "provider_reported_total_found": total_found,
        "any_provider_truncated": truncated,
        "provider_snapshots": [
            {
                "provider": item.get("provider"),
                "status": item.get("provider_status"),
                "records_returned": item.get("records_returned"),
                "total_found": item.get("total_found"),
                "snapshot_path": item.get("snapshot_path"),
                "snapshot_sha256": item.get("snapshot_sha256"),
                "checkpoint_path": item.get("checkpoint_path"),
            }
            for item in ordered
        ],
        "provider_failure_history": failure_history,
        "autosave": {
            "enabled": True,
            "unit": "provider_snapshot",
            "resume_same_search_run": True,
            "state_path": str(_state_path(Path(str(version.get("_project_root") or ".")))),
        },
        "metadata_only": True,
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "scientific_gate_effect": "NONE",
        "human_decision_inferred": False,
    }
    if corpus:
        payload.update(
            {
                "unique_records": int(corpus.get("unique_records") or 0),
                "duplicates_removed": int(corpus.get("duplicates_removed") or 0),
                "possible_duplicates": int(corpus.get("possible_duplicates") or 0),
                "master_corpus_path": str(corpus.get("master_jsonl_path") or ""),
                "corpus_manifest_path": str(corpus.get("manifest_path") or ""),
            }
        )
    return payload


def pre_review_collection_status(
    project_root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Read collection status without manufacturing a human/scientific decision."""
    root = Path(project_root)
    repo = Path(repo_root) if repo_root is not None else _default_repo_root()
    current = _load_json(_state_path(root))
    try:
        version = _matching_nonformal_version(root, repo)
        _, canonical_query = _canonical_gf02_query(repo)
    except Exception as exc:
        return {
            **current,
            "complete": False,
            "can_run": False,
            "reason": f"gf02_canonical_query_unavailable:{exc}",
            "path": str(_state_path(root)),
        }
    if version is None:
        return {
            **current,
            "complete": False,
            "can_run": True,
            "reason": "gf02_operational_mirror_will_be_materialized_on_run",
            "canonical_pubmed_query_present": bool(canonical_query),
            "path": str(_state_path(root)),
        }
    checksum = str(version.get("checksum_sha256") or "")
    complete = bool(
        current
        and current.get("collection_type") == "REAL_PRE_REVIEW_COLLECTION"
        and str(current.get("source_strategy_checksum_sha256") or "") == checksum
        and str(current.get("status") or "") in {"COMPLETE", "COMPLETE_WITH_WARNINGS"}
        and not list(current.get("providers_pending") or [])
        and current.get("prisma_eligible") is False
        and current.get("formal_execution_authorized") is False
    )
    return {
        **current,
        "complete": complete,
        "can_run": True,
        "source_strategy_version_id": version.get("version_id"),
        "source_strategy_checksum_sha256": checksum,
        "path": str(_state_path(root)),
    }


def _ensure_search_run(
    project_root: Path,
    *,
    version: dict[str, Any],
    run_id: str,
    limit: int,
    started_at: str,
) -> None:
    db_path = default_registry_path(project_root)
    existing = get_search_run(db_path, run_id)
    if existing is None:
        create_search_run(
            db_path,
            version_id=str(version["version_id"]),
            breadth="specific",
            provider_limit=limit,
            resume_enabled=True,
            run_id=run_id,
            started_at=started_at,
        )
        return
    if str(existing.get("version_id") or "") != str(version["version_id"]):
        raise RuntimeError("Autosave search_run_id pertence a outra strategy version.")
    if str(existing.get("breadth") or "") != "specific":
        raise RuntimeError("Autosave search_run_id possui breadth incompatível.")
    if int(existing.get("provider_limit") or 0) != int(limit):
        raise RuntimeError("Autosave search_run_id possui provider_limit incompatível.")


def run_pre_review_collection(
    project_root: Path,
    *,
    repo_root: Path | None = None,
    progress_fn: ProgressFn | None = None,
    limit: int = 10000,
    search_fn: SearchFn = search_provider,
) -> dict[str, Any]:
    """Collect real data with durable per-provider autosave and same-run resume."""
    root = Path(project_root)
    repo = Path(repo_root) if repo_root is not None else _default_repo_root()
    safe_limit = int(limit)
    if safe_limit <= 0 or safe_limit > 10000:
        raise ValueError("limit must be between 1 and 10000")

    version = _matching_nonformal_version(root, repo)
    if version is None:
        if progress_fn:
            progress_fn(
                "Materializando no registry um espelho operacional determinístico da query GF-02 já canônica."
            )
        version = _materialize_gf02_operational_mirror(root, repo)
    if str(version.get("search_type") or "").upper() != "PILOT" or bool(
        version.get("prisma_eligible")
    ):
        raise RuntimeError("Coleta pré-revisão aceita somente estratégia PILOT não-PRISMA.")

    existing = pre_review_collection_status(root, repo_root=repo)
    if bool(existing.get("complete")):
        return existing

    providers, deferred = executable_collection_providers(root, version)
    if not providers:
        result = {
            "schema_version": COLLECTION_SCHEMA_VERSION,
            "collection_type": "REAL_PRE_REVIEW_COLLECTION",
            "status": "BLOCKED",
            "reason": "no_provider_is_executable_without_external_input",
            "source_strategy_version_id": version.get("version_id"),
            "source_strategy_checksum_sha256": version.get("checksum_sha256"),
            "providers_deferred": deferred,
            "providers_pending": [],
            "prisma_eligible": False,
            "formal_execution_authorized": False,
            "scientific_gate_effect": "NONE",
            "human_decision_inferred": False,
        }
        _atomic_json(_state_path(root), result)
        return result

    checksum = str(version.get("checksum_sha256") or "")
    reusable = bool(
        existing
        and str(existing.get("source_strategy_checksum_sha256") or "") == checksum
        and str(existing.get("search_run_id") or "").strip()
        and str(existing.get("status") or "")
        in {"RUNNING", "INTERRUPTED", "PARTIAL", "COMPLETE_WITH_WARNINGS"}
    )
    run_id = (
        str(existing["search_run_id"])
        if reusable
        else "pre_review_"
        + datetime.now(LOCAL_TIMEZONE).strftime("%Y%m%dT%H%M%S%z")
        + "_"
        + uuid4().hex[:10]
    )
    started_at = str(existing.get("started_at") or "") if reusable else ""
    started_at = started_at or _now_iso()
    failure_history = list(existing.get("provider_failure_history") or []) if reusable else []
    version_for_state = dict(version)
    version_for_state["_project_root"] = str(root)

    _ensure_search_run(
        root,
        version=version,
        run_id=run_id,
        limit=safe_limit,
        started_at=started_at,
    )
    artifacts = _verified_artifacts(root, run_id=run_id, requested=providers)

    if progress_fn:
        if artifacts:
            progress_fn(
                "Retomando autosave: "
                f"{len(artifacts)}/{len(providers)} fontes já estão salvas e verificadas; "
                "elas não serão pesquisadas novamente."
            )
        else:
            progress_fn("Coleta real pré-revisão: executando " + ", ".join(providers) + ".")
        progress_fn(
            "Autosave ativo: cada fonte concluída grava JSONL + SHA-256 imediatamente. "
            "Se a execução parar, o próximo clique retoma do mesmo search_run_id."
        )
        progress_fn(
            "Estes resultados são reais e auditáveis, mas permanecem NÃO-FORMAIS e fora do PRISMA até FREEZE/FORMAL."
        )

    initial = _partial_payload(
        version=version_for_state,
        run_id=run_id,
        providers=providers,
        deferred=deferred,
        artifacts=artifacts,
        failure_history=failure_history,
        status="RUNNING",
        reason="partial_autosave_active",
        started_at=started_at,
    )
    initial["autosave"]["state_path"] = str(_state_path(root))
    _atomic_json(_state_path(root), initial)

    db_path = default_registry_path(root)
    provider_grid = version.get("providers") or {}
    run_dir = (
        default_raw_search_root(root)
        / _safe_component(str(version["version_id"]))
        / _safe_component(run_id)
    )
    checkpoint_dir = root / "07_logs" / "checkpoints" / "search_registry"
    logs_dir = root / "07_logs"
    attempted_statuses: dict[str, str] = {
        provider: str(item.get("provider_status") or "completed")
        for provider, item in artifacts.items()
    }

    try:
        for provider in providers:
            if provider in artifacts:
                if progress_fn:
                    progress_fn(
                        f"{provider}: restaurado do autosave ({artifacts[provider].get('records_returned', 0)} registros)."
                    )
                continue

            expression = str(provider_grid[provider]["specific"]).strip()
            provider_query, provider_filter = parse_provider_expression(provider, expression)
            if progress_fn:
                progress_fn(f"{provider}: pesquisando dados reais...")
            try:
                result = search_fn(
                    provider=provider,
                    query=provider_query,
                    workstream=f"pre_review_{version['version_id']}",
                    limit=safe_limit,
                    checkpoint_dir=checkpoint_dir,
                    resume=True,
                    run_id=run_id,
                    logs_dir=logs_dir,
                    context={
                        "provider_filter": provider_filter,
                        "strategy_version_id": version["version_id"],
                        "exact_expression": expression,
                        "project_root": str(root),
                        "collection_type": "REAL_PRE_REVIEW_COLLECTION",
                    },
                )
                if not isinstance(result, ProviderResult):
                    raise TypeError("search provider returned an invalid result object")
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                result = ProviderResult(
                    provider=provider,
                    query=provider_query,
                    status="failed",
                    error=str(exc),
                )

            attempted_statuses[provider] = result.status
            execution = record_search_execution(
                db_path,
                version_id=str(version["version_id"]),
                provider=provider,
                breadth="specific",
                expression=expression,
                status=(
                    "SUCCEEDED"
                    if result.status in _PROVIDER_SUCCESS
                    else "CANCELLED"
                    if result.status == "skipped"
                    else "FAILED"
                ),
                records_found=(
                    int(result.total_found)
                    if result.total_found is not None
                    else int(result.total_returned)
                ),
                error_message=result.error or "",
            )

            if result.status in _PROVIDER_SUCCESS:
                snapshot_path = run_dir / f"{_safe_component(provider)}.jsonl"
                snapshot_sha256 = _atomic_jsonl(snapshot_path, list(result.rows or []))
                artifact = record_execution_artifact(
                    db_path,
                    run_id=run_id,
                    execution_id=str(execution["execution_id"]),
                    version_id=str(version["version_id"]),
                    provider=provider,
                    breadth="specific",
                    exact_expression=expression,
                    provider_query=provider_query,
                    provider_filter=provider_filter,
                    provider_status=result.status,
                    records_returned=int(result.total_returned),
                    total_found=(
                        int(result.total_found) if result.total_found is not None else None
                    ),
                    snapshot_path=str(snapshot_path),
                    snapshot_sha256=snapshot_sha256,
                    checkpoint_path=result.checkpoint_path or "",
                    metadata=dict(result.meta or {}),
                )
                artifacts[provider] = artifact
                if progress_fn:
                    progress_fn(
                        f"{provider}: SALVO — {int(result.total_returned)} registros, SHA-256 {snapshot_sha256[:12]}…"
                    )
            else:
                failure_history.append(
                    {
                        "provider": provider,
                        "status": result.status,
                        "error": result.error or "",
                        "attempted_at": _now_iso(),
                        "search_run_id": run_id,
                    }
                )
                if progress_fn:
                    progress_fn(
                        f"{provider}: não concluído; erro preservado e a fonte continuará pendente para nova tentativa."
                    )

            partial = _partial_payload(
                version=version_for_state,
                run_id=run_id,
                providers=providers,
                deferred=deferred,
                artifacts=artifacts,
                failure_history=failure_history,
                status="RUNNING",
                reason="partial_autosave_available",
                started_at=started_at,
            )
            partial["autosave"]["state_path"] = str(_state_path(root))
            _atomic_json(_state_path(root), partial)
    except BaseException as exc:
        interrupted = _partial_payload(
            version=version_for_state,
            run_id=run_id,
            providers=providers,
            deferred=deferred,
            artifacts=artifacts,
            failure_history=failure_history,
            status="INTERRUPTED",
            reason="partial_autosave_available_resume_same_run",
            started_at=started_at,
        )
        interrupted["last_error_type"] = type(exc).__name__
        interrupted["autosave"]["state_path"] = str(_state_path(root))
        _atomic_json(_state_path(root), interrupted)
        raise

    provider_summaries = [artifacts[p] for p in providers if p in artifacts]
    pending = [provider for provider in providers if provider not in artifacts]
    records_identified = sum(int(item.get("records_returned") or 0) for item in provider_summaries)
    provider_reported_total_found = sum(
        int(item.get("total_found"))
        if item.get("total_found") is not None
        else int(item.get("records_returned") or 0)
        for item in provider_summaries
    )
    run_status = "PARTIAL" if pending else (
        "PARTIAL"
        if any(str(item.get("provider_status") or "") == "partial" for item in provider_summaries)
        else "SUCCEEDED"
    )
    manifest_path = run_dir / "run_manifest.json"
    manifest = {
        "schema_version": 1,
        "collection_type": "REAL_PRE_REVIEW_COLLECTION",
        "run_id": run_id,
        "version_id": version["version_id"],
        "search_type": "PILOT",
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "scientific_gate_effect": "NONE",
        "provider_limit": safe_limit,
        "resume_enabled": True,
        "started_at": started_at,
        "finished_at": _now_iso(),
        "status": run_status,
        "records_identified_before_deduplication": records_identified,
        "provider_reported_total_found": provider_reported_total_found,
        "providers": provider_summaries,
        "providers_pending": pending,
        "failure_history": failure_history,
    }
    manifest_sha256 = _atomic_json(manifest_path, manifest)
    finish_search_run(
        db_path,
        run_id=run_id,
        status=run_status,
        records_identified=records_identified,
        provider_reported_total_found=provider_reported_total_found,
        prisma_records_identified=0,
        manifest_path=str(manifest_path),
        error_message="; ".join(
            f"{item.get('provider')}: {item.get('error')}" for item in failure_history[-20:]
        ),
    )

    corpus: dict[str, Any] = {}
    if provider_summaries:
        if progress_fn:
            progress_fn("Organizando o que já foi salvo em corpus deduplicado auditável...")
        corpus = build_corpus_from_search_run(root, run_id=run_id)

    any_truncated = any(
        item.get("total_found") is not None
        and int(item.get("total_found") or 0) > int(item.get("records_returned") or 0)
        for item in provider_summaries
    )
    if pending:
        final_status = "PARTIAL"
        reason = "providers_pending_retry_available"
    elif any_truncated or any(
        str(item.get("provider_status") or "") == "partial" for item in provider_summaries
    ):
        final_status = "COMPLETE_WITH_WARNINGS"
        reason = "collection_complete_with_audited_warnings"
    else:
        final_status = "COMPLETE"
        reason = "collection_complete"

    result = _partial_payload(
        version=version_for_state,
        run_id=run_id,
        providers=providers,
        deferred=deferred,
        artifacts=artifacts,
        failure_history=failure_history,
        status=final_status,
        reason=reason,
        started_at=started_at,
        corpus=corpus,
    )
    result["finished_at"] = _now_iso()
    result["search_manifest_path"] = str(manifest_path)
    result["search_manifest_sha256"] = manifest_sha256
    result["autosave"]["state_path"] = str(_state_path(root))
    _atomic_json(_state_path(root), result)

    if progress_fn:
        if pending:
            progress_fn(
                "Coleta parcial preservada: "
                f"{records_identified} registros já estão salvos; faltam "
                + ", ".join(pending)
                + ". Clique novamente depois para retomar sem repetir as fontes salvas."
            )
        else:
            progress_fn(
                "Coleta real concluída: "
                f"{records_identified} registros recuperados; "
                f"{int(corpus.get('unique_records') or 0)} documentos únicos após deduplicação automática."
            )
    return result


__all__ = [
    "executable_collection_providers",
    "pre_review_collection_status",
    "run_pre_review_collection",
]