from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3

import pytest

from nutev.review.article_screening import (
    ensure_screening_session,
    save_article_screening_decision,
)
from nutev.review.evidence_matrix import (
    adjudicate_extraction,
    adjudicate_quality,
    assign_instrument,
    compare_extractions,
    compare_quality,
    export_snapshot,
    final_extraction,
    final_quality,
    included_documents,
    initialize,
    list_instruments,
    list_schema,
    save_schema_field,
    submit_extraction,
    submit_quality,
)
from nutev.review.full_text_assessment import (
    save_full_text_eligibility_decision,
    save_full_text_retrieval,
)
from nutev.search.base import ProviderResult
from nutev.search.corpus_builder import build_corpus_from_search_run
from nutev.search.strategy_executor import execute_strategy_version
from nutev.search.strategy_registry import (
    default_registry_path,
    save_strategy_version,
)


def _payload() -> dict:
    return {
        "article_scope": "all_articles",
        "query": ["food competence"],
        "filters": {},
        "providers": {"pubmed": {"specific": "food competence[tiab]"}},
    }


def _included_session(tmp_path: Path) -> tuple[Path, str, str, Path]:
    registry = default_registry_path(tmp_path)
    version = save_strategy_version(
        registry,
        title="Evidence matrix formal",
        query_text="food competence",
        strategy_payload=_payload(),
        search_type="FORMAL",
        created_by="Researcher",
        created_at="2026-08-04T20:00:00-03:00",
    )
    rows = [
        {
            "title": "Competence trial",
            "doi": "10.1000/matrix",
            "pmid": "321",
            "url": "https://example.org/matrix",
            "year": 2025,
            "article_type": "randomized trial",
            "abstract": "A randomized trial of food competence.",
        }
    ]

    def fake_search(**kwargs):
        return ProviderResult(
            provider=kwargs["provider"],
            query=kwargs["query"],
            rows=rows,
            total_found=1,
            total_returned=1,
            status="completed",
        )

    execute_strategy_version(
        tmp_path,
        registry_path=registry,
        version_id=version.version_id,
        breadth="specific",
        providers=["pubmed"],
        limit=20,
        resume=False,
        search_fn=fake_search,
        run_id="run_matrix",
        started_at="2026-08-04T20:05:00-03:00",
    )
    build = build_corpus_from_search_run(
        tmp_path,
        registry_path=registry,
        run_id="run_matrix",
        build_id="build_matrix",
        started_at="2026-08-04T20:10:00-03:00",
    )
    record = json.loads(
        Path(build["master_jsonl_path"])
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    document_id = str(record["document_id"])
    session = ensure_screening_session(
        registry,
        build_id=str(build["build_id"]),
        protocol_version="v1",
        created_by="Researcher",
    )
    session_id = str(session["session_id"])
    for article_id in ("article_1", "article_2"):
        save_article_screening_decision(
            registry,
            session_id=session_id,
            document_id=document_id,
            article_id=article_id,
            decision="INCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
            stage="TITLE_ABSTRACT",
        )
    artifact = tmp_path / "full_text.pdf"
    artifact.write_bytes(b"%PDF-1.4\nsynthetic full text\n")
    save_full_text_retrieval(
        registry,
        session_id=session_id,
        document_id=document_id,
        status="AVAILABLE",
        reviewer_name="Reviewer",
        reviewer_role="reviewer_1",
        artifact_path=str(artifact),
        source_url="https://example.org/matrix.pdf",
    )
    for article_id in ("article_1", "article_2"):
        save_full_text_eligibility_decision(
            registry,
            session_id=session_id,
            document_id=document_id,
            article_id=article_id,
            decision="INCLUDE",
            reviewer_name="Reviewer",
            reviewer_role="reviewer_1",
        )
    return registry, session_id, document_id, artifact


def _schema_values(
    schema: list[dict],
    *,
    different_result: bool = False,
) -> dict:
    values: dict = {}
    for field in schema:
        key = field["field_key"]
        kind = field["field_type"]
        if kind == "INTEGER":
            values[key] = 100
        elif kind == "FLOAT":
            values[key] = 1.5
        elif kind == "BOOLEAN":
            values[key] = True
        elif kind == "DATE":
            values[key] = "2026-08-04"
        elif kind == "SINGLE_SELECT":
            values[key] = field["options"][0]
        elif kind == "MULTI_SELECT":
            values[key] = field["options"][:1]
        elif kind == "JSON":
            values[key] = {"value": 1}
        elif field["required"] or key in {"main_results", "mechanism"}:
            values[key] = f"Valor para {key}"
        else:
            values[key] = None
    if different_result:
        values["main_results"] = "Resultado divergente do revisor 2"
    return values


def _domain_values(tool: dict, *, divergent: bool = False) -> dict:
    values = {}
    for index, domain in enumerate(tool["domains"]):
        judgment = domain["judgments"][0]
        if divergent and index == 0 and len(domain["judgments"]) > 1:
            judgment = domain["judgments"][1]
        values[domain["domain_key"]] = {
            "judgment": judgment,
            "justification": f"Justificativa para {domain['domain_key']}",
        }
    return values


def test_double_extraction_adjudication_and_article_specific_schema(tmp_path):
    registry, session_id, document_id, _ = _included_session(tmp_path)
    saved_field = save_schema_field(
        registry,
        field_key="mechanism",
        label="Mecanismo comportamental",
        field_type="SINGLE_SELECT",
        options=["antecedent", "consequence"],
        required=True,
        article_id="article_1",
        created_by="Researcher",
        display_order=50,
    )
    assert saved_field["revision"] == 1
    article_1_schema = list_schema(registry, "article_1")
    article_2_schema = list_schema(registry, "article_2")
    assert "mechanism" in {row["field_key"] for row in article_1_schema}
    assert "mechanism" not in {row["field_key"] for row in article_2_schema}

    reviewer_1 = _schema_values(article_1_schema)
    reviewer_2 = _schema_values(article_1_schema, different_result=True)
    first = submit_extraction(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        reviewer_slot="REVIEWER_1",
        reviewer_name="Reviewer One",
        reviewer_role="reviewer_1",
        values=reviewer_1,
    )
    second = submit_extraction(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        reviewer_slot="REVIEWER_2",
        reviewer_name="Reviewer Two",
        reviewer_role="reviewer_2",
        values=reviewer_2,
    )
    assert first["revision"] == 1
    assert second["revision"] == 1
    comparison = compare_extractions(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
    )
    main_result = next(
        row for row in comparison if row["field_key"] == "main_results"
    )
    assert main_result["status"] == "DIVERGENT"
    assert main_result["final_status"] == "PENDING"

    adjudication = adjudicate_extraction(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        field_key="main_results",
        final_value="Resultado final adjudicado",
        adjudicator_name="Principal Investigator",
        adjudicator_role="principal_investigator",
        notes="Conferido no texto completo.",
    )
    assert adjudication["revision"] == 1
    final = final_extraction(
        registry,
        session_id,
        document_id,
        "article_1",
    )
    assert final["extraction_complete"] is True
    assert final["extracted__main_results"] == "Resultado final adjudicado"

    revision = submit_extraction(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        reviewer_slot="REVIEWER_1",
        reviewer_name="Reviewer One",
        reviewer_role="reviewer_1",
        values=reviewer_1,
    )
    assert revision["revision"] == 2
    with sqlite3.connect(registry) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM extraction_submissions "
            "WHERE session_id=? AND document_id=? AND article_id='article_1' "
            "AND reviewer_slot='REVIEWER_1'",
            (session_id, document_id),
        ).fetchone()[0]
    assert count == 2


def test_double_quality_appraisal_adjudication_and_export(tmp_path):
    registry, session_id, document_id, _ = _included_session(tmp_path)
    schema = list_schema(registry, "article_1")
    values = _schema_values(schema)
    for slot, role in (
        ("REVIEWER_1", "reviewer_1"),
        ("REVIEWER_2", "reviewer_2"),
    ):
        submit_extraction(
            registry,
            session_id=session_id,
            document_id=document_id,
            article_id="article_1",
            reviewer_slot=slot,
            reviewer_name=slot,
            reviewer_role=role,
            values=values,
        )

    tools = list_instruments(registry, "randomized trial")
    assert tools
    tool = tools[0]
    assignment = assign_instrument(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        instrument_id=tool["id"],
        selection_basis="RULE_SUGGESTION",
        rationale="O desenho documental foi conferido pelo revisor.",
        reviewer_name="Reviewer One",
        reviewer_role="reviewer_1",
    )
    assert assignment["revision"] == 1

    domains_1 = _domain_values(tool)
    domains_2 = _domain_values(tool, divergent=True)
    submit_quality(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        reviewer_slot="REVIEWER_1",
        domains=domains_1,
        overall=tool["overall_values"][0],
        rationale="Avaliação do revisor 1.",
        reviewer_name="Reviewer One",
        reviewer_role="reviewer_1",
    )
    submit_quality(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        reviewer_slot="REVIEWER_2",
        domains=domains_2,
        overall=tool["overall_values"][1],
        rationale="Avaliação do revisor 2.",
        reviewer_name="Reviewer Two",
        reviewer_role="reviewer_2",
    )
    comparison = compare_quality(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
    )
    assert comparison["complete"] is False
    assert comparison["overall_status"] == "DIVERGENT"
    assert any(
        row["status"] == "DIVERGENT" for row in comparison["domains"]
    )

    final_domains = {
        key: {
            "judgment": value["judgment"],
            "justification": f"Adjudicado: {value['justification']}",
        }
        for key, value in domains_1.items()
    }
    adjudication = adjudicate_quality(
        registry,
        session_id=session_id,
        document_id=document_id,
        article_id="article_1",
        domains=final_domains,
        overall=tool["overall_values"][0],
        adjudicator_name="Principal Investigator",
        adjudicator_role="principal_investigator",
        notes="Decisão final após conferência conjunta.",
    )
    assert adjudication["revision"] == 1
    final = final_quality(registry, session_id, document_id, "article_1")
    assert final["quality_complete"] is True
    assert final["quality_instrument"] == tool["name"]

    exported = export_snapshot(
        registry,
        session_id,
        export_id="matrix_export_test",
    )
    assert exported["summary"]["included_article_documents"] == 2
    assert exported["summary"]["extraction_complete"] == 1
    assert exported["summary"]["quality_complete"] == 1
    for path in exported["paths"].values():
        assert Path(path).exists()
    manifest = json.loads(
        Path(exported["paths"]["manifest"]).read_text(encoding="utf-8")
    )
    assert manifest["governance"]["double_extraction"] is True
    assert manifest["governance"]["quality_adjudication"] is True
    with Path(exported["paths"]["evidence"]).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2


def test_tampered_full_text_blocks_extraction_and_export(tmp_path):
    registry, session_id, _, artifact = _included_session(tmp_path)
    artifact.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity is mismatch"):
        included_documents(registry, session_id, "article_1")
    with pytest.raises(ValueError, match="integrity is mismatch"):
        export_snapshot(registry, session_id)


def test_initialize_adds_tables_to_existing_registry(tmp_path):
    registry = default_registry_path(tmp_path)
    save_strategy_version(
        registry,
        title="Legacy registry",
        query_text="legacy",
        strategy_payload=_payload(),
        search_type="PILOT",
        created_by="Researcher",
    )
    initialize(registry)
    expected = {
        "extraction_schema_fields",
        "extraction_submissions",
        "extraction_adjudications",
        "quality_instrument_versions",
        "quality_instrument_domains",
        "quality_instrument_assignments",
        "quality_assessments",
        "quality_adjudications",
        "evidence_matrix_exports",
    }
    with sqlite3.connect(registry) as connection:
        actual = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert expected <= actual


def test_search_registry_panel_imports_complete_workflow():
    from nutev.ui.search_registry_panel import render_search_registry_panel

    assert callable(render_search_registry_panel)
