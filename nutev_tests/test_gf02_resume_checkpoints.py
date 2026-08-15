from __future__ import annotations

import json
from pathlib import Path

import pytest

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
                    "v0.4": {
                        "status": "SUPERSEDED_PROVIDER_BOOLEAN_SEMANTICS_BUG",
                        "execution_allowed": False,
                    }
                },
                "lines": {
                    "#1": {"label": "core", "query": "DIET_CORE"},
                    "#2": {"label": "normative", "query": "NORMATIVE_MAIN"},
                    "#3": {"label": "main", "combine": {"left": "#1", "operator": "AND", "right": "#2"}},
                    "#4": {"label": "neutral rescue", "query": "guideline[ti]"},
                    "#5": {"label": "exclusions", "query": "(hasabstract OR comment[pt])"},
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
                        "canonical_title": "Sentinel A",
                        "doi": "10.1/a",
                        "pmid": "41651737",
                        "document_unit_rule": "one intellectual document",
                        "identity_status": "RESOLVED",
                    },
                    {
                        "sentinel_id": "NORM-063",
                        "canonical_title": "Sentinel B",
                        "doi": "10.1/b",
                        "pmid": "36994026",
                        "document_unit_rule": "one intellectual document",
                        "identity_status": "RESOLVED",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_interrupted_gf02_reuses_completed_line_checkpoints(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    _write_repo(repo)

    first_calls = {"count": 0}

    def interrupting_request(endpoint: str, params: dict, **kwargs):
        first_calls["count"] += 1
        if first_calls["count"] == 4:
            raise KeyboardInterrupt()
        return {
            "esearchresult": {
                "count": "123",
                "querytranslation": "translated",
                "warninglist": {},
                "errorlist": {},
            }
        }

    monkeypatch.setattr(optimized, "_request_json", interrupting_request)

    with pytest.raises(KeyboardInterrupt):
        optimized.run_gf02_pubmed_pilot(
            repo,
            project_root=project,
            run_id="stable_resume",
            noise_sample_size=10,
            resume=True,
        )

    run_dir = project / "07_logs" / "gf02" / "pubmed" / "stable_resume"
    assert (run_dir / "line_1.audit.json").is_file()
    assert (run_dir / "line_2.audit.json").is_file()
    assert (run_dir / "line_3.audit.json").is_file()
    assert not (run_dir / "line_4.audit.json").exists()

    second_requests: list[dict] = []

    def stable_request(endpoint: str, params: dict, **kwargs):
        second_requests.append(dict(params))
        return {
            "esearchresult": {
                "count": "123",
                "querytranslation": "translated",
                "warninglist": {},
                "errorlist": {},
            }
        }

    def fake_rescue_search(query: str, limit: int, context: dict) -> ProviderResult:
        rows = [{"pmid": str(1000 + idx), "title": f"Rescue {idx}"} for idx in range(limit)]
        return ProviderResult(
            "pubmed",
            query,
            rows=rows,
            total_found=50,
            total_returned=len(rows),
            status="completed",
            meta={"querytranslation": "translated rescue", "warninglist": {}},
        )

    monkeypatch.setattr(optimized, "_request_json", stable_request)
    monkeypatch.setattr(optimized, "_search", fake_rescue_search)

    manifest = optimized.run_gf02_pubmed_pilot(
        repo,
        project_root=project,
        run_id="stable_resume",
        noise_sample_size=10,
        resume=True,
    )

    assert manifest["status"] == "SUCCEEDED"
    assert manifest["resume_enabled"] is True
    assert manifest["checkpoint_units_reused"] >= 3
    # 3 remaining line counts + 6 sentinel probes. The first 3 line counts were not repeated.
    assert len(second_requests) == 9
