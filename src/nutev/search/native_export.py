"""Auditable ingestion for official native SciELO and LILACS/BVS exports.

SciELO and BVS interfaces can export search results as CSV/RIS. This module
imports those official artifacts without scraping HTML or pretending a Crossref
proxy is a native-platform search. The exact provider query and source export
SHA-256 travel with every result.
"""
from __future__ import annotations

import csv
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Iterable

from nutev.search.base import ProviderResult

NATIVE_EXPORT_PROVIDERS = {"scielo_native", "lilacs_bvs"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first(row: dict[str, Any], *keys: str) -> str:
    lowered = {str(key).strip().casefold(): value for key, value in row.items()}
    for key in keys:
        value = lowered.get(key.casefold())
        if value not in (None, ""):
            return _clean(value)
    return ""


def _year(value: object) -> str:
    match = re.search(r"\b(?:18|19|20|21)\d{2}\b", str(value or ""))
    return match.group(0) if match else ""


def _split_authors(value: object) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    parts = re.split(r"\s*;\s*|\s*\|\s*|\s+and\s+", raw, flags=re.IGNORECASE)
    return [_clean(part) for part in parts if _clean(part)]


def _normalize_csv_row(row: dict[str, Any], *, provider: str, query: str) -> dict[str, Any]:
    title = _first(row, "title", "titulo", "título", "ti", "document title")
    authors_raw = _first(row, "authors", "author", "autores", "autor", "au")
    abstract = _first(row, "abstract", "resumo", "resumen", "ab")
    language = _first(row, "language", "idioma", "la")
    doi = _first(row, "doi", "do")
    url = _first(row, "url", "link", "ur", "full text", "texto completo")
    journal = _first(
        row,
        "journal",
        "journal title",
        "source",
        "revista",
        "periodico",
        "periódico",
        "ta",
    )
    year = _year(_first(row, "year", "publication year", "ano", "fecha", "date", "py"))
    keywords = _first(row, "keywords", "keyword", "palavras-chave", "palabras clave", "kw")
    record_id = _first(row, "id", "pid", "record id", "identifier", "an")
    return {
        "source": provider,
        "source_provider": provider,
        "metadata_status": "native_official_export",
        "title": title,
        "authors": _split_authors(authors_raw),
        "abstract": abstract,
        "language": language,
        "language_original": language,
        "doi": doi,
        "url": url,
        "journal": journal,
        "year": year,
        "keywords": keywords,
        "provider_record_id": record_id,
        "query": query,
        "provider_query": query,
        "native_export_format": "CSV",
        "native_export_raw": {str(key): value for key, value in row.items()},
    }


def _ris_records(lines: Iterable[str]) -> list[dict[str, list[str]]]:
    records: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] = {}
    last_tag = ""
    for raw in lines:
        line = raw.rstrip("\r\n")
        match = re.match(r"^([A-Z0-9]{2})\s*-\s?(.*)$", line)
        if match:
            tag, value = match.group(1), match.group(2).strip()
            if tag == "TY" and current:
                records.append(current)
                current = {}
            current.setdefault(tag, []).append(value)
            last_tag = tag
            if tag == "ER":
                records.append(current)
                current = {}
                last_tag = ""
        elif line.strip() and last_tag and current.get(last_tag):
            current[last_tag][-1] = _clean(current[last_tag][-1] + " " + line.strip())
    if current:
        records.append(current)
    return records


def _ris_first(row: dict[str, list[str]], *tags: str) -> str:
    for tag in tags:
        values = row.get(tag) or []
        if values:
            return _clean(values[0])
    return ""


def _normalize_ris_row(row: dict[str, list[str]], *, provider: str, query: str) -> dict[str, Any]:
    authors = [_clean(value) for tag in ("AU", "A1") for value in (row.get(tag) or []) if _clean(value)]
    keywords = [_clean(value) for value in (row.get("KW") or []) if _clean(value)]
    language = _ris_first(row, "LA")
    return {
        "source": provider,
        "source_provider": provider,
        "metadata_status": "native_official_export",
        "title": _ris_first(row, "TI", "T1", "CT"),
        "authors": authors,
        "abstract": _ris_first(row, "AB", "N2"),
        "language": language,
        "language_original": language,
        "doi": _ris_first(row, "DO"),
        "url": _ris_first(row, "UR", "L1", "L2"),
        "journal": _ris_first(row, "JO", "JF", "T2", "JA"),
        "year": _year(_ris_first(row, "PY", "Y1", "DA")),
        "keywords": "; ".join(keywords),
        "provider_record_id": _ris_first(row, "AN", "ID", "M1"),
        "article_type": _ris_first(row, "TY"),
        "query": query,
        "provider_query": query,
        "native_export_format": "RIS",
        "native_export_raw": {tag: list(values) for tag, values in row.items()},
    }


def _read_csv(path: Path, *, provider: str, query: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    return [_normalize_csv_row(dict(row), provider=provider, query=query) for row in reader]


def _read_ris(path: Path, *, provider: str, query: str) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    return [_normalize_ris_row(row, provider=provider, query=query) for row in _ris_records(lines)]


def read_native_export(
    provider: str,
    *,
    query: str,
    export_path: Path,
) -> list[dict[str, Any]]:
    normalized = provider.strip().lower()
    if normalized not in NATIVE_EXPORT_PROVIDERS:
        raise ValueError(f"unsupported native export provider: {provider}")
    path = Path(export_path)
    if not path.is_file():
        raise FileNotFoundError(f"native provider export not found: {path}")
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        rows = _read_csv(path, provider=normalized, query=query)
    elif suffix in {".ris", ".txt"}:
        rows = _read_ris(path, provider=normalized, query=query)
    else:
        raise ValueError("native export must be CSV or RIS")
    export_sha = _sha256_file(path)
    for row in rows:
        row["native_export_path"] = str(path.resolve())
        row["native_export_sha256"] = export_sha
    return rows


def search_native_export(
    provider: str,
    query: str,
    *,
    export_path: Path,
    limit: int = 10000,
) -> ProviderResult:
    """Return an official-export snapshot through the canonical provider contract."""
    rows = read_native_export(provider, query=query, export_path=export_path)
    safe_limit = max(1, min(int(limit), 10000))
    returned = rows[:safe_limit]
    path = Path(export_path).resolve()
    return ProviderResult(
        provider=provider.strip().lower(),
        query=query,
        rows=returned,
        total_found=len(rows),
        total_returned=len(returned),
        status="completed" if rows else "empty",
        meta={
            "native_official_export": True,
            "native_export_path": str(path),
            "native_export_sha256": _sha256_file(path),
            "native_export_format": path.suffix.lstrip(".").upper(),
            "provider_substitution": False,
            "query_preserved_exactly": True,
        },
    )


__all__ = ["NATIVE_EXPORT_PROVIDERS", "read_native_export", "search_native_export"]
