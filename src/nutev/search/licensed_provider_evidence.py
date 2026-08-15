"""Immutable evidence records for licensed/manual provider executions.

Scopus and Web of Science are external licensed routes in the Article 1 method.
This module records a real execution; it never executes, substitutes, or infers
those databases from another provider.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

PROVIDERS = {"scopus", "web_of_science"}
STATUSES = {"SUCCEEDED", "PARTIAL", "FAILED"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class LicensedProviderExecution:
    provider: str
    strategy_version: str
    search_type: str
    executed_at: str
    executed_by: str
    exact_expression: str
    interface: str
    status: str
    total_found: int | None
    records_retrieved: int
    export_path: str
    export_sha256: str
    notes: str = ""


def validate_licensed_execution(record: LicensedProviderExecution) -> LicensedProviderExecution:
    provider = record.provider.strip().lower()
    status = record.status.strip().upper()
    search_type = record.search_type.strip().upper()
    if provider not in PROVIDERS:
        raise ValueError(f"licensed provider must be one of {sorted(PROVIDERS)}")
    if search_type not in {"PILOT", "FORMAL"}:
        raise ValueError("licensed provider search_type must be PILOT or FORMAL")
    required = {
        "strategy_version": record.strategy_version,
        "executed_at": record.executed_at,
        "executed_by": record.executed_by,
        "exact_expression": record.exact_expression,
        "interface": record.interface,
    }
    missing = [name for name, value in required.items() if not _clean(value)]
    if missing:
        raise ValueError("licensed execution lacks: " + ", ".join(missing))
    if status not in STATUSES:
        raise ValueError(f"invalid licensed execution status: {record.status}")
    if record.total_found is not None and int(record.total_found) < 0:
        raise ValueError("total_found cannot be negative")
    if int(record.records_retrieved) < 0:
        raise ValueError("records_retrieved cannot be negative")
    if status in {"SUCCEEDED", "PARTIAL"}:
        if not _clean(record.export_path):
            raise ValueError(f"{status} licensed execution requires export_path")
        if not _SHA256.fullmatch(record.export_sha256.strip()):
            raise ValueError(f"{status} licensed execution requires a 64-character export_sha256")
    return record


def execution_digest(record: LicensedProviderExecution) -> str:
    validate_licensed_execution(record)
    payload = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def default_licensed_evidence_path(project_root: Path, provider: str) -> Path:
    normalized = provider.strip().lower()
    if normalized not in PROVIDERS:
        raise ValueError(f"unknown licensed provider: {provider}")
    return Path(project_root) / "07_logs" / "licensed_providers" / f"{normalized}.json"


def save_licensed_execution(path: Path, record: LicensedProviderExecution) -> Path:
    validate_licensed_execution(record)
    target = Path(path)
    payload = {
        "schema_version": 1,
        "execution": asdict(record),
        "execution_digest": execution_digest(record),
        "substitution_inferred": False,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing != payload:
            raise FileExistsError(f"licensed provider evidence is immutable at {target}")
        return target
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_licensed_execution(path: Path) -> LicensedProviderExecution:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    row = payload.get("execution") or {}
    record = LicensedProviderExecution(
        provider=_clean(row.get("provider")),
        strategy_version=_clean(row.get("strategy_version")),
        search_type=_clean(row.get("search_type")),
        executed_at=_clean(row.get("executed_at")),
        executed_by=_clean(row.get("executed_by")),
        exact_expression=_clean(row.get("exact_expression")),
        interface=_clean(row.get("interface")),
        status=_clean(row.get("status")),
        total_found=int(row["total_found"]) if row.get("total_found") is not None else None,
        records_retrieved=int(row.get("records_retrieved") or 0),
        export_path=_clean(row.get("export_path")),
        export_sha256=_clean(row.get("export_sha256")),
        notes=_clean(row.get("notes")),
    )
    validate_licensed_execution(record)
    expected = _clean(payload.get("execution_digest"))
    actual = execution_digest(record)
    if expected and expected != actual:
        raise ValueError("licensed provider execution_digest mismatch")
    return record


def licensed_pilot_status(project_root: Path) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    blockers: list[str] = []
    for provider in sorted(PROVIDERS):
        path = default_licensed_evidence_path(project_root, provider)
        if not path.is_file():
            providers[provider] = {"status": "MISSING", "path": str(path)}
            blockers.append(f"{provider}:missing")
            continue
        try:
            record = load_licensed_execution(path)
        except Exception as exc:
            providers[provider] = {"status": "INVALID", "path": str(path), "error": str(exc)}
            blockers.append(f"{provider}:invalid")
            continue
        status = record.status.strip().upper()
        providers[provider] = {
            "status": status,
            "search_type": record.search_type.strip().upper(),
            "strategy_version": record.strategy_version,
            "path": str(path),
        }
        if record.search_type.strip().upper() != "PILOT" or status != "SUCCEEDED":
            blockers.append(f"{provider}:{record.search_type.strip().upper()}:{status}")
    return {
        "complete": not blockers,
        "providers": providers,
        "blockers": blockers,
        "provider_substitution_allowed": False,
    }


__all__ = [
    "LicensedProviderExecution",
    "default_licensed_evidence_path",
    "execution_digest",
    "licensed_pilot_status",
    "load_licensed_execution",
    "save_licensed_execution",
    "validate_licensed_execution",
]
