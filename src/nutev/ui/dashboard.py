from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from nutev.ui.charts import (
    render_domain_distribution,
    render_pipeline_timeline,
    render_recommendation_status_chart,
    render_status_distribution,
)
from nutev.ui.components import (
    claim_card,
    download_card,
    empty_state,
    info_banner,
    inject_premium_css,
    metric_card,
    recommendation_card,
    render_header,
    safety_notice,
    safe_columns,
    section_card,
    warning_banner,
)
from nutev.ui.loaders import (
    calculate_overview_metrics,
    list_export_artifacts,
    load_csv,
    load_json_file,
    load_jsonl,
    load_xlsx_or_csv,
)


def load_data(project_root: Path) -> dict[str, object]:
    metadata, _ = load_csv(project_root / "02_metadata" / "metadata_master.csv")
    claims, _ = load_csv(project_root / "02_metadata" / "NUTEV_EVIDENCE_CLAIMS.csv")
    recs, _ = load_csv(project_root / "02_metadata" / "NUTEV_RECOMMENDATION_CANDIDATES.csv")
    global_matrix, gm_status = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_GLOBAL_EVIDENCE_MATRIX.xlsx", project_root / "06_tables" / "NUTEV_GLOBAL_EVIDENCE_MATRIX.csv")
    protocol_matrix, pm_status = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_PROTOCOL_TRANSLATION_MATRIX.xlsx", project_root / "06_tables" / "NUTEV_PROTOCOL_TRANSLATION_MATRIX.csv")
    hrq, _ = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_HUMAN_REVIEW_QUEUE.xlsx", project_root / "06_tables" / "NUTEV_HUMAN_REVIEW_QUEUE.csv")
    readiness, _ = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_PROTOCOL_READINESS_MATRIX.xlsx", project_root / "06_tables" / "NUTEV_PROTOCOL_READINESS_MATRIX.csv")
    gaps, _ = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_EVIDENCE_GAP_REGISTER.xlsx", project_root / "06_tables" / "NUTEV_EVIDENCE_GAP_REGISTER.csv")
    convergence, _ = load_xlsx_or_csv(project_root / "06_tables" / "NUTEV_EVIDENCE_CONVERGENCE_MATRIX.xlsx", project_root / "06_tables" / "NUTEV_EVIDENCE_CONVERGENCE_MATRIX.csv")
    run_summary, _ = load_json_file(project_root / "07_logs" / "run_summary.json")
    events, _ = load_jsonl(project_root / "07_logs" / "run_events.jsonl")
    decisions, _ = load_csv(project_root / "07_logs" / "human_review_decisions.csv")
    return {
        "metadata": metadata,
        "claims": claims,
        "recs": recs,
        "global_matrix": global_matrix,
        "gm_status": gm_status,
        "protocol_matrix": protocol_matrix,
        "pm_status": pm_status,
        "hrq": hrq,
        "readiness": readiness,
        "gaps": gaps,
        "convergence": convergence,
        "run_summary": run_summary,
        "events": events,
        "decisions": decisions,
    }


def filter_dataframe(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    view = df.copy()
    for col in cols:
        if col in view.columns:
            values = sorted([v for v in view[col].dropna().astype(str).unique().tolist() if v and v != "nan"])
            selected = st.multiselect(col, values, default=[])
            if selected:
                view = view[view[col].astype(str).isin(selected)]
    return view


def render_metrics(metrics: dict[str, int]) -> None:
    items = list(metrics.items())
    for start in range(0, len(items), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, items[start : start + 4]):
            with col:
                metric_card(label.replace("_", " ").title(), value)


def build_human_review_queue(claims: pd.DataFrame, recs: pd.DataFrame, hrq: pd.DataFrame) -> pd.DataFrame:
    q = hrq.copy()
    if not claims.empty:
        needs = pd.Series(False, index=claims.index)
        if "needs_human_review" in claims.columns:
            needs = claims["needs_human_review"].astype(str).str.lower().isin(["true", "1", "yes"])
        if "claim_status" in claims.columns:
            needs = needs | claims["claim_status"].astype(str).isin(["inference_only", "insufficient_evidence", "conflicting", "needs_human_review"])
        add = claims[needs].copy()
        if not add.empty:
            add["item_type"] = "claim"
            q = pd.concat([q, add], ignore_index=True)
    if not recs.empty and "recommendation_status" in recs.columns:
        add_r = recs[recs["recommendation_status"].astype(str).isin(["insufficient_evidence", "conflicting_evidence", "draft_needs_evidence", "ready_for_human_review"])].copy()
        if not add_r.empty:
            add_r["item_type"] = "recommendation_candidate"
            q = pd.concat([q, add_r], ignore_index=True)
    return q


def run_dashboard(project_root: Path) -> None:
    st.set_page_config(page_title="NutEV Control Center", layout="wide")
    inject_premium_css()
    data = load_data(project_root)
    metadata = data["metadata"]
    claims = data["claims"]
    recs = data["recs"]
    global_matrix = data["global_matrix"]
    protocol_matrix = data["protocol_matrix"]
    hrq = data["hrq"]
    readiness = data["readiness"]
    convergence = data["convergence"]
    run_summary = data["run_summary"]
    events = data["events"]
    decisions = data["decisions"]

    st.sidebar.markdown("## NutEV Control Center")
    st.sidebar.caption("Evidence Engine for Lifestyle Nutrition")
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Evidence Engine", "Search Strategy", "Audit Engine", "Recommendations", "Human Review", "Provider Settings", "Export Center", "Logs", "Methods"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Project root: `{project_root}`")

    if page == "Home":
        render_header("NutEV Control Center", "Evidence Engine for Lifestyle Nutrition")
        safety_notice()
        render_metrics(calculate_overview_metrics(run_summary, metadata, claims, recs))
        section_card("Evidence to protocol", "Evidence -> Claim -> Evaluation -> Recommendation Candidate -> Human Review -> Protocol Readiness")
        c1, c2 = st.columns(2)
        with c1:
            render_status_distribution(claims, "claim_status")
        with c2:
            render_recommendation_status_chart(recs)

    elif page == "Evidence Engine":
        render_header("Evidence Engine", "Global evidence matrix, lenses, domains and protocol translation")
        tabs = st.tabs(["Global Matrix", "Protocol Translation", "Convergence"])
        with tabs[0]:
            if global_matrix.empty:
                empty_state("Global matrix unavailable", str(data["gm_status"]))
            else:
                view = filter_dataframe(global_matrix, ["evidence_lens", "workstream", "nutev_domains", "clinical_conditions", "dietary_patterns", "outcomes", "country"])
                render_domain_distribution(view)
                st.dataframe(view, use_container_width=True)
        with tabs[1]:
            if protocol_matrix.empty:
                empty_state("Protocol translation unavailable", str(data["pm_status"]))
            else:
                st.dataframe(protocol_matrix, use_container_width=True)
        with tabs[2]:
            if convergence.empty:
                empty_state("Convergence matrix unavailable", "Run the scientific rigor exports to populate this table.")
            else:
                st.dataframe(convergence, use_container_width=True)

    elif page == "Search Strategy":
        render_header("Pesquisa global NutEV", "Um único campo de pesquisa para todos os artigos")
        info_banner(
            "A consulta é construída uma única vez e enviada às bases selecionadas. "
            "A associação com os Artigos 1 a 5 acontece depois da recuperação, "
            "sem duplicar o registro bibliográfico. Separe termos alternativos por "
            "vírgula, ponto e vírgula ou nova linha."
        )
        import json

        from nutev.search.strategy_builder import BREADTHS, build_all, parse_strategy, unified_from_text
        from nutev.ui.search_registry_panel import render_search_registry_panel

        query_text = st.text_area(
            "O que você deseja pesquisar?",
            placeholder=(
                "adesão alimentar\n"
                "competências alimentares\n"
                "guias alimentares\n"
                "implementação de intervenções nutricionais"
            ),
            height=180,
            help=(
                "Este é o único campo de pesquisa. Os termos informados são usados "
                "em todos os artigos e classificados posteriormente."
            ),
        )

        with st.expander("Opções avançadas", expanded=False):
            col_y1, col_y2, col_y3, col_y4 = st.columns(4)
            with col_y1:
                year_from = st.number_input("Ano inicial", min_value=0, max_value=3000, value=0, step=1)
            with col_y2:
                year_to = st.number_input("Ano final", min_value=0, max_value=3000, value=0, step=1)
            with col_y3:
                languages = st.text_input("Idiomas", placeholder="eng, por, spa")
            with col_y4:
                publication_types = st.text_input("Tipos de publicação", placeholder="Guideline")

        spec_dict = unified_from_text(
            query_text,
            year_from=year_from,
            year_to=year_to,
            languages=languages,
            publication_types=publication_types,
        )

        if not spec_dict:
            empty_state("Nenhuma pesquisa informada", "Digite um tema, pergunta ou conjunto de termos no campo acima.")
        else:
            grid = build_all(parse_strategy(spec_dict))
            st.caption(
                "broad e balanced usam o mesmo campo global; specific acrescenta "
                "os filtros opcionais de ano, idioma e tipo de publicação."
            )
            for provider, by_breadth in grid.items():
                st.subheader(provider)
                for breadth in BREADTHS:
                    expression = by_breadth.get(breadth) or "(empty)"
                    st.markdown(f"**{breadth}**")
                    st.code(expression, language="text")

            strategy_payload = {
                "article_scope": spec_dict["article_scope"],
                "query": spec_dict["query"],
                "filters": {
                    "year_from": spec_dict.get("year_from"),
                    "year_to": spec_dict.get("year_to"),
                    "languages": spec_dict.get("languages", []),
                    "publication_types": spec_dict.get("publication_types", []),
                },
                "providers": grid,
            }
            render_search_registry_panel(
                project_root,
                query_text=query_text,
                strategy_payload=strategy_payload,
            )
            st.download_button(
                "Baixar estratégia global (JSON)",
                json.dumps(strategy_payload, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="NUTEV_GLOBAL_SEARCH_STRATEGY.json",
                mime="application/json",
            )

    elif page == "Audit Engine":
        render_header("Audit Engine", "Document to claim traceability and anti-hallucination safeguards")
        if claims.empty:
            empty_state("Claims unavailable", "No Evidence Claims file found yet.")
        else:
            view = filter_dataframe(claims, ["claim_status", "human_validation_status", "evidence_type", "needs_human_review"])
            render_status_distribution(view, "claim_status")
            st.dataframe(safe_columns(view, ["claim_id", "document_id", "title", "claim_text", "exact_quote", "source_url", "evidence_type", "claim_status", "human_validation_status", "needs_human_review"]), use_container_width=True)
            for _, row in view.head(3).iterrows():
                claim_card(row)

    elif page == "Recommendations":
        render_header("Recommendation Candidates", "Candidates are not final recommendations")
        warning_banner("RecommendationCandidate is not a final recommendation. Do not advance items without support and human review.")
        if recs.empty:
            empty_state("Recommendations unavailable", "No recommendation candidate file found yet.")
        else:
            view = filter_dataframe(recs, ["recommendation_status", "human_approval_status", "protocol_component", "readiness_class"])
            render_recommendation_status_chart(view)
            st.dataframe(safe_columns(view, ["recommendation_id", "recommendation_text", "protocol_component", "supporting_claim_ids", "supporting_document_ids", "conflicting_claim_ids", "recommendation_status", "human_approval_status", "readiness_class", "evidence_gap"]), use_container_width=True)
            for _, row in view.head(3).iterrows():
                recommendation_card(row)
        if not readiness.empty:
            st.subheader("Protocol readiness")
            st.dataframe(readiness, use_container_width=True)

    elif page == "Human Review":
        render_header("Human Review", "Queue, decisions and adjudication support")
        q = build_human_review_queue(claims, recs, hrq)
        if q.empty:
            empty_state("Human review queue unavailable", "No queue items found yet.")
        else:
            st.dataframe(q, use_container_width=True)
            st.download_button("Download Human Review Queue CSV", q.to_csv(index=False).encode("utf-8"), file_name="NUTEV_HUMAN_REVIEW_QUEUE.csv")
        st.subheader("Recorded decisions")
        st.dataframe(decisions if not decisions.empty else pd.DataFrame({"status": ["not available yet"]}), use_container_width=True)

    elif page == "Provider Settings":
        render_header("Provider Settings", "Local providers and LLM governance")
        info_banner("Use environment variables for provider credentials. LLMs are assistive only and cannot approve protocol items.")
        from nutev.search.provider_registry import provider_credential_rows

        st.dataframe(pd.DataFrame(provider_credential_rows()), use_container_width=True)

    elif page == "Export Center":
        render_header("Export Center", "Download matrices, reports and logs")
        artifacts = list_export_artifacts(project_root)
        st.dataframe(artifacts, use_container_width=True)
        for _, row in artifacts[artifacts["status"] == "available"].iterrows():
            download_card(str(row["artifact"]), project_root / str(row["relative_path"]))

    elif page == "Logs":
        render_header("Logs", "Run summary, events and failure diagnostics")
        st.subheader("run_summary.json")
        st.json(run_summary if run_summary else {"status": "not available yet"})
        render_pipeline_timeline(events)
        failed, _ = load_csv(project_root / "03_corpus" / "failed_downloads.csv")
        st.subheader("failed_downloads.csv")
        st.dataframe(failed if not failed.empty else pd.DataFrame({"status": ["not available yet"]}), use_container_width=True)

    elif page == "Methods":
        render_header("Methods Preview", "Qualification-ready methodological text")
        for label, path in [("Methods", project_root / "08_docs" / "NUTEV_METHODS_MASTER.md"), ("Pilot report", project_root / "08_docs" / "NUTEV_PILOT_REPORT.md"), ("Scientific rigor report", project_root / "08_docs" / "NUTEV_SCIENTIFIC_RIGOR_REPORT.md")]:
            st.subheader(label)
            if path.exists():
                st.markdown(path.read_text(encoding="utf-8"))
            else:
                empty_state(f"{label} unavailable", f"{path.name} not generated yet.")


def main() -> None:
    default_root = os.environ.get("NUTEV_DASHBOARD_PROJECT_ROOT", "./project_output")
    root = Path(st.sidebar.text_input("Project Root", default_root))
    run_dashboard(root)


if __name__ == "__main__":
    main()
