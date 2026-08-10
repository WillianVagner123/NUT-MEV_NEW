from __future__ import annotations

import csv
from pathlib import Path

from nutev.export.metadata_tables import write_simple_csv


def test_schema_bound_empty_csv_preserves_header(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"

    write_simple_csv([], path, fieldnames=["document_id", "status"])

    assert path.read_text(encoding="utf-8").splitlines() == ["document_id,status"]


def test_schema_bound_csv_ignores_provider_specific_extra_fields(tmp_path: Path) -> None:
    path = tmp_path / "provider.csv"

    write_simple_csv(
        [
            {
                "document_id": "doc-1",
                "status": "completed",
                "provider_debug_metadata": "not part of this export schema",
            }
        ],
        path,
        fieldnames=["document_id", "status"],
    )

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [{"document_id": "doc-1", "status": "completed"}]
