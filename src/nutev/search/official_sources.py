from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("nutev.search.official_sources")


def _read_manifest(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("official manifest unreadable: path=%s error=%s", path, exc)
        return {}


def _source_key(source: dict) -> str:
    url = str(source.get("url") or "").strip()
    if url:
        try:
            parsed = urlparse(url)
        except Exception:
            parsed = None
        if parsed and parsed.netloc:
            netloc = parsed.netloc.lower().removeprefix("www.")
            path = parsed.path.rstrip("/") or "/"
            return f"{netloc}{path}".rstrip("/")
        return url.lower().rstrip("/")
    return str(source.get("name") or source.get("title") or "").strip().lower()


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        key = _source_key(source)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def load_official_manifest(config_root: Path, include_countries: bool = True) -> dict:
    """Load official-source manifests without imposing research-workflow labels."""
    base = _read_manifest(Path(config_root) / "official_sources_manifest.json")
    if not isinstance(base.get("workstreams"), dict):
        base["workstreams"] = {}
    if include_countries:
        countries = _read_manifest(Path(config_root) / "official_sources_countries.json")
        extra = countries.get("workstreams") if isinstance(countries, dict) else None
        if isinstance(extra, dict):
            for label, rows in extra.items():
                if isinstance(rows, list):
                    base["workstreams"].setdefault(str(label), []).extend(rows)
    return base


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def manifest_sources(manifest: dict, category: str) -> list[dict]:
    rows = (manifest.get("workstreams") or {}).get(category, []) if isinstance(manifest, dict) else []
    if not isinstance(rows, list):
        return []
    output: list[dict] = []
    for source in _dedupe_sources(rows):
        url = str(source.get("url") or "").strip()
        title = str(source.get("name") or source.get("title") or "").strip()
        if not url or not title or not _valid_url(url):
            continue
        output.append(
            {
                "source": "official",
                "source_provider": "official_web",
                "title": title,
                "url": url,
                "authority": source.get("authority", 1),
                "source_institution": source.get("institution") or source.get("authority_name") or title,
                "metadata_status": "official_manifest",
                "query": category,
                "provider_query": category,
                "source_category": category,
            }
        )
    return output


def all_manifest_sources(manifest: dict) -> list[dict]:
    """Return deduplicated references from every configured official-source category."""
    workstreams = manifest.get("workstreams") if isinstance(manifest, dict) else None
    if not isinstance(workstreams, dict):
        return []
    collected: list[dict] = []
    seen: set[str] = set()
    for category in sorted(str(key) for key in workstreams):
        for row in manifest_sources(manifest, category):
            key = _source_key(row)
            if not key or key in seen:
                continue
            seen.add(key)
            collected.append(row)
    return collected
