from __future__ import annotations

import csv

from nutev.export.metadata_tables import write_article_data_csv, write_metadata_csv


def _read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_explicit_metadata_only_status_is_exported(tmp_path) -> None:
    output = tmp_path / "metadata_master.csv"
    write_metadata_csv(
        [
            {
                "document_id": "doc-1",
                "title": "Metadata only guideline",
                "download_status": "metadata_only",
            }
        ],
        output,
    )

    [row] = _read_rows(output)
    assert row["download_status"] == "metadata_only"
    assert row["metadata_status"] == "metadata_only"


def test_pdf_path_can_be_conservatively_recognized_as_full_text(tmp_path) -> None:
    output = tmp_path / "article_data.csv"
    write_article_data_csv(
        [
            {
                "document_id": "doc-2",
                "title": "Captured PDF",
                "file_path": "05_downloads/doc-2.pdf",
            }
        ],
        output,
    )

    [row] = _read_rows(output)
    assert row["download_status"] == "pdf"
    assert row["metadata_status"] == "full_text_available"
    assert row["artifact_paths"] == "05_downloads/doc-2.pdf"


def test_arbitrary_artifact_path_is_not_promoted_to_full_text(tmp_path) -> None:
    output = tmp_path / "metadata_master.csv"
    write_metadata_csv(
        [
            {
                "document_id": "doc-3",
                "title": "Metadata record with audit artifact",
                "artifact_paths": "02_metadata/doc-3.json",
            }
        ],
        output,
    )

    [row] = _read_rows(output)
    assert row["download_status"] == "metadata_only"
    assert row["metadata_status"] == "metadata_only"


def test_successful_extraction_marks_full_text_without_guessing_file_type(tmp_path) -> None:
    output = tmp_path / "metadata_master.csv"
    write_metadata_csv(
        [
            {
                "document_id": "doc-4",
                "title": "Extracted document",
                "download_status": "unknown",
                "extraction_status": "success",
            }
        ],
        output,
    )

    [row] = _read_rows(output)
    assert row["metadata_status"] == "full_text_available"


def test_explicit_metadata_status_is_preserved(tmp_path) -> None:
    output = tmp_path / "metadata_master.csv"
    write_metadata_csv(
        [
            {
                "document_id": "doc-5",
                "title": "Preserved status",
                "metadata_status": "capture_failed",
                "download_status": "failed",
            }
        ],
        output,
    )

    [row] = _read_rows(output)
    assert row["metadata_status"] == "capture_failed"
