"""Generic scientific gates, PRESS evidence, and immutable freeze records.

These objects record scientific state; they never infer human approval from
successful software execution. GF-02 keeps its specialized evidence logic and
can be represented here only after its real evidence/human decision exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Iterable

GATE_IDS = tuple(f"GF-{number:02d}" for number in range(1, 11))
GATE_STATUSES = {
    "PENDING",
    "PARTIAL",
    "BLOCKED_HUMAN",
    "COMPLETED",
    "NOT_AUTHORIZED",
    "AUTHORIZED",
}
PRESS_STATUSES = {"NOT_SUBMITTED", "SUBMITTED", "CHANGES_REQUESTED", "APPROVED"}
PRE_FREEZE_GATES = (
    "GF-02",
    "GF-03",
    "GF-04",
    "GF-05",
    "GF-06",
    "GF-07",
    "GF-08",
    "GF-09",
)
_SHA40 = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class GateRecord:
    gate_id: str
    requirement: str
    evidence: tuple[str, ...] = ()
    status: str = "PENDING"
    blocks_freeze: bool = True
    owner: str = ""
    completion_date: str = ""
    next_action: str = ""
    decisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PressRecord:
    press_submission_id: str
    strategy_version: str
    reviewer: str = ""
    submission_date: str = ""
    review_status: str = "NOT_SUBMITTED"
    comments: tuple[str, ...] = ()
    recommended_changes: tuple[str, ...] = ()
    implemented_changes: tuple[str, ...] = ()
    final_decision: str = ""


@dataclass(frozen=True)
class FreezeRecord:
    freeze_id: str
    date: str
    software_version: str
    git_commit_sha: str
    strategy_versions: tuple[str, ...]
    source_registry_version: str
    repository_registry_version: str
    sentinel_suite_version: str
    press_evidence_id: str
    filters: tuple[tuple[str, str], ...]
    final_search_date_rule: str
    config_digest: str
    reviewers: tuple[str, ...]


def validate_gate_record(record: GateRecord) -> GateRecord:
    gate_id = record.gate_id.strip().upper()
    status = record.status.strip().upper()
    if gate_id not in GATE_IDS:
        raise ValueError(f"invalid gate_id: {record.gate_id}")
    if status not in GATE_STATUSES:
        raise ValueError(f"invalid gate status: {record.status}")
    if not record.requirement.strip():
        raise ValueError(f"requirement is required for {gate_id}")
    if status in {"COMPLETED", "AUTHORIZED"}:
        missing = []
        if not record.evidence:
            missing.append("evidence")
        if not record.owner.strip():
            missing.append("owner")
        if not record.completion_date.strip():
            missing.append("completion_date")
        if missing:
            raise ValueError(f"{gate_id} {status} lacks: " + ", ".join(missing))
    return record


def validate_gate_set(records: Iterable[GateRecord]) -> list[GateRecord]:
    validated: list[GateRecord] = []
    seen: set[str] = set()
    for record in records:
        validate_gate_record(record)
        gate_id = record.gate_id.strip().upper()
        if gate_id in seen:
            raise ValueError(f"duplicate gate_id: {gate_id}")
        seen.add(gate_id)
        validated.append(record)
    return validated


def pre_freeze_blockers(records: Iterable[GateRecord]) -> list[str]:
    """Return unmet mandatory prerequisites for GF-10 authorization."""
    by_id = {row.gate_id.strip().upper(): row for row in validate_gate_set(records)}
    blockers: list[str] = []
    for gate_id in PRE_FREEZE_GATES:
        record = by_id.get(gate_id)
        if record is None:
            blockers.append(f"{gate_id}:missing")
            continue
        if record.blocks_freeze and record.status.strip().upper() not in {
            "COMPLETED",
            "AUTHORIZED",
        }:
            blockers.append(f"{gate_id}:{record.status.strip().upper()}")
    return blockers


def global_freeze_status(records: Iterable[GateRecord]) -> dict[str, object]:
    rows = validate_gate_set(records)
    blockers = pre_freeze_blockers(rows)
    gf10 = next((row for row in rows if row.gate_id.strip().upper() == "GF-10"), None)
    authorized = (
        not blockers
        and gf10 is not None
        and gf10.status.strip().upper() == "AUTHORIZED"
    )
    return {
        "gate": "GF-10",
        "authorized": authorized,
        "status": "AUTHORIZED" if authorized else "NOT_AUTHORIZED",
        "active_blockers": blockers,
        "active_blocker_count": len(blockers),
    }


def validate_press_record(record: PressRecord) -> PressRecord:
    status = record.review_status.strip().upper()
    if not record.press_submission_id.strip() or not record.strategy_version.strip():
        raise ValueError("press_submission_id and strategy_version are required")
    if status not in PRESS_STATUSES:
        raise ValueError(f"invalid PRESS status: {record.review_status}")
    if status != "NOT_SUBMITTED":
        if not record.reviewer.strip() or not record.submission_date.strip():
            raise ValueError("submitted PRESS evidence requires reviewer and submission_date")
    if status == "APPROVED" and not record.final_decision.strip():
        raise ValueError("APPROVED PRESS evidence requires final_decision")
    return record


def validate_freeze_record(record: FreezeRecord) -> FreezeRecord:
    required = {
        "freeze_id": record.freeze_id,
        "date": record.date,
        "software_version": record.software_version,
        "source_registry_version": record.source_registry_version,
        "repository_registry_version": record.repository_registry_version,
        "sentinel_suite_version": record.sentinel_suite_version,
        "press_evidence_id": record.press_evidence_id,
        "final_search_date_rule": record.final_search_date_rule,
    }
    missing = [name for name, value in required.items() if not _clean(value)]
    if not record.strategy_versions:
        missing.append("strategy_versions")
    if not record.reviewers:
        missing.append("reviewers")
    if missing:
        raise ValueError("freeze record lacks: " + ", ".join(missing))
    if not _SHA40.fullmatch(record.git_commit_sha.strip()):
        raise ValueError("freeze git_commit_sha must be a 40-character Git SHA")
    if not _SHA256.fullmatch(record.config_digest.strip()):
        raise ValueError("freeze config_digest must be a 64-character SHA-256")
    return record


def freeze_digest(record: FreezeRecord) -> str:
    validate_freeze_record(record)
    payload = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def formal_execution_authorization(
    *,
    gates: Iterable[GateRecord],
    freeze: FreezeRecord | None,
    current_git_sha: str,
    current_config_digest: str,
) -> dict[str, object]:
    """Authorize nothing implicitly; report exact blockers at the execution edge."""
    rows = validate_gate_set(gates)
    blockers = list(pre_freeze_blockers(rows))
    gf10 = next((row for row in rows if row.gate_id.strip().upper() == "GF-10"), None)
    if gf10 is None or gf10.status.strip().upper() != "AUTHORIZED":
        blockers.append("GF-10:not_authorized")

    freeze_id: str | None = None
    if freeze is None:
        blockers.append("freeze_record_missing")
    else:
        try:
            validate_freeze_record(freeze)
        except ValueError as exc:
            blockers.append(f"freeze_invalid:{exc}")
        else:
            freeze_id = freeze.freeze_id
            if freeze.git_commit_sha.casefold() != current_git_sha.strip().casefold():
                blockers.append("freeze_git_sha_mismatch")
            if freeze.config_digest.casefold() != current_config_digest.strip().casefold():
                blockers.append("freeze_config_digest_mismatch")
            if gf10 and freeze.freeze_id not in gf10.evidence:
                blockers.append("GF-10:freeze_evidence_mismatch")

    unique_blockers = list(dict.fromkeys(blockers))
    return {
        "authorized": not unique_blockers,
        "formal_execution_authorized": not unique_blockers,
        "prisma_eligible": not unique_blockers,
        "freeze_id": freeze_id,
        "blockers": unique_blockers,
    }


__all__ = [
    "FreezeRecord",
    "GATE_IDS",
    "GateRecord",
    "PressRecord",
    "formal_execution_authorization",
    "freeze_digest",
    "global_freeze_status",
    "pre_freeze_blockers",
    "validate_freeze_record",
    "validate_gate_record",
    "validate_gate_set",
    "validate_press_record",
]
