from __future__ import annotations

from pathlib import Path

import pytest

import nutev.pipelines.article1_engine as engine


def _scientific(phase: str) -> dict:
    return {
        "article1_current_phase": phase,
        "gf02": {"candidate_version": "v0.5"},
    }


def test_one_button_runs_automatic_stage_then_pauses_at_human_gate(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    phase = {"value": "GF02_PUBMED_PILOT"}
    calls: list[dict] = []

    monkeypatch.setattr(
        engine,
        "derive_article1_scientific_status",
        lambda repo_root, project_root: _scientific(phase["value"]),
    )

    def fake_gf02(repo_root: Path, **kwargs):
        calls.append(kwargs)
        phase["value"] = "GF02_NOISE_REVIEW"
        return {"status": "SUCCEEDED", "run_id": kwargs["run_id"], "errors": []}

    monkeypatch.setattr(engine, "run_gf02_pubmed_pilot", fake_gf02)

    state = engine.run_or_resume_article1_engine(repo, project_root=project)

    assert state["status"] == "WAITING_HUMAN"
    assert state["current_phase"] == "GF02_NOISE_REVIEW"
    assert len(calls) == 1
    assert calls[0]["resume"] is True
    assert engine.load_article1_engine_state(project)["gf02_run_id"] == calls[0]["run_id"]


def test_interrupted_run_reuses_same_gf02_run_id_on_continue(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    phase = {"value": "GF02_PUBMED_PILOT"}
    seen_run_ids: list[str] = []
    attempts = {"count": 0}

    monkeypatch.setattr(
        engine,
        "derive_article1_scientific_status",
        lambda repo_root, project_root: _scientific(phase["value"]),
    )

    def fake_gf02(repo_root: Path, **kwargs):
        seen_run_ids.append(str(kwargs["run_id"]))
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary network failure")
        phase["value"] = "GF02_NOISE_REVIEW"
        return {"status": "SUCCEEDED", "run_id": kwargs["run_id"], "errors": []}

    monkeypatch.setattr(engine, "run_gf02_pubmed_pilot", fake_gf02)

    with pytest.raises(RuntimeError, match="temporary network failure"):
        engine.run_or_resume_article1_engine(repo, project_root=project)

    failed = engine.load_article1_engine_state(project)
    assert failed["status"] == "FAILED"

    resumed = engine.run_or_resume_article1_engine(repo, project_root=project)
    assert resumed["status"] == "WAITING_HUMAN"
    assert len(seen_run_ids) == 2
    assert seen_run_ids[0] == seen_run_ids[1]
