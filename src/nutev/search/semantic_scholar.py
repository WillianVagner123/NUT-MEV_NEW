"""Semantic Scholar paper-search connector (Graph API).

Broad academic coverage via the public Semantic Scholar Graph API. A key is
optional (``S2_API_KEY``). Without one the shared rate limit applies and the
connector fails safe on throttling.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

_S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,year,authors,externalIds,venue,openAccessPdf,url"
USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _headers() -> dict:
    key = os.environ.get("S2_API_KEY")
    headers = {"User-Agent": USER_AGENT}
    if key:
        headers["x-api-key"] = key
    return headers


def _normalize_paper(paper: dict, query: str) -> dict:
    ext = paper.get("externalIds", {}) or {}
    authors = "; ".join(
        _clean(a.get("name"))
        for a in paper.get("authors", []) or []
        if isinstance(a, dict) and a.get("name")
    )
    doi = _clean(ext.get("DOI"))
    oa = (paper.get("openAccessPdf") or {}).get("url")
    url = (
        _clean(oa)
        or _clean(paper.get("url"))
        or (f"https://doi.org/{doi}" if doi else "")
    )
    abstract = _clean(paper.get("abstract"))
    return {
        "source": "semantic_scholar",
        "source_provider": "semantic_scholar",
        "title": _clean(paper.get("title")),
        "abstract": abstract,
        "snippet": abstract,
        "doi": doi,
        "pmid": _clean(ext.get("PubMed")),
        "pmcid": _clean(ext.get("PubMedCentral")),
        "url": url,
        "journal": _clean(paper.get("venue")),
        "year": _clean(paper.get("year")),
        "publication_date": _clean(paper.get("year")),
        "article_type": "article",
        "authors": authors,
        "metadata_status": "semantic_scholar_search",
        "query": query,
        "provider_query": query,
    }


def _s2_get(query: str, limit: int, offset: int) -> dict | None:
    """GET one page with exponential backoff. Returns parsed JSON or None."""
    params = {"query": query, "limit": limit, "offset": offset, "fields": _FIELDS}
    for attempt in range(1, 4):
        try:
            response = requests.get(
                _S2_URL,
                params=params,
                timeout=45,
                headers=_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(min(2**attempt, 8))
    return None


def _resolve_max_results(page_size: int, max_results: int | None) -> int:
    """Default preserves single-page behaviour; opt into deeper recall with
    NUTEV_SEMANTIC_SCHOLAR_MAX_RESULTS so default runs stay reproducible."""
    if max_results is not None:
        return max(max_results, 0)
    env = os.environ.get("NUTEV_SEMANTIC_SCHOLAR_MAX_RESULTS", "")
    return int(env) if env.isdigit() and int(env) > 0 else page_size


def search_semantic_scholar(
    query: str,
    page_size: int = 18,
    max_results: int | None = None,
) -> list[dict]:
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return []
    if os.environ.get("NUTEV_SKIP_SEMANTIC_SCHOLAR") == "1":
        return []

    page_size = max(1, min(page_size, 100))
    target = _resolve_max_results(page_size, max_results)

    if target <= page_size:
        data = _s2_get(query, page_size, 0)
        if not data:
            return []
        return [
            _normalize_paper(paper, query) for paper in data.get("data", []) or []
        ]

    collected: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while len(collected) < target:
        page = min(page_size, target - len(collected))
        data = _s2_get(query, page, offset)
        if not data:
            break
        papers = data.get("data", []) or []
        if not papers:
            break
        for paper in papers:
            row = _normalize_paper(paper, query)
            key = row["doi"] or row["title"]
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            collected.append(row)
            if len(collected) >= target:
                break
        if data.get("next") is None or len(papers) < page:
            break
        offset += page
    return collected
