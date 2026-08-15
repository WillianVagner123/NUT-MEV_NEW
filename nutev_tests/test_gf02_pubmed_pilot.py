from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from nutev.search.base import ProviderResult
from nutev.search.gf02_pubmed_pilot import (
    load_candidate_config,
    resolved_line_expressions,
    run_gf02_pubmed_pilot,
)


def _config() -> dict:
    return {
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
            "v0.3": {"status": "SUPERSEDED", "execution_allowed": False},
            "v0.4": {"status": "SUPERSEDED_PROVIDER_BOOLEAN_SEMANTICS_BUG", "execution_allowed": False},
        },
        "lines": {
            "#1": {"label": "core", "query": "DIET_CORE"},
            "#2": {"label": "normative", "query": "NORMATIVE_MAIN"},
            "#3": {"label": "main", "combine": {"left": "#1", "operator": "AND", "right": "#2"}},
            "#4": {"label": "neutral rescue", "query": "GUIDELINE_TITLE"},
            "#5": {"label": "exclusions", "query": "(hasabstract OR comment[pt])"},
            "#6": {"label": "rescue", "combine": {"left": "#4", "operator": "NOT", "right": "#5"}},
            "#7": {"label": "final", "combine": {"left": "#3", "operator": "OR", "right": "#6"}},
        },
        "final_line": "#7",
        "required_count_lines": ["#1", "#2", "#3", "#4", "#6", "#7"],
        "rescue_only": {"left": "#6", "operator": "NOT", "right": "#3"},
        "rescue_sample": {"minimum": 10, "maximum": 20, "default": 20},
        "priority_expectations": {
            "NORM-035": {"pmid": "41651737", "expected_final": True},
            "NORM-063": {"pmid": "36994026", "expected_final": True},
        },
    }


def _write_repo(repo: Path, config: dict | None = None) -> None:
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(config or _config()), encoding="utf-8"
    )
    (repo / "config" / "article1_sentinel_registry.json").write_text(
        json.dumps(
            {
                "sentinels": [
                    {
                        "sentinel_id": "NORM-035",
                        "canonical_title": "French dyslipidemia consensus",
                        "doi": "10.1016/j.acvd.2026.01.001",
                        "pmid": "41651737",
                        "document_unit_rule": "one intellectual consensus",
                        "identity_status": "RESOLVED",
                    },
                    {
                        "sentinel_id": "NORM-063",
                        "canonical_title": "AIIMS-DST guideline",
                        "doi": "10.4103/jfmpc.jfmpc_51_22",
                        "pmid": "36994026",
                        "pmcid": "PMC10041015",
                        "document_unit_rule": "parent guideline only",
                        "identity_status": "RESOLVED",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def test_repository_candidate_is_v05_condition_neutral_and_boolean_valid() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = load_candidate_config(repo_root / "config" / "gf02_pubmed_candidates.json")
    expressions = resolved_line_expressions(config)

    assert config["current_candidate"] == "v0.5"
    assert config["superseded_candidates"]["v0.4"]["execution_allowed"] is False
    assert config["required_count_lines"] == ["#1", "#2", "#3", "#4", "#6", "#7"]
    assert "diabetes[ti]" not in expressions["#4"].lower()
    assert "obes" not in expressions["#4"].lower()
    assert expressions["#6"] == f"({expressions['#4']}) NOT ({expressions['#5']})"
    assert expressions["#7"] == f"({expressions['#3']}) OR ({expressions['#6']})"


def test_candidate_config_rejects_condition_specific_rescue(tmp_path: Path) -> None:
    config = _config()
    config["lines"]["#4"]["query"] = "guideline[ti] AND diabetes[ti]"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="condition-neutral"):
        load_candidate_config(path)


def test_candidate_config_rejects_superseded_executable_versions(tmp_path: Path) -> None:
    config = _config()
    config["superseded_candidates"]["v0.4"]["execution_allowed"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="superseded"):
        load_candidate_config(path)


def test_runner_records_dynamic_version_translation_and_unclassified_sample(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    _write_repo(repo)

    totals = {
        "gf02_v0_5_line_1": 100,
        "gf02_v0_5_line_2": 50,
        "gf02_v0_5_line_3": 30,
        "gf02_v0_5_line_4": 10,
        "gf02_v0_5_line_6": 8,
        "gf02_v0_5_line_7": 35,
        "gf02_v0_5_rescue_only": 12,
    }

    def fake_search(query: str, limit: int, context: dict) -> ProviderResult:
        workstream = context["workstream"]
        if workstream.startswith("gf02_probe_"):
            recovered = "line_3" not in workstream
            rows = [{"pmid": query.split(" AND ")[-1].split("[")[0]}] if recovered else []
            return ProviderResult(
                "pubmed",
                query,
                rows=rows,
                total_found=len(rows),
                total_returned=len(rows),
                status="completed" if rows else "empty",
                meta={"querytranslation": f"translated:{workstream}", "warninglist": {}},
            )
        total = totals[workstream]
        if workstream == "gf02_v0_5_rescue_only":
            rows = [
                {"pmid": str(1000 + idx), "doi": f"10.1/{idx}", "title": f"Rescue {idx}"}
                for idx in range(12)
            ]
        elif workstream == "gf02_v0_5_line_7":
            rows = [
                {"pmid": "2001", "title": "Final A"},
                {"pmid": "2002", "title": "Final B"},
                {"pmid": "2003", "title": "Final C"},
            ]
        else:
            rows = [{"pmid": "1", "title": "Count probe"}]
        return ProviderResult(
            "pubmed",
            query,
            rows=rows[:limit],
            total_found=total,
            total_returned=min(len(rows), limit),
            status="completed",
            meta={"querytranslation": f"translated:{workstream}", "warninglist": {}},
        )

    manifest = run_gf02_pubmed_pilot(
        repo,
        project_root=project,
        limit=100,
        noise_sample_size=10,
        noise_seed=7,
        search_fn=fake_search,
        started_at="2026-08-15T17:00:00-03:00",
        run_id="gf02_v05_test",
    )

    assert manifest["status"] == "SUCCEEDED"
    assert manifest["candidate_version"] == "v0.5"
    assert manifest["search_type"] == "PILOT"
    assert manifest["prisma_eligible"] is False
    assert manifest["formal_execution_authorized"] is False
    assert manifest["line_counts"] == {"#1": 100, "#2": 50, "#3": 30, "#4": 10, "#6": 8, "#7": 35}
    assert manifest["final_ncbi_query_translation"] == "translated:gf02_v0_5_line_7"
    assert manifest["priority_sentinel_mechanism"] == {
        "NORM-035": {"#3": False, "#6": True, "#7": True},
        "NORM-063": {"#3": False, "#6": True, "#7": True},
    }
    assert manifest["rescue_only"]["total_found"] == 12

    sample_path = Path(manifest["rescue_only_sample"])
    assert sample_path.name == "rescue_only_sample_v0_5.csv"
    with sample_path.open(encoding="utf-8-sig", newline="") as handle:
        sample_rows = list(csv.DictReader(handle))
    assert len(sample_rows) == 10
    assert all(row["classification"] == "" for row in sample_rows)
    assert all(row["reviewer"] == "" for row in sample_rows)
    assert all(row["strategy_version"] == "B-NORM-PUBMED-v0.5-rescue-only" for row in sample_rows)

    stored = json.loads(
        (project / "07_logs" / "gf02" / "pubmed" / "gf02_v05_test" / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert stored["candidate_version"] == "v0.5"
    assert stored["scientific_interpretation_allowed"] is False
    assert stored["ready_for_press_inferred"] is False
    assert stored["press_approved"] is False
    assert stored["freeze_authorized"] is False


def test_runner_fails_on_boolean_semantics_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_repo(repo)

    def fake_search(query: str, limit: int, context: dict) -> ProviderResult:
        return ProviderResult(
            "pubmed",
            query,
            rows=[{"pmid": "1"}],
            total_found=1,
            total_returned=1,
            status="completed",
            meta={"warninglist": {"phrasesignored": ["NOT"]}},
        )

    manifest = run_gf02_pubmed_pilot(
        repo,
        project_root=tmp_path / "project",
        noise_sample_size=10,
        search_fn=fake_search,
        run_id="boolean_warning",
    )
    assert manifest["status"] == "FAILED"
    assert any("BOOLEAN_SEMANTICS_WARNING" in item for item in manifest["errors"])


def test_runner_rejects_rescue_sample_outside_methodological_range(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_repo(repo)

    with pytest.raises(ValueError, match="between 10 and 20"):
        run_gf02_pubmed_pilot(
            repo,
            project_root=tmp_path / "project",
            noise_sample_size=9,
            search_fn=lambda query, limit, context: ProviderResult("pubmed", query),
        )
