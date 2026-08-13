from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from nutev.engine.validators import validate_workstream

logger = logging.getLogger("nutev.search.official_sources")


def _read_manifest(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("official manifest unreadable, dropped: path=%s error=%s", path, exc)
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
            logger.warning("official source row dropped: not an object: %r", source)
            continue
        key = _source_key(source)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def _canonical_workstreams(manifest: dict) -> dict:
    output = dict(manifest) if isinstance(manifest, dict) else {}
    if "workstreams" not in output:
        return output
    raw = output.get("workstreams")
    if not isinstance(raw, dict):
        output["workstreams"] = {}
        return output
    canonical: dict[str, list[dict]] = {}
    for raw_label, sources in raw.items():
        try:
            label = validate_workstream(str(raw_label))
        except ValueError:
            logger.warning("unknown official-source analytical label dropped: %s", raw_label)
            continue
        if not label or not isinstance(sources, list):
            continue
        canonical[label] = _dedupe_sources(list(canonical.get(label, [])) + list(sources))
    output["workstreams"] = canonical
    return output


def load_official_manifest(config_root: Path, include_countries: bool = True) -> dict:
    """Load official sources and expose canonical semantic labels in memory."""
    base = _read_manifest(Path(config_root) / "official_sources_manifest.json")
    if include_countries:
        countries = _read_manifest(Path(config_root) / "official_sources_countries.json")
        extra_ws = countries.get("workstreams") if isinstance(countries, dict) else None
        if isinstance(extra_ws, dict):
            workstreams = base.setdefault("workstreams", {})
            for label, extra in extra_ws.items():
                if isinstance(extra, list):
                    workstreams[label] = list(workstreams.get(label, [])) + extra
    return _canonical_workstreams(base)


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def manifest_sources(manifest: dict, workstream: str) -> list[dict]:
    """Return rows using semantic labels even when the input manifest is legacy."""
    try:
        canonical_manifest = _canonical_workstreams(manifest)
        label = validate_workstream(workstream)
        if not label:
            return []
        sources = _dedupe_sources(
            list(canonical_manifest.get("workstreams", {}).get(label, []) or [])
        )
    except Exception as exc:
        logger.warning("official sources unresolved for analytical_label=%s, dropped: error=%s", workstream, exc)
        return []

    rows: list[dict] = []
    for source in sources:
        try:
            url = str(source.get("url") or "").strip()
            title = str(source.get("name") or source.get("title") or "").strip()
            if not url or not title or not _valid_url(url):
                continue
            rows.append(
                {
                    "source": "official",
                    "source_provider": "official_web",
                    "title": title,
                    "url": url,
                    "authority": source.get("authority", 1),
                    "source_institution": source.get("institution") or source.get("authority_name") or title,
                    "metadata_status": "official_manifest",
                    "query": label,
                    "provider_query": label,
                    "analytical_label": label,
                }
            )
        except Exception as exc:
            logger.warning("official source row dropped: source=%r error=%s", source, exc)
            continue
    return rows
