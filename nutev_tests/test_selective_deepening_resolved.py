from __future__ import annotations

import json
from pathlib import Path

from nutev.science.deepening import run_selective_bank_deepening
from nutev.science.deepening_resolved import (
    DEEPENING_PIPELINE_VERSION,
    run_selective_bank_deepening_resolved,
)
from nutev.science.workbench_priority import augment_workbench_priority

from nutev_tests.test_workbench_priority import _build_workbench


def test_resolver_v2_reprocesses_v1_batch_once_then_resumes(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root, search_id = _build_workbench(output_root)
    augment_workbench_priority(search_id, output_root=output_root)

    first = run_selective_bank_deepening(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        allow_network=False,
    )
    assert first["status"] == "COMPLETE"
    assert first["processed_documents"] == 1

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
    v1_manifest = json.loads(batch_path.read_text(encoding="utf-8"))
    assert "pipeline_version" not in v1_manifest

    events: list[dict[str, object]] = []
    upgraded = run_selective_bank_deepening_resolved(
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
    assert upgraded["processed_documents"] == 1
    assert any(event.get("stage") == "full_text_resolution" for event in events)

    v2_manifest = json.loads(batch_path.read_text(encoding="utf-8"))
    assert v2_manifest["pipeline_version"] == DEEPENING_PIPELINE_VERSION
    assert v2_manifest["status"] == "PASS"
    assert v2_manifest["resolver_route_counts"]["recorded_url"] == 1

    workbench_manifest = json.loads(
        (workbench_root / "WORKBENCH_MANIFEST.json").read_text(encoding="utf-8")
    )
    batch_id = v2_manifest["batch_id"]
    assert (
        workbench_manifest["extensions"]["deepening"]["batches"][batch_id]["status"]
        == "PASS"
    )

    resumed_events: list[dict[str, object]] = []
    resumed = run_selective_bank_deepening_resolved(
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
    assert resumed["processed_documents"] == 1
    assert any(
        event.get("stage") == "batch_skipped_complete" for event in resumed_events
    )
