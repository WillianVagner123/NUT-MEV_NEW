"""Minimal one-button execution surface for the canonical Article 1 engine."""
from __future__ import annotations

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
        "GF02_PUBMED_PILOT": "Busca PILOT PubMed",
        "GF02_NOISE_REVIEW": "Revisão humana da amostra",
        "GF02_HUMAN_DECISION": "Decisão READY_FOR_PRESS",
        "GF03_PRESS": "PRESS",
        "POST_PRESS_PROVIDER_VALIDATION": "Validação pós-PRESS",
    }.get(phase, phase or "Pronto")


def _status_copy(state: dict, scientific: dict) -> tuple[str, str]:
    status = str(state.get("status") or "READY") if state else "READY"
    phase = str(scientific.get("article1_current_phase") or "")
    if status == "FAILED":
        return "Interrompido", "Seu progresso foi salvo. Clique CONTINUAR para retomar do último checkpoint."
    if status == "WAITING_HUMAN":
        return "Aguardando você", str(state.get("last_message") or "Existe um gate humano pendente.")
    if status == "WAITING_EXTERNAL":
        return "Aguardando etapa externa", str(state.get("last_message") or "Existe um gate externo pendente.")
    if status == "COMPLETE":
        return "Concluído", "Todas as etapas atualmente automatizadas foram concluídas."
    if state and status == "RUNNING":
        return "Pronto para continuar", "Uma execução anterior foi interrompida; o checkpoint está salvo."
    if phase == "GF02_PUBMED_PILOT":
        return "Pronto", "O Engine vai executar automaticamente tudo que puder e salvar cada avanço."
    return "Pronto para continuar", "O Engine detectou o ponto científico atual e continuará a partir dele."


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
            min-height: 4.15rem;
            border-radius: 18px;
            font-size: 1.18rem;
            font-weight: 760;
            letter-spacing: .01em;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 24px !important;
            box-shadow: 0 16px 44px rgba(20, 35, 55, 0.07);
        }
        .nutev-kicker {font-size: .76rem; letter-spacing: .13em; font-weight: 750; opacity: .56;}
        .nutev-title {font-size: 2.05rem; line-height: 1.08; font-weight: 780; margin: .45rem 0 .5rem 0;}
        .nutev-sub {font-size: 1rem; opacity: .70; margin-bottom: 1.5rem;}
        .nutev-state {font-size: 1.05rem; font-weight: 720; margin-bottom: .25rem;}
        .nutev-message {font-size: .94rem; opacity: .74; margin-bottom: .25rem;}
        .nutev-phase {font-size: .82rem; opacity: .58; margin: .7rem 0 .9rem 0;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 2.6, 1])
    del left, right
    with center:
        with st.container(border=True):
            st.markdown('<div class="nutev-kicker">NUTEV EVIDENCE ENGINE</div>', unsafe_allow_html=True)
            st.markdown('<div class="nutev-title">Um botão. O Engine cuida do resto.</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="nutev-sub">Executa o fluxo automático, salva checkpoints e retoma exatamente do ponto interrompido.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="nutev-state">{title}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="nutev-message">{message}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="nutev-phase">Etapa atual: {_phase_label(phase)}</div>',
                unsafe_allow_html=True,
            )

            if st.button(
                button_label,
                type="primary",
                use_container_width=True,
                key="article1_engine_run_all",
            ):
                status_box = st.status("NutEV em execução...", expanded=True)

                def progress(text: str) -> None:
                    status_box.write(text)

                try:
                    result = run_or_resume_article1_engine(
                        repo,
                        project_root=project_root,
                        progress_fn=progress,
                    )
                except Exception as exc:
                    status_box.update(
                        label="Execução interrompida — checkpoint salvo",
                        state="error",
                        expanded=True,
                    )
                    st.error(str(exc))
                else:
                    result_status = str(result.get("status") or "")
                    if result_status == "WAITING_HUMAN":
                        status_box.update(
                            label="Automação concluída até o gate humano",
                            state="complete",
                            expanded=False,
                        )
                    elif result_status == "WAITING_EXTERNAL":
                        status_box.update(
                            label="Automação concluída até o gate externo",
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
            "O Engine nunca atravessa gates humanos ou externos sozinho. Ele para, salva o estado "
            "e continua depois pelo mesmo botão."
        )


__all__ = ["render_article1_play_panel"]
