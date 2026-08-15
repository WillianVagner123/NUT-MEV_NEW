"""Canonical NutEV Evidence Engine desktop dashboard.

The normal product surface intentionally exposes one Article 1 workflow instead
of the historical multi-page control center. Scientific/audit modules remain in
the package and are invoked by the engine when needed, but operators do not have
to navigate legacy panels to run the canonical workflow.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from nutev.ui.article1_play_panel import render_article1_play_panel


def _shell_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarCollapsedControl"] {display: none;}
        .block-container {
            max-width: 1180px;
            padding-top: 3.2rem;
            padding-bottom: 3rem;
        }
        header[data-testid="stHeader"] {background: transparent;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_dashboard(project_root: Path) -> None:
    """Render the canonical one-button NutEV application."""
    root = Path(project_root)
    root.mkdir(parents=True, exist_ok=True)
    _shell_css()
    render_article1_play_panel(root)
    with st.expander("Execução e auditoria", expanded=False):
        st.caption(f"Projeto: {root.resolve()}")
        st.caption(
            "Checkpoints, ledgers, manifests, hashes e filas humanas permanecem "
            "persistidos no diretório do projeto e são carregados automaticamente."
        )


def main() -> None:
    st.set_page_config(
        page_title="NutEV Evidence Engine",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    default_root = os.environ.get(
        "NUTEV_DASHBOARD_PROJECT_ROOT",
        "./project_output_scientific",
    )
    run_dashboard(Path(default_root))


if __name__ == "__main__":
    main()
