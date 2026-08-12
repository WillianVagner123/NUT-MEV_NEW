"""Canonical article-level identity normalization and deduplication helpers.

Pure functions collapse duplicate records by a canonical key (DOI → PMID → PMCID
→ normalized URL → title+year → row hash) and merge survivors while preserving
provider provenance and preferring stronger full-text locations.

These helpers are independent of any historical workstream pipeline and are used
as reusable analysis primitives by current corpus/review workflows and tests.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_doi(value: object) -> str:
    text = as_text(value).lower()
    if not text:
        return ""
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.rstrip("/")


def normalize_url(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    try:
        parsed = urlsplit(text if "://" in text else f"https://{text}")
    except ValueError:
        return text.lower().rstrip("/")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parsed.port
    if port and not ((parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80)):
        host = f"{host}:{port}"
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/")
    return f"{host}{path}" if path else host


def normalize_title(value: object) -> str:
    text = as_text(value).casefold()
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_year(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    match = re.search(r"\b(18|19|20|21)\d{2}\b", text)
    return match.group(0) if match else ""


def hash_fallback(row: dict) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_article_key(row: dict) -> tuple[str, str]:
    doi = normalize_doi(row.get("doi"))
    if doi:
        return "doi", doi
    pmid = as_text(row.get("pmid"))
    if pmid:
        return "pmid", pmid
    pmcid = as_text(row.get("pmcid")).upper()
    if pmcid:
        return "pmcid", pmcid
    url = normalize_url(row.get("url"))
    if url:
        return "url", url
    title = normalize_title(row.get("title"))
    year = normalize_year(row.get("year") or row.get("publication_year") or row.get("publication_date"))
    if title:
        return "title_year", f"{title}|{year}"
    return "row_hash", hash_fallback(row)


def _provider_values(row: dict) -> list[str]:
    values: list[str] = []
    for key in ("matched_providers", "source_provider", "source"):
        raw = as_text(row.get(key))
        if not raw:
            continue
        for item in raw.split("|"):
            item = item.strip()
            if item and item not in values:
                values.append(item)
    return values


def _url_rank(value: object) -> tuple[int, int]:
    url = as_text(value).lower()
    if not url:
        return 0, 0
    score = 1
    if "pmc.ncbi.nlm.nih.gov" in url or "ncbi.nlm.nih.gov/pmc" in url:
        score = 6
    elif url.endswith(".pdf") or ".pdf?" in url:
        score = 5
    elif "doi.org/" not in url:
        score = 3
    return score, len(url)


def merge_article_rows(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value in (None, "", [], {}):
            continue
        current = merged.get(key)
        if current in (None, "", [], {}):
            merged[key] = value
            continue
        if key in {"abstract", "snippet", "extracted_text"} and len(as_text(value)) > len(as_text(current)):
            merged[key] = value
        elif key in {"url", "oa_url", "pdf_url", "fulltext_url"} and _url_rank(value) > _url_rank(current):
            merged[key] = value
    providers: list[str] = []
    for row in (existing, incoming):
        for provider in _provider_values(row):
            if provider not in providers:
                providers.append(provider)
    if providers:
        merged["matched_providers"] = "|".join(providers)
    return merged


def dedup_rows(rows: list[dict]) -> list[dict]:
    order: list[tuple[str, str]] = []
    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = canonical_article_key(row)
        if key not in grouped:
            grouped[key] = dict(row)
            order.append(key)
        else:
            grouped[key] = merge_article_rows(grouped[key], row)
    return [grouped[key] for key in order]
