"""Safe reachability probing for public/open-access full-text candidates.

This module performs lightweight streaming requests to determine which already-
discovered public candidate should be handed to the enrichment downloader. It
never bypasses authentication or access controls and never treats reachability as
scientific eligibility, quality, or evidence strength.
"""

from __future__ import annotations

import ipaddress
import os
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urljoin, urlparse

import requests


Requester = Callable[..., Any]
DEFAULT_TIMEOUT_SECONDS = 12
MAX_REDIRECTS = 5


def _headers(media_type: str | None = None) -> dict[str, str]:
    user_agent = os.environ.get(
        "NUTEV_HTTP_USER_AGENT",
        "NutEV-Evidence-Engine/1.0 (+https://nutev.mindsperformance.com.br/)",
    ).strip()
    accept = "*/*"
    normalized = str(media_type or "").casefold()
    if "pdf" in normalized:
        accept = "application/pdf,application/octet-stream;q=0.8,*/*;q=0.2"
    elif "xml" in normalized:
        accept = "application/xml,text/xml;q=0.9,text/plain;q=0.3,*/*;q=0.1"
    elif "html" in normalized:
        accept = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.2"
    return {"User-Agent": user_agent, "Accept": accept}


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("unsupported_remote_url")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("localhost_not_allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local:
        raise ValueError("private_or_link_local_not_allowed")


def _content_type_compatible(expected: str | None, actual: str | None) -> bool:
    expected_value = str(expected or "").split(";", 1)[0].strip().casefold()
    actual_value = str(actual or "").split(";", 1)[0].strip().casefold()
    if not expected_value or not actual_value:
        return True
    if expected_value == "application/pdf":
        return actual_value in {
            "application/pdf",
            "application/octet-stream",
            "binary/octet-stream",
        }
    if "xml" in expected_value:
        return (
            "xml" in actual_value
            or actual_value in {"text/plain", "application/octet-stream"}
        )
    if "html" in expected_value:
        return "html" in actual_value or "xhtml" in actual_value
    return True


def _candidate_variants(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    primary = dict(candidate)
    variants = [primary]
    url = str(primary.get("url") or "").strip()
    if url.startswith("http://"):
        upgraded = dict(primary)
        upgraded["url"] = "https://" + url[len("http://") :]
        upgraded["probe_variant"] = "https_upgrade"
        variants.append(upgraded)
    return variants


def probe_candidate(
    candidate: Mapping[str, Any],
    *,
    requester: Requester = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    """Probe one candidate without consuming its response body.

    Returns ``(reachable, selected_candidate, audit_attempt)``. Redirect targets
    are validated at every hop to preserve the enrichment SSRF boundary.
    """

    selected = dict(candidate)
    current_url = str(selected.get("url") or "").strip()
    expected_media = str(selected.get("media_type") or "").strip() or None
    attempt: dict[str, Any] = {
        "url": current_url,
        "resolver_route": selected.get("resolver_route"),
        "scope": selected.get("scope"),
        "media_type_expected": expected_media,
        "reachable": False,
    }
    response: Any | None = None
    try:
        for redirect_count in range(MAX_REDIRECTS + 1):
            _validate_public_url(current_url)
            response = requester(
                current_url,
                headers=_headers(expected_media),
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
            status = int(getattr(response, "status_code", 0) or 0)
            headers = getattr(response, "headers", {}) or {}
            if status in {301, 302, 303, 307, 308}:
                location = str(headers.get("location") or headers.get("Location") or "").strip()
                if not location:
                    attempt.update({"http_status": status, "reason": "redirect_without_location"})
                    return False, selected, attempt
                if redirect_count >= MAX_REDIRECTS:
                    attempt.update({"http_status": status, "reason": "too_many_redirects"})
                    return False, selected, attempt
                next_url = urljoin(current_url, location)
                _validate_public_url(next_url)
                current_url = next_url
                try:
                    response.close()
                except Exception:
                    pass
                response = None
                continue

            content_type = str(
                headers.get("content-type") or headers.get("Content-Type") or ""
            ).strip()
            attempt.update(
                {
                    "http_status": status,
                    "final_url": current_url,
                    "content_type": content_type or None,
                }
            )
            if status < 200 or status >= 400:
                attempt["reason"] = f"http_status_{status or 'unknown'}"
                return False, selected, attempt
            if not _content_type_compatible(expected_media, content_type):
                attempt["reason"] = "content_type_mismatch"
                return False, selected, attempt

            selected["url"] = current_url
            attempt["reachable"] = True
            attempt["reason"] = "reachable"
            return True, selected, attempt

        attempt["reason"] = "too_many_redirects"
        return False, selected, attempt
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        attempt["reason"] = f"probe_failed:{type(exc).__name__}"
        return False, selected, attempt
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def select_reachable_candidate(
    candidates: Sequence[Mapping[str, Any]],
    *,
    allow_network: bool,
    requester: Requester = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_candidates: int = 10,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Select the first reachable candidate, preserving ordered fallback audit.

    If probing is disabled or all probes fail, the original first candidate is
    returned so the existing enrichment failure semantics remain unchanged.
    """

    materialized = [dict(candidate) for candidate in candidates if candidate]
    if not materialized:
        return None, []
    if not allow_network:
        return dict(materialized[0]), []

    attempts: list[dict[str, Any]] = []
    examined = 0
    for candidate in materialized:
        for variant in _candidate_variants(candidate):
            if examined >= max_candidates:
                break
            examined += 1
            reachable, selected, attempt = probe_candidate(
                variant,
                requester=requester,
                timeout=timeout,
            )
            if variant.get("probe_variant"):
                attempt["probe_variant"] = variant["probe_variant"]
            attempts.append(attempt)
            if reachable:
                selected["probe_selected"] = True
                selected["probe_selected_attempt"] = len(attempts)
                if variant.get("probe_variant"):
                    selected["probe_variant"] = variant["probe_variant"]
                return selected, attempts
        if examined >= max_candidates:
            break

    fallback = dict(materialized[0])
    fallback["probe_selected"] = False
    return fallback, attempts
