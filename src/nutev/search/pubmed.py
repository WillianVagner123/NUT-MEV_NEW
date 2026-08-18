from __future__ import annotations

import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

from nutev.search.base import ProviderResult
from nutev.search.checkpoint import (
    checkpoint_path,
    load_checkpoint,
    query_hash,
    save_checkpoint,
)

DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
DOI_URL_RE = re.compile(r"https?://(?:dx\.)?doi\.org/", re.I)
PMCID_RE = re.compile(r"\bPMC\s*([0-9]+)\b", re.I)
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
RETRY_STATUSES = {429, 500, 502, 503, 504}
USER_AGENT = "NutEV-Reference-Engine/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"
DEFAULT_NCBI_TOOL = "nutev_reference_engine"


class PubMedUnavailable(RuntimeError):
    """Raised only after all PubMed request fallbacks fail."""


def _clean_doi(value: Any | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    raw = DOI_URL_RE.sub(" ", raw)
    raw = raw.replace("doi.org/", " ").replace("dx.doi.org/", " ")
    raw = raw.replace("DOI:", " ").replace("doi:", " ")
    match = DOI_RE.search(raw)
    if not match:
        return None
    return match.group(1).rstrip(" .;,)]}")


def _clean_pmcid(value: Any | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    match = PMCID_RE.search(raw)
    if match:
        return f"PMC{match.group(1)}"
    if raw.isdigit():
        return f"PMC{raw}"
    return raw.upper() if raw.lower().startswith("pmc") else raw


def _pick_article_id(item: dict[str, Any], *id_types: str) -> str | None:
    wanted = {id_type.lower() for id_type in id_types}
    for article_id in item.get("articleids", []) or []:
        if not isinstance(article_id, dict):
            continue
        if str(article_id.get("idtype", "")).lower() in wanted:
            value = article_id.get("value")
            if value:
                return str(value).strip()
    return None


def _extract_doi(item: dict[str, Any]) -> str | None:
    return _clean_doi(_pick_article_id(item, "doi")) or _clean_doi(
        item.get("elocationid")
    )


def _extract_pmcid(item: dict[str, Any]) -> str | None:
    return _clean_pmcid(_pick_article_id(item, "pmc", "pmcid"))


def _extract_year(*values: Any) -> str:
    for value in values:
        if not value:
            continue
        match = re.search(r"\b(19|20)\d{2}\b", str(value))
        if match:
            return match.group(0)
    return ""


def _extract_authors(item: dict[str, Any], limit: int = 12) -> str:
    names: list[str] = []
    for author in item.get("authors", []) or []:
        if isinstance(author, dict) and author.get("name"):
            names.append(str(author["name"]))
    if len(names) > limit:
        return "; ".join(names[:limit]) + f"; +{len(names) - limit} more"
    return "; ".join(names)


def _pick_pubmed_url(pmid: str, doi: str | None, pmcid: str | None) -> str:
    if pmcid:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    if doi:
        return f"https://doi.org/{doi}"
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def _ncbi_email() -> str | None:
    return os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL")


def _ncbi_params(params: dict[str, Any]) -> dict[str, Any]:
    out = dict(params)
    out["tool"] = os.environ.get("NCBI_TOOL", DEFAULT_NCBI_TOOL)
    email = _ncbi_email()
    api_key = os.environ.get("NCBI_API_KEY")
    if email:
        out["email"] = email
    if api_key:
        out["api_key"] = api_key
    return out


def _rate_limit_sleep() -> None:
    # NCBI: 3 req/s without API key, 10 req/s with key. Use a safety margin.
    time.sleep(0.13 if os.environ.get("NCBI_API_KEY") else 0.40)


def _request_json(
    endpoint: str,
    params: dict[str, Any],
    *,
    timeout: int | tuple[int, int] = (10, 60),
    max_attempts: int = 4,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    url = f"{EUTILS_BASE}/{endpoint}"
    params = _ncbi_params(params)
    last_error: Exception | None = None
    owns_session = session is None
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        }
    )
    try:
        for attempt in range(1, max_attempts + 1):
            for method in ("get", "post"):
                try:
                    _rate_limit_sleep()
                    if method == "get":
                        response = session.get(url, params=params, timeout=timeout)
                    else:
                        response = session.post(url, data=params, timeout=timeout)
                    if response.status_code in RETRY_STATUSES:
                        raise requests.HTTPError(
                            f"HTTP {response.status_code}", response=response
                        )
                    response.raise_for_status()
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise PubMedUnavailable(
                            f"Invalid JSON from PubMed {endpoint}"
                        ) from exc
                except (
                    requests.Timeout,
                    requests.ConnectionError,
                    requests.HTTPError,
                    PubMedUnavailable,
                ) as exc:
                    last_error = exc
                    continue
            time.sleep(min(2**attempt, 8))
    finally:
        if owns_session:
            session.close()
    raise PubMedUnavailable(
        f"PubMed E-utilities request failed after retries: {last_error}"
    )


def _request_text(
    endpoint: str,
    params: dict[str, Any],
    *,
    timeout: int | tuple[int, int] = (10, 60),
    max_attempts: int = 4,
    session: requests.Session | None = None,
) -> str:
    url = f"{EUTILS_BASE}/{endpoint}"
    params = _ncbi_params(params)
    last_error: Exception | None = None
    owns_session = session is None
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/xml,text/xml,text/plain,*/*",
        }
    )
    try:
        for attempt in range(1, max_attempts + 1):
            for method in ("get", "post"):
                try:
                    _rate_limit_sleep()
                    response = (
                        session.get(url, params=params, timeout=timeout)
                        if method == "get"
                        else session.post(url, data=params, timeout=timeout)
                    )
                    if response.status_code in RETRY_STATUSES:
                        raise requests.HTTPError(
                            f"HTTP {response.status_code}", response=response
                        )
                    response.raise_for_status()
                    return response.text
                except (
                    requests.Timeout,
                    requests.ConnectionError,
                    requests.HTTPError,
                ) as exc:
                    last_error = exc
                    continue
            time.sleep(min(2**attempt, 8))
    finally:
        if owns_session:
            session.close()
    raise PubMedUnavailable(
        f"PubMed E-utilities text request failed after retries: {last_error}"
    )


def _abstracts_from_efetch_xml(xml_text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise PubMedUnavailable("Invalid XML from PubMed efetch") from exc
    abstracts: dict[str, str] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = ""
        pmid_node = article.find(".//PMID")
        if pmid_node is not None and pmid_node.text:
            pmid = pmid_node.text.strip()
        if not pmid:
            continue
        parts = [
            "".join(node.itertext()).strip()
            for node in article.findall(".//Abstract/AbstractText")
        ]
        text = "\n".join(part for part in parts if part)
        if text:
            abstracts[pmid] = text
    return abstracts


def _normalize_summary(item: dict[str, Any], pmid: str, query: str) -> dict[str, Any]:
    doi = _extract_doi(item)
    pmcid = _extract_pmcid(item)
    pubdate = item.get("pubdate") or item.get("epubdate") or ""
    title = item.get("title") or ""
    return {
        "source": "pubmed",
        "source_provider": "pubmed",
        "title": title,
        "abstract": item.get("abstract") or "",
        "snippet": item.get("summary") or item.get("abstract") or title,
        "summary": item.get("summary") or item.get("abstract") or "",
        "doi": doi or "",
        "pmid": str(pmid),
        "pmcid": pmcid or "",
        "url": _pick_pubmed_url(str(pmid), doi, pmcid),
        "journal": item.get("fulljournalname") or item.get("source") or "",
        "year": _extract_year(item.get("pubdate"), item.get("epubdate"), pubdate),
        "publication_date": pubdate,
        "article_type": "; ".join(item.get("pubtype") or []),
        "authors": _extract_authors(item),
        "metadata_status": "pubmed_esummary",
        "query": query,
        "provider_query": query,
    }


class PubMedClient:
    name = "pubmed"

    def search(
        self,
        query: str,
        *,
        limit: int,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        context = context or {}
        workstream = str(context.get("workstream") or "default")
        checkpoint_dir = Path(
            context.get("checkpoint_dir") or Path("07_logs") / "checkpoints"
        )
        resume = bool(context.get("resume", False))
        batch_size = int(
            context.get("batch_size")
            or os.environ.get("NUTEV_PUBMED_BATCH_SIZE")
            or 200
        )
        logger = context.get("logger") or logging.getLogger(__name__)
        cp_path = checkpoint_path(checkpoint_dir, self.name, workstream, query)
        qh = query_hash(self.name, workstream, query)

        if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
            return ProviderResult(
                self.name,
                query,
                status="skipped",
                error="network_disabled",
                checkpoint_path=str(cp_path),
            )
        if os.environ.get("NUTEV_SKIP_PUBMED") == "1":
            return ProviderResult(
                self.name,
                query,
                status="skipped",
                error="NUTEV_SKIP_PUBMED=1",
                checkpoint_path=str(cp_path),
            )
        if not _ncbi_email():
            logger.warning(
                "NCBI_EMAIL/ENTREZ_EMAIL ausente; usando rate limit conservador para PubMed"
            )

        rows: list[dict[str, Any]] = []
        ids_collected: list[str] = []
        retstart = 0
        count: int | None = None
        webenv = ""
        query_key = ""
        loaded = load_checkpoint(cp_path) if resume else None
        if loaded and loaded.get("status") == "completed":
            cached_rows = loaded.get("rows") or []
            return ProviderResult(
                self.name,
                query,
                rows=cached_rows[:limit],
                total_found=loaded.get("count"),
                total_returned=min(len(cached_rows), limit),
                status="completed",
                checkpoint_path=str(cp_path),
                meta={"resume_used": True, "query_hash": qh},
            )
        if loaded:
            retstart = int(loaded.get("retstart_done") or 0)
            rows = list(loaded.get("rows") or [])
            ids_collected = [str(x) for x in loaded.get("ids") or []]
            count = loaded.get("count")
            webenv = str(loaded.get("webenv") or "")
            query_key = str(loaded.get("query_key") or "")

        try:
            if not webenv or not query_key or count is None:
                search_payload = _request_json(
                    "esearch.fcgi",
                    {
                        "db": "pubmed",
                        "retmode": "json",
                        "term": query,
                        "retmax": 0,
                        "usehistory": "y",
                    },
                )
                result = search_payload.get("esearchresult", {})
                count = int(result.get("count") or 0)
                webenv = str(result.get("webenv") or result.get("WebEnv") or "")
                query_key = str(
                    result.get("querykey") or result.get("query_key") or ""
                )
                if count and (not webenv or not query_key):
                    raise PubMedUnavailable(
                        "PubMed esearch did not return WebEnv/query_key"
                    )
                save_checkpoint(
                    cp_path,
                    {
                        "provider": self.name,
                        "workstream": workstream,
                        "query_hash": qh,
                        "query": query,
                        "count": count,
                        "webenv": webenv,
                        "query_key": query_key,
                        "retstart_done": retstart,
                        "retmax": batch_size,
                        "ids_collected": len(ids_collected),
                        "rows_collected": len(rows),
                        "ids": ids_collected,
                        "rows": rows,
                        "status": "partial",
                    },
                )
            target = min(limit, count or 0)
            while retstart < target:
                retmax = min(batch_size, target - retstart)
                search_payload = _request_json(
                    "esearch.fcgi",
                    {
                        "db": "pubmed",
                        "retmode": "json",
                        "term": query,
                        "retstart": retstart,
                        "retmax": retmax,
                        "usehistory": "y",
                        "WebEnv": webenv,
                        "query_key": query_key,
                    },
                )
                batch_ids = [
                    str(x)
                    for x in search_payload.get("esearchresult", {}).get(
                        "idlist", []
                    )
                ]
                existing_ids = set(ids_collected)
                batch_ids = [pmid for pmid in batch_ids if pmid not in existing_ids]
                if batch_ids:
                    summary_payload = _request_json(
                        "esummary.fcgi",
                        {
                            "db": "pubmed",
                            "retmode": "json",
                            "id": ",".join(batch_ids),
                        },
                    )
                    payload = summary_payload.get("result", {})
                    batch_rows: list[dict[str, Any]] = []
                    for pmid in batch_ids:
                        item = payload.get(pmid, {})
                        if item:
                            batch_rows.append(_normalize_summary(item, pmid, query))
                    if (
                        os.environ.get("NUTEV_PUBMED_FETCH_ABSTRACTS") == "1"
                        and batch_rows
                    ):
                        try:
                            xml_text = _request_text(
                                "efetch.fcgi",
                                {
                                    "db": "pubmed",
                                    "retmode": "xml",
                                    "id": ",".join(batch_ids),
                                },
                            )
                            abstracts = _abstracts_from_efetch_xml(xml_text)
                            for row in batch_rows:
                                abstract = abstracts.get(
                                    str(row.get("pmid") or ""), ""
                                )
                                if abstract and len(abstract) > len(
                                    str(row.get("abstract") or "")
                                ):
                                    row["abstract"] = abstract
                                    row["summary"] = abstract
                                    row["snippet"] = abstract[:500]
                                    row["metadata_status"] = "pubmed_efetch"
                        except Exception as exc:
                            logger.warning(
                                "PubMed efetch abstracts falhou query=%s erro=%s",
                                query,
                                exc,
                            )
                    rows.extend(batch_rows)
                    ids_collected.extend(batch_ids)
                retstart += retmax
                save_checkpoint(
                    cp_path,
                    {
                        "provider": self.name,
                        "workstream": workstream,
                        "query_hash": qh,
                        "query": query,
                        "count": count,
                        "webenv": webenv,
                        "query_key": query_key,
                        "retstart_done": retstart,
                        "retmax": batch_size,
                        "ids_collected": len(ids_collected),
                        "rows_collected": len(rows),
                        "ids": ids_collected,
                        "rows": rows,
                        "status": "partial" if retstart < target else "completed",
                    },
                )
            return ProviderResult(
                self.name,
                query,
                rows=rows[:limit],
                total_found=count,
                total_returned=len(rows[:limit]),
                status="completed" if rows else "empty",
                checkpoint_path=str(cp_path),
                meta={"query_hash": qh, "resume_used": bool(loaded)},
            )
        except Exception as exc:
            status = "partial" if rows else "failed"
            save_checkpoint(
                cp_path,
                {
                    "provider": self.name,
                    "workstream": workstream,
                    "query_hash": qh,
                    "query": query,
                    "count": count,
                    "webenv": webenv,
                    "query_key": query_key,
                    "retstart_done": retstart,
                    "retmax": batch_size,
                    "ids_collected": len(ids_collected),
                    "rows_collected": len(rows),
                    "ids": ids_collected,
                    "rows": rows,
                    "status": status,
                    "error": str(exc),
                },
            )
            return ProviderResult(
                self.name,
                query,
                rows=rows[:limit],
                total_found=count,
                total_returned=len(rows[:limit]),
                status=status,
                error=str(exc),
                checkpoint_path=str(cp_path),
                meta={"query_hash": qh, "resume_used": bool(loaded)},
            )


def search_pubmed(
    query: str,
    retmax: int = 18,
    *,
    checkpoint_dir: str | Path | None = None,
    workstream: str = "default",
    resume: bool = False,
    logger: Any | None = None,
) -> list[dict]:
    result = PubMedClient().search(
        query,
        limit=retmax,
        context={
            "checkpoint_dir": checkpoint_dir or Path("07_logs") / "checkpoints",
            "workstream": workstream,
            "resume": resume,
            "logger": logger,
        },
    )
    return result.rows
