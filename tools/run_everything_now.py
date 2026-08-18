from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nutev.reference_identity import canonical_identity, dedupe_records
from nutev.search.brave_optional import search_brave
from nutev.search.crossref import search_crossref
from nutev.search.doaj import search_doaj
from nutev.search.europepmc import search_europepmc
from nutev.search.google_pse import search_google_pse
from nutev.search.official_sources import all_manifest_sources, load_official_manifest
from nutev.search.openalex import search_openalex
from nutev.search.pubmed import PubMedClient
from nutev.search.reference_queries import load_reference_search
from nutev.search.semantic_scholar import search_semantic_scholar
from nutev.search.serpapi_optional import search_serpapi

SCHEMA_VERSION = 1
COLLECTION_TYPE = "REFERENCE_COLLECTION"
SUCCESS_STATUSES = {"completed", "empty", "partial"}
_SPACE_RE = re.compile(r"\s+")
_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    return cleaned[:160] or "item"


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
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _normalize_doi(value: Any) -> str:
    """Legacy compatibility helper; runtime identity uses nutev.reference_identity."""

    match = _DOI_RE.search(str(value or ""))
    return match.group(0).rstrip(" .;,)]}").lower() if match else ""


def _normalize_pmid(value: Any) -> str:
    """Legacy compatibility helper; runtime identity uses nutev.reference_identity."""

    digits = re.sub(r"\D+", "", str(value or ""))
    return digits if digits else ""


def _normalize_url(value: Any) -> str:
    """Legacy compatibility helper; runtime identity uses nutev.reference_identity."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except Exception:
        return raw
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return raw
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


def _identity(row: dict[str, Any]) -> str:
    return canonical_identity(row)


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_records(rows)


def _save_provider(run_dir: Path, provider: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    records_path = run_dir / "providers" / f"{_safe(provider)}.jsonl"
    digest = _atomic_jsonl(records_path, rows)
    result = {
        "provider": provider,
        "status": meta.get("status") or "completed",
        "records_saved": len(rows),
        "records_path": str(records_path),
        "records_sha256": digest,
        "total_found": meta.get("total_found"),
        "error": str(meta.get("error") or ""),
    }
    _atomic_json(run_dir / "providers" / f"{_safe(provider)}.meta.json", result)
    return result


def _run_list_provider(
    run_dir: Path,
    provider: str,
    loader: Callable[[], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"{provider}: collecting...", flush=True)
    try:
        rows = list(loader() or [])
        meta = _save_provider(run_dir, provider, rows, {"status": "completed"})
    except Exception as exc:
        rows = []
        meta = _save_provider(
            run_dir,
            provider,
            rows,
            {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
        )
    print(f"{provider}: {meta['status']} ({len(rows)} records).", flush=True)
    return rows, meta


def _run_pubmed(
    project_root: Path,
    run_dir: Path,
    query: str,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"pubmed: collecting up to {limit} records...", flush=True)
    try:
        result = PubMedClient().search(
            query,
            limit=min(max(1, limit), 9999),
            context={
                "checkpoint_dir": project_root / "07_logs" / "checkpoints" / "reference_pubmed",
                "resume": True,
                "workstream": "reference_collection",
            },
        )
        rows = list(result.rows or [])
        status = result.status if result.status in SUCCESS_STATUSES else result.status or "failed"
        meta = _save_provider(
            run_dir,
            "pubmed",
            rows,
            {
                "status": status,
                "total_found": result.total_found,
                "error": result.error or "",
            },
        )
        meta["coverage_complete"] = bool(
            result.total_found is None or int(result.total_found or 0) <= len(rows)
        )
    except Exception as exc:
        rows = []
        meta = _save_provider(
            run_dir,
            "pubmed",
            rows,
            {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
        )
        meta["coverage_complete"] = False
    print(f"pubmed: {meta['status']} ({len(rows)} records).", flush=True)
    return rows, meta


def _optional_web(query: str) -> list[tuple[str, bool, Callable[[], Any]]]:
    return [
        (
            "google_pse",
            bool(os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_CSE_ID")),
            lambda: search_google_pse(query, limit=100),
        ),
        ("brave", bool(os.environ.get("BRAVE_API_KEY")), lambda: search_brave(query, limit=20)),
        ("serpapi", bool(os.environ.get("SERPAPI_API_KEY")), lambda: search_serpapi(query, limit=100)),
    ]


def run(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    config_path = REPO_ROOT / "config" / "reference_search.json"
    search_config = load_reference_search(config_path)
    queries = dict(search_config["queries"])
    deep_collection = os.environ.get("NUTEV_DEEP_COLLECTION") == "1"
    limit_key = "deep_provider_limits" if deep_collection else "provider_limits"
    limits = dict(search_config.get(limit_key) or search_config.get("provider_limits") or {})
    collection_profile = "deep" if deep_collection else "operational"
    strategy_sha = sha256(config_path.read_bytes()).hexdigest()
    run_id = "reference_" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "_" + uuid4().hex[:8]
    run_dir = project_root / "13_reference_collection" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"collection profile: {collection_profile}", flush=True)
    print(
        "provider limits: " + ", ".join(f"{name}={value}" for name, value in limits.items()),
        flush=True,
    )
    if deep_collection:
        print("deep collection enabled; this run can take substantially longer.", flush=True)

    rows_by_provider: dict[str, list[dict[str, Any]]] = {}
    provider_meta: dict[str, dict[str, Any]] = {}
    unavailable_sources: list[dict[str, str]] = []

    pubmed_rows, pubmed_meta = _run_pubmed(
        project_root,
        run_dir,
        queries["pubmed"],
        int(limits.get("pubmed") or 2000),
    )
    rows_by_provider["pubmed"] = pubmed_rows
    provider_meta["pubmed"] = pubmed_meta

    loaders: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = [
        (
            "europepmc",
            lambda: search_europepmc(
                queries["generic"], page_size=1000, max_results=int(limits.get("europepmc") or 3000)
            ),
        ),
        (
            "openalex",
            lambda: search_openalex(
                queries["web"], per_page=200, max_results=int(limits.get("openalex") or 3000)
            ),
        ),
        (
            "crossref",
            lambda: search_crossref(
                queries["web"], rows=1000, max_results=int(limits.get("crossref") or 1000)
            ),
        ),
        (
            "doaj",
            lambda: search_doaj(
                queries["web"], page_size=100, max_results=int(limits.get("doaj") or 1000)
            ),
        ),
        (
            "semantic_scholar",
            lambda: search_semantic_scholar(
                queries["web"], page_size=100, max_results=int(limits.get("semantic_scholar") or 1000)
            ),
        ),
    ]
    for provider, loader in loaders:
        rows, meta = _run_list_provider(run_dir, provider, loader)
        rows_by_provider[provider] = rows
        provider_meta[provider] = meta

    official_rows = all_manifest_sources(load_official_manifest(REPO_ROOT / "config", include_countries=True))
    rows_by_provider["official_web"] = official_rows
    provider_meta["official_web"] = _save_provider(
        run_dir, "official_web", official_rows, {"status": "completed"}
    )

    for provider, configured, call in _optional_web(queries["web"]):
        if not configured:
            unavailable_sources.append({"provider": provider, "reason": "credentials_not_configured"})
            continue
        try:
            result = call()
            rows = list(result.rows or [])
            meta = _save_provider(
                run_dir,
                provider,
                rows,
                {
                    "status": result.status if result.status in SUCCESS_STATUSES else result.status,
                    "total_found": result.total_found,
                    "error": result.error or "",
                },
            )
        except Exception as exc:
            rows = []
            meta = _save_provider(
                run_dir,
                provider,
                rows,
                {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
            )
        rows_by_provider[provider] = rows
        provider_meta[provider] = meta

    unavailable_sources.extend(
        [
            {"provider": "scopus", "reason": "licensed_access_not_configured"},
            {"provider": "web_of_science", "reason": "licensed_access_not_configured"},
        ]
    )

    combined: list[dict[str, Any]] = []
    for provider, rows in rows_by_provider.items():
        for row in rows:
            item = dict(row)
            item.setdefault("source_provider", provider)
            item.setdefault("source", provider)
            item["collection_type"] = COLLECTION_TYPE
            combined.append(item)
    master = _dedupe(combined)
    master_path = run_dir / "master_records.jsonl"
    master_sha = _atomic_jsonl(master_path, master)

    status = "COMPLETE"
    failed = [name for name, meta in provider_meta.items() if meta.get("status") == "failed"]
    if failed:
        status = "COMPLETE_WITH_PROVIDER_FAILURES"

    result = {
        "schema_version": SCHEMA_VERSION,
        "collection_type": COLLECTION_TYPE,
        "collection_profile": collection_profile,
        "provider_limits": limits,
        "run_id": run_id,
        "created_at": _now(),
        "status": status,
        "strategy_sha256": strategy_sha,
        "queries": queries,
        "providers": provider_meta,
        "unavailable_sources": unavailable_sources,
        "failed_providers": failed,
        "records_before_cross_source_dedup": len(combined),
        "unique_records_after_cross_source_dedup": len(master),
        "master_records_path": str(master_path),
        "master_records_sha256": master_sha,
        "run_dir": str(run_dir),
        "notes": [
            "Outputs are reference-discovery inputs for human reading priority.",
            "Unavailable or failed providers are reported explicitly and are never simulated.",
            "LILACS/BVS and SciELO are collected by the next canonical pipeline stage.",
            "Set NUTEV_DEEP_COLLECTION=1 only when intentionally requesting the larger deep-collection limits.",
        ],
    }
    _atomic_json(run_dir / "manifest.json", result)
    _atomic_json(project_root / "07_logs" / "collect_everything" / "latest.json", result)
    print(f"Reference collection complete: {len(master)} unique records.", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect references from the supported NutEV Reference Engine sources.")
    parser.add_argument("--project-root", default="./project_output_reference")
    args = parser.parse_args()
    try:
        run(Path(args.project_root))
    except KeyboardInterrupt:
        print("Interrupted; provider checkpoints already written remain available.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Collection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
