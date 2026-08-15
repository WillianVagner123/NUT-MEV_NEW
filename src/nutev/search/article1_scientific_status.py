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

from nutev.search.licensed_provider_evidence import licensed_pilot_status
from nutev.search.scientific_gates import (
    global_freeze_status,
    load_freeze_record,
    load_gate_records,
    pre_freeze_blockers,
)

CANONICAL_SEQUENCE = (
    "PUBMED_PILOT",
    "PRESS",
    "INCORPORATE_PRESS",
    "SCOPUS_WOS_TRANSLATION",
    "LICENSED_PILOT",
    "CLOSE_SCIENTIFIC_GATES",
    "FREEZE",
    "FORMAL_EXECUTION",
    "SCREENING",
    "ABCD_EXTRACTION",
    "SYNTHESIS_PRISMA",
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


def _generic_gate_status(project_root: Path) -> dict[str, Any]:
    gate_path = Path(project_root) / "00_config" / "scientific_gates.json"
    if not gate_path.is_file():
        return {
            "path": str(gate_path),
            "present": False,
            "valid": False,
            "pre_freeze_complete": False,
            "blockers": ["scientific_gates_record_missing"],
            "gf10_authorized": False,
        }
    try:
        records = load_gate_records(gate_path)
        blockers = pre_freeze_blockers(records)
        freeze_status = global_freeze_status(records)
    except Exception as exc:
        return {
            "path": str(gate_path),
            "present": True,
            "valid": False,
            "pre_freeze_complete": False,
            "blockers": [f"scientific_gates_invalid:{exc}"],
            "gf10_authorized": False,
        }
    return {
        "path": str(gate_path),
        "present": True,
        "valid": True,
        "pre_freeze_complete": not blockers,
        "blockers": blockers,
        "gf10_authorized": bool(freeze_status.get("authorized")),
        "global_freeze_status": freeze_status,
    }


def _freeze_record_status(project_root: Path) -> dict[str, Any]:
    path = Path(project_root) / "00_config" / "search_freeze.json"
    if not path.is_file():
        return {"path": str(path), "present": False, "valid": False, "freeze_id": None}
    try:
        record = load_freeze_record(path)
    except Exception as exc:
        return {"path": str(path), "present": True, "valid": False, "freeze_id": None, "error": str(exc)}
    return {"path": str(path), "present": True, "valid": True, "freeze_id": record.freeze_id}


def _formal_play_status(project_root: Path) -> dict[str, Any]:
    summary_path = Path(project_root) / "12_play" / "latest_summary.json"
    summary = _load_json(summary_path)
    scientific = summary.get("scientific_state") or {}
    status = summary.get("status") or {}
    is_formal = str(scientific.get("search_type") or "").upper() == "FORMAL"
    authorized = bool(scientific.get("formal_freeze_authorized"))
    execution_status = str(status.get("execution_status") or "")
    complete = bool(
        summary
        and is_formal
        and authorized
        and bool(scientific.get("prisma_eligible"))
        and execution_status in {"COMPLETE", "COMPLETE_WITH_WARNINGS"}
    )
    return {
        "complete": complete,
        "summary_path": str(summary_path) if summary else None,
        "execution_status": execution_status or None,
        "formal_freeze_authorized": authorized,
    }


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

    licensed = licensed_pilot_status(project) if press_approved else {
        "complete": False,
        "providers": {},
        "blockers": ["PRESS_NOT_APPROVED"],
        "provider_substitution_allowed": False,
    }
    gates = _generic_gate_status(project) if licensed.get("complete") else {
        "present": False,
        "valid": False,
        "pre_freeze_complete": False,
        "blockers": ["LICENSED_PILOT_NOT_COMPLETE"],
        "gf10_authorized": False,
    }
    freeze_record = _freeze_record_status(project) if gates.get("pre_freeze_complete") else {
        "present": False,
        "valid": False,
        "freeze_id": None,
    }
    formal_play = _formal_play_status(project)

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
    elif not bool(licensed.get("complete")):
        current_phase = "POST_PRESS_PROVIDER_VALIDATION"
        next_action = "Incorporate PRESS and register real licensed Scopus/Web of Science PILOT evidence."
    elif not bool(gates.get("pre_freeze_complete")):
        current_phase = "CLOSE_SCIENTIFIC_GATES"
        next_action = "Close the remaining pre-freeze scientific gates with real evidence."
    elif not bool(gates.get("gf10_authorized")) or not bool(freeze_record.get("valid")):
        current_phase = "FREEZE"
        next_action = "Authorize GF-10 and persist the exact immutable search freeze."
    elif not bool(formal_play.get("complete")):
        current_phase = "FORMAL_EXECUTION"
        next_action = "Execute the frozen FORMAL computational chain from zero."
    else:
        current_phase = "SCREENING_HUMAN_REVIEW"
        next_action = "Complete blinded R1/R2 screening and adjudication from the formal corpus."

    blockers_to_press: list[str] = []
    if not pubmed_pilot_complete:
        blockers_to_press.append("gf02_pubmed_pilot_not_complete")
    if pubmed_pilot_complete and not noise_review_complete:
        blockers_to_press.append("gf02_noise_review_not_complete")
    if pubmed_pilot_complete and noise_review_complete and not ready_for_press:
        blockers_to_press.append("gf02_human_ready_for_press_decision_missing")

    phase_order = {
        "GF02_PUBMED_PILOT": 0,
        "GF02_NOISE_REVIEW": 1,
        "GF02_HUMAN_DECISION": 2,
        "GF03_PRESS": 3,
        "POST_PRESS_PROVIDER_VALIDATION": 4,
        "CLOSE_SCIENTIFIC_GATES": 5,
        "FREEZE": 6,
        "FORMAL_EXECUTION": 7,
        "SCREENING_HUMAN_REVIEW": 8,
    }
    phase_index = phase_order.get(current_phase, 0)

    return {
        "schema_version": 2,
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
        "press": {
            "status": press_status,
            "approved": press_approved,
            "is_next_gate": ready_for_press and not press_approved,
        },
        "scopus_wos": {
            "sequence": "POST_PRESS",
            "pre_press_blocker": False,
            "methodology_decision": "D-096",
            "licensed_pilot_complete": bool(licensed.get("complete")),
            "providers": licensed.get("providers") or {},
            "blockers": licensed.get("blockers") or [],
            "provider_substitution_allowed": False,
        },
        "scientific_gates": gates,
        "freeze": {
            "authorized": bool(gates.get("gf10_authorized")) and bool(freeze_record.get("valid")),
            "downstream": phase_index < phase_order["FREEZE"],
            **freeze_record,
        },
        "formal_execution": {
            "authorized": bool(gates.get("gf10_authorized")) and bool(freeze_record.get("valid")),
            "downstream": phase_index < phase_order["FORMAL_EXECUTION"],
            **formal_play,
        },
        "prisma": {
            "formal_count_allowed": bool(formal_play.get("complete")),
            "downstream": phase_index < phase_order["SCREENING_HUMAN_REVIEW"],
        },
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
    elif phase == "POST_PRESS_PROVIDER_VALIDATION":
        body = "PRESS concluído: registrar execuções PILOT licenciadas reais de Scopus/Web of Science. Nenhum provedor substituto fecha este gate."
    elif phase == "CLOSE_SCIENTIFIC_GATES":
        body = "PILOTs de provedores concluídos: fechar os gates científicos pré-FREEZE ainda pendentes com evidência real."
    elif phase == "FREEZE":
        body = "Gates pré-FREEZE completos: falta autorização GF-10 e o registro imutável que vincula estratégia, Git SHA e configuração."
    elif phase == "FORMAL_EXECUTION":
        body = "FREEZE válido detectado: o próximo passo é a execução FORMAL do fluxo computacional congelado."
    else:
        body = "Execução FORMAL detectada: o próximo trabalho é a revisão humana do corpus, preservando R1/R2 e adjudicação."
    return {"title": "EXECUÇÃO CIENTÍFICA", "body": body}


__all__ = ["CANONICAL_SEQUENCE", "derive_article1_scientific_status", "scientific_execution_card"]
