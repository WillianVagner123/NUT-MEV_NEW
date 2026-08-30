from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from nutev.science.deepening import run_selective_bank_deepening
from nutev.science.workbench_priority import augment_workbench_priority

from nutev_tests.test_workbench_priority import _build_workbench


def test_selective_tier_a_deepening_runs_pipeline_overlays_and_resumes(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root, search_id = _build_workbench(output_root)
    augment_workbench_priority(search_id, output_root=output_root)

    events: list[dict[str, object]] = []
    first = run_selective_bank_deepening(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        limit=0,
        allow_network=False,
        on_progress=events.append,
    )

    assert first["status"] == "COMPLETE"
    assert first["target_tier_records"] == 1
    assert first["processed_documents"] == 1
    assert first["completed_batches_this_run"] == 1
    assert first["external_llm_calls"] == 0
    assert any(event.get("stage") == "workbench_overlay" for event in events)
    assert any(event.get("stage") == "complete" for event in events)

    manifest = json.loads((workbench_root / "WORKBENCH_MANIFEST.json").read_text())
    assert manifest["extensions"]["bank_priority"]["status"] == "PASS"
    assert manifest["extensions"]["deepening"]["status"] == "PASS"
    assert manifest["extensions"]["deepening"]["deepened_articles"] == 1
    database = Path(manifest["outputs"]["database"]["path"])
    assert database.name == "evidence_workbench_deepened.sqlite"

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT reference_rank, reference_tier, deepening_status, extraction_method,
                   ocr_used, text_chars, card_json
            FROM article_cards WHERE document_id=?
            """,
            ("doi:10.1000/older",),
        ).fetchone()
        assert row is not None
        assert row["reference_rank"] == 1
        assert row["reference_tier"] == "BANK_A_PROCESSING_PRIORITY"
        assert row["deepening_status"] == "deepened"
        assert row["ocr_used"] == 0
        card = json.loads(row["card_json"])
        assert card["deepening"]["status"] == "deepened"
        assert card["deepening"]["tier"] == "A"
        assert card["deepening"]["search_id"] == search_id

    batch_manifests = list(
        (output_root / "scientific" / "deepening" / search_id / "tier-A" / "batches").glob(
            "*/BATCH_MANIFEST.json"
        )
    )
    assert len(batch_manifests) == 1
    batch_manifest = json.loads(batch_manifests[0].read_text())
    assert batch_manifest["status"] == "PASS"
    assert batch_manifest["documents"] == 1
    assert batch_manifest["network_fetch_enabled"] is False

    second_events: list[dict[str, object]] = []
    second = run_selective_bank_deepening(
        search_id,
        output_root=output_root,
        tier="A",
        batch_size=25,
        allow_network=False,
        on_progress=second_events.append,
    )
    assert second["status"] == "COMPLETE"
    assert second["completed_batches_this_run"] == 0
    assert second["skipped_batches_this_run"] == 1
    assert second["processed_documents"] == 1
    assert any(event.get("stage") == "batch_skipped_complete" for event in second_events)
