"""Public/open-access full-text candidate resolution for selective deepening.

The resolver only discovers public URLs. It does not bypass authentication,
paywalls, robots protections, or license controls. Returned URLs are candidates;
the enrichment layer remains responsible for retrieval, extraction, provenance,
and honest failure states.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping

import requests

from nutev.reference_identity import normalize_doi, normalize_pmid


EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUROPE_PMC_FULL_TEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
OPENALEX_WORKS = "https://api.openalex.org/works"
DEFAULT_TIMEOUT_SECONDS = 12

Requester = Callable[..., Any]


def _headers() -> dict[str, str]:
    user_agent = os.environ.get(
        "NUTEV_HTTP_USER_AGENT",
        "NutEV-Evidence-Engine/1.0 (+https://nutev.mindsperformance.com.br/)",
    ).strip()
    return {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }


def _json_get(
    url: str,
    *,
    params: Mapping[str, Any] | None,
    requester: Requester,
    timeout: int,
) -> dict[str, Any] | None:
    try:
        response = requester(
            url,
            params=dict(params or {}),
            headers=_headers(),
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()
        value = response.json()
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return None
    return value if isinstance(value, dict) else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().casefold() in {
        "y",
        "yes",
        "true",
        "1",
        "open",
        "open access",
        "oa",
        "free",
    }


def _candidate(
    url: str | None,
    *,
    route: str,
    source: str,
    scope: str,
    media_type: str | None = None,
    license_value: str | None = None,
    version: str | None = None,
) -> dict[str, Any] | None:
    normalized = str(url or "").strip()
    if not normalized.startswith(("http://", "https://")):
        return None
    payload: dict[str, Any] = {
        "url": normalized,
        "scope": scope,
        "resolver_route": route,
        "resolver_source": source,
    }
    if media_type:
        payload["media_type"] = media_type
    if license_value:
        payload["license"] = license_value
    if version:
        payload["version"] = version
    return payload


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for candidate in candidates:
        url = str(candidate.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        output.append(candidate)
    return output


def _recorded_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pmcid = str(row.get("pmcid") or row.get("pmc_id") or "").strip()
    if pmcid:
        normalized = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
        candidates.append(
            _candidate(
                EUROPE_PMC_FULL_TEXT.format(pmcid=normalized),
                route="recorded_pmcid_fulltext_xml",
                source="recorded_metadata",
                scope="full_text",
                media_type="application/xml",
            )
            or {}
        )

    field_specs = (
        ("pdf_url", "recorded_pdf_url", "application/pdf"),
        ("full_text_url", "recorded_full_text_url", None),
        ("open_access_url", "recorded_open_access_url", None),
        ("oa_url", "recorded_oa_url", None),
    )
    for field, route, media_type in field_specs:
        value = str(row.get(field) or "").strip()
        candidate = _candidate(
            value,
            route=route,
            source="recorded_metadata",
            scope="full_text",
            media_type=media_type,
        )
        if candidate:
            candidates.append(candidate)
    return [item for item in candidates if item]


def _europe_pmc_candidates(
    row: Mapping[str, Any],
    *,
    requester: Requester,
    timeout: int,
) -> list[dict[str, Any]]:
    doi = normalize_doi(row.get("doi") or row.get("doi_normalized"))
    pmid = normalize_pmid(row.get("pmid") or row.get("pmid_normalized"))
    if pmid:
        query = f"EXT_ID:{pmid} AND SRC:MED"
    elif doi:
        query = f'DOI:"{doi}"'
    else:
        return []

    payload = _json_get(
        EUROPE_PMC_SEARCH,
        params={
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 3,
        },
        requester=requester,
        timeout=timeout,
    )
    if not payload:
        return []
    results = ((payload.get("resultList") or {}).get("result") or [])
    if not isinstance(results, list):
        return []

    selected: dict[str, Any] | None = None
    for result in results:
        if not isinstance(result, dict):
            continue
        result_doi = normalize_doi(result.get("doi"))
        result_pmid = normalize_pmid(result.get("pmid") or result.get("id"))
        if pmid and result_pmid == pmid:
            selected = result
            break
        if doi and result_doi == doi:
            selected = result
            break
    if selected is None:
        selected = next((item for item in results if isinstance(item, dict)), None)
    if selected is None:
        return []

    candidates: list[dict[str, Any]] = []
    pmcid = str(selected.get("pmcid") or "").strip()
    if pmcid:
        normalized = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
        candidate = _candidate(
            EUROPE_PMC_FULL_TEXT.format(pmcid=normalized),
            route="europe_pmc_fulltext_xml",
            source="europe_pmc",
            scope="full_text",
            media_type="application/xml",
        )
        if candidate:
            candidates.append(candidate)

    is_open = _truthy(selected.get("isOpenAccess"))
    full_text_urls = ((selected.get("fullTextUrlList") or {}).get("fullTextUrl") or [])
    if isinstance(full_text_urls, dict):
        full_text_urls = [full_text_urls]
    if isinstance(full_text_urls, list):
        sortable: list[tuple[int, dict[str, Any]]] = []
        for item in full_text_urls:
            if not isinstance(item, dict):
                continue
            style = str(item.get("documentStyle") or "").strip().casefold()
            availability = str(item.get("availability") or "").strip().casefold()
            availability_code = str(item.get("availabilityCode") or "").strip().casefold()
            open_link = is_open or "open" in availability or "free" in availability or availability_code in {
                "oa",
                "f",
                "free",
            }
            if not open_link or style in {"abs", "abstract", "doi"}:
                continue
            score = 0 if "pdf" in style else 1 if "html" in style else 2
            sortable.append((score, item))
        for _, item in sorted(sortable, key=lambda pair: pair[0]):
            style = str(item.get("documentStyle") or "").strip().casefold()
            media_type = "application/pdf" if "pdf" in style else "text/html" if "html" in style else None
            candidate = _candidate(
                item.get("url"),
                route="europe_pmc_open_full_text_link",
                source="europe_pmc",
                scope="full_text",
                media_type=media_type,
            )
            if candidate:
                candidates.append(candidate)
    return candidates


def _openalex_candidates(
    row: Mapping[str, Any],
    *,
    requester: Requester,
    timeout: int,
) -> list[dict[str, Any]]:
    doi = normalize_doi(row.get("doi") or row.get("doi_normalized"))
    openalex_id = str(row.get("openalex_id") or "").strip()
    if openalex_id.startswith("https://openalex.org/"):
        work_id = openalex_id.rsplit("/", 1)[-1]
        url = f"{OPENALEX_WORKS}/{work_id}"
        params: dict[str, Any] = {}
    elif doi:
        url = OPENALEX_WORKS
        params = {"filter": f"doi:https://doi.org/{doi}", "per-page": 1}
    else:
        return []

    mailto = os.environ.get("NUTEV_OPENALEX_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto
    payload = _json_get(
        url,
        params=params,
        requester=requester,
        timeout=timeout,
    )
    if not payload:
        return []
    if isinstance(payload.get("results"), list):
        work = next((item for item in payload["results"] if isinstance(item, dict)), None)
    else:
        work = payload
    if not isinstance(work, dict):
        return []

    candidates: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    best = work.get("best_oa_location")
    if isinstance(best, dict):
        locations.append(best)
    for location in work.get("locations") or []:
        if isinstance(location, dict) and location not in locations:
            locations.append(location)

    sortable: list[tuple[int, dict[str, Any]]] = []
    for location in locations:
        if not _truthy(location.get("is_oa")):
            continue
        pdf_url = str(location.get("pdf_url") or "").strip()
        landing = str(location.get("landing_page_url") or "").strip()
        if pdf_url:
            sortable.append((0, {**location, "resolved_url": pdf_url, "resolved_media": "application/pdf"}))
        if landing:
            source = location.get("source") or {}
            source_type = str(source.get("type") or "").strip().casefold() if isinstance(source, dict) else ""
            landing_score = 1 if "pmc" in landing.casefold() else 3 if source_type == "repository" else 4
            sortable.append((landing_score, {**location, "resolved_url": landing, "resolved_media": None}))

    for _, location in sorted(sortable, key=lambda pair: pair[0]):
        resolved_url = str(location.get("resolved_url") or "").strip()
        media_type = location.get("resolved_media")
        source = location.get("source") or {}
        source_type = str(source.get("type") or "").strip().casefold() if isinstance(source, dict) else ""
        scope = (
            "full_text"
            if media_type == "application/pdf" or "pmc" in resolved_url.casefold()
            else "partial"
        )
        candidate = _candidate(
            resolved_url,
            route="openalex_best_oa_location" if location is best else "openalex_oa_location",
            source="openalex",
            scope=scope,
            media_type=media_type,
            license_value=str(location.get("license") or "").strip() or None,
            version=str(location.get("version") or "").strip() or None,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def _fallback_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("url", "url_normalized"):
        value = str(row.get(key) or "").strip()
        candidate = _candidate(
            value,
            route=f"recorded_{key}",
            source="recorded_metadata",
            scope="partial",
        )
        if candidate:
            candidates.append(candidate)

    doi = normalize_doi(row.get("doi") or row.get("doi_normalized"))
    if doi:
        candidate = _candidate(
            f"https://doi.org/{doi}",
            route="doi_landing_fallback",
            source="doi",
            scope="partial",
        )
        if candidate:
            candidates.append(candidate)
    pmid = normalize_pmid(row.get("pmid") or row.get("pmid_normalized"))
    if pmid:
        candidate = _candidate(
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            route="pubmed_landing_fallback",
            source="pubmed",
            scope="partial",
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def resolve_full_text_candidates(
    row: Mapping[str, Any],
    *,
    requester: Requester = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    include_network_resolvers: bool = True,
) -> list[dict[str, Any]]:
    """Return ordered public full-text/landing candidates with provenance.

    Order is intentionally conservative: recorded OA/full-text identifiers first,
    then Europe PMC, then OpenAlex OA locations, then ordinary recorded/DOI/PubMed
    landing pages as partial fallbacks.
    """

    candidates = _recorded_candidates(row)
    if include_network_resolvers:
        candidates.extend(
            _europe_pmc_candidates(row, requester=requester, timeout=timeout)
        )
        candidates.extend(
            _openalex_candidates(row, requester=requester, timeout=timeout)
        )
    candidates.extend(_fallback_candidates(row))
    return _dedupe(candidates)[:12]
