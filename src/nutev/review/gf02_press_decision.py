"""Persistence for the explicit human GF-02 READY_FOR_PRESS decision.

This module never chooses a decision. It only validates and records the choice
made by an identified human in the existing GF-02 gate status artifact.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

ALLOWED_PRESS_DECISIONS = ("READY_FOR_PRESS", "NOT_READY_FOR_PRESS")


def load_gf02_gate_status(path: Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"GF-02 gate status not found: {target}")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"GF-02 gate status is not valid JSON: {target}") from exc
    if not isinstance(payload, dict) or str(payload.get("gate") or "") != "GF-02":
        raise ValueError("gate status must describe GF-02")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()


def record_gf02_press_decision(
    path: Path,
    *,
    decision: str,
    decided_by: str,
    rationale: str,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """Record one explicit human pre-PRESS decision without authorizing PRESS.

    READY_FOR_PRESS is accepted only when the persisted GF-02 evidence record is
    explicitly complete. The choice never implies PRESS approval, FORMAL
    authorization or PRISMA eligibility.
    """
    normalized = str(decision or "").strip().upper()
    actor = " ".join(str(decided_by or "").strip().split())
    reason = " ".join(str(rationale or "").strip().split())
    if normalized not in ALLOWED_PRESS_DECISIONS:
        raise ValueError("decision must be READY_FOR_PRESS or NOT_READY_FOR_PRESS")
    if not actor:
        raise ValueError("A real human decision-maker identity is required")
    if not reason:
        raise ValueError("A short rationale is required for the human decision")

    payload = load_gf02_gate_status(path)
    if normalized == "READY_FOR_PRESS" and payload.get("evidence_complete") is not True:
        blockers = [str(item) for item in (payload.get("blockers") or [])]
        suffix = f": {', '.join(blockers)}" if blockers else ""
        raise ValueError("READY_FOR_PRESS requires evidence_complete=true in the GF-02 gate status" + suffix)

    timestamp = str(decided_at or "").strip() or datetime.now(timezone.utc).isoformat()
    history = list(payload.get("human_decision_history") or [])
    history.append(
        {
            "decision": normalized,
            "decided_by": actor,
            "rationale": reason,
            "decided_at": timestamp,
        }
    )

    payload["human_decision"] = normalized
    payload["human_decision_by"] = actor
    payload["human_decision_rationale"] = reason
    payload["human_decision_at"] = timestamp
    payload["human_decision_history"] = history
    payload["decision"] = normalized
    payload["press_approval_inferred"] = False
    payload["formal_execution_authorized"] = False
    payload["prisma_eligible"] = False
    _atomic_json(Path(path), payload)
    return payload


__all__ = [
    "ALLOWED_PRESS_DECISIONS",
    "load_gf02_gate_status",
    "record_gf02_press_decision",
]
