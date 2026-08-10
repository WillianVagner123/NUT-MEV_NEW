from __future__ import annotations

import csv

from nutev.global_watch.watch_export import export_watch_outputs


def _read_header(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def test_exports_csv_created(tmp_path) -> None:
    export_watch_outputs(
        [{"document_id": "d1"}],
        [{"document_id": "d1"}],
        tmp_path / "base",
        tmp_path / "run",
    )
    assert (tmp_path / "base" / "global_watch_master.csv").exists()


def test_export_watch_outputs_writes_headers_for_empty_operational_files(tmp_path) -> None:
    base_dir = tmp_path / "09_global_watch"
    run_dir = base_dir / "runs" / "2026-06-27"

    export_watch_outputs([], [], base_dir, run_dir)

    assert "document_id" in _read_header(base_dir / "global_watch_master.csv")
    assert "watch_score" in _read_header(base_dir / "global_watch_new_items.csv")
    assert _read_header(run_dir / "provider_performance.csv") == [
        "provider",
        "hits",
        "captured",
    ]
    assert _read_header(run_dir / "host_failures.csv") == [
        "host",
        "failure_reason",
        "http_status",
    ]
    assert _read_header(run_dir / "capture_manifest.csv") == [
        "document_id",
        "download_status",
        "capture_status",
        "artifact_paths",
    ]


def test_export_watch_outputs_preserves_unexpected_columns_after_schema(tmp_path) -> None:
    base_dir = tmp_path / "09_global_watch"
    run_dir = base_dir / "runs" / "2026-06-27"

    export_watch_outputs(
        [{"document_id": "doc-1", "title": "Nutrition guideline", "extra": "kept"}],
        [],
        base_dir,
        run_dir,
    )

    header = _read_header(base_dir / "global_watch_master.csv")
    assert header[:2] == ["document_id", "title"]
    assert header[-1] == "extra"
