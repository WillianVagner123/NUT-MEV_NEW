"""Single human/external action queue for the one-button Article 1 engine.

The queue never makes scientific decisions. It translates persisted state into
the one blocking action that must be completed before automatic execution can
continue.
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
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "kind": kind,
        "title": title,
        "instruction": instruction,
        "phase": phase,
        "evidence_path": evidence_path,
        "blocking": bool(blocking),
        "details": details or {},
        "decision_inferred": False,
        "status": "OPEN",
    }


def build_human_queue(
    project_root: Path,
    *,
    scientific_status: dict[str, Any],
) -> dict[str, Any]:
    """Return only the currently blocking human/external task for Article 1."""
    project = Path(project_root)
    phase = str(scientific_status.get("article1_current_phase") or "")
    gf02 = scientific_status.get("gf02") or {}
    downstream = scientific_status.get("downstream") or {}
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
    elif phase == "SCREENING_REVIEWER_ASSIGNMENT":
        tasks.append(
            _task(
                task_id="screening_reviewer_assignment",
                kind="HUMAN_GOVERNANCE",
                title="Confirmar R1, R2 e adjudicador",
                instruction=(
                    "Defina três identidades humanas reais e distintas para R1, R2 e adjudicador. "
                    "Nenhuma decisão de triagem é copiada ou inferida. Depois, use CONTINUAR."
                ),
                phase=phase,
                evidence_path=str(project / "01_querypacks" / "search_registry.sqlite3"),
                details={"session_id": downstream.get("session_id")},
            )
        )
    elif phase in {"TITLE_ABSTRACT_HUMAN_REVIEW", "SCREENING_HUMAN_REVIEW"}:
        screening = downstream.get("screening") or {}
        title = screening.get("title_abstract") or {}
        tasks.append(
            _task(
                task_id="title_abstract_dual_review",
                kind="HUMAN_REVIEW",
                title="Triagem R1/R2 de título e resumo",
                instruction=(
                    "Complete somente os registros pendentes em R1 e R2. DOUBT permanece registrado e conflitos "
                    "seguem para adjudicação. Quando a fila zerar, use CONTINUAR."
                ),
                phase=phase,
                evidence_path=str(project / "06_review" / "formal_screening_queue.jsonl"),
                details={
                    "total": title.get("total"),
                    "resolved": title.get("resolved"),
                    "pending": title.get("pending"),
                    "pending_adjudication": title.get("pending_adjudication"),
                    "session_id": downstream.get("session_id"),
                },
            )
        )
    elif phase == "FULLTEXT_HUMAN_REVIEW":
        screening = downstream.get("screening") or {}
        full = screening.get("full_text") or {}
        tasks.append(
            _task(
                task_id="fulltext_dual_review",
                kind="HUMAN_REVIEW",
                title="Triagem R1/R2 de texto completo",
                instruction=(
                    "Revise os textos completos pendentes, registre INCLUDE/EXCLUDE/DOUBT e a família documental "
                    "quando incluir. Conflitos e dúvidas permanecem bloqueados até adjudicação."
                ),
                phase=phase,
                evidence_path=str(project / "06_review" / "formal_screening_queue.jsonl"),
                details={
                    "total": full.get("total"),
                    "resolved": full.get("resolved"),
                    "pending": full.get("pending"),
                    "pending_adjudication": full.get("pending_adjudication"),
                    "session_id": downstream.get("session_id"),
                },
            )
        )
    elif phase == "ABCD_HUMAN_REVIEW":
        runtime = downstream.get("runtime") or {}
        tasks.append(
            _task(
                task_id="abcd_34x2",
                kind="HUMAN_EXTRACTION",
                title="Completar ABCD-NutEV 34/34 em R1 e R2",
                instruction=(
                    "Complete os 34 componentes para cada documento incluído nos dois reviewer slots e adjudique "
                    "somente divergências reais. Ausência de preenchimento nunca significa ausência do componente."
                ),
                phase=phase,
                details={
                    "included_documents": runtime.get("included_documents"),
                    "documents": runtime.get("documents") or [],
                    "session_id": downstream.get("session_id"),
                },
            )
        )
    elif phase in {"RELATIONS_HUMAN_REVIEW", "ADJUDICATION"}:
        runtime = downstream.get("runtime") or {}
        tasks.append(
            _task(
                task_id="abcd_relations_dual_review",
                kind="HUMAN_EXTRACTION",
                title="Fechar relações explícitas e adjudicações",
                instruction=(
                    "R1 e R2 devem encerrar explicitamente a revisão de relações. Divergências de conjunto ficam "
                    "pendentes até decisão do adjudicador; coocorrência não é tratada como relação explícita."
                ),
                phase=phase,
                details={
                    "documents": runtime.get("documents") or [],
                    "session_id": downstream.get("session_id"),
                },
            )
        )

    return {
        "schema_version": 2,
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
