"""Streamlit controls for executing immutable registered search strategies."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from nutev.search.corpus_build_ledger import list_corpus_builds
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_execution_ledger import (
    list_execution_artifacts,
    list_search_runs,
)
from nutev.search.strategy_executor import EXECUTABLE_PROVIDERS, execute_strategy_version
from nutev.search.strategy_registry import list_strategy_versions


def _version_label(row: dict) -> str:
    prisma = "PRISMA" if row["prisma_eligible"] else "fora do PRISMA"
    return f'{row["title"]} · v{row["version"]} · {row["search_type"]} · {prisma}'


def _runs_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "amplitude": row["breadth"],
                "identificados": row["records_identified"],
                "PRISMA": row["prisma_records_identified"],
                "início": row["started_at"],
                "fim": row["finished_at"] or "",
                "manifesto": row["manifest_path"],
            }
            for row in rows
        ]
    )


def _artifacts_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "base": row["provider"],
                "status": row["provider_status"],
                "retornados": row["records_returned"],
                "total informado": row["total_found"],
                "snapshot": row["snapshot_path"],
                "sha256": row["snapshot_sha256"][:12],
            }
            for row in rows
        ]
    )


def _corpus_builds_table(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "build_id": row["build_id"],
                "status": row["status"],
                "identificados": row["input_records"],
                "únicos": row["unique_records"],
                "duplicatas removidas": row["duplicates_removed"],
                "possíveis duplicatas": row["possible_duplicates"],
                "PRISMA após deduplicação": row[
                    "prisma_records_after_deduplication"
                ],
                "metadata mestre": row["metadata_csv_path"],
                "manifesto": row["manifest_path"],
            }
            for row in rows
        ]
    )


def render_search_execution_panel(project_root: Path, *, registry_path: Path) -> None:
    """Select and execute a frozen version, then show its run ledger."""
    versions = list_strategy_versions(registry_path, limit=200)
    with st.expander("Executar uma versão registrada", expanded=False):
        st.caption(
            "A execução usa a versão salva no registro, não o texto atualmente aberto. "
            "Os resultados retornados por cada base são preservados em snapshots imutáveis."
        )
        if not versions:
            st.info("Salve ao menos uma versão antes de executar a pesquisa.")
            return

        labels = [_version_label(row) for row in versions]
        by_label = {label: row for label, row in zip(labels, versions)}
        selected_label = st.selectbox(
            "Versão congelada",
            labels,
            key="search_execution_version",
        )
        selected = by_label[selected_label]
        provider_grid = selected.get("providers") or {}

        col_breadth, col_limit = st.columns(2)
        with col_breadth:
            breadth = st.selectbox(
                "Amplitude",
                ("specific", "balanced", "broad"),
                format_func=lambda value: {
                    "specific": "Específica + filtros",
                    "balanced": "Balanceada",
                    "broad": "Ampla",
                }[value],
                key="search_execution_breadth",
            )
        with col_limit:
            limit = st.number_input(
                "Máximo por base",
                min_value=1,
                max_value=10000,
                value=100,
                step=25,
                key="search_execution_limit",
            )

        available = [
            provider
            for provider in EXECUTABLE_PROVIDERS
            if provider in provider_grid
            and str((provider_grid.get(provider) or {}).get(breadth) or "").strip()
        ]
        providers = st.multiselect(
            "Bases",
            available,
            default=available,
            key=f"search_execution_providers_{selected['version_id']}_{breadth}",
        )
        resume = st.checkbox(
            "Retomar checkpoints disponíveis",
            value=True,
            key="search_execution_resume",
        )

        st.code(selected["query_text"], language="text")
        if selected["prisma_eligible"]:
            st.success("Esta versão está marcada como elegível para o PRISMA.")
        else:
            st.warning(
                "Esta versão não é elegível para o PRISMA. A execução será registrada, "
                "mas sua contagem PRISMA permanecerá zero."
            )

        if st.button(
            "Executar pesquisa registrada",
            type="primary",
            disabled=not providers,
            key="search_execution_run",
        ):
            try:
                with st.spinner("Executando as bases selecionadas..."):
                    summary = execute_strategy_version(
                        project_root,
                        registry_path=registry_path,
                        version_id=str(selected["version_id"]),
                        breadth=breadth,
                        providers=providers,
                        limit=int(limit),
                        resume=resume,
                    )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                if summary["status"] == "SUCCEEDED":
                    st.success("Pesquisa executada e registrada com sucesso.")
                else:
                    st.warning(
                        f'Execução finalizada com status {summary["status"]}. '
                        "Consulte os artefatos para identificar bases parciais ou com erro."
                    )
                metric_a, metric_b, metric_c = st.columns(3)
                metric_a.metric(
                    "Identificados antes da deduplicação",
                    summary["records_identified_before_deduplication"],
                )
                metric_b.metric(
                    "Contagem PRISMA",
                    summary["prisma_records_identified"],
                )
                metric_c.metric(
                    "Total informado pelas bases",
                    summary["provider_reported_total_found"],
                )
                st.caption(f'Manifesto: `{summary["manifest_path"]}`')

        recent_runs = list_search_runs(
            registry_path,
            version_id=str(selected["version_id"]),
            limit=20,
        )
        if recent_runs:
            st.markdown("**Execuções recentes desta versão**")
            st.dataframe(
                _runs_table(recent_runs),
                use_container_width=True,
                hide_index=True,
            )
            latest_run_id = str(recent_runs[0]["run_id"])
            artifacts = list_execution_artifacts(
                registry_path,
                run_id=latest_run_id,
                limit=50,
            )
            if artifacts:
                st.markdown("**Artefatos da execução mais recente**")
                st.dataframe(
                    _artifacts_table(artifacts),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("**Normalização e deduplicação auditável**")
            st.caption(
                "DOI, PMID, PMCID e URL exatos são deduplicados automaticamente. "
                "Coincidências apenas por título e ano permanecem separadas e entram "
                "na fila de revisão humana."
            )
            run_labels = [
                f'{row["run_id"]} · {row["status"]} · {row["records_identified"]} registros'
                for row in recent_runs
            ]
            run_by_label = {
                label: row for label, row in zip(run_labels, recent_runs)
            }
            selected_run_label = st.selectbox(
                "Execução para construir o corpus mestre",
                run_labels,
                key="search_corpus_run",
            )
            selected_run = run_by_label[selected_run_label]
            selected_run_id = str(selected_run["run_id"])

            if st.button(
                "Normalizar e deduplicar esta execução",
                type="secondary",
                disabled=selected_run["status"] == "RUNNING",
                key="search_corpus_build",
            ):
                try:
                    with st.spinner(
                        "Verificando snapshots e construindo o corpus mestre..."
                    ):
                        corpus = build_corpus_from_search_run(
                            project_root,
                            registry_path=registry_path,
                            run_id=selected_run_id,
                        )
                except (OSError, TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Corpus mestre construído e registrado com sucesso.")
                    metrics = corpus["metrics"]
                    metric_a, metric_b, metric_c, metric_d = st.columns(4)
                    metric_a.metric("Registros de entrada", metrics["input_records"])
                    metric_b.metric("Documentos únicos", metrics["unique_records"])
                    metric_c.metric(
                        "Duplicatas removidas",
                        metrics["duplicates_removed"],
                    )
                    metric_d.metric(
                        "Possíveis duplicatas",
                        metrics["possible_duplicates"],
                    )
                    st.caption(
                        "PRISMA após deduplicação automática: "
                        f'{metrics["prisma_records_after_deduplication"]}. '
                        f'Metadata mestre: `{corpus["metadata_csv_path"]}`'
                    )

            corpus_builds = list_corpus_builds(
                registry_path,
                run_id=selected_run_id,
                limit=20,
            )
            if corpus_builds:
                st.markdown("**Construções de corpus desta execução**")
                st.dataframe(
                    _corpus_builds_table(corpus_builds),
                    use_container_width=True,
                    hide_index=True,
                )
