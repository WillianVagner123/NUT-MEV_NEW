"""Explicit status-aware discovery adapters for NutEV scientific audit/search flows.

Legacy provider helpers return lists for backwards compatibility and may collapse a
remote failure into an empty list. These adapters expose the Reference Engine
``ProviderResult`` contract so scientific audit code can distinguish:

- ``empty``: provider responded successfully with zero hits;
- ``failed``: no trustworthy result could be obtained;
- ``partial``: some results were obtained before a later request failed;
- ``skipped``: execution was intentionally disabled;
- ``completed``: bounded request completed successfully.

They are discovery adapters only. Their rows still have to pass the ordinary NutEV
normalization, traceability, deduplication, ranking/audit and CORE pipeline.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from nutev.search.base import ProviderResult
from nutev.search import crossref as crossref_mod
from nutev.search import doaj as doaj_mod
from nutev.search import europepmc as europepmc_mod
from nutev.search import openalex as openalex_mod
from nutev.search import semantic_scholar as semantic_scholar_mod


def _positive_limit(limit: int) -> int:
    value = int(limit)
    if value < 1:
        raise ValueError("provider search limit must be positive")
    return value


def _skip_reason(provider_env: str | None = None) -> str | None:
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return "network_disabled"
    if provider_env and os.environ.get(provider_env) == "1":
        return f"{provider_env}=1"
    return None


def _finish(
    provider: str,
    query: str,
    rows: list[dict[str, Any]],
    *,
    target: int,
    total_found: int | None,
    failed: bool,
    exhausted: bool,
    meta: dict[str, Any] | None = None,
) -> ProviderResult:
    if failed:
        status = "partial" if rows else "failed"
        error = (
            "provider_request_failed_after_partial_results"
            if rows
            else "provider_request_failed"
        )
    else:
        status = "completed"
        error = None

    return ProviderResult(
        provider=provider,
        query=query,
        rows=rows[:target],
        total_found=total_found,
        total_returned=min(len(rows), target),
        status=status,
        error=error,
        meta={
            "status_contract": "explicit_provider_result_v1",
            "target": target,
            "provider_exhausted": exhausted,
            **(meta or {}),
        },
    )


class EuropePMCStatusClient:
    name = "europepmc"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        target = _positive_limit(limit)
        skip = _skip_reason("NUTEV_SKIP_EUROPEPMC")
        if skip:
            return ProviderResult(self.name, query, status="skipped", error=skip)

        page_size = min(100, target)
        cursor = "*"
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_found: int | None = None
        failed = False
        exhausted = False

        while len(rows) < target:
            data = europepmc_mod._europepmc_get(
                {
                    "query": query,
                    "format": "json",
                    "pageSize": min(page_size, target - len(rows)),
                    "cursorMark": cursor,
                }
            )
            if data is None:
                failed = True
                break
            if total_found is None:
                raw_total = data.get("hitCount")
                try:
                    total_found = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_found = None
            items = data.get("resultList", {}).get("result", []) or []
            if not items:
                exhausted = True
                break
            for item in items:
                key = str(
                    item.get("id")
                    or item.get("doi")
                    or item.get("pmid")
                    or item.get("title")
                    or ""
                )
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                row = europepmc_mod._normalize_result(item)
                row["query"] = query
                row["provider_query"] = query
                rows.append(row)
                if len(rows) >= target:
                    break
            next_cursor = data.get("nextCursorMark")
            if len(rows) >= target:
                break
            if not next_cursor or next_cursor == cursor:
                exhausted = True
                break
            cursor = str(next_cursor)

        if total_found is None and not failed and exhausted and not rows:
            total_found = 0
        return _finish(
            self.name,
            query,
            rows,
            target=target,
            total_found=total_found,
            failed=failed,
            exhausted=exhausted,
        )


class OpenAlexStatusClient:
    name = "openalex"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        target = _positive_limit(limit)
        skip = _skip_reason("NUTEV_SKIP_OPENALEX")
        if skip:
            return ProviderResult(self.name, query, status="skipped", error=skip)

        page_size = min(200, target)
        cursor = "*"
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_found: int | None = None
        failed = False
        exhausted = False

        while len(rows) < target:
            data = openalex_mod._openalex_get(
                openalex_mod._request_params(
                    query,
                    min(page_size, target - len(rows)),
                    cursor=cursor,
                )
            )
            if data is None:
                failed = True
                break
            meta = data.get("meta") or {}
            if total_found is None:
                try:
                    raw_total = meta.get("count")
                    total_found = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_found = None
            items = data.get("results", []) or []
            if not items:
                exhausted = True
                break
            for item in items:
                key = str(
                    item.get("id")
                    or item.get("doi")
                    or item.get("display_name")
                    or ""
                )
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                rows.append(openalex_mod._normalize_openalex_item(item, query))
                if len(rows) >= target:
                    break
            next_cursor = meta.get("next_cursor")
            if len(rows) >= target:
                break
            if not next_cursor or next_cursor == cursor:
                exhausted = True
                break
            cursor = str(next_cursor)

        if total_found is None and not failed and exhausted and not rows:
            total_found = 0
        return _finish(
            self.name,
            query,
            rows,
            target=target,
            total_found=total_found,
            failed=failed,
            exhausted=exhausted,
        )


class CrossrefStatusClient:
    name = "crossref"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        target = _positive_limit(limit)
        skip = _skip_reason("NUTEV_SKIP_CROSSREF")
        if skip:
            return ProviderResult(self.name, query, status="skipped", error=skip)

        page_size = min(100, target)
        offset = 0
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_found: int | None = None
        failed = False
        exhausted = False

        while len(rows) < target:
            requested = min(page_size, target - len(rows))
            data = crossref_mod._crossref_get(
                crossref_mod._request_params(
                    query,
                    requested,
                    offset=offset,
                )
            )
            if data is None:
                failed = True
                break
            message = data.get("message") or {}
            if total_found is None:
                try:
                    raw_total = message.get("total-results")
                    total_found = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_found = None
            items = message.get("items", []) or []
            if not items:
                exhausted = True
                break
            for item in items:
                title_value = item.get("title") or [""]
                title = title_value[0] if isinstance(title_value, list) and title_value else ""
                key = str(item.get("DOI") or title or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                rows.append(crossref_mod._normalize_crossref_item(item, query))
                if len(rows) >= target:
                    break
            if len(rows) >= target:
                break
            if len(items) < requested:
                exhausted = True
                break
            offset += requested

        if total_found is None and not failed and exhausted and not rows:
            total_found = 0
        return _finish(
            self.name,
            query,
            rows,
            target=target,
            total_found=total_found,
            failed=failed,
            exhausted=exhausted,
        )


class DOAJStatusClient:
    name = "doaj"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        target = _positive_limit(limit)
        skip = _skip_reason("NUTEV_SKIP_DOAJ")
        if skip:
            return ProviderResult(self.name, query, status="skipped", error=skip)

        page_size = min(100, target)
        page = 1
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_found: int | None = None
        failed = False
        exhausted = False

        while len(rows) < target:
            requested = min(page_size, target - len(rows))
            data = doaj_mod._doaj_get(query, page, requested)
            if data is None:
                failed = True
                break
            if total_found is None:
                try:
                    raw_total = data.get("total")
                    total_found = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_found = None
            items = data.get("results", []) or []
            if not items:
                exhausted = True
                break
            for item in items:
                row = doaj_mod._normalize_doaj_item(item, query)
                key = str(row.get("doi") or row.get("title") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                rows.append(row)
                if len(rows) >= target:
                    break
            if len(rows) >= target:
                break
            if len(items) < requested:
                exhausted = True
                break
            page += 1

        if total_found is None and not failed and exhausted and not rows:
            total_found = 0
        return _finish(
            self.name,
            query,
            rows,
            target=target,
            total_found=total_found,
            failed=failed,
            exhausted=exhausted,
        )


class SemanticScholarStatusClient:
    name = "semantic_scholar"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        target = _positive_limit(limit)
        skip = _skip_reason("NUTEV_SKIP_SEMANTIC_SCHOLAR")
        if skip:
            return ProviderResult(self.name, query, status="skipped", error=skip)

        page_size = min(100, target)
        offset = 0
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_found: int | None = None
        failed = False
        exhausted = False

        while len(rows) < target:
            requested = min(page_size, target - len(rows))
            data = semantic_scholar_mod._s2_get(query, requested, offset)
            if data is None:
                failed = True
                break
            if total_found is None:
                try:
                    raw_total = data.get("total")
                    total_found = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_found = None
            items = data.get("data", []) or []
            if not items:
                exhausted = True
                break
            for item in items:
                row = semantic_scholar_mod._normalize_paper(item, query)
                key = str(row.get("doi") or row.get("title") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                rows.append(row)
                if len(rows) >= target:
                    break
            if len(rows) >= target:
                break
            if data.get("next") is None or len(items) < requested:
                exhausted = True
                break
            offset += requested

        if total_found is None and not failed and exhausted and not rows:
            total_found = 0
        return _finish(
            self.name,
            query,
            rows,
            target=target,
            total_found=total_found,
            failed=failed,
            exhausted=exhausted,
        )


STATUS_AWARE_DISCOVERY_CLIENTS: dict[str, Callable[[], Any]] = {
    "europepmc": EuropePMCStatusClient,
    "openalex": OpenAlexStatusClient,
    "crossref": CrossrefStatusClient,
    "doaj": DOAJStatusClient,
    "semantic_scholar": SemanticScholarStatusClient,
}


def get_status_aware_discovery_client(provider: str) -> Any | None:
    factory = STATUS_AWARE_DISCOVERY_CLIENTS.get(str(provider).strip().lower())
    return factory() if factory else None
