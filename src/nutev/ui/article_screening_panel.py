"""Streamlit panel for duplicate adjudication and Article 1-5 screening."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from nutev.review.article_screening import (
    article_screening_queue,
    duplicate_review_queue,
    ensure_screening_session,
    export_screening_snapshot,
    save_article_screening_decision,
    save_duplicate_review,
    summarize_screening_session,
)
from nutev.review.article_screening_ledger import (
    EXCLUSION_REASONS,
    list_article_catalog,
    list_screening_exports,
    update_article_catalog,
)
from nutev.review.human_review import REVIEWER_ROLES
from nutev.search.corpus_build_ledger import list_corpus_builds

_ROLE_LABELS = {
    "principal_investigator": "Pesquisador principal",
    "advisor": "Orientador",
    "coadvisor": "Coorientador",
    "reviewer_1": "Revisor 1",
    "reviewer_2": "Revisor 2",
    "external_reviewer": "Revisor externo",
}
_REASON_LABELS = {
    "NOT_RELEVANT_TO_ARTICLE": "Não pertinente ao artigo",
    "WRONG_POPULATION": "População inadequada",
    "WRONG_CONCEPT": "Conceito/intervenção inadequado",
    "WRONG_CONTEXT": "Contexto inadequado",
    "WRONG_DOCUMENT_TYPE": "Tipo documental inadequado",
    "WRONG_OUTCOME": "Desfecho inadequado",
    "WRONG_PUBLICATION_DATE": "Período de publicação inadequado",
    "WRONG_LANGUAGE": "Idioma fora do protocolo",
    "INSUFFICIENT_METADATA": "Metadados insuficientes",
    "OTHER": "Outro motivo",
}
_DECISION_LABELS = {
    "INCLUDE": "Incluir",
    "EXCLUDE": "Excluir",
    "MAYBE": "Dúvida / segunda revisão",
}


def _build_label(row: dict) -> str:
    return (
        f'{row["build_id"]} · {row["unique_records"]} documentos · '
        f'{row["possible_duplicates"]} possíveis duplicatas'
    )


def _article_label(row: dict) -> str:
    return f'{row["label"]} · {row["article_id"]}'


def _document_label(row: dict) -> str:
    title = str(row.get("title") or "Sem título")
    year = str(row.get("year") or "s/ano")
    return f'{title[:110]} · {year} · {row["document_id"][-8:]}'


def _summary_table(summary: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artigo": row["article_label"],
                "disponíveis": row["records_available_for_screening"],
                "triados": row["records_screened"],
                "incluídos": row["records_included"],
                "excluídos": row["records_excluded"],
                "dúvidas": row["records_maybe"],
                "pendentes": row["records_pending"],
                "PRISMA — buscados para texto completo": row[
                    "prisma_reports_sought_for_retrieval"
                ],
            }
            for row in summary["articles"]
        ]
    )


def _exports_table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "export_id": row["export_id"],
                "documentos efetivos": row["effective_documents"],
                "duplicatas humanas removidas": row[
                    "human_duplicates_removed"
                ],
                "criado em": row["created_at"],
                "PRISMA": row["prisma_csv_path"],
                "manifesto": row["manifest_path"],
            }
            for row in rows
        ]
    )


def render_article_screening_panel(
    project_root: Path,
    *,
    registry_path: Path,
) -> None:
    """Render one auditable screening session for a completed corpus build."""
    builds = [
        row
        for row in list_corpus_builds(registry_path, limit=200)
        if row["status"] == "SUCCEEDED"
    ]
    with st.expander("Triagem humana e PRISMA por artigo", expanded=False):
        st.caption(
            "A mesma referência pode ser incluída em vários artigos. Cada decisão é "
            "versionada; exclusões exigem motivo e possíveis duplicatas são resolvidas "
            "antes da triagem do documento removido."
        )
        if not builds:
            st.info("Construa ao menos um corpus mestre antes de iniciar a triagem.")
            return

        build_labels = [_build_label(row) for row in builds]
        build_by_label = {
            label: row for label, row in zip(build_labels, builds)
        }
        selected_build_label = st.selectbox(
            "Corpus mestre",
            build_labels,
            key="article_screening_build",
        )
        selected_build = build_by_label[selected_build_label]
        session = ensure_screening_session(
            registry_path,
            build_id=str(selected_build["build_id"]),
            created_by=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
        )
        session_id = str(session["session_id"])
        st.caption(
            f'Sessão: `{session_id}` · protocolo `{session["protocol_version"]}` · '
            f'base `{selected_build["build_id"]}`'
        )

        col_reviewer, col_role = st.columns([2, 1])
        with col_reviewer:
            reviewer_name = st.text_input(
                "Revisor responsável",
                value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
                placeholder="Nome do revisor",
                key=f"screening_reviewer_{session_id}",
            )
        with col_role:
            roles = sorted(REVIEWER_ROLES)
            reviewer_role = st.selectbox(
                "Papel",
                roles,
                format_func=lambda value: _ROLE_LABELS.get(value, value),
                key=f"screening_role_{session_id}",
            )

        articles = list_article_catalog(registry_path, active_only=True)
        article_by_label = {_article_label(row): row for row in articles}

        with st.expander("Configurar os Artigos 1–5", expanded=False):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ID": row["article_id"],
                            "número": row["article_number"],
                            "nome": row["label"],
                            "descrição/critério": row["description"],
                        }
                        for row in articles
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
            edit_label = st.selectbox(
                "Artigo para editar",
                list(article_by_label),
                key=f"screening_article_edit_{session_id}",
            )
            edit_article = article_by_label[edit_label]
            new_label = st.text_input(
                "Nome do artigo",
                value=str(edit_article["label"]),
                key=f"screening_article_label_{edit_article['article_id']}",
            )
            new_description = st.text_area(
                "Descrição ou critério de pertinência",
                value=str(edit_article["description"]),
                height=90,
                key=f"screening_article_description_{edit_article['article_id']}",
            )
            if st.button(
                "Salvar definição do artigo",
                key=f"screening_article_save_{edit_article['article_id']}",
            ):
                try:
                    update_article_catalog(
                        registry_path,
                        article_id=str(edit_article["article_id"]),
                        label=new_label,
                        description=new_description,
                    )
                except (TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Definição do artigo atualizada.")

        st.markdown("**1. Revisão das possíveis duplicatas**")
        duplicate_rows = duplicate_review_queue(
            registry_path,
            session_id=session_id,
        )
        pending_duplicates = [
            row for row in duplicate_rows if row["review_status"] == "PENDING"
        ]
        if not duplicate_rows:
            st.success("Nenhuma possível duplicata por título e ano foi identificada.")
        else:
            st.caption(
                f"{len(pending_duplicates)} de {len(duplicate_rows)} pares aguardam decisão."
            )
            candidate_labels = [
                (
                    f'{row["left_title"][:55]} ↔ {row["right_title"][:55]} · '
                    f'{row["review_status"]} · {row["candidate_id"][-8:]}'
                )
                for row in duplicate_rows
            ]
            candidate_by_label = {
                label: row for label, row in zip(candidate_labels, duplicate_rows)
            }
            selected_candidate_label = st.selectbox(
                "Par para revisar",
                candidate_labels,
                key=f"duplicate_candidate_{session_id}",
            )
            candidate = candidate_by_label[selected_candidate_label]
            left_id = str(candidate["left_document_id"])
            right_id = str(candidate["right_document_id"])
            left_col, right_col = st.columns(2)
            with left_col:
                st.markdown("**Documento A**")
                st.write(candidate["left_title"] or "Sem título")
                st.caption(
                    f'Ano: {candidate["left_year"] or "—"} · '
                    f'DOI: {candidate["left_doi"] or "—"} · '
                    f'Bases: {candidate["left_providers"] or "—"}'
                )
            with right_col:
                st.markdown("**Documento B**")
                st.write(candidate["right_title"] or "Sem título")
                st.caption(
                    f'Ano: {candidate["right_year"] or "—"} · '
                    f'DOI: {candidate["right_doi"] or "—"} · '
                    f'Bases: {candidate["right_providers"] or "—"}'
                )
            duplicate_decision_label = st.radio(
                "Decisão sobre o par",
                ("Não são duplicatas", "Confirmar duplicata"),
                horizontal=True,
                key=f"duplicate_decision_{candidate['candidate_id']}",
            )
            retained_id = ""
            if duplicate_decision_label == "Confirmar duplicata":
                retained_id = st.selectbox(
                    "Documento que será mantido",
                    (left_id, right_id),
                    format_func=lambda value: (
                        candidate["left_title"]
                        if value == left_id
                        else candidate["right_title"]
                    ),
                    key=f"duplicate_retained_{candidate['candidate_id']}",
                )
            duplicate_notes = st.text_area(
                "Justificativa da decisão de duplicidade",
                height=80,
                key=f"duplicate_notes_{candidate['candidate_id']}",
            )
            if st.button(
                "Registrar decisão de duplicidade",
                key=f"duplicate_save_{candidate['candidate_id']}",
            ):
                try:
                    save_duplicate_review(
                        registry_path,
                        session_id=session_id,
                        candidate_id=str(candidate["candidate_id"]),
                        decision=(
                            "CONFIRMED_DUPLICATE"
                            if duplicate_decision_label == "Confirmar duplicata"
                            else "REJECTED"
                        ),
                        reviewer_name=reviewer_name,
                        reviewer_role=reviewer_role,
                        retained_document_id=retained_id,
                        notes=duplicate_notes,
                    )
                except (TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Decisão de duplicidade registrada como nova revisão.")

        st.markdown("**2. Triagem por título e resumo**")
        articles = list_article_catalog(registry_path, active_only=True)
        article_by_label = {_article_label(row): row for row in articles}
        col_article, col_filter = st.columns([2, 1])
        with col_article:
            selected_article_label = st.selectbox(
                "Artigo",
                list(article_by_label),
                key=f"screening_article_{session_id}",
            )
        with col_filter:
            status_filter = st.selectbox(
                "Mostrar",
                ("PENDING", "MAYBE", "INCLUDE", "EXCLUDE", "ALL"),
                format_func=lambda value: {
                    "PENDING": "Pendentes",
                    "MAYBE": "Dúvidas",
                    "INCLUDE": "Incluídos",
                    "EXCLUDE": "Excluídos",
                    "ALL": "Todos",
                }[value],
                key=f"screening_filter_{session_id}",
            )
        selected_article = article_by_label[selected_article_label]
        queue = article_screening_queue(
            registry_path,
            session_id=session_id,
            article_id=str(selected_article["article_id"]),
            status_filter=status_filter,
        )
        if selected_article["description"]:
            st.info(str(selected_article["description"]))
        if not queue:
            st.success("Não há documentos neste filtro.")
        else:
            document_labels = [_document_label(row) for row in queue]
            document_by_label = {
                label: row for label, row in zip(document_labels, queue)
            }
            selected_document_label = st.selectbox(
                "Documento",
                document_labels,
                key=(
                    f"screening_document_{session_id}_"
                    f"{selected_article['article_id']}_{status_filter}"
                ),
            )
            document = document_by_label[selected_document_label]
            st.markdown(f"### {document.get('title') or 'Sem título'}")
            st.caption(
                f"Ano: {document.get('year') or '—'} · "
                f"DOI: {document.get('doi') or '—'} · "
                f"PMID: {document.get('pmid') or '—'} · "
                f"Bases: {document.get('matched_providers') or '—'}"
            )
            abstract = str(document.get("abstract") or "").strip()
            if abstract:
                st.write(abstract)
            else:
                st.warning("Resumo não disponível nos metadados recuperados.")
            st.caption(
                f'Estado atual: **{document["screening_status"]}** · '
                f'revisão {document["screening_revision"]}'
            )

            decision_values = ("INCLUDE", "EXCLUDE", "MAYBE")
            current_status = str(document["screening_status"])
            default_index = (
                decision_values.index(current_status)
                if current_status in decision_values
                else 0
            )
            decision = st.radio(
                "Decisão para este artigo",
                decision_values,
                index=default_index,
                format_func=lambda value: _DECISION_LABELS[value],
                horizontal=True,
                key=(
                    f"screening_decision_{session_id}_"
                    f"{selected_article['article_id']}_{document['document_id']}"
                ),
            )
            exclusion_reason = ""
            if decision == "EXCLUDE":
                exclusion_reason = st.selectbox(
                    "Motivo principal da exclusão",
                    EXCLUSION_REASONS,
                    format_func=lambda value: _REASON_LABELS.get(value, value),
                    key=(
                        f"screening_reason_{session_id}_"
                        f"{selected_article['article_id']}_{document['document_id']}"
                    ),
                )
            notes = st.text_area(
                "Notas da triagem",
                value=str(document.get("screening_notes") or ""),
                height=90,
                key=(
                    f"screening_notes_{session_id}_"
                    f"{selected_article['article_id']}_{document['document_id']}"
                ),
            )
            if st.button(
                "Registrar decisão de triagem",
                type="primary",
                key=(
                    f"screening_save_{session_id}_"
                    f"{selected_article['article_id']}_{document['document_id']}"
                ),
            ):
                try:
                    save_article_screening_decision(
                        registry_path,
                        session_id=session_id,
                        document_id=str(document["document_id"]),
                        article_id=str(selected_article["article_id"]),
                        decision=decision,
                        reviewer_name=reviewer_name,
                        reviewer_role=reviewer_role,
                        exclusion_reason=exclusion_reason,
                        notes=notes,
                    )
                except (TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Decisão registrada como nova revisão imutável.")

        st.markdown("**3. Acompanhamento e snapshot PRISMA**")
        try:
            summary = summarize_screening_session(
                registry_path,
                session_id=session_id,
            )
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
            return
        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Documentos efetivos", summary["effective_documents"])
        metric_b.metric(
            "Duplicatas humanas removidas",
            summary["human_duplicates_removed"],
        )
        metric_c.metric(
            "Pares de duplicatas pendentes",
            summary["pending_duplicate_reviews"],
        )
        st.dataframe(
            _summary_table(summary),
            use_container_width=True,
            hide_index=True,
        )
        if not summary["prisma_eligible"]:
            st.warning(
                "A estratégia de origem não é elegível para PRISMA. As decisões são "
                "preservadas, mas as colunas PRISMA permanecem zeradas."
            )
        if st.button(
            "Gerar snapshot da triagem e PRISMA por artigo",
            key=f"screening_export_{session_id}",
        ):
            try:
                with st.spinner("Gerando snapshot auditável da triagem..."):
                    exported = export_screening_snapshot(
                        registry_path,
                        session_id=session_id,
                    )
            except (OSError, TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success("Snapshot de triagem gerado com sucesso.")
                st.caption(
                    f'PRISMA: `{exported["paths"]["prisma_csv_path"]}` · '
                    f'Manifesto: `{exported["paths"]["manifest_path"]}`'
                )

        exports = list_screening_exports(
            registry_path,
            session_id=session_id,
            limit=20,
        )
        if exports:
            st.markdown("**Snapshots anteriores**")
            st.dataframe(
                _exports_table(exports),
                use_container_width=True,
                hide_index=True,
            )
