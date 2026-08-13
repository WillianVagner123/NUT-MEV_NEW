from __future__ import annotations

import pytest

from nutev.search.scientific_gates import (
    FreezeRecord,
    GateRecord,
    PressRecord,
    formal_execution_authorization,
    freeze_digest,
    global_freeze_status,
    pre_freeze_blockers,
    validate_freeze_record,
    validate_gate_record,
    validate_press_record,
)


GIT_SHA = "a" * 40
CONFIG_DIGEST = "b" * 64


def _completed(gate_id: str) -> GateRecord:
    return GateRecord(
        gate_id=gate_id,
        requirement=f"Requirement for {gate_id}",
        evidence=(f"evidence:{gate_id}",),
        status="COMPLETED",
        owner="human-reviewer",
        completion_date="2026-08-13",
    )


def _freeze() -> FreezeRecord:
    return FreezeRecord(
        freeze_id="FREEZE-A1-001",
        date="2026-08-13",
        software_version="0.3.0.dev1",
        git_commit_sha=GIT_SHA,
        strategy_versions=("B-NORM-PUBMED:v0.3",),
        source_registry_version="sources-v1",
        repository_registry_version="repositories-v1",
        sentinel_suite_version="GF02-PRIORITY-v1",
        press_evidence_id="PRESS-001",
        filters=(("language", "eng|por|spa"),),
        final_search_date_rule="record real execution date at formal run",
        config_digest=CONFIG_DIGEST,
        reviewers=("human-reviewer",),
    )


def test_completed_gate_requires_real_evidence_owner_and_date():
    with pytest.raises(ValueError, match="lacks"):
        validate_gate_record(
            GateRecord(
                gate_id="GF-02",
                requirement="Sentinel validation",
                status="COMPLETED",
            )
        )


def test_press_approval_cannot_be_inferred_without_human_record():
    with pytest.raises(ValueError, match="reviewer and submission_date"):
        validate_press_record(
            PressRecord(
                press_submission_id="PRESS-001",
                strategy_version="B-NORM-PUBMED:v0.3",
                review_status="APPROVED",
                final_decision="APPROVED",
            )
        )


def test_pre_freeze_reports_missing_or_incomplete_gates():
    blockers = pre_freeze_blockers([_completed("GF-02")])
    assert "GF-03:missing" in blockers
    assert "GF-09:missing" in blockers


def test_global_freeze_never_authorizes_without_gf10_human_authorization():
    gates = [_completed(gate_id) for gate_id in (
        "GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07", "GF-08", "GF-09"
    )]
    status = global_freeze_status(gates)
    assert status["authorized"] is False
    assert status["status"] == "NOT_AUTHORIZED"


def test_freeze_record_is_hashable_and_binds_sha_and_config():
    freeze = _freeze()
    assert validate_freeze_record(freeze) == freeze
    digest = freeze_digest(freeze)
    assert len(digest) == 64


def test_formal_execution_requires_all_gates_gf10_and_exact_freeze_identity():
    gates = [_completed(gate_id) for gate_id in (
        "GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07", "GF-08", "GF-09"
    )]
    gates.append(
        GateRecord(
            gate_id="GF-10",
            requirement="Global search freeze",
            evidence=("FREEZE-A1-001",),
            status="AUTHORIZED",
            owner="human-reviewer",
            completion_date="2026-08-13",
        )
    )

    authorized = formal_execution_authorization(
        gates=gates,
        freeze=_freeze(),
        current_git_sha=GIT_SHA,
        current_config_digest=CONFIG_DIGEST,
    )
    assert authorized["authorized"] is True
    assert authorized["formal_execution_authorized"] is True
    assert authorized["prisma_eligible"] is True

    mismatch = formal_execution_authorization(
        gates=gates,
        freeze=_freeze(),
        current_git_sha="c" * 40,
        current_config_digest=CONFIG_DIGEST,
    )
    assert mismatch["authorized"] is False
    assert "freeze_git_sha_mismatch" in mismatch["blockers"]
