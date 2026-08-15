"""Minimal one-button execution surface for the canonical Article 1 engine."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from nutev.pipelines.article1_engine import (
    engine_button_label,
    load_article1_engine_state,
    run_or_resume_article1_engine,
)
from nutev.search.article1_scientific_status import derive_article1_scientific_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _phase_label(phase: str) -> str:
    return {
        "GF02_PUBMED_PILOT": "PILOT PubMed",
        "GF02_NOISE_REVIEW": "Revisão da amostra",
        "GF02_HUMAN_DECISION": "Decisão READY_FOR_PRESS",
        "GF03_PRESS": "PRESS",
        "POST_PRESS_PROVIDER_VALIDATION": "Scopus / Web of Science",
        "CLOSE_SCIENTIFIC_GATES": "Gates científicos",
        "FREEZE": "GF-10 / FREEZE",
        "FORMAL_EXECUTION": "Execução FORMAL",
        "SCREENING_INITIALIZATION": "Preparando triagem",
        "SCREENING_REVIEWER_ASSIGNMENT": "Revisores R1 / R2",
        "TITLE_ABSTRACT_HUMAN_REVIEW": "Título e resumo",
        "SCREENING_HUMAN_REVIEW": "Título e resumo",
        "FULLTEXT_HUMAN_REVIEW": "Texto completo",
        "ABCD_HUMAN_REVIEW": "ABCD-NutEV 34/34",
        "RELATIONS_HUMAN_REVIEW": "Relações ABCD",
        "ADJUDICATION": "Adjudicação",
        "SYNTHESIS_PRISMA": "Síntese e PRISMA",
        "COMPLETE": "Concluído",
    }.get(phase, phase or "Pronto")


def _load_human_queue(project_root: Path) -> dict:
    path = Path(project_root) / "07_logs" / "engine" / "human_queue.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status_copy(state: dict, scientific: dict) -> tuple[str, str]:
    status = str(state.get("status") or "READY") if state else "READY"
    phase = str(scientific.get("article1_current_phase") or "")
    if phase == "COMPLETE":
        return "Concluído", "Fluxo FORMAL, síntese e pacote PRISMA validados."
    if status == "FAILED":
        return "Interrompido", "Seu progresso foi salvo. Clique CONTINUAR para retomar do último checkpoint."
    if status == "WAITING_HUMAN":
        return "Aguardando você", str(state.get("last_message") or "Existe um gate humano pendente.")
    if status == "WAITING_EXTERNAL":
        return "Aguardando etapa externa", str(state.get("last_message") or "Existe um gate externo pendente.")
    if state and status == "RUNNING":
        return "Pronto para continuar", "Uma execução anterior foi interrompida; o checkpoint está salvo."
    if phase == "GF02_PUBMED_PILOT":
        return "Pronto", "Clique uma vez. O Engine executa tudo que estiver autorizado e salva cada avanço."
    return "Pronto para continuar", "O Engine detectou automaticamente o ponto atual e continua dali."


def _render_human_task(project_root: Path) -> None:
    queue = _load_human_queue(project_root)
    tasks = list(queue.get("tasks") or [])
    if not tasks:
        return
    task = tasks[0]
    title = str(task.get("title") or "Ação humana necessária")
    instruction = str(task.get("instruction") or "Complete a ação pendente e depois use CONTINUAR.")
    evidence_path = str(task.get("evidence_path") or "")
    details = task.get("details") or {}
    st.markdown(
        f"""
        <div class="nutev-human-card">
          <div class="nutev-human-kicker">PRECISO DE VOCÊ</div>
          <div class="nutev-human-title">{title}</div>
          <div class="nutev-human-text">{instruction}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    compact = []
    for label, key in (
        ("Total", "total"),
        ("Resolvidos", "resolved"),
        ("Pendentes", "pending"),
        ("Adjudicação", "pending_adjudication"),
        ("Incluídos", "included_documents"),
    ):
        if details.get(key) is not None:
            compact.append(f"{label}: {details[key]}")
    if compact:
        st.caption(" · ".join(compact))
    if evidence_path:
        st.caption(f"Arquivo de trabalho: {evidence_path}")


def render_article1_play_panel(project_root: Path) -> None:
    repo = _repo_root()
    state = load_article1_engine_state(project_root)
    scientific = derive_article1_scientific_status(repo, project_root)
    phase = str(scientific.get("article1_current_phase") or "")
    title, message = _status_copy(state, scientific)
    button_label = engine_button_label(repo, project_root)

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button {
            min-height: 4.4rem;
            border-radius: 20px;
            font-size: 1.18rem;
            font-weight: 760;
            letter-spacing: .01em;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 24px !important;
            box-shadow: 0 18px 50px rgba(20, 35, 55, 0.07);
        }
        .nutev-kicker {font-size: .72rem; letter-spacing: .15em; font-weight: 780; opacity: .52;}
        .nutev-title {font-size: 2.15rem; line-height: 1.05; font-weight: 790; margin: .5rem 0 .55rem 0;}
        .nutev-sub {font-size: 1rem; opacity: .66; margin-bottom: 1.6rem;}
        .nutev-state {font-size: 1.08rem; font-weight: 740; margin-bottom: .25rem;}
        .nutev-message {font-size: .94rem; opacity: .72; margin-bottom: .25rem;}
        .nutev-phase {font-size: .82rem; opacity: .56; margin: .8rem 0 1rem 0;}
        .nutev-human-card {
            margin: .7rem 0 .7rem 0;
            padding: 1rem 1.05rem;
            border-radius: 16px;
            border: 1px solid rgba(120, 120, 120, .18);
            background: rgba(120, 120, 120, .05);
        }
        .nutev-human-kicker {font-size: .70rem; letter-spacing: .13em; font-weight: 800; opacity: .56;}
        .nutev-human-title {font-size: 1.04rem; font-weight: 760; margin: .25rem 0 .3rem 0;}
        .nutev-human-text {font-size: .91rem; line-height: 1.45; opacity: .76;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 2.8, 1])
    del left, right
    with center:
        with st.container(border=True):
            st.markdown('<div class="nutev-kicker">NUTEV EVIDENCE ENGINE</div>', unsafe_allow_html=True)
            st.markdown('<div class="nutev-title">Rodar tudo.</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="nutev-sub">Um fluxo, um checkpoint, uma próxima ação.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="nutev-state">{title}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="nutev-message">{message}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="nutev-phase">Etapa atual · {_phase_label(phase)}</div>',
                unsafe_allow_html=True,
            )

            _render_human_task(project_root)

            clicked = st.button(
                button_label,
                type="primary",
                use_container_width=True,
                key="article1_engine_run_all",
                disabled=phase == "COMPLETE",
            )
            if clicked:
                status_box = st.status("NutEV em execução...", expanded=True)

                def progress(text: str) -> None:
                    status_box.write(text)

                try:
                    result = run_or_resume_article1_engine(
                        repo,
                        project_root=project_root,
                        progress_fn=progress,
                    )
                except BaseException as exc:
                    status_box.update(
                        label="Execução interrompida — checkpoint salvo",
                        state="error",
                        expanded=True,
                    )
                    st.error(str(exc) or type(exc).__name__)
                else:
                    result_status = str(result.get("status") or "")
                    if result_status in {"WAITING_HUMAN", "WAITING_EXTERNAL"}:
                        status_box.update(
                            label="Automação concluída até a próxima ação",
                            state="complete",
                            expanded=False,
                        )
                    elif result_status == "COMPLETE":
                        status_box.update(label="Execução concluída", state="complete", expanded=False)
                    else:
                        status_box.update(label="Checkpoint salvo", state="complete", expanded=False)
                    st.rerun()

            state = load_article1_engine_state(project_root)
            if state:
                last_message = str(state.get("last_message") or "")
                updated_at = str(state.get("updated_at") or "")
                if last_message:
                    st.caption(f"Último checkpoint: {last_message}")
                if updated_at:
                    st.caption(f"Salvo em {updated_at}")
                if state.get("last_error"):
                    st.caption(f"Último erro: {state['last_error']}")

        st.caption(
            "O Engine automatiza tudo que é computacional. Decisões científicas humanas são preservadas como gates explícitos."
        )


__all__ = ["render_article1_play_panel"]
