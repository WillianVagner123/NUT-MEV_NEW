"""Lawful open-access full-text resolver for NutEV documents.

Indexed-database retrieval is discovery/metadata. This module resolves an
open-access full-text location for a record in a conservative fallback order:

    (a) existing PMCID                     -> PMC free full text
    (b) provider-declared open-access URL  -> provider OA location
    (c) DOI -> Unpaywall                   -> best OA location/PDF
    (d) PMID -> E-utilities elink          -> PMCID -> PMC free full text
    (e) none                               -> paywall / institutional-access queue

It NEVER fabricates text and never bypasses a paywall. Provider URLs are trusted
as OA only when they are explicitly carried in an OA field (for example
``oa_url``/``pdf_url``) or the provider explicitly marks the record open access.
The actual download reuses the existing downloader; this module only returns a
resolved URL plus provenance. Network sessions are injected and results may be
cached by the caller.
"""
from __future__ import annotations

from typing import Any

_PMC_URL = "https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
_UNPAYWALL = "https://api.unpaywall.org/v2/{doi}?email={email}"
_ELINK = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    "?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _norm_pmcid(pmcid: str) -> str:
    pmcid = pmcid.strip().upper()
    if pmcid and not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    return pmcid


def _is_http_url(value: object) -> bool:
    url = _clean(value).lower()
    return url.startswith("https://") or url.startswith("http://")


def _is_truthy_oa(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _clean(value).casefold() in {"1", "true", "yes", "y", "open", "oa"}


def _explicit_provider_oa_url(record: dict) -> str:
    """Return only an OA URL explicitly declared by provider metadata.

    ``oa_url`` and ``pdf_url`` are explicit OA/full-text fields in current
    provider normalizers. A generic ``url`` is accepted only when the same
    record explicitly marks itself open access. This avoids treating an ordinary
    DOI/publisher landing page as lawful OA merely because it is reachable.
    """
    for field in ("oa_url", "pdf_url"):
        candidate = _clean(record.get(field))
        if candidate and _is_http_url(candidate):
            return candidate

    generic = _clean(record.get("url"))
    if generic and _is_http_url(generic) and _is_truthy_oa(record.get("is_open_access")):
        return generic
    return ""


def _unpaywall_pdf(doi: str, email: str, session: Any, timeout: float) -> str:
    try:
        resp = session.get(
            _UNPAYWALL.format(doi=doi.lower(), email=email),
            timeout=timeout,
        )
        if getattr(resp, "status_code", 0) != 200:
            return ""
        data = resp.json()
        if not data.get("is_oa"):
            return ""
        loc = data.get("best_oa_location") or {}
        return _clean(loc.get("url_for_pdf") or loc.get("url"))
    except Exception:
        return ""


def _pmcid_from_pmid(pmid: str, session: Any, timeout: float) -> str:
    """Resolve a PMID to a PMCID via E-utilities elink (PubMed -> PMC)."""
    try:
        resp = session.get(_ELINK.format(pmid=pmid), timeout=timeout)
        if getattr(resp, "status_code", 0) != 200:
            return ""
        data = resp.json()
        for linkset in data.get("linksets", []):
            for db in linkset.get("linksetdbs", []):
                if db.get("dbto") == "pmc":
                    for link in db.get("links", []):
                        return _norm_pmcid(str(link))
    except Exception:
        return ""
    return ""


def resolve_fulltext(
    record: dict,
    *,
    email: str | None = None,
    session: Any | None = None,
    cache: dict[str, dict] | None = None,
    timeout: float = 20.0,
) -> dict:
    """Return the best lawful open-access full-text location for a record.

    Result keys: ``fulltext_status`` (``fulltext_oa`` | ``paywall`` |
    ``needs_network``), ``retrieval_method`` (``existing_pmcid`` |
    ``provider_oa_url`` | ``unpaywall`` | ``pmc_elink`` | ``none``),
    ``fulltext_url`` and ``pmcid``. No download is performed here.
    """
    doi = _clean(record.get("doi"))
    pmid = _clean(record.get("pmid"))
    pmcid = _norm_pmcid(_clean(record.get("pmcid")))
    provider_oa_url = _explicit_provider_oa_url(record)

    cache_key = doi or pmid or pmcid or provider_oa_url
    if cache is not None and cache_key and cache_key in cache:
        return dict(cache[cache_key])

    def _finish(result: dict) -> dict:
        if cache is not None and cache_key:
            cache[cache_key] = dict(result)
        return result

    # (a) Existing PMCID is already a public PMC full-text route.
    if pmcid:
        return _finish(
            {
                "fulltext_status": "fulltext_oa",
                "retrieval_method": "existing_pmcid",
                "fulltext_url": _PMC_URL.format(pmcid=pmcid),
                "pmcid": pmcid,
            }
        )

    # (b) Reuse provider-declared OA metadata before making another resolver call.
    if provider_oa_url:
        return _finish(
            {
                "fulltext_status": "fulltext_oa",
                "retrieval_method": "provider_oa_url",
                "fulltext_url": provider_oa_url,
                "pmcid": "",
            }
        )

    # Network is required for the remaining resolver methods.
    if session is None:
        return {
            "fulltext_status": "needs_network",
            "retrieval_method": "none",
            "fulltext_url": "",
            "pmcid": "",
        }

    # (c) DOI -> Unpaywall.
    if doi and email:
        pdf = _unpaywall_pdf(doi, email, session, timeout)
        if pdf:
            return _finish(
                {
                    "fulltext_status": "fulltext_oa",
                    "retrieval_method": "unpaywall",
                    "fulltext_url": pdf,
                    "pmcid": "",
                }
            )

    # (d) PMID -> elink -> PMCID.
    if pmid:
        resolved = _pmcid_from_pmid(pmid, session, timeout)
        if resolved:
            return _finish(
                {
                    "fulltext_status": "fulltext_oa",
                    "retrieval_method": "pmc_elink",
                    "fulltext_url": _PMC_URL.format(pmcid=resolved),
                    "pmcid": resolved,
                }
            )

    # (e) No lawful OA route found -> paywall/institutional-access queue.
    return _finish(
        {
            "fulltext_status": "paywall",
            "retrieval_method": "none",
            "fulltext_url": "",
            "pmcid": "",
        }
    )


def resolve_many(
    records: list[dict],
    *,
    email: str | None = None,
    session: Any | None = None,
    timeout: float = 20.0,
) -> list[dict]:
    """Resolve a batch, sharing one cache. Returns records enriched in place."""
    cache: dict[str, dict] = {}
    for rec in records:
        rec.update(
            resolve_fulltext(
                rec,
                email=email,
                session=session,
                cache=cache,
                timeout=timeout,
            )
        )
    return records
