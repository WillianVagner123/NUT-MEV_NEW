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
    article1_relation_calibration_report,
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
    title = str(row.get("title") or "Sem título")[:80]
    year = str(row.get("year") or "")
    return f"{title} · {year} · {str(row['document_id'])[-10:]}"


def _slot_label(slot: str) -> str:
    return "Revisor 1" if slot == "REVIEWER_1" else "Revisor 2"


def _status_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "código": row["code"],
                "componente": row["label"],
                "R1 presença": (row.get("reviewer_1") or {}).get("presence", ""),
                "R1 profundidade": (row.get("reviewer_1") or {}).get("depth", ""),
                "R2 presença": (row.get("reviewer_2") or {}).get("presence", ""),
                "R2 profundidade": (row.get("reviewer_2") or {}).get("depth", ""),
                "situação": row["status"],
                "final": (row.get("final") or {}).get("presence", ""),
            }
            for row in rows
        ]
    )


def _reviewer_assignment(
    db_path: Path, session_id: str, current_reviewer: str
) -> None:
    assignment = article1_reviewer_assignment(db_path, session_id)
    with st.expander("GF-07 · dupla de revisão e adjudicação", expanded=False):
        st.caption(
            "Registre apenas identidades humanas reais. O software não preenche R2 "
            "ou adjudicador automaticamente. Sem esta etapa, execução FORMAL permanece bloqueada."
        )
        with st.form(f"a1_assignment_{session_id}"):
            r1 = st.text_input(
                "Revisor 1",
                value=str((assignment or {}).get("reviewer_1_name") or current_reviewer),
                key=f"a1_assignment_r1_{session_id}",
            )
            r2 = st.text_input(
                "Revisor 2",
                value=str((assignment or {}).get("reviewer_2_name") or ""),
                key=f"a1_assignment_r2_{session_id}",
            )
            adjudicator = st.text_input(
                "Adjudicador",
                value=str((assignment or {}).get("adjudicator_name") or ""),
                key=f"a1_assignment_adj_{session_id}",
            )
            notes = st.text_area(
                "Notas",
                value=str((assignment or {}).get("notes") or ""),
                key=f"a1_assignment_notes_{session_id}",
            )
            submitted = st.form_submit_button("Registrar identidades GF-07")
        if submitted:
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
                st.success(
                    "GF-07 registrado no runtime com R1/R2/adjudicador distintos "
                    f"(revisão {saved['revision']})."
                )


def _abcd_workspace(
    db_path: Path,
    *,
    session_id: str,
    document: dict[str, Any],
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    document_id = str(document["document_id"])
    status = article1_abcd_document_status(
        db_path, session_id=session_id, document_id=document_id
    )
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Componentes esperados", 34)
    metric2.metric("Pendentes", len(status["pending_codes"]))
    metric3.metric("Fechado", "sim" if status["closed"] else "não")
    st.caption(
        f"Codebook `{ABCD_VERSION}` · missing = não avaliado, nunca ausência. "
        "YES exige evidência e profundidade 1–3; NO exige profundidade 0; DÚVIDA não fecha."
    )

    comparison = compare_article1_abcd(
        db_path, session_id=session_id, document_id=document_id
    )
    st.dataframe(_status_table(comparison), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    slot = col1.selectbox(
        "Posição na dupla",
        ["REVIEWER_1", "REVIEWER_2"],
        format_func=_slot_label,
        key=f"a1_abcd_slot_{session_id}_{document_id}",
    )
    mode = col2.selectbox(
        "Modo",
        EXECUTION_MODES,
        key=f"a1_abcd_mode_{session_id}_{document_id}",
    )
    selected_code = col3.selectbox(
        "Componente",
        ABCD_CODES,
        format_func=lambda code: f"{code} · {ABCD_COMPONENTS[code].label}",
        key=f"a1_abcd_code_{session_id}_{document_id}",
    )
    current = next(item for item in comparison if item["code"] == selected_code)
    current_reviewer = current["reviewer_1"] if slot == "REVIEWER_1" else current["reviewer_2"]
    current_reviewer = current_reviewer or {}

    with st.form(f"a1_abcd_form_{session_id}_{document_id}_{slot}_{selected_code}"):
        presence_options = ["YES", "NO", "DOUBT"]
        current_presence = str(current_reviewer.get("presence") or "DOUBT")
        presence = st.selectbox(
            "Presença",
            presence_options,
            index=presence_options.index(current_presence)
            if current_presence in presence_options
            else 2,
        )
        default_depth = current_reviewer.get("depth")
        if presence == "YES":
            depth = st.selectbox(
                "Profundidade",
                [1, 2, 3],
                index=[1, 2, 3].index(default_depth)
                if default_depth in [1, 2, 3]
                else 0,
            )
        elif presence == "NO":
            depth = 0
            st.caption("Profundidade = 0 para ausência confirmada.")
        else:
            depth = None
            st.caption("DÚVIDA mantém profundidade em branco e bloqueia fechamento.")
        family = st.text_input(
            "Família documental",
            value=str(current_reviewer.get("family") or document.get("family") or ""),
        )
        locator = st.text_input(
            "Página/seção/localizador",
            value=str(current_reviewer.get("locator") or ""),
        )
        evidence = st.text_area(
            "Evidência rastreável",
            value=str(current_reviewer.get("evidence") or ""),
        )
        col_a, col_b = st.columns(2)
        action_strategy = col_a.text_area(
            "Ação/estratégia", value=str(current_reviewer.get("action_strategy") or "")
        )
        target = col_b.text_area(
            "Alvo", value=str(current_reviewer.get("target") or "")
        )
        col_c, col_d = st.columns(2)
        actor_responsible = col_c.text_input(
            "Ator/responsável",
            value=str(current_reviewer.get("actor_responsible") or ""),
        )
        frequency_sequence = col_d.text_input(
            "Frequência/sequência",
            value=str(current_reviewer.get("frequency_sequence") or ""),
        )
        col_e, col_f = st.columns(2)
        tool_material = col_e.text_input(
            "Ferramenta/material",
            value=str(current_reviewer.get("tool_material") or ""),
        )
        indicator_criterion = col_f.text_input(
            "Indicador/critério",
            value=str(current_reviewer.get("indicator_criterion") or ""),
        )
        context_condition = st.text_input(
            "Contexto/condição",
            value=str(current_reviewer.get("context_condition") or ""),
        )
        interpretation_nature = st.text_input(
            "Natureza da interpretação",
            value=str(current_reviewer.get("interpretation_nature") or ""),
        )
        submitted = st.form_submit_button("Registrar decisão ABCD")
    if submitted:
        try:
            saved = submit_article1_abcd(
                db_path,
                session_id=session_id,
                document_id=document_id,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                code=selected_code,
                presence=presence,
                depth=depth,
                execution_mode=mode,
                family=family,
                locator=locator,
                evidence=evidence,
                action_strategy=action_strategy,
                target=target,
                actor_responsible=actor_responsible,
                frequency_sequence=frequency_sequence,
                tool_material=tool_material,
                indicator_criterion=indicator_criterion,
                context_condition=context_condition,
                interpretation_nature=interpretation_nature,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"{selected_code} registrado como revisão {saved['revision']}.")

    pending = [
        item
        for item in comparison
        if item["final_status"] == "PENDING"
        and item["status"] in {"DIVERGENT", "UNRESOLVED_DOUBT"}
    ]
    if pending:
        st.markdown("**Adjudicação ABCD**")
        code = st.selectbox(
            "Componente divergente",
            [item["code"] for item in pending],
            key=f"a1_abcd_adj_code_{session_id}_{document_id}",
        )
        item = next(row for row in pending if row["code"] == code)
        with st.form(f"a1_abcd_adj_{session_id}_{document_id}_{code}"):
            final_presence = st.selectbox("Presença final", ["YES", "NO"])
            final_depth = (
                st.selectbox("Profundidade final", [1, 2, 3])
                if final_presence == "YES"
                else 0
            )
            final_evidence = st.text_area(
                "Evidência final",
                value=str(
                    (item.get("reviewer_1") or {}).get("evidence")
                    or (item.get("reviewer_2") or {}).get("evidence")
                    or ""
                ),
            )
            notes = st.text_area("Justificativa")
            adjudicated = st.form_submit_button("Registrar adjudicação ABCD")
        if adjudicated:
            try:
                saved = adjudicate_article1_abcd(
                    db_path,
                    session_id=session_id,
                    document_id=document_id,
                    code=code,
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
                st.success(f"Adjudicação registrada como revisão {saved['revision']}.")


def _relations_workspace(
    db_path: Path,
    *,
    session_id: str,
    document: dict[str, Any],
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    document_id = str(document["document_id"])
    st.caption(
        "Somente relações explicitamente sustentadas pela fonte. Coocorrência não é relação; "
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
                        "R1": "sim" if row["reviewer_1"] else "não",
                        "R2": "sim" if row["reviewer_2"] else "não",
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
            "Nenhuma relação positiva registrada. Para fechar uma revisão sem relações, "
            "R1 e R2 ainda precisam marcar explicitamente a revisão como concluída."
        )

    col1, col2 = st.columns(2)
    slot = col1.selectbox(
        "Posição na dupla",
        ["REVIEWER_1", "REVIEWER_2"],
        format_func=_slot_label,
        key=f"a1_rel_slot_{session_id}_{document_id}",
    )
    mode = col2.selectbox(
        "Modo",
        EXECUTION_MODES,
        key=f"a1_rel_mode_{session_id}_{document_id}",
    )
    with st.form(f"a1_rel_form_{session_id}_{document_id}_{slot}"):
        col_s, col_t = st.columns(2)
        source = col_s.selectbox("Origem", ABCD_CODES)
        target_options = [code for code in ABCD_CODES if code != source]
        target = col_t.selectbox("Destino", target_options)
        col_d, col_r = st.columns(2)
        direction = col_d.selectbox("Direção", RELATION_DIRECTIONS)
        relation_type = col_r.selectbox("Tipo explícito", RELATION_TYPES)
        family = st.text_input(
            "Família documental",
            value=str(document.get("family") or ""),
            key=f"a1_rel_family_{session_id}_{document_id}_{slot}",
        )
        locator = st.text_input("Página/seção/localizador")
        evidence = st.text_area("Trecho/evidência explícita")
        submitted = st.form_submit_button("Registrar relação explícita")
    if submitted:
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
            st.success(f"Relação registrada como revisão {saved['revision']}.")

    if st.button(
        f"Marcar revisão de relações concluída · {_slot_label(slot)}",
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
                complete=True,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success("Revisão de relações marcada como concluída para este revisor.")

    pending = [row for row in comparison if row["final_status"] == "PENDING"]
    if pending:
        relation_key = st.selectbox(
            "Relação divergente para adjudicar",
            [row["relation_key"] for row in pending],
            key=f"a1_rel_adj_{session_id}_{document_id}",
        )
        with st.form(f"a1_rel_adj_form_{session_id}_{document_id}_{relation_key}"):
            final_decision = st.selectbox("Decisão final", ["INCLUDE", "EXCLUDE"])
            notes = st.text_area("Justificativa da adjudicação")
            adjudicated = st.form_submit_button("Registrar adjudicação da relação")
        if adjudicated:
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
                st.success(f"Adjudicação registrada como revisão {saved['revision']}.")


def _synthesis_workspace(db_path: Path, session_id: str) -> None:
    status = article1_runtime_status(db_path, session_id=session_id)
    metric1, metric2 = st.columns(2)
    metric1.metric("Documentos incluídos", status["included_documents"])
    metric2.metric("Síntese liberada", "sim" if status["synthesis_ready"] else "não")
    if status["documents"]:
        st.dataframe(
            pd.DataFrame(status["documents"]),
            use_container_width=True,
            hide_index=True,
        )
    st.caption(
        "A síntese mantém presença, profundidade, coocorrência e relações explícitas "
        "como saídas separadas; não há escore global, média de profundidade ou ranking."
    )
    try:
        synthesis = article1_synthesis(db_path, session_id=session_id, strict=False)
    except (TypeError, ValueError, RuntimeError) as exc:
        st.error(str(exc))
        return
    if synthesis["components"]:
        st.markdown("**Componentes por família documental**")
        st.dataframe(
            pd.DataFrame(synthesis["components"]),
            use_container_width=True,
            hide_index=True,
        )
    if synthesis["explicit_relations"]:
        st.markdown("**Relações explícitas**")
        st.dataframe(
            pd.DataFrame(synthesis["explicit_relations"]),
            use_container_width=True,
            hide_index=True,
        )
    if synthesis["cooccurrence"]:
        st.markdown("**Coocorrência — saída separada, não interpretada como relação**")
        st.dataframe(
            pd.DataFrame(synthesis["cooccurrence"]),
            use_container_width=True,
            hide_index=True,
        )


def render_article1_runtime_panel(
    project_root: Path,
    *,
    registry_path: Path,
) -> None:
    """Render the canonical Article 1 ABCD/relations runtime workspace."""
    del project_root
    initialize_article1_runtime(registry_path)
    sessions = list_screening_sessions(registry_path, limit=200)
    with st.expander(
        "Artigo 1 · ABCD-NutEV 34/34, relações e síntese",
        expanded=False,
    ):
        st.caption(
            "Este é o runtime canônico do Artigo 1 dentro do NutEV Evidence Engine. "
            "A planilha é superfície de auditoria/exportação; decisões científicas permanecem humanas."
        )
        if not sessions:
            st.info("Crie uma sessão de triagem para habilitar o runtime do Artigo 1.")
            return
        labels = [_session_label(row) for row in sessions]
        session = dict(zip(labels, sessions))[
            st.selectbox("Sessão", labels, key="a1_runtime_session")
        ]
        session_id = str(session["session_id"])
        reviewer_name = st.text_input(
            "Revisor/adjudicador ativo",
            value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
            key=f"a1_runtime_reviewer_{session_id}",
        )
        reviewer_role = st.selectbox(
            "Papel",
            sorted(REVIEWER_ROLES),
            key=f"a1_runtime_role_{session_id}",
        )
        _reviewer_assignment(registry_path, session_id, reviewer_name)

        documents = included_documents(registry_path, session_id, "article_1")
        if not documents:
            st.info(
                "Ainda não há documento formalmente incluído no Artigo 1. "
                "O runtime permanece disponível programaticamente para CALIBRATION/STAGING, "
                "mas esta tela downstream só lista documentos após elegibilidade de texto completo."
            )
            return
        document_labels = [_document_label(row) for row in documents]
        document = dict(zip(document_labels, documents))[
            st.selectbox(
                "Documento incluído",
                document_labels,
                key=f"a1_runtime_document_{session_id}",
            )
        ]
        tabs = st.tabs(["ABCD 34/34", "Relações explícitas", "Síntese"])
        with tabs[0]:
            _abcd_workspace(
                registry_path,
                session_id=session_id,
                document=document,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
            )
        with tabs[1]:
            _relations_workspace(
                registry_path,
                session_id=session_id,
                document=document,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
            )
        with tabs[2]:
            _synthesis_workspace(registry_path, session_id)

        st.caption(
            "Calibração de relações (Jaccard descritivo) é calculável pelo runtime quando "
            "um conjunto de Document_IDs de calibração é fornecido; nenhum limiar automático de Jaccard é aplicado."
        )
