"""Article 1 ABCD/relations workspace inside the existing Streamlit Engine."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from nutev.analysis.article1_abcd import ABCD_CODES, ABCD_COMPONENTS, ABCD_VERSION
from nutev.review.article_screening_ledger import list_screening_sessions
from nutev.review.evidence_matrix import (
    EXECUTION_MODES,
    RELATION_DIRECTIONS,
    RELATION_TYPES,
    adjudicate_article1_abcd,
    adjudicate_article1_relation,
    article1_abcd_document_status,
    article1_reviewer_assignment,
    article1_runtime_status,
    article1_synthesis,
    compare_article1_abcd,
    compare_article1_relations,
    complete_article1_relation_review,
    included_documents,
    initialize_article1_runtime,
    set_article1_reviewer_assignment,
    submit_article1_abcd,
    submit_article1_relation,
)
from nutev.review.human_review import REVIEWER_ROLES


def _session_label(row: dict[str, Any]) -> str:
    return f"{row['session_id']} · corpus {row['build_id']} · {row['status']}"


def _document_label(row: dict[str, Any]) -> str:
    return (
        f"{str(row.get('title') or 'Sem título')[:80]} · "
        f"{row.get('year') or ''} · {str(row['document_id'])[-10:]}"
    )


def _slot_label(slot: str) -> str:
    return "Revisor 1" if slot == "REVIEWER_1" else "Revisor 2"


def _render_gf07(db_path: Path, session_id: str, active_name: str) -> None:
    assignment = article1_reviewer_assignment(db_path, session_id)
    with st.expander("GF-07 · revisores humanos", expanded=False):
        st.caption(
            "Use somente identidades humanas reais. Sem R1, R2 e adjudicador "
            "distintos, o runtime bloqueia execução FORMAL."
        )
        with st.form(f"a1_gf07_{session_id}"):
            r1 = st.text_input(
                "Revisor 1",
                value=str((assignment or {}).get("reviewer_1_name") or active_name),
            )
            r2 = st.text_input(
                "Revisor 2",
                value=str((assignment or {}).get("reviewer_2_name") or ""),
            )
            adjudicator = st.text_input(
                "Adjudicador",
                value=str((assignment or {}).get("adjudicator_name") or ""),
            )
            notes = st.text_area(
                "Notas", value=str((assignment or {}).get("notes") or "")
            )
            save = st.form_submit_button("Registrar GF-07")
        if save:
            try:
                saved = set_article1_reviewer_assignment(
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
                st.success(f"GF-07 registrado · revisão {saved['revision']}.")


def _render_abcd(
    db_path: Path,
    session_id: str,
    document: dict[str, Any],
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    document_id = str(document["document_id"])
    status = article1_abcd_document_status(
        db_path, session_id=session_id, document_id=document_id
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("ABCD esperado", "34/34")
    c2.metric("Pendentes", len(status["pending_codes"]))
    c3.metric("Fechado", "sim" if status["closed"] else "não")
    st.caption(
        f"Codebook `{ABCD_VERSION}`. Missing = não avaliado. YES→1–3 + evidência; "
        "NO→0; DÚVIDA→profundidade vazia e não fecha."
    )

    comparison = compare_article1_abcd(
        db_path, session_id=session_id, document_id=document_id
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "código": row["code"],
                    "componente": row["label"],
                    "R1": (row.get("reviewer_1") or {}).get("presence", ""),
                    "R1 prof.": (row.get("reviewer_1") or {}).get("depth", ""),
                    "R2": (row.get("reviewer_2") or {}).get("presence", ""),
                    "R2 prof.": (row.get("reviewer_2") or {}).get("depth", ""),
                    "situação": row["status"],
                    "final": (row.get("final") or {}).get("presence", ""),
                }
                for row in comparison
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    slot = col1.selectbox(
        "Posição",
        ["REVIEWER_1", "REVIEWER_2"],
        format_func=_slot_label,
        key=f"a1_abcd_slot_{session_id}_{document_id}",
    )
    mode = col2.selectbox(
        "Modo",
        EXECUTION_MODES,
        key=f"a1_abcd_mode_{session_id}_{document_id}",
    )
    code = col3.selectbox(
        "Componente",
        ABCD_CODES,
        format_func=lambda value: f"{value} · {ABCD_COMPONENTS[value].label}",
        key=f"a1_abcd_code_{session_id}_{document_id}",
    )
    selected = next(row for row in comparison if row["code"] == code)
    current = (
        selected["reviewer_1"] if slot == "REVIEWER_1" else selected["reviewer_2"]
    ) or {}

    with st.form(f"a1_abcd_{session_id}_{document_id}_{slot}_{code}"):
        presence = st.selectbox(
            "Presença", ["YES", "NO", "DOUBT"],
            index={"YES": 0, "NO": 1, "DOUBT": 2}.get(
                str(current.get("presence") or "DOUBT"), 2
            ),
        )
        if presence == "YES":
            depth = st.selectbox(
                "Profundidade", [1, 2, 3],
                index=[1, 2, 3].index(current.get("depth"))
                if current.get("depth") in [1, 2, 3]
                else 0,
            )
        elif presence == "NO":
            depth = 0
            st.caption("Ausência confirmada → profundidade 0.")
        else:
            depth = None
            st.caption("DÚVIDA → profundidade vazia.")
        family = st.text_input(
            "Família documental",
            value=str(current.get("family") or document.get("family") or ""),
        )
        locator = st.text_input(
            "Página/seção", value=str(current.get("locator") or "")
        )
        evidence = st.text_area(
            "Evidência rastreável", value=str(current.get("evidence") or "")
        )
        action_strategy = st.text_input(
            "Ação/estratégia", value=str(current.get("action_strategy") or "")
        )
        target = st.text_input("Alvo", value=str(current.get("target") or ""))
        actor = st.text_input(
            "Ator/responsável", value=str(current.get("actor_responsible") or "")
        )
        context = st.text_input(
            "Contexto/condição", value=str(current.get("context_condition") or "")
        )
        save = st.form_submit_button("Registrar decisão ABCD")
    if save:
        try:
            saved = submit_article1_abcd(
                db_path,
                session_id=session_id,
                document_id=document_id,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                code=code,
                presence=presence,
                depth=depth,
                execution_mode=mode,
                family=family,
                locator=locator,
                evidence=evidence,
                action_strategy=action_strategy,
                target=target,
                actor_responsible=actor,
                context_condition=context,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"{code} registrado · revisão {saved['revision']}.")

    pending = [
        row
        for row in comparison
        if row["final_status"] == "PENDING"
        and row["status"] in {"DIVERGENT", "UNRESOLVED_DOUBT"}
    ]
    if pending:
        st.markdown("**Adjudicação ABCD**")
        adjudication_code = st.selectbox(
            "Componente divergente",
            [row["code"] for row in pending],
            key=f"a1_adj_code_{session_id}_{document_id}",
        )
        source = next(row for row in pending if row["code"] == adjudication_code)
        with st.form(f"a1_adj_{session_id}_{document_id}_{adjudication_code}"):
            final_presence = st.selectbox("Presença final", ["YES", "NO"])
            final_depth = (
                st.selectbox("Profundidade final", [1, 2, 3])
                if final_presence == "YES"
                else 0
            )
            final_evidence = st.text_area(
                "Evidência final",
                value=str(
                    (source.get("reviewer_1") or {}).get("evidence")
                    or (source.get("reviewer_2") or {}).get("evidence")
                    or ""
                ),
            )
            notes = st.text_area("Justificativa")
            adjudicate = st.form_submit_button("Registrar adjudicação")
        if adjudicate:
            try:
                saved = adjudicate_article1_abcd(
                    db_path,
                    session_id=session_id,
                    document_id=document_id,
                    code=adjudication_code,
                    final_presence=final_presence,
                    final_depth=final_depth,
                    adjudicator_name=reviewer_name,
                    adjudicator_role=reviewer_role,
                    notes=notes,
                    evidence=final_evidence,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(f"Adjudicação registrada · revisão {saved['revision']}.")


def _render_relations(
    db_path: Path,
    session_id: str,
    document: dict[str, Any],
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    document_id = str(document["document_id"])
    st.caption(
        "Somente relação explicitamente sustentada pela fonte. Coocorrência ≠ relação; "
        "não inferir causalidade, função ou direção."
    )
    comparison = compare_article1_relations(
        db_path, session_id=session_id, document_id=document_id
    )
    if comparison:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "relação": row["relation_key"],
                        "R1": bool(row["reviewer_1"]),
                        "R2": bool(row["reviewer_2"]),
                        "situação": row["status"],
                        "final": row["final_status"],
                    }
                    for row in comparison
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "Nenhuma relação positiva registrada. Mesmo assim, R1 e R2 precisam "
            "marcar explicitamente a revisão de relações como concluída."
        )

    col1, col2 = st.columns(2)
    slot = col1.selectbox(
        "Posição",
        ["REVIEWER_1", "REVIEWER_2"],
        format_func=_slot_label,
        key=f"a1_rel_slot_{session_id}_{document_id}",
    )
    mode = col2.selectbox(
        "Modo",
        EXECUTION_MODES,
        key=f"a1_rel_mode_{session_id}_{document_id}",
    )
    with st.form(f"a1_rel_{session_id}_{document_id}_{slot}"):
        source = st.selectbox("Origem", ABCD_CODES)
        target = st.selectbox(
            "Destino", [value for value in ABCD_CODES if value != source]
        )
        direction = st.selectbox("Direção", RELATION_DIRECTIONS)
        relation_type = st.selectbox("Tipo explícito", RELATION_TYPES)
        family = st.text_input(
            "Família documental", value=str(document.get("family") or "")
        )
        locator = st.text_input("Página/seção")
        evidence = st.text_area("Evidência explícita")
        save = st.form_submit_button("Registrar relação")
    if save:
        try:
            saved = submit_article1_relation(
                db_path,
                session_id=session_id,
                document_id=document_id,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                source_code=source,
                target_code=target,
                direction=direction,
                relation_type=relation_type,
                evidence_instances=[{"locator": locator, "evidence": evidence}],
                execution_mode=mode,
                family=family,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Relação registrada · revisão {saved['revision']}.")

    if st.button(
        f"Concluir revisão de relações · {_slot_label(slot)}",
        key=f"a1_rel_complete_{session_id}_{document_id}_{slot}",
    ):
        try:
            complete_article1_relation_review(
                db_path,
                session_id=session_id,
                document_id=document_id,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success("Revisão de relações concluída para este revisor.")

    pending = [row for row in comparison if row["final_status"] == "PENDING"]
    if pending:
        relation_key = st.selectbox(
            "Relação divergente",
            [row["relation_key"] for row in pending],
            key=f"a1_rel_adj_key_{session_id}_{document_id}",
        )
        with st.form(f"a1_rel_adj_{session_id}_{document_id}_{relation_key}"):
            final_decision = st.selectbox("Decisão final", ["INCLUDE", "EXCLUDE"])
            notes = st.text_area("Justificativa")
            adjudicate = st.form_submit_button("Registrar adjudicação da relação")
        if adjudicate:
            try:
                saved = adjudicate_article1_relation(
                    db_path,
                    session_id=session_id,
                    document_id=document_id,
                    relation_key=relation_key,
                    final_decision=final_decision,
                    adjudicator_name=reviewer_name,
                    adjudicator_role=reviewer_role,
                    notes=notes,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(f"Adjudicação registrada · revisão {saved['revision']}.")


def _render_synthesis(db_path: Path, session_id: str) -> None:
    status = article1_runtime_status(db_path, session_id=session_id)
    c1, c2 = st.columns(2)
    c1.metric("Incluídos", status["included_documents"])
    c2.metric("Síntese liberada", "sim" if status["synthesis_ready"] else "não")
    if status["documents"]:
        st.dataframe(
            pd.DataFrame(status["documents"]), use_container_width=True, hide_index=True
        )
    synthesis = article1_synthesis(db_path, session_id=session_id, strict=False)
    st.caption(
        "Presença, profundidade, coocorrência e relações explícitas permanecem "
        "separadas. Não há escore global, média de profundidade ou ranking."
    )
    for title, key in (
        ("Componentes por família", "components"),
        ("Relações explícitas", "explicit_relations"),
        ("Coocorrência — não é relação", "cooccurrence"),
    ):
        if synthesis[key]:
            st.markdown(f"**{title}**")
            st.dataframe(
                pd.DataFrame(synthesis[key]), use_container_width=True, hide_index=True
            )


def render_article1_runtime_panel(
    project_root: Path,
    *,
    registry_path: Path,
) -> None:
    """Render Article 1 workflow using the same registry/Evidence Matrix database."""
    del project_root
    initialize_article1_runtime(registry_path)
    sessions = list_screening_sessions(registry_path, limit=200)
    with st.expander(
        "Artigo 1 · ABCD-NutEV 34/34, relações e síntese", expanded=False
    ):
        st.caption(
            "Runtime canônico dentro do NutEV Evidence Engine. A planilha é audit/export; "
            "decisões científicas permanecem humanas."
        )
        if not sessions:
            st.info("Crie uma sessão de triagem antes de usar o runtime do Artigo 1.")
            return
        session_labels = [_session_label(row) for row in sessions]
        session = dict(zip(session_labels, sessions))[
            st.selectbox("Sessão", session_labels, key="a1_runtime_session")
        ]
        session_id = str(session["session_id"])
        reviewer_name = st.text_input(
            "Revisor/adjudicador ativo",
            value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
            key=f"a1_runtime_name_{session_id}",
        )
        reviewer_role = st.selectbox(
            "Papel",
            sorted(REVIEWER_ROLES),
            key=f"a1_runtime_role_{session_id}",
        )
        _render_gf07(registry_path, session_id, reviewer_name)

        documents = included_documents(registry_path, session_id, "article_1")
        if not documents:
            st.info(
                "Nenhum documento formalmente incluído no Artigo 1 nesta sessão. "
                "CALIBRATION/STAGING continuam disponíveis pela camada runtime sem "
                "ser convertidos em inclusão formal ou PRISMA."
            )
            return
        document_labels = [_document_label(row) for row in documents]
        document = dict(zip(document_labels, documents))[
            st.selectbox(
                "Documento incluído",
                document_labels,
                key=f"a1_runtime_doc_{session_id}",
            )
        ]
        tabs = st.tabs(["ABCD 34/34", "Relações explícitas", "Síntese"])
        with tabs[0]:
            _render_abcd(
                registry_path,
                session_id,
                document,
                reviewer_name,
                reviewer_role,
            )
        with tabs[1]:
            _render_relations(
                registry_path,
                session_id,
                document,
                reviewer_name,
                reviewer_role,
            )
        with tabs[2]:
            _render_synthesis(registry_path, session_id)
