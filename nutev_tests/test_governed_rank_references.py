from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_governed_rank_references.py"
SPEC = importlib.util.spec_from_file_location("run_governed_rank_references", MODULE_PATH)
assert SPEC and SPEC.loader
governed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governed)


def _write_collection(project: Path, rows: list[dict]) -> None:
    run_dir = project / "run"
    log_dir = project / "07_logs" / "collect_everything"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    master = run_dir / "master.jsonl"
    master.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    (log_dir / "latest.json").write_text(
        json.dumps({"master_records_path": str(master)}), encoding="utf-8"
    )


def test_governed_run_requires_explicit_thesis_article(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="explicit A1, A2, A3 or A4"):
        governed.build_effective_config(Path("config"), "all_articles", tmp_path / "effective")


def test_a2_governed_run_records_scope_governance_profile_and_durable_artifacts(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    _write_collection(
        project,
        [
            {
                "title": "Dietary intervention barriers and maintenance",
                "abstract": "Dietary prescription feasibility and adaptation in adults",
                "source_provider": "pubmed",
                "pmid": "123",
                "year": 2025,
            }
        ],
    )
    summary = governed.run(project, Path("config"), "A2", 10)
    root_latest = json.loads(
        (project / "reference_ranking" / "latest.json").read_text(encoding="utf-8")
    )
    article_latest = json.loads(
        (project / "reference_ranking" / "by_article" / "A2" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary == root_latest == article_latest
    assert summary["article_scope"] == "A2"
    assert summary["governance"]["governance_version"] == "2026-08-18.a1-a4"
    assert (
        summary["governance"]["article"]["object"]
        == "dietary_prescription_or_intervention_plus_operational_package"
    )
    assert summary["governance"]["scientific_decision_policy"] == "human_only"
    assert summary["article_profile_purpose"].startswith("discover_and_rank_current_dietary")
    assert summary["article_interpretation_rule"].startswith("implementation_competencies")

    run_dir = Path(summary["durable_run_dir"])
    assert run_dir.is_dir()
    assert (run_dir / "run_manifest.json").is_file()
    assert (run_dir / "nutev_governance_manifest.json").is_file()
    assert (run_dir / "effective_reference_mode.json").is_file()
    for name in ("TOP_REFERENCIAS.md", "reference_ranking.csv", "reference_ranking.jsonl"):
        assert (run_dir / name).is_file()
        assert summary["artifacts"][name]["sha256"]


def test_article_runs_do_not_overwrite_each_others_durable_outputs(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_collection(
        project,
        [
            {
                "title": "Dietary guideline and dietary intervention",
                "abstract": "Healthy eating recommendation and prescription feasibility",
                "source_provider": "pubmed",
                "pmid": "456",
                "year": 2026,
            }
        ],
    )

    a1 = governed.run(project, Path("config"), "A1", 10)
    a1_manifest = Path(a1["run_manifest"])
    a1_jsonl = Path(a1["outputs"]["jsonl"])
    assert a1_manifest.is_file()
    assert a1_jsonl.is_file()

    a2 = governed.run(project, Path("config"), "A2", 10)
    assert a2["run_id"] != a1["run_id"]
    assert Path(a2["run_manifest"]).is_file()
    assert Path(a2["outputs"]["jsonl"]).is_file()
    assert a1_manifest.is_file()
    assert a1_jsonl.is_file()

    a1_latest = json.loads(
        (project / "reference_ranking" / "by_article" / "A1" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    a2_latest = json.loads(
        (project / "reference_ranking" / "by_article" / "A2" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert a1_latest["article_scope"] == "A1"
    assert a2_latest["article_scope"] == "A2"


def test_a4_profile_remains_conceptual_not_cfd(tmp_path: Path) -> None:
    effective_dir = tmp_path / "effective"
    effective = governed.build_effective_config(Path("config"), "A4", effective_dir)
    assert effective["article_scope"] == "A4"
    assert effective["governance_version"] == "2026-08-18.a1-a4"
    profile = json.loads(Path("config/article_reference_profiles.json").read_text(encoding="utf-8"))
    rule = profile["profiles"]["A4"]["interpretation_rule"]
    assert "CFD-I" in rule
    assert "CFD-8" in rule
    assert "algorithm" in rule
