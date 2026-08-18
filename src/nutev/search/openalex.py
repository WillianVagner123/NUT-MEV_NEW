from __future__ import annotations

import os
import time

import requests

_OPENALEX_URL = "https://api.openalex.org/works"
USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"


def _pick_openalex_url(item: dict) -> str:
    primary = item.get("primary_location") or {}
    best_oa = item.get("best_oa_location") or {}
    for candidate in [
        primary.get("pdf_url"),
        primary.get("landing_page_url"),
        best_oa.get("pdf_url"),
        best_oa.get("landing_page_url"),
        item.get("doi"),
        item.get("id"),
    ]:
        if candidate:
            return candidate
    return ""


def _normalize_openalex_item(item: dict, query: str) -> dict:
    return {
        "source": "openalex",
        "source_provider": "openalex",
        "title": item.get("display_name"),
        "abstract": " ".join((item.get("abstract_inverted_index") or {}).keys())
        if isinstance(item.get("abstract_inverted_index"), dict)
        else "",
        "snippet": "",
        "doi": item.get("doi"),
        "url": _pick_openalex_url(item),
        "pmcid": str((item.get("ids") or {}).get("pmcid") or "").rsplit("/", 1)[-1],
        "is_open_access": str(bool((item.get("open_access") or {}).get("is_oa"))).lower(),
        "oa_url": (item.get("open_access") or {}).get("oa_url")
        or (item.get("best_oa_location") or {}).get("pdf_url")
        or (item.get("best_oa_location") or {}).get("landing_page_url")
        or "",
        "journal": ((item.get("primary_location") or {}).get("source") or {}).get(
            "display_name", ""
        ),
        "year": item.get("publication_year") or "",
        "publication_date": item.get("publication_date") or "",
        "article_type": item.get("type") or "",
        "authors": "; ".join(
            [
                str((a.get("author") or {}).get("display_name") or "")
                for a in item.get("authorships", [])[:12]
            ]
        )
        if isinstance(item.get("authorships"), list)
        else "",
        "metadata_status": "openalex_search",
        "query": query,
        "provider_query": query,
    }


def _mailto() -> dict:
    mailto = os.environ.get("OPENALEX_MAILTO")
    return {"mailto": mailto} if mailto else {}


def _openalex_get(params: dict) -> dict | None:
    """GET with exponential backoff. Returns parsed JSON or None."""
    for attempt in range(1, 4):
        try:
            response = requests.get(
                _OPENALEX_URL,
                params=params,
                timeout=(10, 25),
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(min(2**attempt, 8))
    return None


def _resolve_max_results(default: int, max_results: int | None) -> int:
    """Default preserves single-page behaviour; opt in with
    NUTEV_OPENALEX_MAX_RESULTS so default runs stay reproducible."""
    if max_results is not None:
        return max(max_results, 0)
    env = os.environ.get("NUTEV_OPENALEX_MAX_RESULTS", "")
    return int(env) if env.isdigit() and int(env) > 0 else default


def _request_params(
    query: str,
    per_page: int,
    *,
    filter_value: str = "",
    cursor: str | None = None,
) -> dict:
    params: dict = {"search": query, "per-page": per_page, **_mailto()}
    if filter_value.strip():
        params["filter"] = filter_value.strip()
    if cursor is not None:
        params["cursor"] = cursor
    return params


def search_openalex(
    query: str,
    per_page: int = 12,
    max_results: int | None = None,
    filter_value: str = "",
) -> list[dict]:
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return []

    target = _resolve_max_results(per_page, max_results)

    if target <= per_page:
        data = _openalex_get(
            _request_params(query, per_page, filter_value=filter_value)
        )
        if not data:
            return []
        return [
            _normalize_openalex_item(item, query)
            for item in data.get("results", []) or []
        ]

    collected: list[dict] = []
    seen: set[str] = set()
    cursor = "*"
    while len(collected) < target:
        data = _openalex_get(
            _request_params(
                query,
                min(per_page, target - len(collected)),
                filter_value=filter_value,
                cursor=cursor,
            )
        )
        if not data:
            break
        results = data.get("results", []) or []
        if not results:
            break
        for item in results:
            key = str(
                item.get("id") or item.get("doi") or item.get("display_name") or ""
            )
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            collected.append(_normalize_openalex_item(item, query))
            if len(collected) >= target:
                break
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return collected
