"""Verify official-source URLs (base + per-country manifest) against the live web.

Because the manifest is curated offline, URLs can drift or 404. This module
checks each source and produces a report so dead/moved links can be fixed. It
respects NUTEV_DISABLE_NETWORK and never follows into downloads — it only checks
reachability of the official landing pages.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nutev.search.official_sources import load_official_manifest, manifest_sources

WORKSTREAMS = ["policy_systems", "clinical_outcomes", "implementation", "framework"]
_USER_AGENT = "NutEV Source Verifier/1.0 (+https://github.com/WillianVagner123/NutEV-Evidence-Engine)"


def _all_sources(config_root: Path, include_countries: bool = True) -> list[dict]:
    manifest = load_official_manifest(config_root, include_countries=include_countries)
    seen: set[str] = set()
    rows: list[dict] = []
    for ws in WORKSTREAMS:
        for src in manifest_sources(manifest, ws):
            url = src.get("url", "")
            if url and url not in seen:
                seen.add(url)
                rows.append(src)
    return rows


def _check_url(session: Any, url: str, timeout: float) -> dict:
    """Return {status_code, ok, reason} for a single URL."""
    try:
        resp = session.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            stream=True,
        )
        code = int(getattr(resp, "status_code", 0) or 0)
        try:
            resp.close()
        except Exception:
            import logging

            logging.getLogger(__name__).debug("failed to close response", exc_info=True)
        # 403/429 from anti-bot often still means the page exists.
        ok = 200 <= code < 400 or code in {401, 403, 429}
        reason = "ok" if 200 <= code < 400 else ("blocked_but_exists" if code in {401, 403, 429} else "http_error")
        return {"status_code": code, "ok": ok, "reason": reason}
    except Exception as exc:  # network/DNS/timeout
        return {"status_code": 0, "ok": False, "reason": f"unreachable: {type(exc).__name__}"}


def verify_official_sources(
    config_root: Path,
    timeout: float = 20.0,
    include_countries: bool = True,
    session: Any | None = None,
) -> list[dict]:
    """Check every official source URL and return per-source verification rows."""
    sources = _all_sources(config_root, include_countries=include_countries)
    if os.environ.get("NUTEV_DISABLE_NETWORK") == "1":
        return [
            {**s, "status_code": 0, "ok": False, "reason": "network_disabled"}
            for s in sources
        ]
    if session is None:
        import requests

        session = requests.Session()
    results: list[dict] = []
    for src in sources:
        check = _check_url(session, src.get("url", ""), timeout)
        results.append(
            {
                "name": src.get("title") or src.get("name") or "",
                "url": src.get("url", ""),
                "country": src.get("country", ""),
                "institution": src.get("source_institution") or src.get("institution", ""),
                "authority": src.get("authority", ""),
                **check,
            }
        )
    return results


def write_verification_report(rows: list[dict], out_path: Path) -> Path:
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["name", "country", "institution", "authority", "url", "status_code", "ok", "reason"]
    with out_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    return out_path
