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
from nutev.pipelines.article1_pre_review_collection import (
    pre_review_collection_status,
    run_pre_review_collection,
)
from nutev.pipelines.article1_preflight import run_article1_preflight
from nutev.search.article1_scientific_status import derive_article1_scientific_status
from nutev.ui.article1_human_workbench import render_article1_human_workbench
from nutev.ui.gf02_press_decision_workbench import render_gf02_press_decision
from nutev.ui.gf02_review_workbench import render_gf02_easy_review
from nutev.ui.press_gate_workbench import render_press_gate_workbench


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
        return (
            "Automação concluída",
            "Tudo que estava computacionalmente autorizado foi executado. A revisão humana está no final desta tela.",
        )
    if status == "WAITING_EXTERNAL":
        return (
            "Automação concluída — etapa externa",
            str(state.get("last_message") or "Existe um gate externo pendente ao final do fluxo disponível."),
        )
    if state and status == "RUNNING":
        return "Pronto para continuar", "Uma execução anterior foi interrompida; o checkpoint está salvo."
    if phase == "GF02_PUBMED_PILOT":
        return "Pronto", "Clique uma vez. O Engine executa tudo que estiver autorizado e salva cada avanço."
    return "Pronto para continuar", "O Engine detectou automaticamente o ponto atual e continua dali."


def _render_human_task(project_root: Path) -> bool:
    queue = _load_human_queue(project_root)
    tasks = list(queue.get("tasks") or [])
    if not tasks:
        return False
    task = tasks[0]
    title = str(task.get("title") or "Ação humana necessária")
    instruction = str(task.get("instruction") or "Complete a ação pendente e depois use CONTINUAR.")
    evidence_path = str(task.get("evidence_path") or "")
    details = task.get("details") or {}
    st.markdown(
        f"""
        <div class="nutev-human-card">
          <div class="nutev-human-kicker">REVISÃO HUMANA · DEPOIS DA AUTOMAÇÃO</div>
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
        st.caption(f"Artefato auditável: {evidence_path}")
    return True


def _render_human_review_center(project_root: Path, scientific: dict) -> None:
    phase = str(scientific.get("article1_current_phase") or "")
    if phase == "GF03_PRESS" and not bool(pre_review_collection_status(project_root).get("complete")):
        return
    queue = _load_human_queue(project_root)
    if not list(queue.get("tasks") or []):
        return
    st.divider()
    st.markdown("### Revisão humana")
    st.caption(
        "Esta área aparece somente depois que o Engine termina tudo que pode executar sem decisão humana. "
        "Etapas científicas dependentes continuam bloqueadas até a decisão real ser registrada."
    )
    _render_human_task(project_root)
    if phase == "GF02_NOISE_REVIEW":
        render_gf02_easy_review(scientific)
    elif phase == "GF02_HUMAN_DECISION":
        render_gf02_press_decision(project_root)
    elif phase == "GF03_PRESS":
        render_press_gate_workbench(project_root)
    else:
        render_article1_human_workbench(project_root, scientific)


def _render_collection_summary(collection: dict) -> None:
    if not collection:
        return
    if collection.get("complete"):
        st.markdown("#### Coleta real pré-revisão")
        st.success(
            "Busca real concluída e organizada. Estes dados continuam NÃO-FORMAIS e não entram no PRISMA até FREEZE/FORMAL."
        )
        st.caption(
            f"Recuperados: {int(collection.get('records_returned') or 0)} · "
            f"Únicos: {int(collection.get('unique_records') or 0)} · "
            f"Duplicatas automáticas removidas: {int(collection.get('duplicates_removed') or 0)}"
        )
        executed = ", ".join(str(item) for item in (collection.get("providers_executed") or []))
        if executed:
            st.caption(f"Fontes executadas agora: {executed}")
        deferred = collection.get("providers_deferred") or []
        if deferred:
            text = ", ".join(
                f"{item.get('provider')} ({item.get('reason')})" for item in deferred
            )
            st.caption(f"Fontes que ainda dependem de acesso/exportação real: {text}")
        if collection.get("any_provider_truncated"):
            st.warning(
                "Pelo menos uma fonte informou mais resultados do que o limite recuperado nesta coleta. "
                "A truncagem ficou auditada; não é tratada como cobertura completa."
            )
        master = str(collection.get("master_corpus_path") or "")
        if master:
            st.caption(f"Corpus organizado: {master}")
        st.caption(f"Auditoria da coleta: {collection.get('path')}")
    elif collection.get("reason"):
        st.warning(f"Coleta real ainda não executável: {collection.get('reason')}")


def render_article1_play_panel(project_root: Path) -> None:
    repo = _repo_root()
    state = load_article1_engine_state(project_root)
    scientific = derive_article1_scientific_status(repo, project_root)
    phase = str(scientific.get("article1_current_phase") or "")
    title, message = _status_copy(state, scientific)
    button_label = engine_button_label(repo, project_root)
    press_pending = phase == "GF03_PRESS"
    collection = pre_review_collection_status(project_root) if press_pending else {}
    collection_complete = bool(collection.get("complete"))
    collection_can_run = bool(collection.get("can_run"))

    if press_pending and collection_complete:
        title = "Coleta real concluída — PRESS pendente"
        message = (
            f"{int(collection.get('records_returned') or 0)} registros reais foram recuperados e "
            f"{int(collection.get('unique_records') or 0)} documentos únicos foram organizados. "
            "Agora o PRESS só controla a promoção científica posterior para FREEZE/FORMAL/PRISMA."
        )
        visible_button_label = "COLETA REAL CONCLUÍDA — PRESS ABAIXO"
    elif press_pending and collection_can_run:
        title = "Pronto para buscar dados reais"
        message = (
            "O PRESS não bloqueará a coleta exploratória real. O Engine vai consultar agora todas as fontes "
            "já executáveis, salvar resultados brutos, hashes, manifests e corpus deduplicado; nada será promovido a FORMAL/PRISMA."
        )
        visible_button_label = "▶ BUSCAR E ORGANIZAR DADOS REAIS AGORA"
    elif press_pending:
        title = "Coleta real bloqueada"
        message = str(collection.get("reason") or "Não existe estratégia PILOT não-PRISMA executável.")
        visible_button_label = "COLETA BLOQUEADA — VER MOTIVO ABAIXO"
    else:
        visible_button_label = button_label

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
                '<div class="nutev-sub">Primeiro a automação. Depois, somente a revisão humana necessária.</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'<div class="nutev-state">{title}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="nutev-message">{message}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="nutev-phase">Etapa atual · {_phase_label(phase)}</div>',
                unsafe_allow_html=True,
            )

            clicked = st.button(
                visible_button_label,
                type="primary",
                width="stretch",
                key="article1_engine_run_all",
                disabled=(
                    phase == "COMPLETE"
                    or (press_pending and collection_complete)
                    or (press_pending and not collection_can_run)
                ),
            )
            if clicked:
                status_box = st.status("NutEV em execução...", expanded=True)

                def progress(text: str) -> None:
                    status_box.write(text)

                try:
                    preflight = run_article1_preflight(repo, project_root)
                    if not preflight.get("passed"):
                        failures = [
                            str(item.get("name") or "check") + ": " + str(item.get("detail") or "")
                            for item in (preflight.get("checks") or [])
                            if not item.get("ok")
                        ]
                        raise RuntimeError("Pré-teste local falhou: " + "; ".join(failures))
                    if press_pending:
                        status_box.write(
                            "Pré-teste local aprovado. Iniciando coleta REAL não-FORMAL antes da revisão humana..."
                        )
                        result = run_pre_review_collection(project_root, progress_fn=progress)
                        if str(result.get("status") or "") not in {"COMPLETE", "COMPLETE_WITH_WARNINGS"}:
                            raise RuntimeError(
                                "Coleta real não concluída: " + str(result.get("reason") or result.get("status") or "desconhecido")
                            )
                        status_box.update(
                            label="Coleta real concluída — saídas organizadas",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        status_box.write("Pré-teste local aprovado. Iniciando/retomando a execução autorizada...")
                        result = run_or_resume_article1_engine(
                            repo,
                            project_root=project_root,
                            progress_fn=progress,
                        )
                        result_status = str(result.get("status") or "")
                        if result_status in {"WAITING_HUMAN", "WAITING_EXTERNAL"}:
                            status_box.update(
                                label="Automação concluída — revisão/etapa humana no final",
                                state="complete",
                                expanded=False,
                            )
                        elif result_status == "COMPLETE":
                            status_box.update(label="Execução concluída", state="complete", expanded=False)
                        else:
                            status_box.update(label="Checkpoint salvo", state="complete", expanded=False)
                    st.rerun()
                except BaseException as exc:
                    status_box.update(
                        label="Execução interrompida — checkpoint salvo",
                        state="error",
                        expanded=True,
                    )
                    st.error(str(exc) or type(exc).__name__)

            state = load_article1_engine_state(project_root)
            if state:
                last_message = str(state.get("last_message") or "")
                updated_at = str(state.get("updated_at") or "")
                if last_message and not (press_pending and collection_complete):
                    st.caption(f"Último checkpoint: {last_message}")
                if updated_at:
                    st.caption(f"Salvo em {updated_at}")
                if state.get("last_error"):
                    st.caption(f"Último erro: {state['last_error']}")

            if press_pending:
                _render_collection_summary(collection)
            _render_human_review_center(project_root, scientific)

        st.caption(
            "O Engine coleta e organiza primeiro tudo que pode executar de forma real e auditável. "
            "Gates humanos controlam promoção científica posterior; nunca são inferidos pelo software."
        )


__all__ = ["render_article1_play_panel"]
