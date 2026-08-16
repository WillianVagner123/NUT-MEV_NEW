"""Deterministic persistence for the real human PRESS gate.

This module records only explicit human/external PRESS evidence. It never infers
approval and never authorizes FREEZE, FORMAL execution, or PRISMA.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
PRESS_STATUSES = ("APPROVED", "CHANGES_REQUIRED", "REJECTED")


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()


def press_gate_path(project_root: Path) -> Path:
    return Path(project_root) / "07_logs" / "scientific_gates" / "press.json"


def load_press_gate(project_root: Path) -> dict[str, Any]:
    """Return the latest persisted PRESS record, if any."""
    return _load_json(press_gate_path(project_root))


def record_press_gate(
    project_root: Path,
    *,
    review_status: str,
    reviewer: str,
    review_date: str,
    evidence_reference: str,
    requested_changes: str = "",
    incorporated_changes: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Persist one explicit human PRESS decision and append an audit event."""
    status = str(review_status or "").strip().upper()
    if status not in PRESS_STATUSES:
        raise ValueError(f"review_status must be one of: {', '.join(PRESS_STATUSES)}")

    human_reviewer = str(reviewer or "").strip()
    if not human_reviewer:
        raise ValueError("PRESS requires the real reviewer identity")

    reviewed_on = str(review_date or "").strip()
    if not reviewed_on:
        raise ValueError("PRESS requires the real review date")

    evidence = str(evidence_reference or "").strip()
    if not evidence:
        raise ValueError("PRESS requires a real evidence reference, file, URL, DOI, protocol ID, or archived path")

    requested = str(requested_changes or "").strip()
    incorporated = str(incorporated_changes or "").strip()
    if status == "APPROVED" and requested and not incorporated:
        raise ValueError(
            "APPROVED with requested changes requires a record of how those changes were incorporated"
        )

    path = press_gate_path(project_root)
    previous = _load_json(path)
    history = list(previous.get("history") or []) if isinstance(previous.get("history"), list) else []
    event = {
        "event_id": f"press_{uuid4().hex}",
        "review_status": status,
        "reviewer": human_reviewer,
        "review_date": reviewed_on,
        "evidence_reference": evidence,
        "requested_changes": requested,
        "incorporated_changes": incorporated,
        "notes": str(notes or "").strip(),
        "decision_source": "HUMAN",
        "human_validated": True,
        "recorded_at": _now_iso(),
    }
    history.append(event)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "gate": "GF-03_PRESS",
        **event,
        "history": history,
        "press_approval_inferred": False,
        "freeze_authorized": False,
        "formal_execution_authorized": False,
        "prisma_eligible": False,
    }
    _atomic_json(path, payload)
    payload["path"] = str(path)
    return payload


__all__ = [
    "PRESS_STATUSES",
    "load_press_gate",
    "press_gate_path",
    "record_press_gate",
]
