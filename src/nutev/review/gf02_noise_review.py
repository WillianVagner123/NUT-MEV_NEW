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


def _read_with_fields(path: Path) -> tuple[list[str], list[dict[str, str]]]:
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
    return fieldnames, rows


def _atomic_write(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    sample_path = Path(path)
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


def read_rescue_only_sample(path: Path) -> list[dict[str, str]]:
    """Read the rescue-only review CSV without changing scientific content."""
    _, rows = _read_with_fields(path)
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

    fieldnames, rows = _read_with_fields(sample_path)
    matches = [row for row in rows if str(row.get("sample_id") or "").strip() == resolved_sample_id]
    if len(matches) != 1:
        raise ValueError(f"sample_id must identify exactly one row: {resolved_sample_id}")
    target = matches[0]
    target["classification"] = resolved_classification
    target["reviewer"] = resolved_reviewer
    target["note"] = str(note or "").strip()
    _atomic_write(sample_path, fieldnames, rows)

    return {
        "sample_id": resolved_sample_id,
        "classification": resolved_classification,
        "reviewer": resolved_reviewer,
        "note": str(note or "").strip(),
    }


def _normalize_decisions(decisions: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for decision in decisions:
        sample_id = str(decision.get("sample_id") or "").strip()
        classification = str(decision.get("classification") or "").strip().upper()
        if not sample_id:
            raise ValueError("sample_id is required for every batch decision")
        if sample_id in normalized:
            raise ValueError(f"duplicate sample_id in batch review: {sample_id}")
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError(
                f"classification for {sample_id} must be one of: "
                + ", ".join(ALLOWED_CLASSIFICATIONS)
            )
        normalized[sample_id] = {
            "classification": classification,
            "note": str(decision.get("note") or "").strip(),
        }
    return normalized


def save_rescue_only_progress(
    path: Path,
    *,
    reviewer: str,
    decisions: list[dict[str, str]],
) -> dict[str, Any]:
    """Persist an explicit subset of rescue-only decisions in one atomic write.

    This is a save-progress operation. Blank/unsubmitted rows remain blank and
    are never converted into scientific decisions. Every submitted row must
    carry one explicit allowed classification and a real reviewer identity.
    """
    sample_path = Path(path)
    resolved_reviewer = str(reviewer or "").strip()
    if not resolved_reviewer:
        raise ValueError("A real reviewer identity is required")
    if not decisions:
        raise ValueError("At least one explicit human classification is required")

    normalized = _normalize_decisions(decisions)
    fieldnames, rows = _read_with_fields(sample_path)
    expected_ids = {str(row.get("sample_id") or "").strip() for row in rows}
    extra_ids = [sample_id for sample_id in normalized if sample_id not in expected_ids]
    if extra_ids:
        raise ValueError("review progress contains unknown sample_id: " + ", ".join(extra_ids))

    for row in rows:
        sample_id = str(row.get("sample_id") or "").strip()
        if sample_id not in normalized:
            continue
        decision = normalized[sample_id]
        row["classification"] = decision["classification"]
        row["reviewer"] = resolved_reviewer
        row["note"] = decision["note"]

    _atomic_write(sample_path, fieldnames, rows)
    return {
        "updated": len(normalized),
        "reviewer": resolved_reviewer,
        "complete": False,
        "precision_estimated": False,
    }


def save_rescue_only_batch(
    path: Path,
    *,
    reviewer: str,
    decisions: list[dict[str, str]],
) -> dict[str, Any]:
    """Persist the complete rescue-only human review in one atomic write.

    Batch mode is intentionally all-or-nothing: every row in the current sample
    must be present with an explicit classification before the CSV is replaced.
    This supports an end-of-automation review table without silently converting
    blanks into scientific decisions.
    """
    sample_path = Path(path)
    resolved_reviewer = str(reviewer or "").strip()
    if not resolved_reviewer:
        raise ValueError("A real reviewer identity is required")
    if not decisions:
        raise ValueError("At least one human classification is required")

    normalized = _normalize_decisions(decisions)
    fieldnames, rows = _read_with_fields(sample_path)
    expected_ids = [str(row.get("sample_id") or "").strip() for row in rows]
    missing_ids = [sample_id for sample_id in expected_ids if sample_id not in normalized]
    extra_ids = [sample_id for sample_id in normalized if sample_id not in set(expected_ids)]
    if missing_ids:
        raise ValueError("batch review is incomplete; missing sample_id: " + ", ".join(missing_ids))
    if extra_ids:
        raise ValueError("batch review contains unknown sample_id: " + ", ".join(extra_ids))

    for row in rows:
        sample_id = str(row.get("sample_id") or "").strip()
        decision = normalized[sample_id]
        row["classification"] = decision["classification"]
        row["reviewer"] = resolved_reviewer
        row["note"] = decision["note"]

    _atomic_write(sample_path, fieldnames, rows)
    return {
        "updated": len(rows),
        "reviewer": resolved_reviewer,
        "complete": True,
        "precision_estimated": False,
    }


__all__ = [
    "ALLOWED_CLASSIFICATIONS",
    "read_rescue_only_sample",
    "review_progress",
    "save_rescue_only_batch",
    "save_rescue_only_classification",
    "save_rescue_only_progress",
]
