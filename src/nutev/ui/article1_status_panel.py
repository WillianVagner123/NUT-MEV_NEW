"""Canonical Article 1 scientific-state panel."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from nutev.search.article1_scientific_status import (
    derive_article1_scientific_status,
    scientific_execution_card,
)


def render_article1_scientific_status(project_root: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    status = derive_article1_scientific_status(repo_root, project_root)
    card = scientific_execution_card(status)
    st.markdown(f"**{card['title']}**")
    phase = str(status.get("article1_current_phase") or "")
    if phase in {"GF02_PUBMED_PILOT", "GF02_NOISE_REVIEW", "GF02_HUMAN_DECISION"}:
        st.warning(card["body"])
    elif phase == "GF03_PRESS":
        st.info(card["body"])
    else:
        st.info(card["body"])
    with st.expander("Estado científico canônico", expanded=False):
        st.json(status)


__all__ = ["render_article1_scientific_status"]
