"""Streamlit workbench for recording the real PRESS gate inside the app.

This is optional presentation code. Scientific persistence and validation live
in ``nutev.review.press_gate`` and are exercised by executable tests.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from nutev.review.press_gate import PRESS_STATUSES, load_press_gate, record_press_gate


def _status_help(status: str) -> str:  # pragma: no cover
    return {
        "APPROVED": "Parecer PRESS concluído e aprovado. O Engine poderá avançar para o trecho pós-PRESS.",
        "CHANGES_REQUIRED": "O parecer existe, mas exige alterações antes de poder ser considerado aprovado.",
        "REJECTED": "O PRESS não aprovou a estratégia. O fluxo permanece bloqueado até nova evidência real.",
    }.get(status, "")


def render_press_gate_workbench(project_root: Path) -> None:  # pragma: no cover
    existing = load_press_gate(project_root)
    current_status = str(existing.get("review_status") or "").strip().upper()

    st.markdown("#### Registrar o PRESS real")
    st.caption(
        "O PRESS é uma revisão científica externa/humana. O formulário abaixo apenas registra o parecer real em JSON "
        "auditável. O software não inventa aprovação e este registro não autoriza FREEZE, FORMAL ou PRISMA."
    )

    if current_status == "APPROVED":
        st.success(
            "PRESS já registrado como APPROVED. Use CONTINUAR para o Engine verificar e executar o próximo trecho autorizado."
        )
        reviewer = str(existing.get("reviewer") or "")
        review_date = str(existing.get("review_date") or "")
        evidence = str(existing.get("evidence_reference") or "")
        if reviewer or review_date:
            st.caption(f"Revisor: {reviewer or '—'} · Data: {review_date or '—'}")
        if evidence:
            st.caption(f"Evidência PRESS: {evidence}")
        return

    default_index = PRESS_STATUSES.index(current_status) if current_status in PRESS_STATUSES else 0
    status = st.radio(
        "Decisão final do PRESS",
        PRESS_STATUSES,
        index=default_index,
        horizontal=True,
        key="press_review_status",
    )
    st.caption(_status_help(status))

    reviewer = st.text_input(
        "Revisor responsável",
        value=str(existing.get("reviewer") or ""),
        placeholder="Nome real do revisor PRESS",
        key="press_reviewer",
    )
    review_date = st.date_input(
        "Data do parecer",
        value=date.today(),
        key="press_review_date",
    )
    evidence_reference = st.text_input(
        "Evidência do parecer",
        value=str(existing.get("evidence_reference") or ""),
        placeholder="Arquivo, URL, DOI, protocolo, ID ou caminho arquivado do parecer real",
        key="press_evidence_reference",
    )
    requested_changes = st.text_area(
        "Mudanças solicitadas pelo PRESS",
        value=str(existing.get("requested_changes") or ""),
        placeholder="Se não houve mudanças solicitadas, deixe em branco.",
        key="press_requested_changes",
    )
    incorporated_changes = st.text_area(
        "Como as mudanças foram incorporadas",
        value=str(existing.get("incorporated_changes") or ""),
        placeholder="Obrigatório se APPROVED e houver mudanças solicitadas.",
        key="press_incorporated_changes",
    )
    notes = st.text_area(
        "Notas adicionais",
        value=str(existing.get("notes") or ""),
        key="press_notes",
    )

    if st.button("Salvar PRESS real", type="primary", width="stretch", key="save_press_gate"):
        try:
            saved = record_press_gate(
                project_root,
                review_status=status,
                reviewer=reviewer,
                review_date=review_date.isoformat(),
                evidence_reference=evidence_reference,
                requested_changes=requested_changes,
                incorporated_changes=incorporated_changes,
                notes=notes,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            if str(saved.get("review_status") or "") == "APPROVED":
                st.success("PRESS aprovado e registrado. O Engine pode avançar para o próximo gate real.")
            else:
                st.success("Parecer PRESS registrado. O fluxo permanece bloqueado conforme a decisão registrada.")
            st.rerun()


__all__ = ["render_press_gate_workbench"]
