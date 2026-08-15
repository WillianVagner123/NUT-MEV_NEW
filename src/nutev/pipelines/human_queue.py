"""Single human/external action queue for the one-button Article 1 engine.

The queue never makes scientific decisions. It translates the persisted Article 1
phase into explicit work that must be performed by a human or an external licensed
service before the automatic controller can continue.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _task(
    *,
    task_id: str,
    kind: str,
    title: str,
    instruction: str,
    phase: str,
    evidence_path: str = "",
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "kind": kind,
        "title": title,
        "instruction": instruction,
        "phase": phase,
        "evidence_path": evidence_path,
        "blocking": bool(blocking),
        "decision_inferred": False,
        "status": "OPEN",
    }


def build_human_queue(
    project_root: Path,
    *,
    scientific_status: dict[str, Any],
) -> dict[str, Any]:
    """Return the currently required human/external tasks for Article 1.

    Only the current blocking phase is surfaced on the operational page. More
    detailed review workspaces may expose multiple records internally, but the
    one-button UI remains focused on the next legitimate action.
    """
    project = Path(project_root)
    phase = str(scientific_status.get("article1_current_phase") or "")
    gf02 = scientific_status.get("gf02") or {}
    tasks: list[dict[str, Any]] = []

    if phase == "GF02_NOISE_REVIEW":
        manifest_path = Path(str(gf02.get("latest_manifest") or ""))
        sample_path = ""
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                manifest = {}
            sample_path = str(manifest.get("rescue_only_sample") or "")
        tasks.append(
            _task(
                task_id="gf02_noise_review",
                kind="HUMAN_REVIEW",
                title="Revisar a amostra rescue-only",
                instruction=(
                    "Classifique todos os registros da amostra rescue-only e identifique o revisor. "
                    "O Engine não estima precisão nem aceita campos vazios como decisão. Depois, use CONTINUAR."
                ),
                phase=phase,
                evidence_path=sample_path,
            )
        )
    elif phase == "GF02_HUMAN_DECISION":
        tasks.append(
            _task(
                task_id="gf02_ready_for_press",
                kind="HUMAN_DECISION",
                title="Decidir prontidão para PRESS",
                instruction=(
                    "Registre explicitamente READY_FOR_PRESS ou NOT_READY_FOR_PRESS com base na evidência do PILOT "
                    "e na revisão de ruído. O software não pode inferir esta decisão. Depois, use CONTINUAR."
                ),
                phase=phase,
                evidence_path=str(project / "07_logs" / "gf02" / "gate_status.json"),
            )
        )
    elif phase == "GF03_PRESS":
        tasks.append(
            _task(
                task_id="gf03_press",
                kind="EXTERNAL_REVIEW",
                title="Concluir PRESS",
                instruction=(
                    "Submeta/conclua a revisão PRESS e registre o parecer real, identidade do revisor, data, "
                    "mudanças solicitadas e decisão final. O Engine continua somente quando a evidência PRESS existir."
                ),
                phase=phase,
                evidence_path=str(project / "07_logs" / "scientific_gates" / "press.json"),
            )
        )
    elif phase == "POST_PRESS_PROVIDER_VALIDATION":
        tasks.append(
            _task(
                task_id="post_press_licensed_providers",
                kind="LICENSED_EXTERNAL_EXECUTION",
                title="Executar/registrar Scopus e Web of Science",
                instruction=(
                    "Incorpore o parecer PRESS, traduza a estratégia final para Scopus/Web of Science e registre a "
                    "execução PILOT licenciada real. O Engine não substitui essas bases por outro provedor."
                ),
                phase=phase,
            )
        )
    elif phase in {"CLOSE_SCIENTIFIC_GATES", "GF_SCIENTIFIC_GATES"}:
        tasks.append(
            _task(
                task_id="close_scientific_gates",
                kind="HUMAN_GOVERNANCE",
                title="Fechar gates científicos pendentes",
                instruction=(
                    "Resolva os gates científicos ainda pendentes com evidência real, incluindo identidades/calibração "
                    "de revisores quando aplicável. Depois, use CONTINUAR."
                ),
                phase=phase,
                evidence_path=str(project / "00_config" / "scientific_gates.json"),
            )
        )
    elif phase in {"FREEZE", "GF10_FREEZE"}:
        tasks.append(
            _task(
                task_id="gf10_freeze",
                kind="HUMAN_AUTHORIZATION",
                title="Autorizar o FREEZE",
                instruction=(
                    "Registre a autorização humana GF-10 e o freeze imutável vinculado à estratégia, Git SHA, "
                    "configuração e evidências dos gates. O Engine não cria essa autorização por conta própria."
                ),
                phase=phase,
                evidence_path=str(project / "00_config" / "search_freeze.json"),
            )
        )
    elif phase in {"SCREENING_HUMAN_REVIEW", "FULLTEXT_HUMAN_REVIEW", "ABCD_HUMAN_REVIEW", "ADJUDICATION"}:
        tasks.append(
            _task(
                task_id=phase.lower(),
                kind="HUMAN_REVIEW",
                title="Revisão humana necessária",
                instruction=(
                    "Existem unidades pendentes de revisão/consenso/adjudicação. Complete somente as unidades abertas; "
                    "decisões originais e reviewer slots permanecem preservados. Depois, use CONTINUAR."
                ),
                phase=phase,
            )
        )

    return {
        "schema_version": 1,
        "phase": phase,
        "open_task_count": len(tasks),
        "has_blocking_task": any(bool(task.get("blocking")) for task in tasks),
        "tasks": tasks,
        "scientific_decision_inferred": False,
    }


def write_human_queue(
    project_root: Path,
    *,
    scientific_status: dict[str, Any],
) -> dict[str, Any]:
    payload = build_human_queue(project_root, scientific_status=scientific_status)
    path = Path(project_root) / "07_logs" / "engine" / "human_queue.json"
    _atomic_json(path, payload)
    return {**payload, "path": str(path)}


__all__ = ["build_human_queue", "write_human_queue"]
