"""Direct, canonical execution surface for Article 1 GF-02."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from nutev.search.gf02_pubmed_pilot import (
    load_candidate_config,
    resolved_line_expressions,
    run_gf02_pubmed_pilot,
)
from nutev.ui.article1_status_panel import render_article1_scientific_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _latest_manifest(project_root: Path) -> dict[str, Any] | None:
    root = project_root / "07_logs" / "gf02" / "pubmed"
    if not root.exists():
        return None
    manifests = sorted(root.glob("*/run_manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not manifests:
        return None
    try:
        return json.loads(manifests[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_article1_play_panel(project_root: Path) -> None:
    repo = _repo_root()
    config_path = repo / "config" / "gf02_pubmed_candidates.json"
    config = load_candidate_config(config_path)
    expressions = resolved_line_expressions(config)
    candidate = str(config["current_candidate"])

    render_article1_scientific_status(project_root)

    st.markdown("### Execução atual")
    col_candidate, col_type, col_prisma, col_action = st.columns([1.2, 1, 1, 1.6])
    col_candidate.metric("Estratégia", f"B-NORM-PUBMED {candidate}")
    col_type.metric("Tipo", "PILOT")
    col_prisma.metric("PRISMA", "Não")
    col_action.metric("Próximo passo", "Rodar e revisar ruído")

    st.info(
        "A estratégia já está definida e versionada. Não há campo livre de busca nesta fase. "
        "O PLAY conta as linhas canônicas no PubMed, testa as sentinelas e baixa somente "
        "a amostra rescue-only necessária para revisão humana."
    )

    if not (os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL")):
        st.caption(
            "NCBI_EMAIL não configurado: o Engine usa o limite conservador do PubMed. "
            "Isso não impede o PILOT."
        )

    if st.button(
        f"▶ RODAR PILOT GF-02 · {candidate}",
        type="primary",
        use_container_width=True,
        key="article1_gf02_play",
    ):
        status_box = st.status("Executando GF-02 no PubMed...", expanded=True)

        def progress(message: str) -> None:
            status_box.write(message)

        try:
            manifest = run_gf02_pubmed_pilot(
                repo,
                project_root=project_root,
                noise_sample_size=int((config.get("rescue_sample") or {}).get("default") or 20),
                progress_fn=progress,
            )
        except Exception as exc:
            status_box.update(label="GF-02 interrompido", state="error", expanded=True)
            st.error(f"Falha na execução: {exc}")
        else:
            st.session_state["article1_last_gf02_manifest"] = manifest
            if manifest.get("status") == "SUCCEEDED":
                status_box.update(label="PILOT GF-02 concluído", state="complete", expanded=False)
                st.success("Execução concluída. A revisão humana do rescue-only é o próximo gate.")
            else:
                status_box.update(label="PILOT GF-02 terminou com bloqueios", state="error", expanded=True)
                st.error("O Engine registrou erros de auditoria. Veja os detalhes abaixo antes de qualquer decisão humana.")
            st.json(
                {
                    "run_id": manifest.get("run_id"),
                    "status": manifest.get("status"),
                    "candidate_version": manifest.get("candidate_version"),
                    "execution_plan": manifest.get("execution_plan"),
                    "line_counts": manifest.get("line_counts"),
                    "rescue_only_total_found": (manifest.get("rescue_only") or {}).get("total_found"),
                    "rescue_only_sample": manifest.get("rescue_only_sample"),
                    "priority_sentinel_mechanism": manifest.get("priority_sentinel_mechanism"),
                    "errors": manifest.get("errors"),
                }
            )

    latest = st.session_state.get("article1_last_gf02_manifest") or _latest_manifest(project_root)
    if latest:
        with st.expander("Última execução GF-02", expanded=False):
            st.json(
                {
                    "run_id": latest.get("run_id"),
                    "status": latest.get("status"),
                    "candidate_version": latest.get("candidate_version"),
                    "execution_plan": latest.get("execution_plan"),
                    "line_counts": latest.get("line_counts"),
                    "rescue_only_sample": latest.get("rescue_only_sample"),
                    "errors": latest.get("errors"),
                }
            )

    with st.expander("Ver estratégia canônica · somente leitura", expanded=False):
        st.caption(
            "Estas expressões vêm de config/gf02_pubmed_candidates.json. "
            "O operador não reconstrói a busca no dashboard."
        )
        for line_id in config["required_count_lines"]:
            label = str((config.get("lines") or {}).get(line_id, {}).get("label") or "")
            st.markdown(f"**{line_id} · {label}**")
            st.code(expressions[line_id], language="text")

    with st.expander("Fluxo científico downstream", expanded=False):
        st.markdown(
            "**PILOT PubMed → decisão GF-02 → PRESS → incorporar parecer → "
            "Scopus/WoS → PILOT licenciado → fechar gates → FREEZE → FORMAL.**"
        )
        st.caption(
            "O PLAY desta tela não autoriza PRESS, FREEZE ou execução FORMAL/PRISMA."
        )


__all__ = ["render_article1_play_panel"]
