"""Canonical article-level identity normalization and deduplication helpers.

Pure functions collapse duplicate records by a canonical key (DOI → PMID →
PMCID → normalized URL → title+year → row hash) and merge the survivors,
preferring stronger full-text URLs and unioning provider provenance.
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
            text = text[len(prefix) :]
    return text.strip().strip("/")


def normalize_url(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text.strip().rstrip("/").lower().removeprefix("www.")

    netloc = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme.lower() == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if parsed.scheme.lower() == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path.rstrip("/") or "/"
    return f"{netloc}{path}".rstrip("/")


def normalize_title(value: object) -> str:
    text = _WHITESPACE_RE.sub(" ", as_text(value).lower()).strip()
    return _NON_ALNUM_RE.sub(" ", text).strip()


def normalize_year(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    try:
        year = int(float(text))
    except Exception:
        return ""
    return str(year)


def hash_fallback(row: dict) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]  # noqa: S324


def canonical_article_key(row: dict) -> tuple[str, str]:
    doi = normalize_doi(row.get("doi"))
    if doi:
        return "doi", doi

    pmid = as_text(row.get("pmid")).lower()
    if pmid:
        return "pmid", pmid

    pmcid = as_text(row.get("pmcid")).lower()
    if pmcid:
        return "pmcid", pmcid

    url = normalize_url(
        row.get("final_url") or row.get("resolved_url") or row.get("original_url") or row.get("url")
    )
    if url:
        return "url", url

    title = normalize_title(row.get("title"))
    year = normalize_year(row.get("year"))
    if title and year:
        return "title_year", f"{title}|{year}"

    return "row_hash", hash_fallback(row)


def merge_article_rows(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value in (None, "", [], {}):
            continue
        if key in {"abstract", "snippet", "summary"} and len(str(value)) > len(str(merged.get(key) or "")):
            merged[key] = value
        elif not merged.get(key):
            merged[key] = value
    # Keep the stronger URL for capture. PMC and direct full-text URLs tend to
    # produce better artifacts than DOI landing pages.
    existing_url = str(merged.get("url") or "")
    incoming_url = str(incoming.get("url") or "")
    if incoming_url and (
        not existing_url
        or "pmc.ncbi.nlm.nih.gov" in incoming_url
        or incoming_url.lower().endswith(".pdf")
    ):
        merged["url"] = incoming_url
    providers = []
    for value in (merged.get("matched_providers"), merged.get("source_provider"), merged.get("source"), incoming.get("matched_providers"), incoming.get("source_provider"), incoming.get("source")):
        for part in str(value or "").split("|"):
            part = part.strip()
            if part and part not in providers:
                providers.append(part)
    merged["matched_providers"] = "|".join(providers)
    merged["source"] = merged.get("source") or incoming.get("source")
    return merged


def dedup_rows(rows: list[dict]) -> list[dict]:
    by_key: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for r in rows:
        key = canonical_article_key(r)
        if key not in by_key:
            r = dict(r)
            provider = r.get("source_provider") or r.get("source")
            if provider and not r.get("matched_providers"):
                r["matched_providers"] = str(provider)
            by_key[key] = r
            order.append(key)
        else:
            by_key[key] = merge_article_rows(by_key[key], r)
    return [by_key[key] for key in order]
