"""Streamlit steps 10–12: double extraction, appraisal, and final matrices."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from nutev.review.article_screening_ledger import (
    list_article_catalog,
    list_screening_sessions,
)
from nutev.review.evidence_matrix import (
    FIELD_TYPES,
    SLOTS,
    adjudicate_extraction,
    adjudicate_quality,
    assign_instrument,
    compare_extractions,
    compare_quality,
    export_snapshot,
    included_documents,
    instrument_by_id,
    latest_extractions,
    latest_quality_assessments,
    latest_quality_assignment,
    list_instruments,
    list_schema,
    save_instrument,
    save_schema_field,
    submit_extraction,
    submit_quality,
    summarize,
)
from nutev.review.human_review import REVIEWER_ROLES


def _session_label(row: dict[str, Any]) -> str:
    return f"{row['session_id']} · corpus {row['build_id']} · {row['status']}"


def _document_label(row: dict[str, Any]) -> str:
    return (
        f"{str(row.get('title') or 'Sem título')[:90]} · "
        f"{row.get('year') or ''} · {str(row['document_id'])[-10:]}"
    )


def _judgment(value: str) -> str:
    return {
        "YES": "Sim",
        "PARTIAL": "Parcial",
        "NO": "Não",
        "UNCLEAR": "Incerto",
        "NOT_APPLICABLE": "Não aplicável",
        "HIGH": "Alta",
        "MODERATE": "Moderada",
        "LOW": "Baixa",
        "CRITICALLY_LOW": "Criticamente baixa",
        "SOME_CONCERNS": "Algumas preocupações",
        "SERIOUS": "Sério",
        "CRITICAL": "Crítico",
        "NO_INFORMATION": "Sem informação",
        "INSUFFICIENT": "Insuficiente",
    }.get(value, value.replace("_", " ").title())


def _widget(field: dict[str, Any], key: str, value: Any = None) -> Any:
    label = str(field["label"])
    help_text = str(field.get("description") or "") or None
    kind = str(field["field_type"])
    if kind == "LONG_TEXT":
        return st.text_area(
            label,
            value=str(value or ""),
            help=help_text,
            key=key,
        )
    if kind in {"INTEGER", "FLOAT"}:
        return st.text_input(
            label,
            value="" if value in (None, "") else str(value),
            help=help_text,
            key=key,
        )
    if kind == "BOOLEAN":
        return st.checkbox(label, value=bool(value), help=help_text, key=key)
    if kind == "SINGLE_SELECT":
        options = list(field.get("options") or [])
        index = options.index(value) if value in options else 0
        return st.selectbox(
            label,
            options,
            index=index,
            help=help_text,
            key=key,
        )
    if kind == "MULTI_SELECT":
        return st.multiselect(
            label,
            list(field.get("options") or []),
            default=list(value or []),
            help=help_text,
            key=key,
        )
    if kind == "JSON":
        initial = (
            json.dumps(value, ensure_ascii=False, indent=2)
            if value not in (None, "")
            else ""
        )
        return st.text_area(
            label,
            value=initial,
            help="Informe JSON válido.",
            key=key,
        )
    return st.text_input(
        label,
        value=str(value or ""),
        help=help_text,
        key=key,
    )


def _parse_domains(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3:
            raise ValueError(
                f"Linha {number}: use chave | rótulo | julgamentos "
                "separados por ponto e vírgula."
            )
        key, label, values = parts
        judgments = [
            item.strip().upper()
            for item in values.split(";")
            if item.strip()
        ]
        rows.append(
            {
                "domain_key": key,
                "label": label,
                "judgments": judgments,
                "required": True,
            }
        )
    if not rows:
        raise ValueError("Informe ao menos um domínio.")
    return rows


def _schema_tab(db_path: Path, article_id: str, reviewer_name: str) -> None:
    schema = list_schema(db_path, article_id)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "escopo": (
                        "comum" if row["scope"] == "__common__" else article_id
                    ),
                    "campo": row["field_key"],
                    "rótulo": row["label"],
                    "tipo": row["field_type"],
                    "obrigatório": row["required"],
                    "revisão": row["revision"],
                }
                for row in schema
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    with st.form(f"schema_{article_id}"):
        col1, col2, col3 = st.columns(3)
        scope = col1.selectbox("Escopo", ["ARTICLE", "COMMON"])
        field_key = col2.text_input(
            "Chave",
            placeholder="mecanismo_comportamental",
        )
        field_type = col3.selectbox("Tipo", FIELD_TYPES)
        label = st.text_input("Rótulo")
        description = st.text_area("Descrição ao revisor")
        options = st.text_input(
            "Opções separadas por ponto e vírgula",
            disabled=field_type not in {"SINGLE_SELECT", "MULTI_SELECT"},
        )
        required = st.checkbox("Obrigatório")
        submitted = st.form_submit_button("Salvar nova revisão do campo")
    if submitted:
        try:
            saved = save_schema_field(
                db_path,
                field_key=field_key,
                label=label,
                field_type=field_type,
                created_by=reviewer_name,
                article_id=article_id if scope == "ARTICLE" else None,
                description=description,
                options=[
                    item.strip() for item in options.split(";") if item.strip()
                ],
                required=required,
                display_order=len(schema) + 1,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Campo salvo como revisão {saved['revision']}.")


def _extraction_tab(
    db_path: Path,
    session_id: str,
    article_id: str,
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    documents = included_documents(db_path, session_id, article_id)
    if not documents:
        st.info(
            "Nenhum documento foi incluído após a avaliação de texto completo."
        )
        return
    labels = [_document_label(row) for row in documents]
    by_label = dict(zip(labels, documents))
    row = by_label[
        st.selectbox(
            "Documento",
            labels,
            key=f"extract_doc_{session_id}_{article_id}",
        )
    ]
    document_id = str(row["document_id"])
    slot = st.radio(
        "Posição na dupla",
        SLOTS,
        format_func=lambda value: (
            "Revisor 1" if value == "REVIEWER_1" else "Revisor 2"
        ),
        horizontal=True,
        key=f"extract_slot_{session_id}_{article_id}",
    )
    current_rows = latest_extractions(
        db_path,
        session_id,
        article_id,
        document_id,
    )
    current = next(
        (
            item["values"]
            for item in current_rows
            if item["reviewer_slot"] == slot
        ),
        {},
    )
    schema = list_schema(db_path, article_id)
    st.caption(
        f"Arquivo: `{row.get('retrieval_artifact_path') or 'fonte externa'}` · "
        f"Integridade: {row.get('artifact_integrity')}"
    )
    with st.form(
        f"extract_form_{session_id}_{article_id}_{document_id}_{slot}"
    ):
        values = {
            field["field_key"]: _widget(
                field,
                (
                    f"extract_{document_id}_{article_id}_{slot}_"
                    f"{field['field_key']}"
                ),
                current.get(field["field_key"]),
            )
            for field in schema
        }
        submitted = st.form_submit_button("Registrar extração")
    if submitted:
        try:
            saved = submit_extraction(
                db_path,
                session_id=session_id,
                document_id=document_id,
                article_id=article_id,
                reviewer_slot=slot,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
                values=values,
            )
        except (TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Extração registrada como revisão {saved['revision']}.")

    comparison = compare_extractions(
        db_path,
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "campo": item["label"],
                    "revisor 1": item["reviewer_1"],
                    "revisor 2": item["reviewer_2"],
                    "situação": item["status"],
                    "final": item["final"],
                }
                for item in comparison
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    divergent = [
        item
        for item in comparison
        if item["status"] == "DIVERGENT"
        and item["final_status"] == "PENDING"
    ]
    if divergent:
        selected = st.selectbox(
            "Campo para adjudicar",
            [item["field_key"] for item in divergent],
            format_func=lambda key: next(
                item["label"] for item in divergent if item["field_key"] == key
            ),
        )
        item = next(
            value for value in divergent if value["field_key"] == selected
        )
        field = next(
            value for value in schema if value["field_key"] == selected
        )
        with st.form(
            f"extract_adjudication_{session_id}_{article_id}_"
            f"{document_id}_{selected}"
        ):
            final_value = _widget(
                field,
                f"extract_final_{document_id}_{article_id}_{selected}",
                item["reviewer_1"],
            )
            notes = st.text_area("Justificativa da adjudicação")
            adjudicate = st.form_submit_button("Registrar decisão final")
        if adjudicate:
            try:
                saved = adjudicate_extraction(
                    db_path,
                    session_id=session_id,
                    document_id=document_id,
                    article_id=article_id,
                    field_key=selected,
                    final_value=final_value,
                    adjudicator_name=reviewer_name,
                    adjudicator_role=reviewer_role,
                    notes=notes,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Adjudicação registrada como revisão {saved['revision']}."
                )


def _instrument_config(db_path: Path, reviewer_name: str) -> None:
    with st.expander("Configurar nova versão de instrumento", expanded=False):
        st.caption(
            "Registre a estrutura de avaliação e consulte o manual oficial do "
            "instrumento."
        )
        with st.form("quality_instrument_config"):
            col1, col2, col3 = st.columns(3)
            key = col1.text_input("Chave", placeholder="CUSTOM_TOOL")
            name = col2.text_input("Nome")
            version = col3.text_input("Versão", placeholder="v1")
            description = st.text_area("Descrição")
            document_types = st.text_input(
                "Tipos documentais",
                placeholder="guideline; systematic review",
            )
            overall = st.text_input(
                "Julgamentos globais",
                value=(
                    "HIGH; MODERATE; LOW; INSUFFICIENT; NOT_APPLICABLE"
                ),
            )
            domains = st.text_area(
                "Domínios",
                value=(
                    "rigour | Rigor metodológico | "
                    "YES;PARTIAL;NO;UNCLEAR;NOT_APPLICABLE\n"
                    "transparency | Transparência | "
                    "YES;PARTIAL;NO;UNCLEAR;NOT_APPLICABLE"
                ),
            )
            submitted = st.form_submit_button("Salvar versão")
        if submitted:
            try:
                saved = save_instrument(
                    db_path,
                    instrument_key=key,
                    name=name,
                    version_label=version,
                    description=description,
                    document_types=[
                        item.strip()
                        for item in document_types.split(";")
                        if item.strip()
                    ],
                    overall_values=[
                        item.strip().upper()
                        for item in overall.split(";")
                        if item.strip()
                    ],
                    domains=_parse_domains(domains),
                    created_by=reviewer_name,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Instrumento salvo como revisão {saved['revision']}."
                )


def _quality_tab(
    db_path: Path,
    session_id: str,
    article_id: str,
    reviewer_name: str,
    reviewer_role: str,
) -> None:
    _instrument_config(db_path, reviewer_name)
    documents = included_documents(db_path, session_id, article_id)
    if not documents:
        st.info("Nenhum documento incluído para avaliação metodológica.")
        return
    labels = [_document_label(row) for row in documents]
    row = dict(zip(labels, documents))[
        st.selectbox(
            "Documento",
            labels,
            key=f"quality_doc_{session_id}_{article_id}",
        )
    ]
    document_id = str(row["document_id"])
    assignment = latest_quality_assignment(
        db_path,
        session_id,
        document_id,
        article_id,
    )
    document_type = str(
        row.get("article_type") or row.get("document_type") or ""
    )
    instruments = list_instruments(db_path, document_type)
    instrument_labels = [
        f"{item['name']} · {item['instrument_key']} · r{item['revision']}"
        for item in instruments
    ]
    by_label = dict(zip(instrument_labels, instruments))
    default = next(
        (
            index
            for index, item in enumerate(instruments)
            if assignment and item["id"] == assignment["instrument_id"]
        ),
        0,
    )
    with st.form(
        f"instrument_assignment_{session_id}_{article_id}_{document_id}"
    ):
        chosen = st.selectbox("Instrumento", instrument_labels, index=default)
        basis = st.selectbox(
            "Base da seleção",
            ["HUMAN", "RULE_SUGGESTION"],
            format_func=lambda value: (
                "Seleção humana"
                if value == "HUMAN"
                else "Sugestão confirmada pelo revisor"
            ),
        )
        rationale = st.text_area(
            "Justificativa",
            value=str(assignment.get("rationale") or "") if assignment else "",
        )
        submitted = st.form_submit_button("Registrar instrumento")
    if submitted:
        try:
            saved = assign_instrument(
                db_path,
                session_id=session_id,
                document_id=document_id,
                article_id=article_id,
                instrument_id=by_label[chosen]["id"],
                selection_basis=basis,
                rationale=rationale,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Seleção registrada como revisão {saved['revision']}.")
    assignment = latest_quality_assignment(
        db_path,
        session_id,
        document_id,
        article_id,
    )
    if not assignment:
        st.info("Registre o instrumento para abrir a avaliação.")
        return
    tool = instrument_by_id(db_path, assignment["instrument_id"])
    if tool is None:
        st.error("A versão selecionada do instrumento não foi localizada.")
        return
    slot = st.radio(
        "Posição na dupla",
        SLOTS,
        format_func=lambda value: (
            "Revisor 1" if value == "REVIEWER_1" else "Revisor 2"
        ),
        horizontal=True,
        key=f"quality_slot_{session_id}_{article_id}_{document_id}",
    )
    current = latest_quality_assessments(
        db_path,
        session_id,
        document_id,
        article_id,
        tool["id"],
    ).get(slot, {})
    with st.form(
        f"quality_form_{session_id}_{article_id}_{document_id}_{slot}"
    ):
        values: dict[str, dict[str, str]] = {}
        for domain in tool["domains"]:
            prior = (current.get("domains") or {}).get(domain["domain_key"], {})
            col1, col2 = st.columns([1, 2])
            allowed = domain["judgments"]
            index = (
                allowed.index(prior.get("judgment"))
                if prior.get("judgment") in allowed
                else 0
            )
            judgment = col1.selectbox(
                domain["label"],
                allowed,
                index=index,
                format_func=_judgment,
                key=(
                    f"quality_j_{document_id}_{article_id}_{slot}_"
                    f"{domain['domain_key']}"
                ),
            )
            justification = col2.text_area(
                f"Justificativa · {domain['label']}",
                value=str(prior.get("justification") or ""),
                key=(
                    f"quality_x_{document_id}_{article_id}_{slot}_"
                    f"{domain['domain_key']}"
                ),
            )
            values[domain["domain_key"]] = {
                "judgment": judgment,
                "justification": justification,
            }
        overall_values = tool["overall_values"]
        prior_overall = current.get("overall")
        overall_index = (
            overall_values.index(prior_overall)
            if prior_overall in overall_values
            else 0
        )
        overall = st.selectbox(
            "Julgamento global",
            overall_values,
            index=overall_index,
            format_func=_judgment,
        )
        quality_rationale = st.text_area(
            "Racional global",
            value=str(current.get("rationale") or ""),
        )
        assessed = st.form_submit_button("Registrar avaliação")
    if assessed:
        try:
            saved = submit_quality(
                db_path,
                session_id=session_id,
                document_id=document_id,
                article_id=article_id,
                reviewer_slot=slot,
                domains=values,
                overall=overall,
                rationale=quality_rationale,
                reviewer_name=reviewer_name,
                reviewer_role=reviewer_role,
            )
        except (TypeError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.success(f"Avaliação registrada como revisão {saved['revision']}.")

    comparison = compare_quality(
        db_path,
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "domínio": item["label"],
                    "revisor 1": item["reviewer_1"],
                    "revisor 2": item["reviewer_2"],
                    "situação": item["status"],
                    "final": item["final"],
                }
                for item in comparison["domains"]
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    if (
        comparison["reviewer_1"]
        and comparison["reviewer_2"]
        and not comparison["complete"]
    ):
        with st.form(
            f"quality_adjudication_{session_id}_{article_id}_{document_id}"
        ):
            final_domains: dict[str, dict[str, str]] = {}
            for domain in tool["domains"]:
                compared = next(
                    item
                    for item in comparison["domains"]
                    if item["domain_key"] == domain["domain_key"]
                )
                prior = compared["final"] or compared["reviewer_1"] or {}
                col1, col2 = st.columns([1, 2])
                allowed = domain["judgments"]
                index = (
                    allowed.index(prior.get("judgment"))
                    if prior.get("judgment") in allowed
                    else 0
                )
                judgment = col1.selectbox(
                    f"Final · {domain['label']}",
                    allowed,
                    index=index,
                    format_func=_judgment,
                    key=(
                        f"quality_final_j_{document_id}_{article_id}_"
                        f"{domain['domain_key']}"
                    ),
                )
                justification = col2.text_area(
                    f"Justificativa final · {domain['label']}",
                    value=str(prior.get("justification") or ""),
                    key=(
                        f"quality_final_x_{document_id}_{article_id}_"
                        f"{domain['domain_key']}"
                    ),
                )
                final_domains[domain["domain_key"]] = {
                    "judgment": judgment,
                    "justification": justification,
                }
            final_overall = st.selectbox(
                "Julgamento global final",
                tool["overall_values"],
                format_func=_judgment,
            )
            notes = st.text_area("Notas da adjudicação")
            adjudicated = st.form_submit_button("Registrar avaliação final")
        if adjudicated:
            try:
                saved = adjudicate_quality(
                    db_path,
                    session_id=session_id,
                    document_id=document_id,
                    article_id=article_id,
                    domains=final_domains,
                    overall=final_overall,
                    adjudicator_name=reviewer_name,
                    adjudicator_role=reviewer_role,
                    notes=notes,
                )
            except (TypeError, ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Avaliação final registrada como revisão {saved['revision']}."
                )


def render_data_extraction_quality_panel(
    project_root: Path,
    *,
    registry_path: Path,
) -> None:
    del project_root
    sessions = list_screening_sessions(registry_path, limit=200)
    with st.expander(
        "10–12 · Extração, qualidade e matriz final",
        expanded=False,
    ):
        st.caption(
            "Somente documentos incluídos após texto completo entram nesta etapa. "
            "Duas revisões e adjudicação preservam o histórico original."
        )
        if not sessions:
            st.info("Crie uma sessão de triagem antes de iniciar.")
            return
        labels = [_session_label(row) for row in sessions]
        session = dict(zip(labels, sessions))[
            st.selectbox("Sessão científica", labels)
        ]
        session_id = str(session["session_id"])
        articles = list_article_catalog(registry_path, active_only=True)
        article_labels = [
            f"{row['label']} · {row['article_id']}" for row in articles
        ]
        article = dict(zip(article_labels, articles))[
            st.selectbox("Artigo", article_labels)
        ]
        article_id = str(article["article_id"])
        col1, col2 = st.columns(2)
        reviewer_name = col1.text_input(
            "Revisor ou adjudicador",
            value=os.environ.get("NUTEV_RESEARCHER_NAME", ""),
        )
        reviewer_role = col2.selectbox("Papel", sorted(REVIEWER_ROLES))
        summary = summarize(registry_path, session_id)
        current = next(
            row
            for row in summary["articles"]
            if row["article_id"] == article_id
        )
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Incluídos", current["included_documents"])
        metric2.metric("Extração pendente", current["extraction_pending"])
        metric3.metric("Qualidade pendente", current["quality_pending"])
        metric4.metric(
            "Concluídos",
            min(current["extraction_complete"], current["quality_complete"]),
        )
        tabs = st.tabs(
            [
                "Esquema",
                "Extração e adjudicação",
                "Qualidade metodológica",
                "Exportar",
            ]
        )
        with tabs[0]:
            _schema_tab(registry_path, article_id, reviewer_name)
        with tabs[1]:
            _extraction_tab(
                registry_path,
                session_id,
                article_id,
                reviewer_name,
                reviewer_role,
            )
        with tabs[2]:
            _quality_tab(
                registry_path,
                session_id,
                article_id,
                reviewer_name,
                reviewer_role,
            )
        with tabs[3]:
            st.dataframe(
                pd.DataFrame(summary["articles"]),
                use_container_width=True,
                hide_index=True,
            )
            if st.button(
                "Gerar matriz final e manifesto",
                type="primary",
                key=f"matrix_export_{session_id}",
            ):
                try:
                    exported = export_snapshot(registry_path, session_id)
                except (OSError, TypeError, ValueError, RuntimeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Matriz final exportada com SHA-256.")
                    for label, path in exported["paths"].items():
                        st.caption(f"{label}: `{path}`")
