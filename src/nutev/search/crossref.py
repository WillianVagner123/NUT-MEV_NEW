from __future__ import annotations

import os
import time

import requests

USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"


def _pick_crossref_url(item: dict) -> str:
    for link in item.get("link", []) or []:
        if isinstance(link, dict):
            href = link.get("URL") or link.get("url")
            ctype = (link.get("content-type") or "").lower()
            if href and ("pdf" in ctype or href.lower().endswith(".pdf")):
                return href

    doi = item.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"

    resource = item.get("resource") or {}
    primary = resource.get("primary") or {}
    if primary.get("URL"):
        return primary["URL"]

    return item.get("URL") or ""


_CROSSREF_URL = "https://api.crossref.org/works"


def _normalize_crossref_item(it: dict, query: str) -> dict:
    titles = it.get("title") or [""]
    return {
        "source": "crossref",
        "source_provider": "crossref",
        "title": titles[0] if titles else "",
        "abstract": it.get("abstract") or "",
        "snippet": it.get("abstract") or "",
        "doi": it.get("DOI"),
        "pmid": "",
        "pmcid": "",
        "url": _pick_crossref_url(it),
        "journal": (it.get("container-title") or [""])[0]
        if isinstance(it.get("container-title"), list)
        else "",
        "year": str(
            (
                (it.get("published-print") or it.get("published-online") or {}).get(
                    "date-parts"
                )
                or [[""]]
            )[0][0]
            or ""
        ),
        "publication_date": "-".join(
            str(x)
            for x in (
                (
                    (it.get("published-print") or it.get("published-online") or {}).get(
                        "date-parts"
                    )
                    or [[]]
                )[0]
            )
        ),
        "article_type": it.get("type") or "",
        "authors": "; ".join(
            [
                " ".join(
                    [str(a.get("given", "")), str(a.get("family", ""))]
                ).strip()
                for a in it.get("author", [])[:12]
            ]
        )
        if isinstance(it.get("author"), list)
        else "",
        "metadata_status": "crossref_search",
        "query": query,
        "provider_query": query,
    }


def _mailto() -> dict:
    mailto = os.environ.get("CROSSREF_MAILTO")
    return {"mailto": mailto} if mailto else {}


def _crossref_get(params: dict) -> dict | None:
    """GET with exponential backoff. Returns parsed JSON or None."""
    for attempt in range(1, 4):
        try:
            r = requests.get(
                _CROSSREF_URL,
                params=params,
                timeout=45,
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            time.sleep(min(2**attempt, 8))
    return None


def _resolve_max_results(default: int, max_results: int | None) -> int:
    """Default (None) preserves single-page behaviour; opt in with
    NUTEV_CROSSREF_MAX_RESULTS so default runs stay reproducible."""
    if max_results is not None:
        return max(max_results, 0)
    env = os.environ.get("NUTEV_CROSSREF_MAX_RESULTS", "")
    return int(env) if env.isdigit() and int(env) > 0 else default


def _request_params(
    query: str,
    rows: int,
    *,
    filter_value: str = "",
    offset: int | None = None,
) -> dict:
    params: dict = {"query": query, "rows": rows, **_mailto()}
    if filter_value.strip():
        params["filter"] = filter_value.strip()
    if offset is not None:
        params["offset"] = offset
    return params


def search_crossref(
    query: str,
    rows: int = 18,
    max_results: int | None = None,
    filter_value: str = "",
) -> list[dict]:
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return []

    target = _resolve_max_results(rows, max_results)

    if target <= rows:
        data = _crossref_get(_request_params(query, rows, filter_value=filter_value))
        if not data:
            return []
        items = data.get("message", {}).get("items", []) or []
        return [_normalize_crossref_item(it, query) for it in items]

    collected: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while len(collected) < target:
        page = min(rows, target - len(collected))
        data = _crossref_get(
            _request_params(query, page, filter_value=filter_value, offset=offset)
        )
        if not data:
            break
        items = data.get("message", {}).get("items", []) or []
        if not items:
            break
        for it in items:
            key = str(it.get("DOI") or "") or str((it.get("title") or [""])[0] or "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            collected.append(_normalize_crossref_item(it, query))
            if len(collected) >= target:
                break
        if len(items) < page:
            break
        offset += page
    return collected
