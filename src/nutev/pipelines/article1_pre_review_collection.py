"""Real, non-FORMAL Article 1 collection before human PRESS review.

This module deliberately separates *collecting real provider data* from
*promoting a search to FORMAL/PRISMA*. It executes only persisted PILOT,
non-PRISMA expressions. If no Article 1 strategy-registry row exists yet, it may
materialize a deterministic operational mirror of the already-canonical GF-02
PubMed #7 expression; that mirror does not create or change scientific approval.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from nutev.pipelines.play_pipeline import run_play
from nutev.search.gf02_pubmed_current import load_candidate_config, resolved_line_expressions
from nutev.search.strategy_executor import EXECUTABLE_PROVIDERS
from nutev.search.strategy_registry import (
    default_registry_path,
    list_strategy_versions,
    save_strategy_version,
)

ProgressFn = Callable[[str], None]
COLLECTION_SCHEMA_VERSION = 1
NATIVE_EXPORT_PROVIDERS = {"scielo_native", "lilacs_bvs"}
CORE_DISCOVERY_PROVIDERS = (
    "pubmed",
    "europepmc",
    "crossref",
    "openalex",
    "scielo_native",
    "lilacs_bvs",
)


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _state_path(project_root: Path) -> Path:
    return Path(project_root) / "07_logs" / "pre_review_collection" / "latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


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


def run_pre_review_collection(
    project_root: Path,
    *,
    repo_root: Path | None = None,
    progress_fn: ProgressFn | None = None,
    limit: int = 10000,
) -> dict[str, Any]:
    """Collect real searchable data now, without creating FORMAL/PRISMA evidence."""
    root = Path(project_root)
    repo = Path(repo_root) if repo_root is not None else _default_repo_root()
    version = _matching_nonformal_version(root, repo)
    if version is None:
        if progress_fn:
            progress_fn(
                "Materializando no registry um espelho operacional determinístico da query GF-02 já canônica."
            )
        version = _materialize_gf02_operational_mirror(root, repo)

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
            "prisma_eligible": False,
            "formal_execution_authorized": False,
            "scientific_gate_effect": "NONE",
            "human_decision_inferred": False,
        }
        _atomic_json(_state_path(root), result)
        return result

    if progress_fn:
        progress_fn("Coleta real pré-revisão: executando " + ", ".join(providers) + ".")
        progress_fn(
            "Estes resultados são reais e auditáveis, mas permanecem NÃO-FORMAIS e fora do PRISMA até FREEZE/FORMAL."
        )

    summary = run_play(
        root,
        version_id=str(version["version_id"]),
        breadth="specific",
        providers=providers,
        limit=limit,
        resume=True,
        metadata_only=True,
    )
    execution_status = str((summary.get("status") or {}).get("execution_status") or "UNKNOWN")
    search = summary.get("search") or {}
    corpus = summary.get("corpus") or {}
    result = {
        "schema_version": COLLECTION_SCHEMA_VERSION,
        "collection_type": "REAL_PRE_REVIEW_COLLECTION",
        "status": execution_status,
        "source_strategy_version_id": version.get("version_id"),
        "source_strategy_checksum_sha256": version.get("checksum_sha256"),
        "source_strategy_search_type": version.get("search_type"),
        "providers_executed": providers,
        "providers_deferred": deferred,
        "records_returned": int(search.get("records_returned") or 0),
        "provider_reported_total_found": int(search.get("provider_reported_total_found") or 0),
        "any_provider_truncated": bool(search.get("any_truncated")),
        "unique_records": int(corpus.get("unique_records") or 0),
        "duplicates_removed": int(corpus.get("duplicates_removed") or 0),
        "possible_duplicates": int(corpus.get("possible_duplicates") or 0),
        "play_id": summary.get("play_id"),
        "play_summary_path": str((summary.get("artifacts") or {}).get("summary_path") or ""),
        "master_corpus_path": str(corpus.get("master_jsonl_path") or ""),
        "metadata_only": True,
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "scientific_gate_effect": "NONE",
        "human_decision_inferred": False,
    }
    _atomic_json(_state_path(root), result)
    if progress_fn:
        progress_fn(
            "Coleta real concluída: "
            f"{result['records_returned']} registros recuperados; "
            f"{result['unique_records']} documentos únicos após deduplicação automática."
        )
    return result


__all__ = [
    "executable_collection_providers",
    "pre_review_collection_status",
    "run_pre_review_collection",
]
