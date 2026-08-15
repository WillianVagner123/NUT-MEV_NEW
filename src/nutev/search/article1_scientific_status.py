"""Read-only Article 1 scientific status for UI/API surfaces.

This module never authorizes a scientific transition. It summarizes persisted
state without collapsing software completion, pre-PRESS readiness, post-PRESS
provider validation, FREEZE, FORMAL execution, or PRISMA into one flag.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

CANONICAL_SEQUENCE = (
    "PUBMED_PILOT",
    "PRESS",
    "INCORPORATE_PRESS",
    "SCOPUS_WOS_TRANSLATION",
    "LICENSED_PILOT",
    "CLOSE_SCIENTIFIC_GATES",
    "FREEZE",
    "FORMAL_EXECUTION",
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _latest_matching_manifest(project_root: Path, candidate_version: str) -> dict[str, Any]:
    root = Path(project_root) / "07_logs" / "gf02" / "pubmed"
    if not root.is_dir():
        return {}
    matches: list[tuple[float, dict[str, Any]]] = []
    for path in root.glob("*/run_manifest.json"):
        payload = _load_json(path)
        if str(payload.get("candidate_version") or "") != candidate_version:
            continue
        try:
            stamp = path.stat().st_mtime
        except OSError:
            stamp = 0.0
        payload = dict(payload)
        payload["_manifest_path"] = str(path)
        matches.append((stamp, payload))
    return max(matches, key=lambda item: item[0])[1] if matches else {}


def _sample_review_complete(path_value: object) -> bool:
    path = Path(str(path_value or ""))
    if not path.is_file():
        return False
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return False
    return bool(rows) and all(
        str(row.get("classification") or "").strip()
        and str(row.get("reviewer") or "").strip()
        for row in rows
    )


def derive_article1_scientific_status(repo_root: Path, project_root: Path) -> dict[str, Any]:
    repo = Path(repo_root)
    project = Path(project_root)
    config = _load_json(repo / "config" / "gf02_pubmed_candidates.json")
    candidate_version = str(config.get("current_candidate") or "UNKNOWN")
    candidate_status = str(config.get("candidate_status") or "UNKNOWN")
    manifest = _latest_matching_manifest(project, candidate_version)
    pubmed_pilot_complete = bool(
        manifest
        and manifest.get("status") == "SUCCEEDED"
        and manifest.get("search_type") == "PILOT"
        and manifest.get("prisma_eligible") is False
    )
    noise_review_complete = _sample_review_complete(manifest.get("rescue_only_sample"))

    gf02_gate = _load_json(project / "07_logs" / "gf02" / "gate_status.json")
    human_decision = str(gf02_gate.get("human_decision") or "").strip().upper()
    ready_for_press = human_decision == "READY_FOR_PRESS"

    press_record = _load_json(project / "07_logs" / "scientific_gates" / "press.json")
    press_status = str(press_record.get("review_status") or "NOT_SUBMITTED").upper()
    press_approved = press_status == "APPROVED"

    if not pubmed_pilot_complete:
        current_phase = "GF02_PUBMED_PILOT"
        next_action = f"Execute and audit B-NORM-PUBMED {candidate_version}."
    elif not noise_review_complete:
        current_phase = "GF02_NOISE_REVIEW"
        next_action = "Complete the human rescue-only noise classification."
    elif not ready_for_press:
        current_phase = "GF02_HUMAN_DECISION"
        next_action = "Record the human READY_FOR_PRESS or NOT_READY_FOR_PRESS decision."
    elif not press_approved:
        current_phase = "GF03_PRESS"
        next_action = "Submit/complete PRESS review before translating final Scopus/WoS strategies."
    else:
        current_phase = "POST_PRESS_PROVIDER_VALIDATION"
        next_action = "Incorporate PRESS, translate Scopus/WoS, and run licensed PILOT validation."

    blockers_to_press: list[str] = []
    if not pubmed_pilot_complete:
        blockers_to_press.append("gf02_pubmed_pilot_not_complete")
    if pubmed_pilot_complete and not noise_review_complete:
        blockers_to_press.append("gf02_noise_review_not_complete")
    if pubmed_pilot_complete and noise_review_complete and not ready_for_press:
        blockers_to_press.append("gf02_human_ready_for_press_decision_missing")

    return {
        "schema_version": 1,
        "system_core_complete": True,
        "software_only": True,
        "article1_current_phase": current_phase,
        "next_action": next_action,
        "gf02": {
            "candidate_version": candidate_version,
            "candidate_status": candidate_status,
            "search_type": str(config.get("search_type") or ""),
            "prisma_eligible": bool(config.get("prisma_eligible")),
            "formal_execution_authorized": bool(config.get("formal_execution_authorized")),
            "pubmed_pilot_complete": pubmed_pilot_complete,
            "noise_review_complete": noise_review_complete,
            "human_decision": human_decision or None,
            "ready_for_press": ready_for_press,
            "latest_manifest": manifest.get("_manifest_path"),
        },
        "press": {"status": press_status, "approved": press_approved, "is_next_gate": ready_for_press and not press_approved},
        "scopus_wos": {"sequence": "POST_PRESS", "pre_press_blocker": False, "methodology_decision": "D-096"},
        "freeze": {"authorized": False, "downstream": True},
        "formal_execution": {"authorized": False, "downstream": True},
        "prisma": {"formal_count_allowed": False, "downstream": True},
        "blockers_to_press": blockers_to_press,
        "canonical_sequence": list(CANONICAL_SEQUENCE),
        "human_approval_inferred": False,
    }


def scientific_execution_card(status: dict[str, Any]) -> dict[str, str]:
    gf02 = status.get("gf02") or {}
    candidate = str(gf02.get("candidate_version") or "current")
    phase = str(status.get("article1_current_phase") or "")
    if phase == "GF02_PUBMED_PILOT":
        body = (
            f"GF-02 {candidate} permanece em PILOT: falta execução auditável do candidato atual. "
            "PRESS é downstream. Scopus/WoS entram pós-PRESS por D-096; FREEZE, FORMAL e PRISMA continuam bloqueados."
        )
    elif phase == "GF02_NOISE_REVIEW":
        body = (
            f"GF-02 {candidate}: PILOT executado; revisão humana da amostra de ruído ainda pendente. "
            "PRESS vem depois da decisão READY_FOR_PRESS. Scopus/WoS são pós-PRESS (D-096)."
        )
    elif phase == "GF02_HUMAN_DECISION":
        body = (
            f"GF-02 {candidate}: evidência pré-PRESS pronta para decisão humana. Registrar READY_FOR_PRESS ou NOT_READY_FOR_PRESS. "
            "Scopus/WoS não são bloqueadores pré-PRESS; entram depois do PRESS por D-096."
        )
    elif phase == "GF03_PRESS":
        body = "GF-02 pré-PRESS está pronto. O gate atual é GF-03 PRESS. Após o parecer, incorporar mudanças e então traduzir/validar Scopus e WoS."
    else:
        body = "PRESS concluído: fase pós-PRESS de tradução/validação licenciada de Scopus/WoS. FREEZE e execução FORMAL permanecem downstream."
    return {"title": "EXECUÇÃO CIENTÍFICA", "body": body}


__all__ = ["CANONICAL_SEQUENCE", "derive_article1_scientific_status", "scientific_execution_card"]
