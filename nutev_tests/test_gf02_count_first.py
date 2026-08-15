from __future__ import annotations

import json
from pathlib import Path

from nutev.search.base import ProviderResult
import nutev.search.gf02_pubmed_optimized as optimized


def _write_repo(repo: Path) -> None:
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "route_id": "B-NORM-PUBMED",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "formal_execution_authorized": False,
                "current_candidate": "v0.5",
                "candidate_status": "PROVISIONAL_PILOT_PENDING_NOISE_REVIEW",
                "methodology_decisions": ["D-093", "D-094", "D-096", "D-097"],
                "canonical_operational_source": "02I_PRESS_ESTRATEGIAS",
                "superseded_candidates": {
                    "v0.4": {"status": "SUPERSEDED_PROVIDER_BOOLEAN_SEMANTICS_BUG", "execution_allowed": False}
                },
                "lines": {
                    "#1": {"label": "core", "query": "DIET_CORE"},
                    "#2": {"label": "norm", "query": "NORMATIVE_MAIN"},
                    "#3": {"label": "main", "combine": {"left": "#1", "operator": "AND", "right": "#2"}},
                    "#4": {"label": "rescue title", "query": "guideline[ti]"},
                    "#5": {"label": "exclude", "query": "(hasabstract OR comment[pt])"},
                    "#6": {"label": "rescue", "combine": {"left": "#4", "operator": "NOT", "right": "#5"}},
                    "#7": {"label": "final", "combine": {"left": "#3", "operator": "OR", "right": "#6"}},
                },
                "final_line": "#7",
                "required_count_lines": ["#1", "#2", "#3", "#4", "#6", "#7"],
                "rescue_only": {"left": "#6", "operator": "NOT", "right": "#3"},
                "rescue_sample": {"minimum": 10, "maximum": 20, "default": 10},
                "priority_expectations": {
                    "NORM-035": {"pmid": "41651737", "expected_final": True},
                    "NORM-063": {"pmid": "36994026", "expected_final": True},
                },
            }
        ),
        encoding="utf-8",
    )
    (repo / "config" / "article1_sentinel_registry.json").write_text(
        json.dumps(
            {
                "sentinels": [
                    {
                        "sentinel_id": "NORM-035",
                        "canonical_title": "A",
                        "doi": "10.1/a",
                        "pmid": "41651737",
                        "document_unit_rule": "one",
                        "identity_status": "RESOLVED",
                    },
                    {
                        "sentinel_id": "NORM-063",
                        "canonical_title": "B",
                        "doi": "10.1/b",
                        "pmid": "36994026",
                        "document_unit_rule": "one",
                        "identity_status": "RESOLVED",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_real_path_counts_without_downloading_full_final_set(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    _write_repo(repo)
    esearch_calls: list[dict] = []
    row_limits: list[int] = []

    def fake_request_json(endpoint: str, params: dict, **kwargs):
        assert endpoint == "esearch.fcgi"
        esearch_calls.append(dict(params))
        return {
            "esearchresult": {
                "count": "123",
                "querytranslation": "translated",
                "warninglist": {},
                "errorlist": {},
            }
        }

    def fake_search(query: str, limit: int, context: dict) -> ProviderResult:
        row_limits.append(limit)
        rows = [{"pmid": str(1000 + index), "title": f"row {index}"} for index in range(limit)]
        return ProviderResult(
            "pubmed",
            query,
            rows=rows,
            total_found=999,
            total_returned=len(rows),
            status="completed",
            meta={"querytranslation": "translated rescue", "warninglist": {}},
        )

    monkeypatch.setattr(optimized, "_request_json", fake_request_json)
    monkeypatch.setattr(optimized, "_search", fake_search)

    manifest = optimized.run_gf02_pubmed_pilot(
        repo,
        project_root=tmp_path / "project",
        noise_sample_size=10,
        run_id="fast",
    )

    assert len(esearch_calls) == 12
    assert all(call.get("retmax") == 0 for call in esearch_calls)
    assert row_limits == [10]
    assert manifest["execution_plan"] == "COUNT_FIRST_SAMPLE_ONLY_RESUMABLE"
    assert manifest["resume_enabled"] is True
    assert manifest["final_records_returned"] == 0
    assert manifest["rescue_only"]["records_returned"] == 10
