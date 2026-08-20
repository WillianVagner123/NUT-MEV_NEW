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
from nutev.search.crossref import search_crossref
from nutev.search.doaj import search_doaj
from nutev.search.europepmc import search_europepmc
from nutev.search.openalex import search_openalex
from nutev.search.pubmed import PubMedClient
from nutev.search.semantic_scholar import search_semantic_scholar
from nutev.taxonomy import load_canonical_taxonomy
from tools.rank_references import score_record

PROVIDER_ORDER = (
    "pubmed",
    "europepmc",
    "openalex",
    "crossref",
    "doaj",
    "semantic_scholar",
)
PROVIDER_LABELS = {
    "pubmed": "PubMed",
    "europepmc": "Europe PMC",
    "openalex": "OpenAlex",
    "crossref": "Crossref",
    "doaj": "DOAJ",
    "semantic_scholar": "Semantic Scholar",
}
MAX_QUERY_LENGTH = 500
MAX_PER_PROVIDER = 100
MAX_RESULTS = 300
_SPACE_RE = re.compile(r"\s+")


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
    raise ValueError(f"Provider não suportado no modo web: {provider}")


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


def search_evidence(
    query: object,
    *,
    providers: list[str] | None = None,
    per_provider: int = 25,
    max_results: int = 100,
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

    provider_status: list[dict[str, Any]] = []
    combined: list[dict[str, Any]] = []
    network_disabled = os.environ.get("NUTEV_DISABLE_NETWORK") == "1"

    for provider in chosen:
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

    unique = dedupe_records(combined)
    ranked = _score_rows(unique) if unique else []
    returned = ranked[:max_results]
    failed = [item["provider"] for item in provider_status if item["status"] == "failed"]

    return {
        "schema_version": 1,
        "search_id": search_id,
        "query": question,
        "created_at": _now(),
        "status": "COMPLETE_WITH_PROVIDER_FAILURES" if failed else "COMPLETE",
        "providers": provider_status,
        "failed_providers": failed,
        "records_before_dedup": len(combined),
        "unique_records": len(unique),
        "returned_records": len(returned),
        "ranking_policy": "query-conditioned retrieval + canonical NutEV reference priority score",
        "ranking_warning": "Ranking é prioridade de leitura; não representa recomendação clínica, elegibilidade científica ou qualidade metodológica.",
        "interactive_limitations": [
            "LILACS/BVS e SciELO permanecem no pipeline canônico separado e ainda não estão ligados ao modo web interativo.",
            "Scopus e Web of Science não são simulados e exigem acesso licenciado separado.",
        ],
        "results": returned,
    }
