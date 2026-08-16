"""Human-only UI for the GF-02 pre-PRESS readiness decision."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from nutev.review.gf02_press_decision import record_gf02_press_decision
from nutev.search.gf02_gate_materialization import materialize_gf02_prepress_gate


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def render_gf02_press_decision(project_root: Path) -> None:
    gate_path = Path(project_root) / "07_logs" / "gf02" / "gate_status.json"
    try:
        gate = materialize_gf02_prepress_gate(_repo_root(), project_root)
    except (OSError, ValueError) as exc:
        st.error(f"Não foi possível montar a evidência GF-02 para a decisão: {exc}")
        st.caption(
            "O Engine não vai inventar READY_FOR_PRESS. Corrija o artefato apontado acima e use CONTINUAR para retomar."
        )
        return

    evidence_complete = gate.get("evidence_complete") is True
    blockers = [str(item) for item in (gate.get("blockers") or [])]
    current = str(gate.get("human_decision") or "").strip().upper()
    counts = gate.get("sample_classification_counts") or {}
    sentinel = gate.get("pubmed_sentinel_evidence") or {}

    st.markdown("#### Decisão de prontidão para PRESS")
    st.caption(
        "Esta decisão diz apenas se a estratégia está pronta para seguir ao PRESS. "
        "Ela não aprova o PRESS, não autoriza a busca FORMAL e não libera contagens PRISMA."
    )

    summary_cols = st.columns(3)
    summary_cols[0].metric("Amostra revisada", int(gate.get("sample_size") or 0))
    summary_cols[1].metric("Sentinelas recuperados", len(sentinel.get("recovered_sentinel_ids") or []))
    summary_cols[2].metric("Bloqueios", len(blockers))
    if counts:
        st.caption(
            "Classificações rescue-only: "
            + " · ".join(f"{label}: {value}" for label, value in sorted(counts.items()))
        )
    recovered = [str(item) for item in (sentinel.get("recovered_sentinel_ids") or [])]
    missing = [str(item) for item in (sentinel.get("missing_resolved_sentinel_ids") or [])]
    if recovered:
        st.caption("Sentinelas recuperados no resultado final: " + ", ".join(recovered))
    if missing:
        st.caption("Sentinelas prioritários ausentes: " + ", ".join(missing))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**READY_FOR_PRESS · seguir para PRESS**")
        st.caption(
            "Use quando, após revisar o PILOT e a amostra rescue-only, você considera a evidência pré-PRESS "
            "suficiente para submeter a estratégia à revisão PRESS."
        )
    with c2:
        st.markdown("**NOT_READY_FOR_PRESS · ainda não seguir**")
        st.caption(
            "Use quando ainda há ruído, perda de documentos relevantes, problema de estratégia ou outra questão "
            "que exige correção antes do PRESS."
        )

    if evidence_complete:
        st.success("Evidência GF-02 materializada e completa para esta decisão humana.")
    else:
        st.warning("O gate GF-02 não está marcado como evidence_complete=true. READY_FOR_PRESS ficará bloqueado.")
        if blockers:
            st.caption("Bloqueios registrados: " + " · ".join(blockers))

    if current:
        st.info(
            f"Decisão atualmente registrada: {current}. Você pode registrar uma nova decisão explícita; "
            "o histórico anterior será preservado quando a base de evidência for a mesma."
        )

    labels = {
        "Pronto para PRESS": "READY_FOR_PRESS",
        "Ainda não está pronto": "NOT_READY_FOR_PRESS",
    }
    default_label = (
        "Pronto para PRESS"
        if current == "READY_FOR_PRESS"
        else "Ainda não está pronto"
        if current == "NOT_READY_FOR_PRESS"
        else "Pronto para PRESS"
    )

    with st.form("gf02_ready_for_press_form"):
        choice_label = st.radio(
            "Sua decisão",
            list(labels),
            index=list(labels).index(default_label),
            horizontal=True,
        )
        decided_by = st.text_input(
            "Responsável pela decisão",
            value=str(gate.get("human_decision_by") or ""),
            placeholder="Nome do responsável",
            help="Identidade humana real que assume esta decisão científica.",
        )
        rationale = st.text_area(
            "Justificativa curta",
            value=str(gate.get("human_decision_rationale") or ""),
            placeholder=(
                "Ex.: PILOT recuperou os sentinelas prioritários e a revisão rescue-only mostrou nível de ruído aceitável para seguir ao PRESS."
            ),
            help="Registre o fundamento da decisão. Não precisa ser longo, mas não pode ficar em branco.",
        )
        save = st.form_submit_button("Registrar decisão", width="stretch")

    if save:
        decision = labels[choice_label]
        try:
            record_gf02_press_decision(
                gate_path,
                decision=decision,
                decided_by=decided_by,
                rationale=rationale,
            )
        except (OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            if decision == "READY_FOR_PRESS":
                st.success("READY_FOR_PRESS registrado. Agora clique CONTINUAR para o Engine seguir ao gate PRESS.")
            else:
                st.warning(
                    "NOT_READY_FOR_PRESS registrado. O Engine continuará bloqueado antes do PRESS até que a estratégia/evidência seja corrigida e uma nova decisão humana seja registrada."
                )
            st.rerun()


__all__ = ["render_gf02_press_decision"]
