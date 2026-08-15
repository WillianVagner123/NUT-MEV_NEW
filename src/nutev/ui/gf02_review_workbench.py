"""Fast, filterable human review surface for the GF-02 rescue-only sample.

The UI offers filters and explicit bulk actions, but never chooses a scientific
classification on behalf of the reviewer. Blank rows remain blank until a human
selects a label.

This module is optional Streamlit presentation code. Its user-facing contract is
covered by source-level dashboard tests; scientific persistence and validation
live in ``nutev.review.gf02_noise_review`` and are exercised by executable tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from nutev.review.gf02_noise_review import (
    ALLOWED_CLASSIFICATIONS,
    read_rescue_only_sample,
    review_progress,
    save_rescue_only_batch,
    save_rescue_only_progress,
)


def _sample_path(scientific: dict[str, Any]) -> Path | None:  # pragma: no cover
    manifest_path = Path(str((scientific.get("gf02") or {}).get("latest_manifest") or ""))
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    sample = Path(str(payload.get("rescue_only_sample") or ""))
    return sample if sample.is_file() else None


def _editor_records(value: Any) -> list[dict[str, Any]]:  # pragma: no cover
    if hasattr(value, "to_dict"):
        rows = value.to_dict(orient="records")
    elif isinstance(value, list):
        rows = value
    else:
        rows = list(value or [])
    return [dict(row) for row in rows]


def _draft_key(sample_path: Path) -> str:  # pragma: no cover
    return f"gf02_easy_review_draft::{sample_path}"


def _reviewer_key(sample_path: Path) -> str:  # pragma: no cover
    return f"gf02_easy_review_reviewer::{sample_path}"


def _reset_draft(sample_path: Path) -> None:  # pragma: no cover
    st.session_state.pop(_draft_key(sample_path), None)
    st.session_state.pop(_reviewer_key(sample_path), None)


def _ensure_draft(  # pragma: no cover
    sample_path: Path,
    rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    key = _draft_key(sample_path)
    current = st.session_state.get(key)
    expected = {str(row.get("sample_id") or "").strip() for row in rows}
    if not isinstance(current, dict) or set(current) != expected:
        current = {
            str(row.get("sample_id") or "").strip(): {
                "classification": str(row.get("classification") or "").strip().upper(),
                "note": str(row.get("note") or "").strip(),
            }
            for row in rows
        }
        st.session_state[key] = current
    return current


def _classification_help() -> None:  # pragma: no cover
    st.markdown("##### Como classificar")
    st.caption(
        "Aqui você avalia se o registro recuperado pelo rescue-only é pertinente ao escopo da busca normativa. "
        "Não é uma nota de qualidade do artigo."
    )
    relevant, irrelevant, doubt = st.columns(3)
    with relevant:
        st.markdown("**RELEVANT · manter**")
        st.caption(
            "Parece pertencer ao escopo pretendido da busca. Ex.: guideline, recomendação, consenso ou documento "
            "normativo pertinente à alimentação/nutrição/estilo de vida no escopo do protocolo."
        )
    with irrelevant:
        st.markdown("**IRRELEVANT · ruído**")
        st.caption(
            "Está claramente fora do escopo que a estratégia deveria recuperar. Ex.: tipo documental ou tema "
            "incompatível com o corpus normativo definido pelo protocolo."
        )
    with doubt:
        st.markdown("**DOUBT · revisar**")
        st.caption(
            "Título/metadados não permitem decidir com segurança. Use quando precisar conferir mais informação "
            "antes de considerar o registro relevante ou ruído."
        )


def _matches(  # pragma: no cover
    row: dict[str, str],
    *,
    query: str,
    status_filter: str,
    draft: dict[str, dict[str, str]],
) -> bool:
    sample_id = str(row.get("sample_id") or "").strip()
    classification = str((draft.get(sample_id) or {}).get("classification") or "").strip().upper()
    if status_filter == "Não classificados" and classification:
        return False
    if status_filter in ALLOWED_CLASSIFICATIONS and classification != status_filter:
        return False
    needle = query.strip().casefold()
    if not needle:
        return True
    haystack = " ".join(
        str(row.get(key) or "")
        for key in ("sample_id", "title", "pmid", "doi", "record_id")
    ).casefold()
    return needle in haystack


def _draft_counts(draft: dict[str, dict[str, str]]) -> dict[str, int]:  # pragma: no cover
    values = [str(item.get("classification") or "").strip().upper() for item in draft.values()]
    return {
        "total": len(values),
        "unclassified": sum(not value for value in values),
        "relevant": values.count("RELEVANT"),
        "irrelevant": values.count("IRRELEVANT"),
        "doubt": values.count("DOUBT"),
    }


def _decisions_from_draft(  # pragma: no cover
    draft: dict[str, dict[str, str]],
    *,
    complete: bool,
) -> list[dict[str, str]]:
    decisions: list[dict[str, str]] = []
    for sample_id, item in draft.items():
        classification = str(item.get("classification") or "").strip().upper()
        if not classification and not complete:
            continue
        decisions.append(
            {
                "sample_id": sample_id,
                "classification": classification,
                "note": str(item.get("note") or "").strip(),
            }
        )
    return decisions


def render_gf02_easy_review(scientific: dict[str, Any]) -> None:  # pragma: no cover
    """Render a spreadsheet-like GF-02 review with filters and explicit bulk actions."""
    sample_path = _sample_path(scientific)
    if sample_path is None:
        st.error("A amostra rescue-only não foi localizada no manifest GF-02 atual.")
        return
    try:
        rows = read_rescue_only_sample(sample_path)
        progress = review_progress(sample_path)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown("#### Revisão rescue-only · modo rápido")
    st.caption(
        "Filtre, selecione e classifique várias linhas de uma vez. Todas as ações em lote são decisões explícitas "
        "do revisor; o Engine não preenche classificações automaticamente."
    )
    _classification_help()

    if progress["complete"]:
        st.success("A amostra já está completa. Clique CONTINUAR para o Engine executar o próximo trecho autorizado.")
        return

    draft = _ensure_draft(sample_path, rows)
    existing_reviewers = [
        str(row.get("reviewer") or "").strip()
        for row in rows
        if str(row.get("reviewer") or "").strip()
    ]
    reviewer_key = _reviewer_key(sample_path)
    if reviewer_key not in st.session_state:
        st.session_state[reviewer_key] = existing_reviewers[0] if existing_reviewers else ""

    reviewer = st.text_input(
        "Revisor humano",
        key=reviewer_key,
        placeholder="Digite seu nome uma vez",
        help="A identidade informada será gravada somente nas linhas que você salvar/finalizar.",
    )

    counts = _draft_counts(draft)
    metric_cols = st.columns(5)
    metric_cols[0].metric("Total", counts["total"])
    metric_cols[1].metric("Sem classe", counts["unclassified"])
    metric_cols[2].metric("Relevant", counts["relevant"])
    metric_cols[3].metric("Irrelevant", counts["irrelevant"])
    metric_cols[4].metric("Doubt", counts["doubt"])

    search_col, filter_col = st.columns([2, 1])
    with search_col:
        query = st.text_input(
            "Buscar nos registros",
            placeholder="Título, PMID, DOI ou ID da amostra",
            key=f"gf02_easy_search::{sample_path}",
        )
    with filter_col:
        status_filter = st.selectbox(
            "Mostrar",
            ["Todos", "Não classificados", *ALLOWED_CLASSIFICATIONS],
            key=f"gf02_easy_filter::{sample_path}",
        )

    visible_rows = [
        row
        for row in rows
        if _matches(row, query=query, status_filter=status_filter, draft=draft)
    ]
    st.caption(f"Exibindo {len(visible_rows)} de {len(rows)} registros. Você pode ordenar colunas clicando no cabeçalho.")

    table_rows: list[dict[str, Any]] = []
    for row in visible_rows:
        sample_id = str(row.get("sample_id") or "").strip()
        pmid = str(row.get("pmid") or "").strip()
        doi = str(row.get("doi") or "").strip()
        item = draft[sample_id]
        table_rows.append(
            {
                "selecionar": False,
                "sample_id": sample_id,
                "title": str(row.get("title") or ""),
                "classification": str(item.get("classification") or ""),
                "note": str(item.get("note") or ""),
                "pmid": pmid,
                "doi": doi,
                "pubmed_link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                "doi_link": f"https://doi.org/{doi}" if doi else "",
            }
        )

    edited = st.data_editor(
        table_rows,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        height=min(680, max(180, 42 + 36 * len(table_rows))),
        disabled=["sample_id", "title", "pmid", "doi", "pubmed_link", "doi_link"],
        column_order=[
            "selecionar",
            "classification",
            "title",
            "note",
            "pmid",
            "doi",
            "pubmed_link",
            "doi_link",
            "sample_id",
        ],
        column_config={
            "selecionar": st.column_config.CheckboxColumn("✓", width="small"),
            "classification": st.column_config.SelectboxColumn(
                "Classificação",
                options=["", *ALLOWED_CLASSIFICATIONS],
                required=False,
                width="medium",
                help="RELEVANT = pertinente; IRRELEVANT = ruído; DOUBT = precisa conferir.",
            ),
            "title": st.column_config.TextColumn("Título", width="large"),
            "note": st.column_config.TextColumn("Nota / justificativa", width="large"),
            "pmid": st.column_config.TextColumn("PMID", width="small"),
            "doi": st.column_config.TextColumn("DOI", width="medium"),
            "pubmed_link": st.column_config.LinkColumn("PubMed", display_text="Abrir", width="small"),
            "doi_link": st.column_config.LinkColumn("DOI ↗", display_text="Abrir", width="small"),
            "sample_id": st.column_config.TextColumn("ID", width="small"),
        },
        key=f"gf02_easy_editor::{sample_path}::{status_filter}::{query}",
    )

    edited_records = _editor_records(edited)
    for item in edited_records:
        sample_id = str(item.get("sample_id") or "").strip()
        if sample_id not in draft:
            continue
        draft[sample_id]["classification"] = str(item.get("classification") or "").strip().upper()
        draft[sample_id]["note"] = str(item.get("note") or "").strip()
    st.session_state[_draft_key(sample_path)] = draft

    st.markdown("##### Ações rápidas em lote")
    scope_col, overwrite_col = st.columns([1.2, 1])
    with scope_col:
        bulk_scope = st.radio(
            "Aplicar em",
            ["Linhas selecionadas", "Todos os resultados filtrados"],
            horizontal=True,
            key=f"gf02_easy_scope::{sample_path}",
        )
    with overwrite_col:
        only_blank = st.checkbox(
            "Preencher somente as vazias",
            value=True,
            key=f"gf02_easy_only_blank::{sample_path}",
            help="Evita substituir classificações que você já revisou manualmente.",
        )

    selected_ids = [
        str(item.get("sample_id") or "").strip()
        for item in edited_records
        if bool(item.get("selecionar"))
    ]
    filtered_ids = [str(row.get("sample_id") or "").strip() for row in visible_rows]
    target_ids = selected_ids if bulk_scope == "Linhas selecionadas" else filtered_ids

    def apply_bulk(classification: str) -> None:
        if not target_ids:
            st.warning("Nenhuma linha selecionada/filtrada para aplicar a ação.")
            return
        changed = 0
        for sample_id in target_ids:
            if sample_id not in draft:
                continue
            if only_blank and str(draft[sample_id].get("classification") or "").strip():
                continue
            draft[sample_id]["classification"] = classification
            changed += 1
        st.session_state[_draft_key(sample_path)] = draft
        if changed:
            st.toast(f"{changed} linha(s) marcadas como {classification} no rascunho.")
            st.rerun()
        else:
            st.info("Nenhuma linha foi alterada. Desmarque 'Preencher somente as vazias' se quiser substituir valores existentes.")

    bulk_cols = st.columns(3)
    if bulk_cols[0].button("Marcar RELEVANT", use_container_width=True, key=f"gf02_bulk_rel::{sample_path}"):
        apply_bulk("RELEVANT")
    if bulk_cols[1].button("Marcar IRRELEVANT", use_container_width=True, key=f"gf02_bulk_irr::{sample_path}"):
        apply_bulk("IRRELEVANT")
    if bulk_cols[2].button("Marcar DOUBT", use_container_width=True, key=f"gf02_bulk_doubt::{sample_path}"):
        apply_bulk("DOUBT")

    counts = _draft_counts(draft)
    save_col, finish_col, reset_col = st.columns([1, 1.25, 0.8])
    save_progress = save_col.button(
        "Salvar progresso",
        use_container_width=True,
        key=f"gf02_save_progress::{sample_path}",
        help="Salva somente as linhas que já têm uma classificação explícita; as demais permanecem em branco.",
    )
    finish = finish_col.button(
        "Finalizar revisão",
        type="primary",
        use_container_width=True,
        disabled=counts["unclassified"] > 0,
        key=f"gf02_finish_review::{sample_path}",
        help="Fica disponível quando todas as linhas tiverem classificação.",
    )
    reset = reset_col.button(
        "Recarregar",
        use_container_width=True,
        key=f"gf02_reset_draft::{sample_path}",
        help="Descarta alterações ainda não salvas e recarrega o CSV auditável.",
    )

    if reset:
        _reset_draft(sample_path)
        st.rerun()

    if save_progress:
        decisions = _decisions_from_draft(draft, complete=False)
        try:
            result = save_rescue_only_progress(
                sample_path,
                reviewer=reviewer,
                decisions=decisions,
            )
        except (OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Progresso salvo: {result['updated']} linha(s) persistidas no CSV auditável.")
            _reset_draft(sample_path)
            st.rerun()

    if finish:
        decisions = _decisions_from_draft(draft, complete=True)
        try:
            save_rescue_only_batch(
                sample_path,
                reviewer=reviewer,
                decisions=decisions,
            )
        except (OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.success("Revisão humana completa salva. Agora use CONTINUAR.")
            _reset_draft(sample_path)
            st.rerun()

    if counts["unclassified"]:
        st.caption(
            f"Faltam {counts['unclassified']} classificação(ões). Use o filtro 'Não classificados' + uma ação em lote para acelerar."
        )


__all__ = ["render_gf02_easy_review"]
