from __future__ import annotations

from pathlib import Path

import pytest

import nutev.pipelines.article1_final_outputs as final_outputs
import nutev.pipelines.article1_downstream_status as downstream


def _formal_summary() -> dict:
    return {
        "scientific_state": {
            "search_type": "FORMAL",
            "formal_freeze_authorized": True,
            "prisma_eligible": True,
        },
        "status": {"execution_status": "COMPLETE"},
        "corpus": {"build_id": "build-formal"},
    }


def test_final_zero_inclusion_package_is_hash_validated(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    (project / "12_play").mkdir(parents=True)
    (project / "12_play" / "latest_summary.json").write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        final_outputs,
        "_formal_lineage",
        lambda db_path, session_id: {
            "session": {"session_id": session_id, "build_id": "build-formal"},
            "build": {
                "build_id": "build-formal",
                "version_id": "version-formal",
                "manifest_path": str(project / "corpus_manifest.json"),
                "manifest_sha256": "manifest-sha",
                "status": "SUCCEEDED",
            },
            "version": {
                "version_id": "version-formal",
                "search_type": "FORMAL",
                "prisma_eligible": True,
            },
        },
    )
    monkeypatch.setattr(
        final_outputs,
        "formal_screening_status",
        lambda *args, **kwargs: {"phase": "SCREENING_COMPLETE", "included_documents": 0},
    )
    monkeypatch.setattr(
        final_outputs,
        "_screening_rows",
        lambda *args, **kwargs: (
            [
                {
                    "document_id": "doc-1",
                    "title": "Excluded report",
                    "doi": "10.1/example",
                    "pmid": "1",
                    "status": "RESOLVED_EXCLUDE",
                    "final_action": "EXCLUDE",
                }
            ],
            [],
        ),
    )
    monkeypatch.setattr(
        final_outputs,
        "article1_runtime_status",
        lambda *args, **kwargs: {"included_documents": 0, "documents": [], "synthesis_ready": False},
    )

    result = final_outputs.build_article1_final_outputs(
        project,
        formal_summary=_formal_summary(),
        session_id="session-formal",
    )

    assert result["status"] == "SUCCEEDED"
    assert result["prisma"]["records_screened_title_abstract"] == 1
    assert result["prisma"]["reports_included_article_1"] == 0
    status = final_outputs.final_outputs_status(project, session_id="session-formal")
    assert status["complete"] is True

    prisma_path = Path(result["outputs"]["prisma_path"])
    prisma_path.write_text("tampered\n", encoding="utf-8")
    invalid = final_outputs.final_outputs_status(project, session_id="session-formal")
    assert invalid["complete"] is False
    assert "hash_mismatch:prisma_path" in invalid["blockers"]


def test_final_outputs_block_included_documents_until_abcd_relations_close(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    monkeypatch.setattr(
        final_outputs,
        "_formal_lineage",
        lambda db_path, session_id: {
            "session": {"session_id": session_id, "build_id": "build-formal"},
            "build": {"build_id": "build-formal", "version_id": "version-formal", "status": "SUCCEEDED"},
            "version": {"version_id": "version-formal", "search_type": "FORMAL", "prisma_eligible": True},
        },
    )
    monkeypatch.setattr(
        final_outputs,
        "formal_screening_status",
        lambda *args, **kwargs: {"phase": "SCREENING_COMPLETE", "included_documents": 1},
    )
    monkeypatch.setattr(
        final_outputs,
        "_screening_rows",
        lambda *args, **kwargs: (
            [{"document_id": "doc-1", "status": "RESOLVED_ADVANCE", "final_action": "ADVANCE"}],
            [{"document_id": "doc-1", "status": "RESOLVED_INCLUDE", "final_action": "INCLUDE", "final_decision": "INCLUDE"}],
        ),
    )
    monkeypatch.setattr(
        final_outputs,
        "article1_runtime_status",
        lambda *args, **kwargs: {"included_documents": 1, "synthesis_ready": False, "documents": [{"document_id": "doc-1"}]},
    )

    with pytest.raises(ValueError, match="ABCD and relation review"):
        final_outputs.build_article1_final_outputs(
            project,
            formal_summary=_formal_summary(),
            session_id="session-formal",
        )


def test_downstream_moves_from_screening_to_abcd_relations_final_and_complete(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    formal = _formal_summary()
    monkeypatch.setattr(downstream, "_formal_session_id", lambda db_path, build_id: "session-formal")

    screening_state = {"phase": "TITLE_ABSTRACT_HUMAN_REVIEW", "included_documents": 0}
    monkeypatch.setattr(downstream, "formal_screening_status", lambda *args, **kwargs: dict(screening_state))
    first = downstream.derive_postformal_status(project, formal)
    assert first["phase"] == "TITLE_ABSTRACT_HUMAN_REVIEW"

    screening_state.update({"phase": "SCREENING_COMPLETE", "included_documents": 1})
    runtime_state = {
        "included_documents": 1,
        "synthesis_ready": False,
        "documents": [{"document_id": "doc-1", "abcd_closed": False, "relations_closed": False}],
    }
    monkeypatch.setattr(downstream, "article1_runtime_status", lambda *args, **kwargs: dict(runtime_state))
    monkeypatch.setattr(downstream, "final_outputs_status", lambda *args, **kwargs: {"complete": False})
    assert downstream.derive_postformal_status(project, formal)["phase"] == "ABCD_HUMAN_REVIEW"

    runtime_state["documents"][0]["abcd_closed"] = True
    assert downstream.derive_postformal_status(project, formal)["phase"] == "RELATIONS_HUMAN_REVIEW"

    runtime_state["documents"][0]["relations_closed"] = True
    runtime_state["synthesis_ready"] = True
    assert downstream.derive_postformal_status(project, formal)["phase"] == "SYNTHESIS_PRISMA"

    monkeypatch.setattr(downstream, "final_outputs_status", lambda *args, **kwargs: {"complete": True})
    assert downstream.derive_postformal_status(project, formal)["phase"] == "COMPLETE"
