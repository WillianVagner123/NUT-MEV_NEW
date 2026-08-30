from __future__ import annotations

import json
from pathlib import Path

from nutev.science.deepening_resolved import run_selective_bank_deepening_resolved
from nutev.science.deepening_resolved_v3 import (
    DEEPENING_PIPELINE_VERSION,
    run_selective_bank_deepening_resolved_v3,
)
from nutev.science.workbench_priority import augment_workbench_priority

from nutev_tests.test_workbench_priority import _build_workbench


def test_resolver_v3_reprocesses_v2_batch_once_then_resumes(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root, search_id = _build_workbench(output_root)
    augment_workbench_priority(search_id, output_root=output_root)

    v2 = run_selective_bank_deepening_resolved(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        allow_network=False,
    )
    assert v2["status"] == "COMPLETE"

    batch_path = next(
        (
            output_root
            / "scientific"
            / "deepening"
            / search_id
            / "tier-A"
            / "batches"
        ).glob("*/BATCH_MANIFEST.json")
    )
    old_manifest = json.loads(batch_path.read_text(encoding="utf-8"))
    assert old_manifest["pipeline_version"] == "oa_resolver_v2"

    events: list[dict[str, object]] = []
    upgraded = run_selective_bank_deepening_resolved_v3(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        allow_network=False,
        on_progress=events.append,
    )
    assert upgraded["status"] == "COMPLETE"
    assert upgraded["pipeline_version"] == DEEPENING_PIPELINE_VERSION
    assert upgraded["completed_batches_this_run"] == 1
    assert upgraded["skipped_batches_this_run"] == 0

    new_manifest = json.loads(batch_path.read_text(encoding="utf-8"))
    assert new_manifest["pipeline_version"] == DEEPENING_PIPELINE_VERSION
    assert new_manifest["status"] == "PASS"

    workbench_manifest = json.loads(
        (workbench_root / "WORKBENCH_MANIFEST.json").read_text(encoding="utf-8")
    )
    batch_id = new_manifest["batch_id"]
    assert workbench_manifest["extensions"]["deepening"]["batches"][batch_id]["status"] == "PASS"

    resumed_events: list[dict[str, object]] = []
    resumed = run_selective_bank_deepening_resolved_v3(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        allow_network=False,
        on_progress=resumed_events.append,
    )
    assert resumed["status"] == "COMPLETE"
    assert resumed["completed_batches_this_run"] == 0
    assert resumed["skipped_batches_this_run"] == 1
    assert any(event.get("stage") == "batch_skipped_complete" for event in resumed_events)
