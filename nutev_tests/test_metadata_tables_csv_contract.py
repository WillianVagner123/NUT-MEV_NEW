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


def test_empty_download_manifest_uses_current_downloader_schema(tmp_path: Path) -> None:
    path = tmp_path / "download_manifest.csv"

    write_simple_csv([], path)

    assert path.read_text(encoding="utf-8").splitlines() == [
        "document_id,url,resolved_url,path,ext,source,status"
    ]


def test_empty_failed_downloads_uses_current_downloader_schema(tmp_path: Path) -> None:
    path = tmp_path / "failed_downloads.csv"

    write_simple_csv([], path)

    assert path.read_text(encoding="utf-8").splitlines() == [
        "document_id,url,resolved_url,status,reason,head_status"
    ]


def test_empty_extraction_manifest_uses_current_extractor_schema(tmp_path: Path) -> None:
    path = tmp_path / "extraction_manifest.csv"

    write_simple_csv([], path)

    assert path.read_text(encoding="utf-8").splitlines() == [
        "file,ext,used_ocr,ocr_failed_pages,text_path,chars,extraction_status,reason"
    ]


def test_unknown_empty_simple_csv_remains_schema_free(tmp_path: Path) -> None:
    path = tmp_path / "custom_empty.csv"

    write_simple_csv([], path)

    assert path.read_text(encoding="utf-8") == ""
