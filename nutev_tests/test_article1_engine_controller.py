from __future__ import annotations

from pathlib import Path

import pytest

import nutev.pipelines.article1_engine as engine


def _scientific(phase: str, *, downstream: dict | None = None) -> dict:
    return {
        "article1_current_phase": phase,
        "gf02": {"candidate_version": "v0.5"},
        "downstream": downstream or {},
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


def test_one_button_initializes_formal_screening_then_pauses_for_review(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    phase = {"value": "SCREENING_INITIALIZATION"}
    calls = {"count": 0}

    monkeypatch.setattr(
        engine,
        "derive_article1_scientific_status",
        lambda repo_root, project_root: _scientific(phase["value"]),
    )

    def fake_context(project_root: Path):
        calls["count"] += 1
        phase["value"] = "TITLE_ABSTRACT_HUMAN_REVIEW"
        return {
            "session_id": "session-formal",
            "build_id": "build-formal",
            "reviewer_assignment_present": True,
        }

    monkeypatch.setattr(engine, "ensure_formal_screening_context", fake_context)

    state = engine.run_or_resume_article1_engine(repo, project_root=project)

    assert calls["count"] == 1
    assert state["status"] == "WAITING_HUMAN"
    assert state["current_phase"] == "TITLE_ABSTRACT_HUMAN_REVIEW"
    assert state["completed_stages"]["SCREENING_INITIALIZATION"]["session_id"] == "session-formal"


def test_one_button_builds_final_package_syncs_when_possible_and_reaches_complete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    phase = {"value": "SYNTHESIS_PRISMA"}
    calls = {"final": 0, "sync": 0}

    def fake_status(repo_root: Path, project_root: Path):
        return _scientific(
            phase["value"],
            downstream={"session_id": "session-formal"},
        )

    monkeypatch.setattr(engine, "derive_article1_scientific_status", fake_status)
    monkeypatch.setattr(
        engine,
        "_formal_summary",
        lambda project_root: {
            "scientific_state": {
                "search_type": "FORMAL",
                "formal_freeze_authorized": True,
            }
        },
    )

    export_bundle = project / "08_exports" / "article1_final" / "article1_export_bundle.json"

    def fake_final(project_root: Path, **kwargs):
        calls["final"] += 1
        assert kwargs["session_id"] == "session-formal"
        phase["value"] = "COMPLETE"
        return {
            "status": "SUCCEEDED",
            "manifest_path": str(project / "08_exports" / "article1_final" / "manifest.json"),
            "manifest_sha256": "abc123",
            "outputs": {"export_bundle_path": str(export_bundle)},
        }

    def fake_sync(project_root: Path, path: Path):
        calls["sync"] += 1
        assert path == export_bundle
        return {
            "status": "SKIPPED_NOT_CONFIGURED",
            "audit_path": str(project / "08_exports" / "article1_final" / "google_sheets_sync.json"),
            "spreadsheet_id": None,
            "reason": "not configured",
        }

    monkeypatch.setattr(engine, "build_article1_final_outputs", fake_final)
    monkeypatch.setattr(engine, "sync_article1_export_bundle", fake_sync)

    state = engine.run_or_resume_article1_engine(repo, project_root=project)

    assert calls == {"final": 1, "sync": 1}
    assert state["status"] == "COMPLETE"
    assert state["current_phase"] == "COMPLETE"
    assert state["completed_stages"]["SYNTHESIS_PRISMA"]["manifest_sha256"] == "abc123"
    assert state["completed_stages"]["SYNTHESIS_PRISMA"]["google_sheets_sync_status"] == "SKIPPED_NOT_CONFIGURED"
    assert engine.engine_button_label(repo, project) == "✓ CONCLUÍDO"
