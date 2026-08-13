"""P2.1 — Official dietary-guideline fetcher (Track 1).

Official guides are NOT indexed in bibliographic databases; they live in the FAO
Food-Based Dietary Guidelines registry and on ministry sites. This module fetches
them by sampling frame — reusing the existing country seed list in
``config/official_sources_countries.json`` (loaded via
``nutev.search.official_sources.load_official_manifest``) instead of a second
parallel list.

For every fetched file it records auditable provenance: ``source_url``,
``access_date`` (UTC), ``sha256``, issuing body, AACODS authority tier and
``fulltext_status``. The HTTP session is injected (mockable, rate-limitable);
nothing is fabricated. Copyright/ToS are respected — see
``docs/COPYRIGHT_AND_FULL_TEXT_POLICY.md``.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nutev.analysis.article1_coding import sha256_of_file
from nutev.search.official_sources import load_official_manifest

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def load_guide_sources(config_root: str | Path) -> list[dict]:
    """Return the Track-1 dietary-guide seed list using canonical semantics."""
    manifest = load_official_manifest(Path(config_root), include_countries=True)
    return list(manifest.get("workstreams", {}).get("policy_systems", []))


def _slug(text: str, maxlen: int = 40) -> str:
    return _SLUG_RE.sub("-", str(text or "").strip().lower()).strip("-")[:maxlen] or "guide"


def _content_kind(content_type: str, body: bytes) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct or body[:5] == b"%PDF-":
        return "pdf"
    if "html" in ct or body[:15].lstrip().lower().startswith((b"<!doctype", b"<html")):
        return "html"
    return "other"


def _max_download_bytes() -> int:
    """Optional cap on one download (NUTEV_MAX_DOWNLOAD_MB; 0 = no cap)."""
    try:
        mb = float(os.environ.get("NUTEV_MAX_DOWNLOAD_MB", "0") or 0)
    except ValueError:
        return 0
    return int(mb * 1024 * 1024) if mb > 0 else 0


def fetch_guide(
    source: dict,
    dest_dir: str | Path,
    session: Any,
    *,
    timeout: float = 30.0,
) -> dict:
    """Fetch one guide, save it, and return an auditable provenance record."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    url = str(source.get("url") or "").strip()
    access_date = datetime.now(timezone.utc).isoformat()
    base = {
        "name": source.get("name", ""),
        "country": source.get("country", source.get("region", "")),
        "institution": source.get("institution", ""),
        "source_url": url,
        "access_date": access_date,
        "retrieval_method": "guias_fetcher",
        "aacods_authority_tier": source.get("authority", ""),
        "archived_pdf_path": "",
        "sha256": "",
        "fulltext_status": "error",
        "reason": "",
    }
    if not url:
        base["reason"] = "empty_url"
        return base
    try:
        resp = session.get(url, timeout=timeout)
        code = getattr(resp, "status_code", 0)
        if code != 200:
            base["reason"] = f"http_{code}"
            return base
        body = resp.content or b""
        cap = _max_download_bytes()
        if cap and len(body) > cap:
            base["reason"] = f"too_large_{len(body)}_bytes"
            return base
        kind = _content_kind(
            getattr(resp, "headers", {}).get("Content-Type", "") if hasattr(resp, "headers") else "",
            body,
        )
        ext = "pdf" if kind == "pdf" else ("html" if kind == "html" else "bin")
        fname = f"{_slug(source.get('country') or source.get('name'))}__{_slug(source.get('name'))}.{ext}"
        out_path = dest / fname
        out_path.write_bytes(body)
        base["archived_pdf_path"] = str(out_path)
        base["sha256"] = sha256_of_file(out_path) or ""
        base["fulltext_status"] = (
            "fulltext_pdf" if kind == "pdf" else ("fulltext_html" if kind == "html" else "other")
        )
        base["reason"] = ""
    except Exception as exc:
        base["reason"] = f"{type(exc).__name__}: {exc}"
    return base


def fetch_guides(
    sources: list[dict],
    dest_dir: str | Path,
    session: Any,
    *,
    timeout: float = 30.0,
    limit: int | None = None,
) -> list[dict]:
    """Fetch a batch of guides; returns one provenance record per source."""
    out: list[dict] = []
    for source in sources[: limit or len(sources)]:
        out.append(fetch_guide(source, dest_dir, session, timeout=timeout))
    return out
