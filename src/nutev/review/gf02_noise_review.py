"""Human-only persistence helpers for the GF-02 rescue-only review.

This module never classifies records automatically. It only reads and writes the
existing audit CSV produced by the GF-02 PILOT while preserving row order,
metadata and any columns added by older/newer runner versions.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from uuid import uuid4

ALLOWED_CLASSIFICATIONS = ("RELEVANT", "IRRELEVANT", "DOUBT")
_REQUIRED_COLUMNS = {"sample_id", "classification", "reviewer", "note"}


def read_rescue_only_sample(path: Path) -> list[dict[str, str]]:
    """Read the rescue-only review CSV without changing scientific content."""
    sample_path = Path(path)
    if not sample_path.is_file():
        raise FileNotFoundError(f"GF-02 rescue-only sample not found: {sample_path}")
    with sample_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = sorted(_REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise ValueError("GF-02 rescue-only sample is missing columns: " + ", ".join(missing))
        rows = [
            {str(key): str(value or "") for key, value in row.items() if key is not None}
            for row in reader
        ]
    if not rows:
        raise ValueError("GF-02 rescue-only sample is empty")
    sample_ids = [row.get("sample_id", "").strip() for row in rows]
    if any(not value for value in sample_ids):
        raise ValueError("GF-02 rescue-only sample contains a blank sample_id")
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("GF-02 rescue-only sample contains duplicate sample_id values")
    return rows


def review_progress(path: Path) -> dict[str, Any]:
    """Return descriptive completion only; never estimate precision."""
    rows = read_rescue_only_sample(path)
    resolved = sum(
        1
        for row in rows
        if row.get("classification", "").strip() and row.get("reviewer", "").strip()
    )
    return {
        "total": len(rows),
        "resolved": resolved,
        "pending": len(rows) - resolved,
        "complete": resolved == len(rows),
        "precision_estimated": False,
    }


def save_rescue_only_classification(
    path: Path,
    *,
    sample_id: str,
    classification: str,
    reviewer: str,
    note: str = "",
) -> dict[str, str]:
    """Persist one explicit human classification atomically.

    The function requires an identified human reviewer and one explicit label.
    It does not infer labels, fill blank rows, or summarize the sample as a
    precision estimate.
    """
    sample_path = Path(path)
    resolved_sample_id = str(sample_id or "").strip()
    resolved_reviewer = str(reviewer or "").strip()
    resolved_classification = str(classification or "").strip().upper()
    if not resolved_sample_id:
        raise ValueError("sample_id is required")
    if not resolved_reviewer:
        raise ValueError("A real reviewer identity is required")
    if resolved_classification not in ALLOWED_CLASSIFICATIONS:
        raise ValueError(
            "classification must be one of: " + ", ".join(ALLOWED_CLASSIFICATIONS)
        )

    with sample_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = sorted(_REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise ValueError("GF-02 rescue-only sample is missing columns: " + ", ".join(missing))
        rows = [dict(row) for row in reader]

    matches = [row for row in rows if str(row.get("sample_id") or "").strip() == resolved_sample_id]
    if len(matches) != 1:
        raise ValueError(f"sample_id must identify exactly one row: {resolved_sample_id}")
    target = matches[0]
    target["classification"] = resolved_classification
    target["reviewer"] = resolved_reviewer
    target["note"] = str(note or "").strip()

    tmp = sample_path.with_name(f".{sample_path.name}.{uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(sample_path)
    finally:
        if tmp.exists():
            tmp.unlink()

    return {
        "sample_id": resolved_sample_id,
        "classification": resolved_classification,
        "reviewer": resolved_reviewer,
        "note": str(note or "").strip(),
    }


__all__ = [
    "ALLOWED_CLASSIFICATIONS",
    "read_rescue_only_sample",
    "review_progress",
    "save_rescue_only_classification",
]
