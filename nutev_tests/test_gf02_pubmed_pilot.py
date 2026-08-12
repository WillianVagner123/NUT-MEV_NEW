from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from nutev.search.base import ProviderResult
from nutev.search.gf02_pubmed_pilot import load_candidate_config, run_gf02_pubmed_pilot


def test_candidate_config_is_explicitly_pilot_and_non_prisma(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "search_type": "FORMAL",
                "prisma_eligible": True,
                "candidates": {"v0.2": "x", "v0.3": "y"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="PILOT"):
        load_candidate_config(bad)


def test_runner_preserves_exact_queries_probes_sentinels_and_noise_template(tmp_path: Path):
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)

    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "route_id": "B-NORM-PUBMED",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "candidates": {
                    "v0.2": "BASE QUERY",
                    "v0.3": "BASE QUERY OR RESCUE NOT hasabstract",
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

    def fake_search(query: str, limit: int, context: dict) -> ProviderResult:
        is_v03 = "RESCUE NOT hasabstract" in query
        if "41651737[pmid]" in query:
            rows = (
                [{"pmid": "41651737", "doi": "10.1016/j.acvd.2026.01.001", "title": "French"}]
                if is_v03
                else []
            )
            return ProviderResult("pubmed", query, rows=rows, total_found=len(rows))
        if "36994026[pmid]" in query:
            rows = (
                [{"pmid": "36994026", "doi": "10.4103/jfmpc.jfmpc_51_22", "title": "AIIMS"}]
                if is_v03
                else []
            )
            return ProviderResult("pubmed", query, rows=rows, total_found=len(rows))

        rows = [
            {"pmid": "100", "doi": "10.1/a", "title": "Record A"},
            {"pmid": "200", "doi": "10.1/b", "title": "Record B"},
            {"pmid": "300", "doi": "10.1/c", "title": "Record C"},
        ]
        return ProviderResult("pubmed", query, rows=rows, total_found=3)

    manifest = run_gf02_pubmed_pilot(
        repo,
        project_root=project,
        limit=100,
        noise_sample_size=2,
        noise_seed=7,
        search_fn=fake_search,
        started_at="2026-08-12T01:00:00-03:00",
        run_id="gf02_test",
    )

    assert manifest["status"] == "SUCCEEDED"
    assert manifest["search_type"] == "PILOT"
    assert manifest["prisma_eligible"] is False
    assert manifest["formal_execution_authorized"] is False
    assert manifest["versions"]["v0.2"]["exact_query"] == "BASE QUERY"
    assert manifest["versions"]["v0.3"]["exact_query"] == "BASE QUERY OR RESCUE NOT hasabstract"
    assert manifest["priority_sentinel_comparison"] == {
        "NORM-035": {"v0.2": False, "v0.3": True},
        "NORM-063": {"v0.2": False, "v0.3": True},
    }

    noise_path = Path(manifest["noise_sample"])
    with noise_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert all(row["classification"] == "" for row in rows)
    assert all(row["reviewer"] == "" for row in rows)
    assert all("seed=7" in row["sampling_rule"] for row in rows)

    stored = json.loads(
        (project / "07_logs" / "gf02" / "pubmed" / "gf02_test" / "run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert stored["prisma_eligible"] is False
    assert stored["priority_sentinel_comparison"]["NORM-035"]["v0.3"] is True


def test_truncation_is_explicit_in_noise_sampling_rule(tmp_path: Path):
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "route_id": "B-NORM-PUBMED",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "candidates": {"v0.2": "Q2", "v0.3": "Q3"},
            }
        ), encoding="utf-8"
    )
    (repo / "config" / "article1_sentinel_registry.json").write_text(
        json.dumps(
            {
                "sentinels": [
                    {"sentinel_id": "NORM-035", "canonical_title": "A", "doi": "10.1/a", "pmid": "1", "document_unit_rule": "A", "identity_status": "RESOLVED"},
                    {"sentinel_id": "NORM-063", "canonical_title": "B", "doi": "10.1/b", "pmid": "2", "document_unit_rule": "B", "identity_status": "RESOLVED"},
                ]
            }
        ), encoding="utf-8"
    )

    def fake_search(query: str, limit: int, context: dict) -> ProviderResult:
        if "[pmid]" in query:
            return ProviderResult("pubmed", query, rows=[], total_found=0)
        return ProviderResult(
            "pubmed", query, rows=[{"pmid": "9", "title": "Only fetched row"}], total_found=99
        )

    manifest = run_gf02_pubmed_pilot(
        repo, project_root=project, limit=1, noise_sample_size=1, search_fn=fake_search, run_id="truncated"
    )
    assert manifest["versions"]["v0.3"]["truncated"] is True
    with Path(manifest["noise_sample"]).open(encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert "truncated" in row["sampling_rule"]
