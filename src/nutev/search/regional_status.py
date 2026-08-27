"""Status-aware native regional discovery for LILACS/BVS and SciELO.

This promotes the existing native-search strategy from ``tools/run_latin_sources.py``
into the Reference Engine provider contract. The adapters query only the official
public search interfaces and retain response HTML as retrieval evidence when a
checkpoint directory is supplied.

A HTTP 200 page with no parsed candidates is *not* automatically a scientific zero.
It becomes ``empty`` only when the response contains an explicit no-results marker;
otherwise the run is ``failed`` with an interface/parser warning. Access-denied
responses are explicit failures and never fabricated coverage.
"""

from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from uuid import uuid4

import requests

from nutev.search.base import ProviderResult

USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"
_SPACE_RE = re.compile(r"\s+")
_NO_RESULT_MARKERS = (
    "nenhum resultado encontrado",
    "nenhum resultado foi encontrado",
    "no results found",
    "no result found",
    "no se encontraron resultados",
    "sin resultados",
    "0 resultados",
    "0 results",
)


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


class _AnchorParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._href = ""
        self._parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = _clean(dict(attrs).get("href"))
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return
        title = _clean(" ".join(self._parts))
        url = urljoin(self.base_url, self._href)
        if title and url:
            self.anchors.append((url, title))
        self._href = ""
        self._parts = []


def lilacs_search_url(query: str) -> str:
    params = [("lang", "pt"), ("q", query), ("filter[db_cluster][]", "LILACS")]
    return "https://pesquisa.bvsalud.org/portal/?" + urlencode(params)


def scielo_search_url(query: str) -> str:
    return "https://search.scielo.org/?" + urlencode(
        {"lang": "en", "q": f"subject:({query})"}
    )


def _candidate(
    provider: str,
    search_url: str,
    url: str,
    title: str,
    query: str,
) -> dict[str, Any] | None:
    parsed = urlparse(url)
    title = _clean(title)
    if len(title) < 20:
        return None
    if provider == "lilacs_bvs":
        if "bvsalud.org" not in parsed.netloc:
            return None
        if (
            "/resource/" not in parsed.path
            and "id=" not in parsed.query
            and "biblio-" not in url
        ):
            return None
        source_provider = "lilacs_bvs_native"
    elif provider == "scielo":
        if "scielo" not in parsed.netloc:
            return None
        if not any(
            token in url.lower()
            for token in ("article", "script=sci_arttext", "pid=", "doi.org")
        ):
            return None
        source_provider = "scielo_native"
    else:
        return None
    return {
        "source": source_provider,
        "source_provider": source_provider,
        "title": title,
        "abstract": "",
        "snippet": "",
        "doi": "",
        "pmid": "",
        "pmcid": "",
        "url": url,
        "query": query,
        "provider_query": query,
        "provider_search_url": search_url,
        "collection_type": "REFERENCE_COLLECTION",
        "metadata_status": "native_search_html_candidate",
    }


def _explicit_no_results(html: str) -> bool:
    text = _clean(re.sub(r"<[^>]+>", " ", html)).casefold()
    return any(marker in text for marker in _NO_RESULT_MARKERS)


def _checkpoint_raw_html(
    context: dict[str, Any] | None,
    provider: str,
    query: str,
    html: str,
) -> tuple[str | None, str]:
    digest = sha256(query.encode("utf-8")).hexdigest()[:16]
    html_sha = sha256(html.encode("utf-8")).hexdigest()
    context = context or {}
    checkpoint_dir_raw = context.get("checkpoint_dir")
    if not checkpoint_dir_raw:
        return None, html_sha
    path = Path(checkpoint_dir_raw) / "regional_html" / f"{provider}_{digest}.html"
    saved_sha = _atomic_text(path, html)
    return str(path), saved_sha


def _search_native(
    provider: str,
    query: str,
    *,
    limit: int,
    context: dict[str, Any] | None,
) -> ProviderResult:
    target = int(limit)
    if target < 1:
        raise ValueError("provider search limit must be positive")
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return ProviderResult(provider, query, status="skipped", error="network_disabled")
    skip_env = "NUTEV_SKIP_LILACS_BVS" if provider == "lilacs_bvs" else "NUTEV_SKIP_SCIELO"
    if os.environ.get(skip_env) == "1":
        return ProviderResult(provider, query, status="skipped", error=f"{skip_env}=1")

    search_url = lilacs_search_url(query) if provider == "lilacs_bvs" else scielo_search_url(query)
    try:
        response = requests.get(
            search_url,
            timeout=(10, 60),
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
            },
        )
    except requests.RequestException as exc:
        return ProviderResult(
            provider,
            query,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            meta={"search_url": search_url, "status_contract": "regional_native_html_v1"},
        )

    if response.status_code in {401, 403}:
        return ProviderResult(
            provider,
            query,
            status="failed",
            error=(
                f"HTTP {response.status_code}: native public search interface does not allow "
                "this automated request"
            ),
            meta={
                "search_url": search_url,
                "http_status": response.status_code,
                "availability": "unavailable_for_automated_request",
                "status_contract": "regional_native_html_v1",
            },
        )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        return ProviderResult(
            provider,
            query,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            meta={
                "search_url": search_url,
                "http_status": response.status_code,
                "status_contract": "regional_native_html_v1",
            },
        )

    html = response.text
    raw_path, raw_sha = _checkpoint_raw_html(context, provider, query, html)
    parser = _AnchorParser(search_url)
    try:
        parser.feed(html)
    except Exception as exc:
        return ProviderResult(
            provider,
            query,
            status="failed",
            error=f"html_parse_failure: {type(exc).__name__}: {exc}",
            meta={
                "search_url": search_url,
                "http_status": response.status_code,
                "raw_html_path": raw_path,
                "raw_html_sha256": raw_sha,
                "status_contract": "regional_native_html_v1",
            },
        )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url, title in parser.anchors:
        row = _candidate(provider, search_url, url, title, query)
        if row is None:
            continue
        key = str(row.get("url") or row.get("title") or "").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= target:
            break

    meta = {
        "search_url": search_url,
        "http_status": response.status_code,
        "raw_html_path": raw_path,
        "raw_html_sha256": raw_sha,
        "parsed_anchor_count": len(parser.anchors),
        "status_contract": "regional_native_html_v1",
        "bounded_limit": target,
    }
    if rows:
        return ProviderResult(
            provider,
            query,
            rows=rows,
            total_found=None,
            total_returned=len(rows),
            status="completed",
            meta=meta,
        )
    if _explicit_no_results(html):
        return ProviderResult(
            provider,
            query,
            rows=[],
            total_found=0,
            total_returned=0,
            status="completed",
            meta={**meta, "explicit_zero_marker": True},
        )
    return ProviderResult(
        provider,
        query,
        rows=[],
        total_found=None,
        total_returned=0,
        status="failed",
        error="native_html_no_candidates_unverified_zero",
        meta={
            **meta,
            "explicit_zero_marker": False,
            "parser_note": (
                "HTTP search response succeeded but no candidate anchors or explicit zero-result "
                "marker were verified; scientific zero is therefore not asserted."
            ),
        },
    )


class LilacsBVSStatusClient:
    name = "lilacs_bvs"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        return _search_native(
            self.name,
            query,
            limit=limit,
            context=context,
        )


class SciELOStatusClient:
    name = "scielo"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        return _search_native(
            self.name,
            query,
            limit=limit,
            context=context,
        )
