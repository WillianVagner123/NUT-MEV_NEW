from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_PMID_RE = re.compile(r"^[0-9]{1,9}$")
_PMCID_RE = re.compile(r"^PMC[0-9]+$", re.I)
_SPACE_RE = re.compile(r"\s+")


def normalize_doi(value: Any) -> str:
    """Return a canonical DOI only when its syntax is plausible."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    lowered = raw.casefold()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lowered.startswith(prefix):
            raw = raw[len(prefix) :].strip()
            break
    raw = raw.rstrip(" .;,)]}")
    if not _DOI_RE.fullmatch(raw):
        return ""
    return raw.casefold()


def valid_doi(value: Any) -> bool:
    return bool(normalize_doi(value))


def normalize_pmid(value: Any) -> str:
    """Return a PMID only when the complete supplied value is valid."""

    raw = str(value or "").strip()
    return raw if raw and _PMID_RE.fullmatch(raw) else ""


def valid_pmid(value: Any) -> bool:
    return bool(normalize_pmid(value))


def normalize_pmcid(value: Any) -> str:
    raw = str(value or "").strip()
    return raw.upper() if raw and _PMCID_RE.fullmatch(raw) else ""


def valid_pmcid(value: Any) -> bool:
    return bool(normalize_pmcid(value))


def normalize_url(value: Any) -> str:
    """Normalize a traceable HTTP(S) URL; invalid schemes return blank."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except Exception:
        return ""
    if parts.scheme.casefold() not in {"http", "https"} or not parts.netloc:
        return ""
    host = parts.netloc.casefold().removeprefix("www.")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), host, path, parts.query, ""))


def normalize_title(value: Any) -> str:
    """Conservative exact-title fallback: Unicode normalize, casefold, collapse spaces."""

    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    return _SPACE_RE.sub(" ", text)


def valid_identifier_kind(row: dict[str, Any]) -> str:
    """Return the first valid primary identifier kind without inferring repairs."""

    if normalize_doi(row.get("doi") or row.get("doi_normalized")):
        return "doi"
    if normalize_pmid(row.get("pmid") or row.get("pmid_normalized")):
        return "pmid"
    if normalize_pmcid(row.get("pmcid")):
        return "pmcid"
    return ""


def has_valid_identifier(row: dict[str, Any]) -> bool:
    return bool(valid_identifier_kind(row))


def canonical_identity(row: dict[str, Any]) -> str:
    """Canonical cross-stage identity: DOI -> PMID -> HTTP(S) URL -> title."""

    doi = normalize_doi(row.get("doi") or row.get("doi_normalized"))
    if doi:
        return "doi:" + doi
    pmid = normalize_pmid(row.get("pmid") or row.get("pmid_normalized"))
    if pmid:
        return "pmid:" + pmid
    url = normalize_url(row.get("url") or row.get("url_normalized"))
    if url:
        return "url:" + url.casefold()
    title = normalize_title(row.get("title"))
    return "title:" + title if title else ""


def dedupe_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate with one identity rule and keep the richer descriptive record."""

    best: dict[str, dict[str, Any]] = {}
    unkeyed: list[dict[str, Any]] = []
    for row in rows:
        key = canonical_identity(row)
        if not key:
            unkeyed.append(dict(row))
            continue
        current = best.get(key)
        if current is None:
            best[key] = dict(row)
            continue
        old_text = str(
            current.get("abstract") or current.get("summary") or current.get("snippet") or ""
        )
        new_text = str(
            row.get("abstract") or row.get("summary") or row.get("snippet") or ""
        )
        if len(new_text) > len(old_text):
            best[key] = dict(row)
    return list(best.values()) + unkeyed
