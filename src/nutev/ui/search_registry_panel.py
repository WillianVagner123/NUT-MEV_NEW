"""Streamlit controls for the versioned NutEV Search Registry."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from nutev.search.strategy_registry import (
    SEARCH_TYPES,
    default_registry_path,
    list_strategies,
    list_strategy_versions,
    save_strategy_version,
)
from nutev.ui.article1_runtime_panel import render_article1_runtime_panel
from nutev.ui.article1_status_panel import render_article1_scientific_status
from nutev.ui.article_screening_panel import render_article_screening_panel
from nutev.ui.data_extraction_quality_panel import (
    render_data_extraction_quality_panel,
)
from nutev.ui.full_text_assessment_panel import render_full_text_assessment_panel
from nutev.ui.search_execution_panel import render_search_execution_panel


def _strategy_option_label(item: dict) -> str:
    suffix = str(item["strategy_id"])[-8:]
    return f'{item["title"]} · v{item["latest_version"]} · {suffix}'


def _version_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "estratégia": row["title"],
                "versão": row["version"],
                "tipo": row["search_type"],
                "PRISMA": "sim" if row["prisma_eligible"] else "não",
                "responsável": row["created_by"],
                "criada em": row["created_at"],
                "checksum": row["checksum_sha256"][:12],
                "version_id": row["version_id"],
            }
            for row in rows
        ]
    )


def _render_workflow_map() -> None:
    st.markdown("**Fluxo científico desta pesquisa**")
    st.caption(
        "1. PILOT PubMed → 2. decisão GF-02 → 3. PRESS → 4. incorporar parecer → "
        "5. traduzir Scopus/WoS → 6. PILOT licenciado → 7. fechar gates → "
        "8. FREEZE → 9. execução FORMAL → 10. corpus/triagem → 11. texto completo → "
        "12. ABCD 34/34 → 13. relações explícitas → 14. adjudicação/síntese → 15. PRISMA/export."
    )
    st.caption(
        "Compatibilidade do Evidence Matrix: 10. Extração permanece disponível no "
        "fluxo genérico e 12. Matriz final continua sendo o snapshot auditável; "
        "no Artigo 1, a extração científica canônica é ABCD 34/34 + relações explícitas."
    )
    st.caption(
        "No Artigo 1, ABCD, relações e síntese operam no mesmo Evidence Engine. "
        "Coocorrência permanece separada de relação explícita e a planilha é apenas superfície de auditoria/exportação."
    )
    st.caption(
        "A ordem metodológica é sequencial: Scopus/WoS não bloqueiam a ida ao PRESS "
        "antes da etapa pós-PRESS definida em D-096."
    )


def render_search_registry_panel(
    project_root: Path,
    *,
    query_text: str,
    strategy_payload: dict,
) -> None:
    """Render the complete registered-search and review workflow."""
    registry_path = default_registry_path(project_root)
    strategies = list_strategies(registry_path)
    labels = ["Criar nova estratégia"] + [
        _strategy_option_label(item) for item in strategies
    ]
    by_label = {_strategy_option_label(item): item for item in strategies}

    render_article1_scientific_status(project_root)
    _render_workflow_map()

    with st.expander("3 · Registro e versionamento", expanded=True):
        st.caption(
            "Cada salvamento cria uma versão imutável. Buscas piloto não entram "
            "automaticamente no PRISMA; buscas formais e suplementares entram "
            "somente quando os gates científicos e o FREEZE autorizarem."
        )

        selected_label = st.selectbox(
            "Estratégia",
            labels,
            key="search_registry_strategy",
        )
        selected = by_label.get(selected_label)
        selected_strategy_id = str(selected["strategy_id"]) if selected else None

        col_title, col_type = st.columns([2, 1])
        with col_title:
            if selected:
                title = st.text_input(
                    "Título da estratégia",
                    value=str(selected["title"]),
                    disabled=True,
                    key="search_registry_existing_title",
                )
            else:
                title = st.text_input(
                    "Título da estratégia",
                    placeholder="Busca global NutEV — diretrizes e competências",
                    key="search_registry_new_title",
                )
        with col_type:
            search_type = st.selectbox(
                "Tipo de busca",
                SEARCH_TYPES,
                format_func=lambda value: {
                    "PILOT": "Piloto",
                    "FORMAL": "Formal",
                    "SUPPLEMENTARY": "Suplementar",
                }[value],
                key="search_registry_type",
            )

        col_owner, col_prisma = st.columns([2, 1])
        with col_owner:
            created_by = st.text_input(
                "Responsável",
                value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
                placeholder="Nome do pesquisador responsável",
                key="search_registry_created_by",
            )
        with col_prisma:
            prisma_default = search_type != "PILOT"
            prisma_eligible = st.checkbox(
                "Elegível para PRISMA",
                value=prisma_default,
                key=f"search_registry_prisma_{search_type}",
            )

        notes = st.text_area(
            "Notas da versão",
            placeholder=(
                "Ex.: versão aprovada após teste piloto e calibração da equipe."
            ),
            height=90,
            key="search_registry_notes",
        )

        if st.button(
            "Salvar versão no registro",
            type="primary",
            key="search_registry_save",
        ):
            try:
                saved = save_strategy_version(
                    registry_path,
                    strategy_id=selected_strategy_id,
                    title=title,
                    query_text=query_text,
                    strategy_payload=strategy_payload,
                    search_type=search_type,
                    created_by=created_by,
                    notes=notes,
                    prisma_eligible=prisma_eligible,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Estratégia salva como versão {saved.version} "
                    f"({saved.version_id})."
                )

        st.caption(f"Banco local: `{registry_path}`")
        recent_versions = list_strategy_versions(registry_path, limit=20)
        if recent_versions:
            st.markdown("**Versões recentes**")
            st.dataframe(
                _version_table(recent_versions),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhuma estratégia foi salva neste projeto ainda.")

    render_search_execution_panel(project_root, registry_path=registry_path)
    render_article_screening_panel(project_root, registry_path=registry_path)
    render_full_text_assessment_panel(project_root, registry_path=registry_path)
    render_article1_runtime_panel(project_root, registry_path=registry_path)
    render_data_extraction_quality_panel(
        project_root,
        registry_path=registry_path,
    )
