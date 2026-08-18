from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

GUARDRAIL_POLICY_VERSION = "2026-08-18.2"

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_PMID_RE = re.compile(r"^[0-9]{1,9}$")
_PMCID_RE = re.compile(r"^PMC[0-9]+$", re.I)


class IntegrityError(RuntimeError):
    """Raised when an input cannot be proven to match its recorded manifest."""


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _has_http_url(value: Any) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        parts = urlsplit(raw)
    except Exception:
        return False
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def _normalized_doi(value: Any) -> str:
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
    return raw.rstrip(" .;,)]}")


def _valid_doi(value: Any) -> bool:
    doi = _normalized_doi(value)
    return bool(doi and _DOI_RE.fullmatch(doi))


def _valid_pmid(value: Any) -> bool:
    raw = str(value or "").strip()
    return bool(raw and _PMID_RE.fullmatch(raw))


def _valid_pmcid(value: Any) -> bool:
    raw = str(value or "").strip()
    return bool(raw and _PMCID_RE.fullmatch(raw))


def record_traceability(row: dict[str, Any]) -> tuple[str, list[str]]:
    """Classify whether a record is independently traceable without inference.

    An identifier must be syntactically plausible to qualify. The engine never
    upgrades, repairs, or invents identifiers. Records that cannot be traced to a
    valid identifier or HTTP(S) URL are quarantined instead of silently ranked.
    """

    provider = str(row.get("source_provider") or row.get("source") or "").strip()
    title = str(row.get("title") or "").strip()
    reasons: list[str] = []

    if not provider:
        reasons.append("missing_provider")
    if not title:
        reasons.append("missing_title")

    if reasons:
        return "Q_INCOMPLETE_ORIGIN", reasons

    doi_value = row.get("doi") or row.get("doi_normalized")
    pmid_value = row.get("pmid") or row.get("pmid_normalized")
    pmcid_value = row.get("pmcid")

    invalid_identifiers: list[str] = []
    if doi_value:
        if _valid_doi(doi_value):
            return "A_IDENTIFIER", ["doi"]
        invalid_identifiers.append("invalid_doi")
    if pmid_value:
        if _valid_pmid(pmid_value):
            return "A_IDENTIFIER", ["pmid"]
        invalid_identifiers.append("invalid_pmid")
    if pmcid_value:
        if _valid_pmcid(pmcid_value):
            return "A_IDENTIFIER", ["pmcid"]
        invalid_identifiers.append("invalid_pmcid")

    if _has_http_url(row.get("url") or row.get("url_normalized")):
        return "B_TRACEABLE_URL", ["url", *invalid_identifiers]

    if invalid_identifiers:
        return "Q_INVALID_IDENTIFIER", invalid_identifiers
    return "Q_UNTRACEABLE", ["no_valid_identifier_or_http_url"]


def annotate_record(row: dict[str, Any]) -> dict[str, Any]:
    traceability, reasons = record_traceability(row)
    provider = str(row.get("source_provider") or row.get("source") or "").strip()
    origin_payload = {
        "provider": provider,
        "doi": row.get("doi") or row.get("doi_normalized") or "",
        "pmid": row.get("pmid") or row.get("pmid_normalized") or "",
        "pmcid": row.get("pmcid") or "",
        "url": row.get("url") or row.get("url_normalized") or "",
        "title": row.get("title") or "",
        "provider_query": row.get("provider_query") or row.get("query") or "",
    }
    annotated = dict(row)
    annotated.update(
        {
            "audit_policy_version": GUARDRAIL_POLICY_VERSION,
            "audit_traceability": traceability,
            "audit_quarantined": traceability.startswith("Q_"),
            "audit_reasons": reasons,
            "audit_origin_sha256": canonical_json_sha256(origin_payload),
        }
    )
    return annotated


def verify_manifest_master(state_path: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    """Verify a master file against its manifest and return audit metadata.

    Missing files are ignored only when the manifest does not claim a master.
    Once a master path is claimed, a SHA-256 is mandatory and mismatch is fatal.
    """

    master_raw = str(state.get("master_records_path") or "").strip()
    if not master_raw:
        return None
    master_path = Path(master_raw)
    if not master_path.is_file():
        raise IntegrityError(f"Manifest points to missing master file: {master_path}")

    expected = str(state.get("master_records_sha256") or "").strip().lower()
    if not expected:
        raise IntegrityError(f"Manifest has no master_records_sha256: {state_path}")

    actual = sha256_file(master_path)
    if actual != expected:
        raise IntegrityError(
            f"SHA-256 mismatch for {master_path}: expected {expected}, got {actual}"
        )

    return {
        "state_path": str(state_path),
        "state_run_id": str(state.get("run_id") or ""),
        "state_status": str(state.get("status") or ""),
        "collection_type": str(state.get("collection_type") or ""),
        "master_records_path": str(master_path),
        "master_records_sha256": actual,
    }
