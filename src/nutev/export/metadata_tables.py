from __future__ import annotations
import csv
from pathlib import Path

REQUIRED_METADATA_COLUMNS = [
    "document_id", "title", "doi", "pmid", "pmcid", "original_url", "final_url", "source_provider", "source_institution",
    "country", "region", "workstream", "year", "language", "evidence_type", "capture_status", "download_status", "extraction_status",
    "artifact_paths", "failure_reason", "relevance_score", "novelty_score", "domains", "outcomes", "diet_patterns", "clinical_conditions",
    "first_seen_date", "last_seen_date", "is_new", "llm_decision", "llm_reason",
    "journal", "publication_date", "article_type", "authors", "abstract", "metadata_status", "retrieved_at",
    "editorial_priority_score", "editorial_priority_tier",
    # Article 1 analytical schema (see nutev.analysis.article1_coding).
    "track", "issuing_body", "who_region", "income_band", "document_version",
    "access_date", "official_url", "archived_pdf_path", "archived_pdf_sha256",
    "domain_A", "domain_B", "domain_C", "domain_D", "profile", "n_domains",
    "mentions_cost", "mentions_equity", "domain_coding_needs_human_review",
    "authority", "accuracy", "coverage", "objectivity", "date_currency",
    "significance", "aacods_needs_human_review",
]

ARTICLE_DATA_COLUMNS = [
    "document_id",
    "workstream",
    "source_provider",
    "title",
    "authors",
    "journal",
    "year",
    "publication_date",
    "article_type",
    "doi",
    "pmid",
    "pmcid",
    "original_url",
    "final_url",
    "abstract",
    "relevance_score",
    "editorial_priority_score",
    "editorial_priority_tier",
    "download_status",
    "extraction_status",
    "artifact_paths",
    "metadata_status",
    "failure_reason",
    # Article 1 assistive coding + key phrases (enter human review).
    "track",
    "profile",
    "n_domains",
    "domain_A",
    "domain_B",
    "domain_C",
    "domain_D",
    # Rich thematic detection + evidence tier (assistive).
    "doc_type",
    "evidence_weight",
    "diet_patterns",
    "n_themes",
    "themes_present",
    "nutrition_macros_pct",
    "nutrition_fiber_g",
    "nutrition_sodium",
    "nutrition_micronutrients",
    "reference",
    "n_key_phrases",
    "top_terms",
    "key_phrases_text",
]

# Known operational artifacts are valid even when a run produces zero rows.
# These schemas mirror the dictionaries emitted by the current downloader and
# extractor; they are intentionally filename-scoped so an empty artifact remains
# distinguishable from a failed/truncated write without inventing unavailable data.
_SIMPLE_CSV_DEFAULT_COLUMNS = {
    "download_manifest.csv": [
        "document_id",
        "url",
        "resolved_url",
        "path",
        "ext",
        "source",
        "status",
    ],
    "failed_downloads.csv": [
        "document_id",
        "url",
        "resolved_url",
        "status",
        "reason",
        "head_status",
    ],
    "extraction_manifest.csv": [
        "file",
        "ext",
        "used_ocr",
        "ocr_failed_pages",
        "text_path",
        "chars",
        "extraction_status",
        "reason",
    ],
}

_FULL_TEXT_DOWNLOAD_STATUSES = {"pdf", "html", "html_snapshot", "success", "downloaded"}
_FULL_TEXT_CAPTURE_STATUSES = {"pdf", "html", "html_snapshot", "success", "ok", "captured"}
_FULL_TEXT_EXTRACTION_STATUSES = {"ok", "success", "extracted"}


def _derived_download_status(row: dict) -> str:
    """Return a conservative download status without treating arbitrary files as full text."""
    explicit = str(row.get("download_status", "") or "").strip()
    if explicit:
        return explicit

    artifact = str(row.get("file_path") or row.get("artifact_paths") or "").strip().lower()
    if artifact.endswith(".pdf"):
        return "pdf"
    if artifact.endswith((".html", ".htm")):
        return "html_snapshot"
    return "metadata_only"


def _default_metadata_status(row: dict, download_status: str) -> str:
    explicit = str(row.get("metadata_status", "") or "").strip()
    if explicit:
        return explicit

    download = download_status.strip().lower()
    capture = str(row.get("capture_status", "") or "").strip().lower()
    extraction = str(row.get("extraction_status", "") or "").strip().lower()

    if (
        download in _FULL_TEXT_DOWNLOAD_STATUSES
        or capture in _FULL_TEXT_CAPTURE_STATUSES
        or extraction in _FULL_TEXT_EXTRACTION_STATUSES
    ):
        return "full_text_available"
    if download == "metadata_only" or capture == "metadata_only":
        return "metadata_only"
    return ""


def _normalize_metadata_row(row: dict) -> dict:
    out = {k: row.get(k, "") for k in REQUIRED_METADATA_COLUMNS}
    out["document_id"] = row.get("document_id") or row.get("id") or ""
    out["title"] = row.get("title", "")
    out["doi"] = row.get("doi", "")
    out["pmid"] = row.get("pmid", "")
    out["pmcid"] = row.get("pmcid", "")
    out["original_url"] = row.get("original_url", row.get("url", ""))
    out["final_url"] = row.get("final_url", row.get("resolved_url", row.get("url", "")))
    out["source_provider"] = row.get("source_provider", row.get("source", ""))
    out["artifact_paths"] = row.get("artifact_paths", row.get("file_path", ""))
    out["capture_status"] = row.get("capture_status", "missing")
    out["download_status"] = _derived_download_status(row)
    out["extraction_status"] = row.get("extraction_status", "missing")
    out["journal"] = row.get("journal", "")
    out["publication_date"] = row.get("publication_date", "")
    out["article_type"] = row.get("article_type", row.get("evidence_type", ""))
    out["authors"] = row.get("authors", "")
    out["abstract"] = row.get("abstract", "")
    out["metadata_status"] = _default_metadata_status(row, out["download_status"])
    out["editorial_priority_score"] = row.get("editorial_priority_score", "")
    out["editorial_priority_tier"] = row.get("editorial_priority_tier", "")
    return out


def _normalize_article_data_row(row: dict) -> dict:
    metadata = _normalize_metadata_row(row)
    return {k: metadata.get(k, row.get(k, "")) for k in ARTICLE_DATA_COLUMNS}


def write_metadata_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata_rows = [_normalize_metadata_row(r) for r in rows]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_METADATA_COLUMNS)
        w.writeheader()
        w.writerows(metadata_rows)


def write_article_data_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    article_rows = [_normalize_article_data_row(r) for r in rows]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ARTICLE_DATA_COLUMNS)
        w.writeheader()
        w.writerows(article_rows)


def write_simple_csv(
    rows: list[dict],
    path: Path,
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = fieldnames or sorted({k for r in rows for k in r.keys()})
    if not keys:
        keys = _SIMPLE_CSV_DEFAULT_COLUMNS.get(path.name, [])
    with path.open("w", newline="", encoding="utf-8") as f:
        if not keys:
            return
        # When callers provide an explicit or known operational schema,
        # provider-specific metadata may legitimately contain extra keys. The
        # schema is authoritative for this export, so ignore those extras instead
        # of failing the entire run.
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
