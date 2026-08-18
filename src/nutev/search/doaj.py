"""DOAJ (Directory of Open Access Journals) article-search connector.

Adds open-access journal coverage via the public DOAJ REST API — no key required.
Follows the same shape as the other bibliographic connectors: a reproducible
single-page default, opt-in bounded pagination, and exponential backoff.
"""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import requests

_DOAJ_URL = "https://doaj.org/api/search/articles/"
USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _pick_doi(bibjson: dict) -> str:
    for ident in bibjson.get("identifier", []) or []:
        if isinstance(ident, dict) and str(ident.get("type", "")).lower() == "doi":
            return _clean(ident.get("id"))
    return ""


def _pick_url(bibjson: dict, doi: str) -> str:
    for link in bibjson.get("link", []) or []:
        if isinstance(link, dict) and link.get("url"):
            return _clean(link.get("url"))
    return f"https://doi.org/{doi}" if doi else ""


def _normalize_doaj_item(item: dict, query: str) -> dict:
    bibjson = item.get("bibjson", {}) if isinstance(item, dict) else {}
    doi = _pick_doi(bibjson)
    authors = "; ".join(
        _clean(a.get("name"))
        for a in bibjson.get("author", []) or []
        if isinstance(a, dict) and a.get("name")
    )
    abstract = _clean(bibjson.get("abstract"))
    return {
        "source": "doaj",
        "source_provider": "doaj",
        "title": _clean(bibjson.get("title")),
        "abstract": abstract,
        "snippet": abstract,
        "doi": doi,
        "pmid": "",
        "pmcid": "",
        "url": _pick_url(bibjson, doi),
        "journal": _clean((bibjson.get("journal") or {}).get("title")),
        "year": _clean(bibjson.get("year")),
        "publication_date": _clean(bibjson.get("year")),
        "article_type": "open_access_article",
        "authors": authors,
        "is_open_access": "true",
        "metadata_status": "doaj_search",
        "query": query,
        "provider_query": query,
    }


def _doaj_get(query: str, page: int, page_size: int) -> dict | None:
    """GET one page with exponential backoff. Returns parsed JSON or None."""
    url = _DOAJ_URL + quote(query, safe="")
    for attempt in range(1, 4):
        try:
            response = requests.get(
                url,
                params={"page": page, "pageSize": page_size},
                timeout=45,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(min(2**attempt, 8))
    return None


def _resolve_max_results(page_size: int, max_results: int | None) -> int:
    """Default preserves single-page behaviour; opt into deeper recall with
    NUTEV_DOAJ_MAX_RESULTS so default runs stay reproducible."""
    if max_results is not None:
        return max(max_results, 0)
    env = os.environ.get("NUTEV_DOAJ_MAX_RESULTS", "")
    return int(env) if env.isdigit() and int(env) > 0 else page_size


def search_doaj(
    query: str,
    page_size: int = 18,
    max_results: int | None = None,
) -> list[dict]:
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return []
    if os.environ.get("NUTEV_SKIP_DOAJ") == "1":
        return []

    page_size = max(1, min(page_size, 100))
    target = _resolve_max_results(page_size, max_results)

    if target <= page_size:
        data = _doaj_get(query, 1, page_size)
        if not data:
            return []
        return [
            _normalize_doaj_item(item, query)
            for item in data.get("results", []) or []
        ]

    collected: list[dict] = []
    seen: set[str] = set()
    page = 1
    while len(collected) < target:
        requested = min(page_size, target - len(collected))
        data = _doaj_get(query, page, requested)
        if not data:
            break
        results = data.get("results", []) or []
        if not results:
            break
        for item in results:
            row = _normalize_doaj_item(item, query)
            key = row["doi"] or row["title"]
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            collected.append(row)
            if len(collected) >= target:
                break
        if len(results) < requested:
            break
        page += 1
    return collected
