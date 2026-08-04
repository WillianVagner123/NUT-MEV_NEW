"""Streamlit panel for full-text retrieval and article-level eligibility."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from nutev.review.article_screening_ledger import (
    list_article_catalog,
    list_screening_sessions,
)
from nutev.review.full_text_assessment import (
    export_full_text_snapshot,
    full_text_assessment_queue,
    full_text_retrieval_queue,
    save_full_text_eligibility_decision,
    save_full_text_retrieval,
    summarize_full_text_assessment,
)
from nutev.review.full_text_assessment_ledger import (
    FULL_TEXT_EXCLUSION_REASONS,
    RETRIEVAL_STATUSES,
    list_full_text_exports,
)
from nutev.review.human_review import REVIEWER_ROLES


def _session_label(row: dict) -> str:
    return (
        f'{row["session_id"]} · corpus {row["build_id"]} · '
        f'{row["status"]} · protocolo {row["protocol_version"]}'
    )


def _document_label(row: dict) -> str:
    title = str(row.get("title") or "Sem título")
    if len(title) > 100:
        title = title[:97] + "..."
    return f'{title} · {row["document_id"]}'


def _retrieval_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "documento": row["document_id"],
                "título": row.get("title", ""),
                "artigos": row["target_article_labels"],
                "recuperação": row["retrieval_status"],
                "integridade": row["artifact_integrity"],
                "sugestão do sistema": row["system_suggested_retrieval_status"],
                "revisão": row["retrieval_revision"],
            }
            for row in rows
        ]
    )


def _eligibility_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "documento": row["document_id"],
                "título": row.get("title", ""),
                "triagem inicial": row["title_abstract_decision"],
                "texto completo": row["retrieval_status"],
                "integridade": row["artifact_integrity"],
                "elegibilidade": row["full_text_status"],
                "motivo": row["full_text_exclusion_reason"],
                "revisão": row["full_text_revision"],
            }
            for row in rows
        ]
    )


def _summary_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "artigo": row["article_label"],
                "buscados": row["reports_sought_for_retrieval"],
                "recuperados": row["reports_retrieved"],
                "não recuperados": row["reports_not_retrieved"],
                "aguardando recuperação": row["reports_pending_retrieval"],
                "avaliados": row["reports_assessed_for_eligibility"],
                "excluídos": row["reports_excluded_at_full_text"],
                "incluídos": row["reports_included"],
                "dúvida": row["reports_maybe"],
                "pendentes": row["reports_pending_eligibility"],
            }
            for row in rows
        ]
    )


def _exports_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "export_id": row["export_id"],
                "criado em": row["created_at"],
                "relatórios buscados": row["distinct_reports_sought"],
                "recuperados": row["distinct_reports_retrieved"],
                "não recuperados": row["distinct_reports_not_retrieved"],
                "inclusões por artigo": row["article_inclusions"],
                "manifesto": row["manifest_path"],
            }
            for row in rows
        ]
    )


def render_full_text_assessment_panel(
    project_root: Path,
    *,
    registry_path: Path,
) -> None:
    """Render retrieval, full-text eligibility, and PRISMA controls."""
    del project_root
    sessions = list_screening_sessions(registry_path, limit=200)
    with st.expander("Texto completo, elegibilidade e inclusão final", expanded=False):
        st.caption(
            "O texto completo é recuperado uma vez por documento. A elegibilidade é "
            "decidida separadamente para cada Artigo 1–5, com histórico de revisões."
        )
        if not sessions:
            st.info("Crie uma sessão de triagem por artigo antes desta etapa.")
            return

        session_labels = [_session_label(row) for row in sessions]
        session_by_label = {label: row for label, row in zip(session_labels, sessions)}
        selected_session_label = st.selectbox(
            "Sessão de triagem",
            session_labels,
            key="full_text_session",
        )
        session = session_by_label[selected_session_label]
        session_id = str(session["session_id"])
        if session["status"] != "OPEN":
            st.warning(
                "Esta sessão está concluída. Os dados podem ser consultados e exportados, "
                "mas novas decisões não serão aceitas."
            )

        col_name, col_role = st.columns([2, 1])
        with col_name:
            reviewer_name = st.text_input(
                "Revisor do texto completo",
                value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
                key="full_text_reviewer_name",
            )
        with col_role:
            reviewer_role = st.selectbox(
                "Papel do revisor",
                sorted(REVIEWER_ROLES),
                key="full_text_reviewer_role",
            )

        retrieval_tab, eligibility_tab, prisma_tab = st.tabs(
            ["Recuperação", "Elegibilidade por artigo", "PRISMA e exportação"]
        )

        with retrieval_tab:
            retrieval_filter = st.selectbox(
                "Situação da recuperação",
                ("ALL", "PENDING", *RETRIEVAL_STATUSES),
                format_func=lambda value: {
                    "ALL": "Todas",
                    "PENDING": "Pendente",
                    "AVAILABLE": "Disponível",
                    "REQUESTED": "Solicitado",
                    "NOT_FOUND": "Não localizado",
                    "PAYWALLED": "Bloqueado por acesso",
                    "FAILED": "Falha na recuperação",
                }[value],
                key="full_text_retrieval_filter",
            )
            retrieval_rows = full_text_retrieval_queue(
                registry_path,
                session_id=session_id,
                status_filter=retrieval_filter,
            )
            st.dataframe(
                _retrieval_table(retrieval_rows),
                use_container_width=True,
                hide_index=True,
            )
            if retrieval_rows:
                document_labels = [_document_label(row) for row in retrieval_rows]
                document_by_label = {
                    label: row for label, row in zip(document_labels, retrieval_rows)
                }
                selected_document_label = st.selectbox(
                    "Documento para registrar a recuperação",
                    document_labels,
                    key="full_text_retrieval_document",
                )
                document = document_by_label[selected_document_label]
                st.markdown(f'**{document.get("title") or "Sem título"}**')
                st.caption(
                    f'Artigos: {document["target_article_labels"]} · '
                    f'Ano: {document.get("year", "")} · DOI: {document.get("doi", "")}'
                )
                if document.get("abstract"):
                    st.text_area(
                        "Resumo",
                        value=str(document["abstract"]),
                        height=160,
                        disabled=True,
                        key=f'full_text_retrieval_abstract_{document["document_id"]}',
                    )

                status = st.selectbox(
                    "Resultado da recuperação",
                    RETRIEVAL_STATUSES,
                    index=(
                        RETRIEVAL_STATUSES.index(document["retrieval_status"])
                        if document["retrieval_status"] in RETRIEVAL_STATUSES
                        else 0
                    ),
                    format_func=lambda value: {
                        "AVAILABLE": "Disponível",
                        "REQUESTED": "Solicitado",
                        "NOT_FOUND": "Não localizado",
                        "PAYWALLED": "Bloqueado por acesso",
                        "FAILED": "Falha na recuperação",
                    }[value],
                    key=f'full_text_retrieval_status_{document["document_id"]}',
                )
                source_url = st.text_input(
                    "URL do texto completo ou fonte",
                    value=(
                        document["retrieval_source_url"]
                        or str(document.get("url") or "")
                    ),
                    key=f'full_text_source_url_{document["document_id"]}',
                )
                artifact_path = st.text_input(
                    "Caminho local do arquivo, quando houver",
                    value=document["retrieval_artifact_path"],
                    placeholder="Ex.: 04_documents/pdfs/artigo.pdf",
                    key=f'full_text_artifact_path_{document["document_id"]}',
                )
                notes = st.text_area(
                    "Notas da recuperação",
                    value=document["retrieval_notes"],
                    placeholder="Registre tentativas, bloqueios, contato com autores ou justificativas.",
                    key=f'full_text_retrieval_notes_{document["document_id"]}',
                )
                if st.button(
                    "Salvar situação do texto completo",
                    type="primary",
                    disabled=session["status"] != "OPEN",
                    key=f'full_text_save_retrieval_{document["document_id"]}',
                ):
                    try:
                        saved = save_full_text_retrieval(
                            registry_path,
                            session_id=session_id,
                            document_id=str(document["document_id"]),
                            status=status,
                            reviewer_name=reviewer_name,
                            reviewer_role=reviewer_role,
                            source_url=source_url,
                            artifact_path=artifact_path,
                            notes=notes,
                        )
                    except (OSError, TypeError, ValueError, RuntimeError) as exc:
                        st.error(str(exc))
                    else:
                        st.success(
                            "Recuperação registrada como revisão "
                            f'{saved["revision"]}: {saved["status"]}.'
                        )
            else:
                st.info("Nenhum documento corresponde ao filtro selecionado.")

        with eligibility_tab:
            articles = list_article_catalog(registry_path, active_only=True)
            article_labels = [f'{row["label"]} · {row["article_id"]}' for row in articles]
            article_by_label = {
                label: row for label, row in zip(article_labels, articles)
            }
            selected_article_label = st.selectbox(
                "Artigo",
                article_labels,
                key="full_text_article",
            )
            article = article_by_label[selected_article_label]
            article_id = str(article["article_id"])
            eligibility_filter = st.selectbox(
                "Situação da elegibilidade",
                (
                    "ALL",
                    "WAITING_RETRIEVAL",
                    "NOT_RETRIEVED",
                    "PENDING_ELIGIBILITY",
                    "INCLUDE",
                    "EXCLUDE",
                    "MAYBE",
                ),
                format_func=lambda value: {
                    "ALL": "Todas",
                    "WAITING_RETRIEVAL": "Aguardando recuperação",
                    "NOT_RETRIEVED": "Não recuperado",
                    "PENDING_ELIGIBILITY": "Pendente de avaliação",
                    "INCLUDE": "Incluído",
                    "EXCLUDE": "Excluído",
                    "MAYBE": "Dúvida",
                }[value],
                key="full_text_eligibility_filter",
            )
            eligibility_rows = full_text_assessment_queue(
                registry_path,
                session_id=session_id,
                article_id=article_id,
                status_filter=eligibility_filter,
            )
            st.dataframe(
                _eligibility_table(eligibility_rows),
                use_container_width=True,
                hide_index=True,
            )
            if eligibility_rows:
                eligibility_labels = [_document_label(row) for row in eligibility_rows]
                eligibility_by_label = {
                    label: row for label, row in zip(eligibility_labels, eligibility_rows)
                }
                selected_eligibility_label = st.selectbox(
                    "Documento para avaliar",
                    eligibility_labels,
                    key=f"full_text_eligibility_document_{article_id}",
                )
                document = eligibility_by_label[selected_eligibility_label]
                st.markdown(f'**{document.get("title") or "Sem título"}**')
                st.caption(
                    f'Triagem inicial: {document["title_abstract_decision"]} · '
                    f'Texto completo: {document["retrieval_status"]} · '
                    f'Integridade: {document["artifact_integrity"]}'
                )
                if document["retrieval_source_url"]:
                    st.code(document["retrieval_source_url"], language="text")
                if document.get("abstract"):
                    st.text_area(
                        "Resumo de apoio",
                        value=str(document["abstract"]),
                        height=150,
                        disabled=True,
                        key=f'full_text_eligibility_abstract_{article_id}_{document["document_id"]}',
                    )

                decision = st.selectbox(
                    "Decisão de elegibilidade",
                    ("INCLUDE", "EXCLUDE", "MAYBE"),
                    index=(
                        ("INCLUDE", "EXCLUDE", "MAYBE").index(document["full_text_status"])
                        if document["full_text_status"] in {"INCLUDE", "EXCLUDE", "MAYBE"}
                        else 0
                    ),
                    format_func=lambda value: {
                        "INCLUDE": "Incluir no artigo",
                        "EXCLUDE": "Excluir após texto completo",
                        "MAYBE": "Dúvida / segunda revisão",
                    }[value],
                    key=f'full_text_decision_{article_id}_{document["document_id"]}',
                )
                exclusion_reason = ""
                if decision == "EXCLUDE":
                    exclusion_reason = st.selectbox(
                        "Motivo da exclusão em texto completo",
                        FULL_TEXT_EXCLUSION_REASONS,
                        format_func=lambda value: value.replace("_", " ").title(),
                        key=f'full_text_reason_{article_id}_{document["document_id"]}',
                    )
                notes = st.text_area(
                    "Justificativa e notas",
                    value=document["full_text_notes"],
                    key=f'full_text_notes_{article_id}_{document["document_id"]}',
                )
                can_assess = (
                    session["status"] == "OPEN"
                    and document["retrieval_status"] == "AVAILABLE"
                    and document["artifact_integrity"] not in {"MISSING", "MISMATCH"}
                )
                if not can_assess:
                    st.warning(
                        "A decisão só pode ser salva quando o texto completo estiver "
                        "disponível e, se local, com integridade válida."
                    )
                if st.button(
                    "Salvar decisão de texto completo",
                    type="primary",
                    disabled=not can_assess,
                    key=f'full_text_save_decision_{article_id}_{document["document_id"]}',
                ):
                    try:
                        saved = save_full_text_eligibility_decision(
                            registry_path,
                            session_id=session_id,
                            document_id=str(document["document_id"]),
                            article_id=article_id,
                            decision=decision,
                            reviewer_name=reviewer_name,
                            reviewer_role=reviewer_role,
                            exclusion_reason=exclusion_reason,
                            notes=notes,
                        )
                    except (OSError, TypeError, ValueError, RuntimeError) as exc:
                        st.error(str(exc))
                    else:
                        st.success(
                            "Elegibilidade registrada como revisão "
                            f'{saved["revision"]}: {saved["decision"]}.'
                        )
            else:
                st.info("Nenhum documento corresponde ao filtro selecionado.")

        with prisma_tab:
            summary = summarize_full_text_assessment(
                registry_path,
                session_id=session_id,
            )
            metric_a, metric_b, metric_c, metric_d = st.columns(4)
            metric_a.metric("Relatórios buscados", summary["distinct_reports_sought"])
            metric_b.metric("Recuperados", summary["distinct_reports_retrieved"])
            metric_c.metric("Não recuperados", summary["distinct_reports_not_retrieved"])
            metric_d.metric("Documentos incluídos", summary["distinct_documents_included"])
            if not summary["prisma_eligible"]:
                st.warning(
                    "A estratégia desta sessão não é elegível para PRISMA. As decisões "
                    "continuam auditáveis, mas as colunas PRISMA permanecem zeradas."
                )
            st.dataframe(
                _summary_table(summary["articles"]),
                use_container_width=True,
                hide_index=True,
            )
            if st.button(
                "Gerar snapshot de texto completo e PRISMA",
                type="primary",
                key="full_text_export",
            ):
                try:
                    exported = export_full_text_snapshot(
                        registry_path,
                        session_id=session_id,
                    )
                except (OSError, TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Snapshot de texto completo exportado com sucesso.")
                    st.caption(f'Manifesto: `{exported["manifest_path"]}`')

            exports = list_full_text_exports(
                registry_path,
                session_id=session_id,
                limit=20,
            )
            if exports:
                st.markdown("**Exportações recentes**")
                st.dataframe(
                    _exports_table(exports),
                    use_container_width=True,
                    hide_index=True,
                )
