"""Inline human workbench for the one-button Article 1 product surface.

Only the human action required by the current persisted phase is rendered. The
workbench never infers a scientific decision and writes to the same canonical
ledgers/artifacts used by the engine controller.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from nutev.review.article1_runtime import (
    article1_reviewer_assignment,
    set_article1_reviewer_assignment,
)
from nutev.review.article1_screening_runtime import (
    adjudicate_screening,
    full_text_queue,
    submit_screening_decision,
    title_abstract_queue,
)
from nutev.review.gf02_noise_review import (
    ALLOWED_CLASSIFICATIONS,
    read_rescue_only_sample,
    review_progress,
    save_rescue_only_classification,
)
from nutev.review.screening import EXCLUSION_REASONS
from nutev.search.strategy_registry import default_registry_path


def _session_id(scientific: dict[str, Any]) -> str:
    return str((scientific.get("downstream") or {}).get("session_id") or "").strip()


def _assignment(db_path: Path, session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    return article1_reviewer_assignment(db_path, session_id)


def _record_label(row: dict[str, Any]) -> str:
    title = str(row.get("title") or "Sem título").strip()
    year = str(row.get("year") or "").strip()
    suffix = str(row.get("document_id") or "")[-10:]
    return f"{title[:95]} · {year} · {suffix}"


def _gf02_sample_path(scientific: dict[str, Any]) -> Path | None:
    manifest_path = Path(str((scientific.get("gf02") or {}).get("latest_manifest") or ""))
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    sample = Path(str(payload.get("rescue_only_sample") or ""))
    return sample if sample.is_file() else None


def _gf02_row_label(row: dict[str, str]) -> str:
    sample_id = str(row.get("sample_id") or "").strip()
    title = str(row.get("title") or "Sem título").strip()
    return f"{sample_id} · {title[:100]}"


def _render_gf02_noise_review(scientific: dict[str, Any]) -> None:
    sample_path = _gf02_sample_path(scientific)
    if sample_path is None:
        st.error("A amostra rescue-only não foi localizada no manifest GF-02 atual.")
        return
    try:
        rows = read_rescue_only_sample(sample_path)
        progress = review_progress(sample_path)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown("#### Revisão rescue-only")
    st.caption(
        "Faça a classificação humana aqui. O Engine apenas salva sua decisão no CSV auditável; "
        "não estima precisão e não preenche decisões automaticamente."
    )
    st.caption(
        f"Progresso: {progress['resolved']}/{progress['total']} classificados · "
        f"{progress['pending']} pendentes"
    )
    if progress["complete"]:
        st.success("A amostra está completa. Clique CONTINUAR para registrar a próxima decisão científica.")
        return

    pending = [
        row
        for row in rows
        if not (
            str(row.get("classification") or "").strip()
            and str(row.get("reviewer") or "").strip()
        )
    ]
    by_label = {_gf02_row_label(row): row for row in pending}
    selected_label = st.selectbox(
        "Registro pendente",
        list(by_label),
        key=f"gf02_noise_record_{sample_path}",
    )
    row = by_label[selected_label]
    sample_id = str(row.get("sample_id") or "").strip()
    title = str(row.get("title") or "Sem título").strip()
    st.markdown(f"**{title}**")
    metadata = []
    pmid = str(row.get("pmid") or "").strip()
    doi = str(row.get("doi") or "").strip()
    if pmid:
        metadata.append(f"PMID: {pmid}")
    if doi:
        metadata.append(f"DOI: {doi}")
    if metadata:
        st.caption(" · ".join(metadata))
    st.caption(f"Amostra: {sample_id}")

    existing_reviewers = [
        str(item.get("reviewer") or "").strip()
        for item in rows
        if str(item.get("reviewer") or "").strip()
    ]
    default_reviewer = existing_reviewers[0] if existing_reviewers else ""
    with st.form(f"gf02_noise_form_{sample_id}"):
        reviewer = st.text_input("Revisor humano", value=default_reviewer)
        classification = st.selectbox(
            "Classificação",
            [""] + list(ALLOWED_CLASSIFICATIONS),
            format_func=lambda value: "Selecione..." if not value else value,
        )
        note = st.text_area("Nota / justificativa", value=str(row.get("note") or ""))
        save = st.form_submit_button("Salvar e próximo", use_container_width=True)
    if save:
        try:
            save_rescue_only_classification(
                sample_path,
                sample_id=sample_id,
                classification=classification,
                reviewer=reviewer,
                note=note,
            )
        except (OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.success("Classificação humana salva no artefato GF-02.")
            st.rerun()


def _render_assignment(project_root: Path, scientific: dict[str, Any]) -> None:
    session_id = _session_id(scientific)
    if not session_id:
        st.error("Sessão FORMAL ainda não foi persistida. Use CONTINUAR para inicializá-la.")
        return
    db_path = default_registry_path(project_root)
    current = _assignment(db_path, session_id) or {}
    st.markdown("#### Revisores do Artigo 1")
    st.caption("R1, R2 e adjudicador devem ser pessoas reais e distintas. Nenhuma decisão é preenchida automaticamente.")
    with st.form(f"a1_inline_assignment_{session_id}"):
        r1 = st.text_input("Revisor 1", value=str(current.get("reviewer_1_name") or ""))
        r2 = st.text_input("Revisor 2", value=str(current.get("reviewer_2_name") or ""))
        adjudicator = st.text_input("Adjudicador", value=str(current.get("adjudicator_name") or ""))
        notes = st.text_area("Notas", value=str(current.get("notes") or ""))
        save = st.form_submit_button("Salvar revisores", use_container_width=True)
    if save:
        try:
            set_article1_reviewer_assignment(
                db_path,
                session_id=session_id,
                reviewer_1_name=r1,
                reviewer_2_name=r2,
                adjudicator_name=adjudicator,
                notes=notes,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success("Revisores registrados. O checkpoint científico foi preservado.")
            st.rerun()


def _pending_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not row.get("final_action")]


def _missing_slots(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not row.get("reviewer_1"):
        missing.append("REVIEWER_1")
    if not row.get("reviewer_2"):
        missing.append("REVIEWER_2")
    return missing


def _reviewer_for_slot(assignment: dict[str, Any], slot: str) -> str:
    return str(
        assignment.get("reviewer_1_name")
        if slot == "REVIEWER_1"
        else assignment.get("reviewer_2_name")
    )


def _render_adjudication(
    db_path: Path,
    *,
    session_id: str,
    row: dict[str, Any],
    phase: str,
    assignment: dict[str, Any],
) -> None:
    document_id = str(row["document_id"])
    st.warning("R1 e R2 divergiram ou mantiveram dúvida. A decisão final exige o adjudicador registrado.")
    with st.form(f"a1_inline_adj_{phase}_{document_id}"):
        final_decision = st.selectbox("Decisão final", ["INCLUDE", "EXCLUDE"])
        final_family = ""
        if phase == "FULL_TEXT" and final_decision == "INCLUDE":
            final_family = st.text_input("Família documental final")
        rationale = st.text_area("Justificativa da adjudicação")
        save = st.form_submit_button("Registrar adjudicação", use_container_width=True)
    if save:
        try:
            adjudicate_screening(
                db_path,
                session_id=session_id,
                document_id=document_id,
                phase=phase,
                final_decision=final_decision,
                adjudicator_name=str(assignment.get("adjudicator_name") or ""),
                rationale=rationale,
                final_family=final_family,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success("Adjudicação registrada.")
            st.rerun()


def _render_dual_screening(
    project_root: Path,
    scientific: dict[str, Any],
    *,
    phase: str,
) -> None:
    session_id = _session_id(scientific)
    if not session_id:
        st.error("Sessão FORMAL ausente. Use CONTINUAR para recuperar o checkpoint.")
        return
    db_path = default_registry_path(project_root)
    assignment = _assignment(db_path, session_id)
    if not assignment:
        _render_assignment(project_root, scientific)
        return

    rows = (
        title_abstract_queue(db_path, session_id=session_id)
        if phase == "TITLE_ABSTRACT"
        else full_text_queue(db_path, session_id=session_id, project_root=project_root)
    )
    pending = _pending_rows(rows)
    if not pending:
        st.success("Esta etapa humana está completa. Clique CONTINUAR para o Engine avançar.")
        return

    by_label = {_record_label(row): row for row in pending}
    label = st.selectbox(
        "Registro pendente",
        list(by_label),
        key=f"a1_inline_record_{phase}_{session_id}",
    )
    row = by_label[label]
    document_id = str(row["document_id"])
    st.markdown(f"**{row.get('title') or 'Sem título'}**")
    metadata = []
    for key, prefix in (("year", "Ano"), ("doi", "DOI"), ("pmid", "PMID")):
        value = str(row.get(key) or "").strip()
        if value:
            metadata.append(f"{prefix}: {value}")
    if metadata:
        st.caption(" · ".join(metadata))
    abstract = str(row.get("abstract") or "").strip()
    if abstract:
        st.write(abstract)
    if phase == "FULL_TEXT":
        full_text_path = str(row.get("full_text_path") or "").strip()
        flag = str(row.get("screen_flag") or "").strip()
        if flag:
            st.caption(f"Disponibilidade técnica: {flag}")
        if full_text_path:
            st.caption(f"Texto organizado: {full_text_path}")

    if row.get("requires_adjudication"):
        _render_adjudication(
            db_path,
            session_id=session_id,
            row=row,
            phase=phase,
            assignment=assignment,
        )
        return

    missing = _missing_slots(row)
    if not missing:
        st.info("As duas avaliações existem; o Engine atualizará a resolução no próximo CONTINUAR.")
        return
    slot = (
        missing[0]
        if len(missing) == 1
        else st.selectbox(
            "Avaliação a registrar",
            missing,
            format_func=lambda value: "Revisor 1" if value == "REVIEWER_1" else "Revisor 2",
            key=f"a1_inline_slot_{phase}_{document_id}",
        )
    )
    reviewer_name = _reviewer_for_slot(assignment, slot)
    st.caption(f"Registrando como {'R1' if slot == 'REVIEWER_1' else 'R2'} · {reviewer_name}. A avaliação do outro revisor não é exibida antes do pareamento.")

    with st.form(f"a1_inline_screen_{phase}_{document_id}_{slot}"):
        decision = st.selectbox("Decisão", ["INCLUDE", "EXCLUDE", "DOUBT"])
        reason = ""
        if decision == "EXCLUDE":
            reason = st.selectbox(
                "Motivo da exclusão",
                list(EXCLUSION_REASONS),
                format_func=lambda value: value.replace("_", " ").title(),
            )
        family = ""
        if phase == "FULL_TEXT" and decision == "INCLUDE":
            family = st.text_input("Família documental")
        notes = st.text_area("Notas")
        save = st.form_submit_button("Salvar decisão humana", use_container_width=True)
    if save:
        try:
            submit_screening_decision(
                db_path,
                session_id=session_id,
                document_id=document_id,
                phase=phase,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                decision=decision,
                exclusion_reason=reason,
                family=family,
                notes=notes,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success("Decisão salva. O próximo registro pendente será carregado.")
            st.rerun()


def _render_abcd_or_relations(project_root: Path, scientific: dict[str, Any]) -> None:
    session_id = _session_id(scientific)
    if not session_id:
        st.error("Sessão FORMAL não encontrada.")
        return
    st.markdown("#### Trabalho humano FORMAL")
    st.caption("O workspace abaixo usa exatamente a sessão atual. Decisões humanas continuam separadas da automação.")
    from nutev.ui.article1_runtime_panel import render_article1_runtime_panel

    render_article1_runtime_panel(
        project_root,
        registry_path=default_registry_path(project_root),
    )


def render_article1_human_workbench(
    project_root: Path,
    scientific: dict[str, Any],
) -> None:
    """Render the current human task inline; render nothing for automatic phases."""
    phase = str(scientific.get("article1_current_phase") or "")
    if phase == "GF02_NOISE_REVIEW":
        _render_gf02_noise_review(scientific)
    elif phase == "SCREENING_REVIEWER_ASSIGNMENT":
        _render_assignment(project_root, scientific)
    elif phase in {"TITLE_ABSTRACT_HUMAN_REVIEW", "SCREENING_HUMAN_REVIEW"}:
        _render_dual_screening(project_root, scientific, phase="TITLE_ABSTRACT")
    elif phase == "FULLTEXT_HUMAN_REVIEW":
        _render_dual_screening(project_root, scientific, phase="FULL_TEXT")
    elif phase in {"ABCD_HUMAN_REVIEW", "RELATIONS_HUMAN_REVIEW", "ADJUDICATION"}:
        _render_abcd_or_relations(project_root, scientific)


__all__ = ["render_article1_human_workbench"]
