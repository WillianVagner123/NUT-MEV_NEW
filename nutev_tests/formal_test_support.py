from __future__ import annotations

from pathlib import Path

from nutev.search.formal_execution_guard import default_freeze_path, default_gate_path
from nutev.search.scientific_gates import FreezeRecord, GateRecord, save_freeze_record, save_gate_records

TEST_GIT_SHA = "a" * 40
TEST_CONFIG_DIGEST = "b" * 64


def authorize_formal_strategy(project_root: Path, version_id: str) -> dict[str, str]:
    gates = [
        GateRecord(
            gate_id=gate_id,
            requirement=f"Test evidence for {gate_id}",
            evidence=(f"test:{gate_id}",),
            status="COMPLETED",
            owner="test-human-reviewer",
            completion_date="2026-08-13",
        )
        for gate_id in ("GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07", "GF-08", "GF-09")
    ]
    gates.append(
        GateRecord(
            gate_id="GF-10",
            requirement="Test global search freeze",
            evidence=("FREEZE-TEST-001",),
            status="AUTHORIZED",
            owner="test-human-reviewer",
            completion_date="2026-08-13",
        )
    )
    save_gate_records(default_gate_path(project_root), gates, registry_version="test-gates-v1")
    save_freeze_record(
        default_freeze_path(project_root),
        FreezeRecord(
            freeze_id="FREEZE-TEST-001",
            date="2026-08-13",
            software_version="0.3.0.dev1",
            git_commit_sha=TEST_GIT_SHA,
            strategy_versions=(version_id,),
            source_registry_version="test-sources-v1",
            repository_registry_version="test-repositories-v1",
            sentinel_suite_version="test-sentinels-v1",
            press_evidence_id="PRESS-TEST-001",
            filters=(),
            final_search_date_rule="test execution date",
            config_digest=TEST_CONFIG_DIGEST,
            reviewers=("test-human-reviewer",),
        ),
    )
    return {
        "authorization_git_sha": TEST_GIT_SHA,
        "authorization_config_digest": TEST_CONFIG_DIGEST,
    }
