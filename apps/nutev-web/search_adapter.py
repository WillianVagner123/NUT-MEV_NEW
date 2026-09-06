from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nutev.reference_identity import dedupe_records
from nutev.search.brave_optional import search_brave
from nutev.search.crossref import search_crossref
from nutev.search.doaj import search_doaj
from nutev.search.europepmc import search_europepmc
from nutev.search.google_pse import search_google_pse
from nutev.search.openalex import search_openalex
from nutev.search.pubmed import PubMedClient
from nutev.search.semantic_scholar import search_semantic_scholar
from nutev.search.serpapi_optional import search_serpapi
from nutev.taxonomy import load_canonical_taxonomy
from tools.rank_references import score_record
from tools.run_latin_sources import run as run_latin_sources

DIRECT_PROVIDERS = (
    "pubmed",
    "europepmc",
    "openalex",
    "crossref",
    "doaj",
    "semantic_scholar",
    "google_pse",
    "brave",
    "serpapi",
)
LATIN_PROVIDERS = (
    "lilacs_bvs_native",
    "scielo_native",
)
PROVIDER_ORDER = DIRECT_PROVIDERS + LATIN_PROVIDERS
PROVIDER_LABELS = {
    "pubmed": "PubMed",
    "europepmc": "Europe PMC",
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "doaj": "DOAJ",
    "semantic_scholar": "Semantic Scholar",
    "google_pse": "Google Programmable Search",
    "brave": "Brave Search",
    "serpapi": "SerpAPI / Google",
    "lilacs_bvs_native": "LILACS / BVS",
    "scielo_native": "SciELO",
}
OPTIONAL_WEB_CAPS = {
    "google_pse": 100,
    "brave": 20,
    "serpapi": 100,
}
MAX_QUERY_LENGTH = 500
MAX_PER_PROVIDER = 100
MAX_RESULTS = 300
_SPACE_RE = re.compile(r"\s+")
_SEARCH_ID_RE = re.compile(r"^web_[A-Za-z0-9+_-]+$")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_query(value: object) -> str:
    query = _SPACE_RE.sub(" ", str(value or "")).strip()
    if not query:
        raise ValueError("A pergunta de busca não pode ficar vazia.")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"A pergunta deve ter no máximo {MAX_QUERY_LENGTH} caracteres.")
    return query


def _read_profile() -> dict[str, Any]:
    path = REPO_ROOT / "config" / "reference_mode.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("config/reference_mode.json inválido")
    return data


def _normalize_provider_result(value: Any) -> tuple[list[dict[str, Any]], str, int | None, str]:
    if hasattr(value, "rows"):
        rows = list(getattr(value, "rows") or [])
        status = str(getattr(value, "status", "completed") or "completed")
        total_found = getattr(value, "total_found", None)
        error = str(getattr(value, "error", "") or "")
        return rows, status, total_found, error
    rows = list(value or [])
    return rows, ("completed" if rows else "empty"), len(rows), ""


def _cap_aware_optional_result(
    provider: str,
    requested_limit: int,
    cap: int,
    call: Callable[[], Any],
) -> Any:
    """Preserve provider caps instead of falsely claiming exhaustive coverage."""

    result = call()
    rows = list(getattr(result, "rows", None) or [])
    status = str(getattr(result, "status", "") or "")
    if requested_limit > cap and len(rows) >= cap and status == "completed":
        result.status = "partial"
        note = f"connector_limit_reached:{provider}:{cap}"
        previous = str(getattr(result, "error", "") or "").strip()
        result.error = f"{previous}; {note}" if previous else note
    return result


def _provider_call(provider: str, query: str, limit: int) -> Callable[[], Any]:
    if provider == "pubmed":
        return lambda: PubMedClient().search(
            query,
            limit=limit,
            context={
                "checkpoint_dir": REPO_ROOT / ".cache" / "nutev-web" / "pubmed",
                "resume": True,
                "workstream": "interactive_web_search",
            },
        )
    if provider == "europepmc":
        return lambda: search_europepmc(query, page_size=min(1000, max(25, limit)), max_results=limit)
    if provider == "openalex":
        return lambda: search_openalex(query, per_page=min(200, max(25, limit)), max_results=limit)
    if provider == "crossref":
        return lambda: search_crossref(query, rows=min(1000, max(25, limit)), max_results=limit)
    if provider == "doaj":
        return lambda: search_doaj(query, page_size=min(100, max(25, limit)), max_results=limit)
    if provider == "semantic_scholar":
        return lambda: search_semantic_scholar(query, page_size=min(100, max(25, limit)), max_results=limit)
    if provider == "google_pse":
        cap = OPTIONAL_WEB_CAPS[provider]
        return lambda: _cap_aware_optional_result(
            provider,
            limit,
            cap,
            lambda: search_google_pse(query, limit=min(limit, cap)),
        )
    if provider == "brave":
        cap = OPTIONAL_WEB_CAPS[provider]
        return lambda: _cap_aware_optional_result(
            provider,
            limit,
            cap,
            lambda: search_brave(query, limit=min(limit, cap)),
        )
    if provider == "serpapi":
        cap = OPTIONAL_WEB_CAPS[provider]
        return lambda: _cap_aware_optional_result(
            provider,
            limit,
            cap,
            lambda: search_serpapi(query, limit=min(limit, cap)),
        )
    raise ValueError(f"Provider não suportado no modo web direto: {provider}")


def _score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    taxonomy, taxonomy_meta = load_canonical_taxonomy(REPO_ROOT / "config")
    profile = _read_profile()
    focus_keywords = list(profile.get("focus_keywords") or [])
    provider_weights = dict(profile.get("provider_weights") or {})
    guardrails = dict(profile.get("guardrails") or {})
    primary_dimension_order = list((taxonomy_meta or {}).get("primary_dimension_order") or [])

    ranked: list[dict[str, Any]] = []
    for row in rows:
        scored = score_record(
            row,
            taxonomy,
            focus_keywords,
            provider_weights,
            guardrails=guardrails,
            primary_dimension_order=primary_dimension_order,
        )
        ranked.append(scored)
    ranked.sort(
        key=lambda item: (
            -float(item.get("reference_score") or 0.0),
            str(item.get("title") or "").casefold(),
        )
    )
    for index, item in enumerate(ranked, start=1):
        item["reference_rank"] = index
    return ranked


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _output_root(value: Path | None = None) -> Path:
    return (value or (REPO_ROOT / "project_output_reference")).resolve()


def _web_run_dir(output_root: Path, search_id: str) -> Path:
    if not _SEARCH_ID_RE.fullmatch(search_id):
        raise ValueError("search_id inválido")
    return output_root / "15_web_searches" / search_id


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _persist_search(result: dict[str, Any], output_root: Path) -> None:
    run_dir = _web_run_dir(output_root, str(result["search_id"]))
    payload = dict(result)
    payload["run_dir"] = str(run_dir)
    payload["result_path"] = str(run_dir / "result.json")
    _atomic_json(run_dir / "result.json", payload)
    _atomic_json(output_root / "07_logs" / "web_search" / "latest.json", payload)


def _latin_rows_and_status(
    query: str,
    selected: list[str],
    *,
    output_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    if not selected:
        return [], [], None
    summary = run_latin_sources(output_root, query, providers=selected)
    rows: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for item in summary.get("providers", []) or []:
        provider = str(item.get("provider") or "")
        if provider not in selected:
            continue
        provider_rows = _read_jsonl(Path(str(item.get("records_path") or "")))
        rows.extend(provider_rows)
        statuses.append(
            {
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "status": str(item.get("status") or "failed"),
                "returned": len(provider_rows),
                "total_found": None,
                "error": str(item.get("error") or ""),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "search_url": item.get("search_url"),
            }
        )
    return rows, statuses, str(summary.get("summary_path") or "") or None


def search_evidence(
    query: object,
    *,
    providers: list[str] | None = None,
    per_provider: int = 25,
    max_results: int = 100,
    output_root: Path | None = None,
) -> dict[str, Any]:
    question = _clean_query(query)
    chosen = list(dict.fromkeys(providers or PROVIDER_ORDER))
    invalid = [provider for provider in chosen if provider not in PROVIDER_ORDER]
    if invalid:
        raise ValueError("Providers inválidos: " + ", ".join(invalid))
    if not chosen:
        raise ValueError("Selecione pelo menos um provider.")

    per_provider = max(1, min(int(per_provider), MAX_PER_PROVIDER))
    max_results = max(1, min(int(max_results), MAX_RESULTS))
    search_id = "web_" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "_" + uuid4().hex[:8]
    root = _output_root(output_root)

    provider_status: list[dict[str, Any]] = []
    combined: list[dict[str, Any]] = []
    network_disabled = os.environ.get("NUTEV_DISABLE_NETWORK") == "1"

    for provider in [item for item in chosen if item in DIRECT_PROVIDERS]:
        started = _now()
        if network_disabled:
            provider_status.append(
                {
                    "provider": provider,
                    "label": PROVIDER_LABELS[provider],
                    "status": "skipped",
                    "returned": 0,
                    "total_found": None,
                    "error": "network_disabled",
                    "started_at": started,
                    "finished_at": _now(),
                }
            )
            continue
        try:
            raw = _provider_call(provider, question, per_provider)()
            rows, status, total_found, error = _normalize_provider_result(raw)
        except Exception as exc:
            rows = []
            status = "failed"
            total_found = None
            error = f"{type(exc).__name__}: {exc}"

        for row in rows:
            item = dict(row)
            item.setdefault("source_provider", provider)
            item.setdefault("source", provider)
            item["query"] = question
            item["provider_query"] = item.get("provider_query") or question
            item["interactive_search_id"] = search_id
            item["interactive_retrieved_at"] = _now()
            combined.append(item)

        provider_status.append(
            {
                "provider": provider,
                "label": PROVIDER_LABELS[provider],
                "status": status,
                "returned": len(rows),
                "total_found": total_found,
                "error": error,
                "started_at": started,
                "finished_at": _now(),
            }
        )

    latin_selected = [item for item in chosen if item in LATIN_PROVIDERS]
    latin_summary_path: str | None = None
    if latin_selected:
        if network_disabled:
            for provider in latin_selected:
                provider_status.append(
                    {
                        "provider": provider,
                        "label": PROVIDER_LABELS[provider],
                        "status": "skipped",
                        "returned": 0,
                        "total_found": None,
                        "error": "network_disabled",
                        "started_at": _now(),
                        "finished_at": _now(),
                    }
                )
        else:
            try:
                latin_rows, latin_status, latin_summary_path = _latin_rows_and_status(
                    question,
                    latin_selected,
                    output_root=root,
                )
            except Exception as exc:
                latin_rows = []
                latin_status = [
                    {
                        "provider": provider,
                        "label": PROVIDER_LABELS[provider],
                        "status": "failed",
                        "returned": 0,
                        "total_found": None,
                        "error": f"{type(exc).__name__}: {exc}",
                        "started_at": _now(),
                        "finished_at": _now(),
                    }
                    for provider in latin_selected
                ]
            for row in latin_rows:
                item = dict(row)
                item["interactive_search_id"] = search_id
                item["interactive_retrieved_at"] = _now()
                combined.append(item)
            provider_status.extend(latin_status)

    status_by_provider = {item["provider"]: item for item in provider_status}
    provider_status = [status_by_provider[p] for p in chosen if p in status_by_provider]

    unique = dedupe_records(combined)
    ranked = _score_rows(unique) if unique else []
    returned = ranked[:max_results]
    failed = [item["provider"] for item in provider_status if item["status"] == "failed"]
    unavailable = [item["provider"] for item in provider_status if item["status"] == "unavailable"]
    partial = [item["provider"] for item in provider_status if item["status"] == "partial"]
    skipped = [item["provider"] for item in provider_status if item["status"] == "skipped"]

    result = {
        "schema_version": 2,
        "search_id": search_id,
        "query": question,
        "created_at": _now(),
        "status": "COMPLETE_WITH_PROVIDER_GAPS" if (failed or unavailable or partial or skipped) else "COMPLETE",
        "providers": provider_status,
        "failed_providers": failed,
        "unavailable_providers": unavailable,
        "partial_providers": partial,
        "skipped_providers": skipped,
        "records_before_dedup": len(combined),
        "unique_records": len(unique),
        "returned_records": len(returned),
        "ranking_policy": "query-conditioned retrieval + canonical NutEV reference priority score",
        "ranking_warning": "Ranking é prioridade de leitura; não representa recomendação clínica, elegibilidade científica ou qualidade metodológica.",
        "latin_summary_path": latin_summary_path,
        "interactive_limitations": [
            "Google Programmable Search, Brave Search e SerpAPI são fontes web opcionais: sem credenciais, ficam registradas como skipped; ausência de credencial nunca é interpretada como ausência de literatura.",
            "Os conectores web opcionais preservam seus limites próprios (Google PSE até 100, Brave até 20 e SerpAPI até 100 registros por query no conector atual); atingir o limite é registrado como cobertura parcial, não como exaustão demonstrada.",
            "LILACS/BVS e SciELO usam as interfaces públicas nativas; bloqueios HTTP são registrados como indisponibilidade e nunca substituídos por resultados fabricados.",
            "Scopus e Web of Science não são simulados e exigem acesso licenciado separado.",
        ],
        "results": returned,
    }
    _persist_search(result, root)
    return result


def list_search_runs(*, output_root: Path | None = None, limit: int = 30) -> list[dict[str, Any]]:
    root = _output_root(output_root) / "15_web_searches"
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in root.glob("web_*/result.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        items.append(
            {
                "search_id": value.get("search_id"),
                "query": value.get("query"),
                "created_at": value.get("created_at"),
                "status": value.get("status"),
                "unique_records": value.get("unique_records", 0),
                "returned_records": value.get("returned_records", 0),
                "failed_providers": value.get("failed_providers", []),
                "unavailable_providers": value.get("unavailable_providers", []),
            }
        )
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return items[: max(1, min(int(limit), 200))]


def load_search_run(search_id: str, *, output_root: Path | None = None) -> dict[str, Any]:
    path = _web_run_dir(_output_root(output_root), str(search_id)) / "result.json"
    if not path.is_file():
        raise FileNotFoundError(search_id)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Run web inválido")
    return value
