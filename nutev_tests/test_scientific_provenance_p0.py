from __future__ import annotations

import csv
import json
from pathlib import Path

from nutev.export.logs import assess_scientific_readiness, write_run_summary
from nutev.export.methods_writer import EXECUTION_FIELDS, write_methods_docs


def _write_provider_performance(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXECUTION_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in EXECUTION_FIELDS})


def test_methods_export_distinguishes_generated_from_executed_queries(tmp_path: Path):
    logs = tmp_path / "07_logs"
    docs = tmp_path / "08_docs"
    logs.mkdir(parents=True)

    generated = {"busca1": ["actual query", "generated but budget truncated"]}
    provider_generated = {
        "busca1": {
            "pubmed": ["actual query", "generated but budget truncated"],
        }
    }
    (logs / "querypack_executed.json").write_text(
        json.dumps(generated), encoding="utf-8"
    )
    (logs / "querypack_executed.csv").write_text(
        "workstream,query_order,query_text\n"
        "busca1,1,actual query\n"
        "busca1,2,generated but budget truncated\n",
        encoding="utf-8",
    )
    (logs / "provider_querypack_executed.json").write_text(
        json.dumps(provider_generated), encoding="utf-8"
    )
    (logs / "provider_querypack_executed.csv").write_text(
        "workstream,provider,query_order,semantic_blocks,query_text\n"
        "busca1,pubmed,1,,actual query\n"
        "busca1,pubmed,2,,generated but budget truncated\n",
        encoding="utf-8",
    )

    _write_provider_performance(
        logs / "provider_performance.csv",
        [
            {
                "run_id": "older_run",
                "provider": "pubmed",
                "workstream": "busca1",
                "query_hash": "oldhash",
                "query": "old query from another run",
                "status": "completed",
                "total_found": "3",
                "rows_returned": "3",
            },
            {
                "run_id": "current_run",
                "provider": "pubmed",
                "workstream": "busca1",
                "query_hash": "actualhash",
                "query": "actual query",
                "status": "completed",
                "total_found": "10",
                "rows_returned": "8",
                "resume_used": "False",
            },
        ],
    )

    write_methods_docs(docs, logs)

    generated_after_first_finalize = (logs / "querypack_generated.json").read_text(
        encoding="utf-8"
    )
    provider_generated_after_first_finalize = (
        logs / "provider_querypack_generated.json"
    ).read_text(encoding="utf-8")

    assert json.loads(generated_after_first_finalize) == generated
    assert json.loads(provider_generated_after_first_finalize) == provider_generated

    executed = json.loads(
        (logs / "provider_querypack_executed.json").read_text(encoding="utf-8")
    )
    assert executed == {"busca1": {"pubmed": ["actual query"]}}
    assert "generated but budget truncated" not in json.dumps(executed)
    assert "old query from another run" not in json.dumps(executed)

    ledger = json.loads((logs / "query_execution_ledger.json").read_text(encoding="utf-8"))
    assert len(ledger) == 1
    assert ledger[0]["run_id"] == "current_run"
    assert ledger[0]["query"] == "actual query"

    ledger_pairs = {(row["provider"], row["workstream"], row["query"]) for row in ledger}
    for workstream, providers in executed.items():
        for provider, queries in providers.items():
            for query in queries:
                assert (provider, workstream, query) in ledger_pairs

    methods = (docs / "NUTEV_METHODS_BUSCA1.md").read_text(encoding="utf-8")
    assert "actual query" in methods
    assert "generated but budget truncated" not in methods
    assert "query_execution_ledger.csv" in methods
    assert "querypack_generated" in methods

    # Re-running methods generation for the same run must not relabel the already
    # finalized executed artifacts as the original generated search space.
    write_methods_docs(docs, logs)
    assert (logs / "querypack_generated.json").read_text(
        encoding="utf-8"
    ) == generated_after_first_finalize
    assert (logs / "provider_querypack_generated.json").read_text(
        encoding="utf-8"
    ) == provider_generated_after_first_finalize


def test_scientific_readiness_does_not_infer_manuscript_approval():
    result = assess_scientific_readiness(
        {
            "run_status": "completed",
            "providers_failed": 0,
            "providers_unsupported_by_workstream": {},
            "coverage_loss": {"unrecoverable": 0},
        }
    )
    assert result["execution_status"] == "completed"
    assert result["scientific_readiness"] == "computationally_ready_for_human_review"
    assert result["scientific_readiness_blockers"] == []
    assert result["human_review_complete"] is False


def test_scientific_readiness_blocks_downstream_errors_and_provider_failures():
    result = assess_scientific_readiness(
        {
            "run_status": "partial",
            "providers_failed": 1,
            "providers_unsupported_by_workstream": {"busca1": ["provider_x"]},
            "coverage_loss": {"unrecoverable": 2},
            "article1_report_error": "simulated failure",
        }
    )
    assert result["scientific_readiness"] == "blocked"
    assert "execution_status=partial" in result["scientific_readiness_blockers"]
    assert "provider_failures_present" in result["scientific_readiness_blockers"]
    assert "declared_providers_not_executed" in result["scientific_readiness_blockers"]
    assert "unrecoverable_coverage_loss" in result["scientific_readiness_blockers"]
    assert "article1_report_error" in result["scientific_readiness_blockers"]


def test_manuscript_ready_requires_explicit_human_and_manuscript_gates():
    result = assess_scientific_readiness(
        {
            "run_status": "completed",
            "providers_failed": 0,
            "providers_unsupported_by_workstream": {},
            "coverage_loss": {"unrecoverable": 0},
            "human_review_complete": True,
            "manuscript_gates_complete": True,
        }
    )
    assert result["scientific_readiness"] == "manuscript_ready"


def test_write_run_summary_mutates_returned_summary_contract(tmp_path: Path):
    summary = {"run_status": "completed"}
    path = tmp_path / "run_summary.json"
    write_run_summary(path, summary)
    assert summary["execution_status"] == "completed"
    assert summary["scientific_readiness"] == "computationally_ready_for_human_review"
    assert json.loads(path.read_text(encoding="utf-8"))["scientific_readiness"] == (
        "computationally_ready_for_human_review"
    )
