from __future__ import annotations

from typing import Any

from nutev.search.pubmed import _request_json


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_messages(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, list[str]] = {}
    for key, raw in value.items():
        items = _as_list(raw)
        if items:
            output[str(key)] = items
    return output


def parse_pubmed_search_details(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("PubMed Search Details payload inválido")
    result = payload.get("esearchresult")
    if not isinstance(result, dict):
        raise ValueError("PubMed Search Details sem esearchresult")

    count_raw = result.get("count")
    try:
        count = int(count_raw) if count_raw is not None else None
    except (TypeError, ValueError):
        count = None

    warnings = _normalize_messages(result.get("warninglist"))
    errors = _normalize_messages(result.get("errorlist"))
    query_translation = str(result.get("querytranslation") or "").strip()

    return {
        "source": "pubmed_esearch",
        "count": count,
        "query_translation": query_translation,
        "warninglist": warnings,
        "errorlist": errors,
        "warnings_present": bool(warnings),
        "errors_present": bool(errors),
        "search_details_complete": bool(query_translation or count == 0),
    }


def collect_pubmed_search_details(query: str) -> dict[str, Any]:
    payload = _request_json(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "retmode": "json",
            "term": query,
            "retmax": 0,
            "usehistory": "n",
        },
    )
    return parse_pubmed_search_details(payload)
