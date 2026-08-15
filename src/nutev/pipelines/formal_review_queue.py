"""Persistent human screening queue generated from the FORMAL corpus.

The queue pre-organizes evidence availability and reviewer slots but never fills a
scientific INCLUDE/EXCLUDE/DOUBT decision. Existing human decisions are preserved
when the queue is rebuilt after new extraction artifacts become available.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not Path(path).is_file():
        return rows
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str))
            handle.write("\n")
    tmp.replace(path)
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _quality_flag(extractions: list[dict[str, Any]]) -> tuple[str, str, str]:
    if not extractions:
        return "no_full_text", "", "No usable extracted full text is linked to this document."
    usable = [row for row in extractions if str(row.get("text_path") or "").strip()]
    if not usable:
        statuses = sorted({str(row.get("extraction_status") or "") for row in extractions if row.get("extraction_status")})
        if any(status in {"ocr_fail", "pdf_needs_ocr_setup", "pdf_no_text"} for status in statuses):
            return "poor_ocr", "", "Full text exists, but OCR/extraction is not usable yet."
        return "no_full_text", "", "No usable extracted full text is linked to this document."
    best = max(usable, key=lambda row: int(row.get("chars") or 0))
    failed_pages = str(best.get("ocr_failed_pages") or "").strip()
    if failed_pages:
        return "poor_ocr", str(best.get("text_path") or ""), f"OCR has failed pages: {failed_pages}."
    return "ready_to_screen", str(best.get("text_path") or ""), "Evidence is organized for human screening."


def build_formal_review_queue(
    project_root: Path,
    *,
    master_rows: list[dict[str, Any]],
    extraction_manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    root = Path(project_root)
    queue_path = root / "06_review" / "formal_screening_queue.jsonl"
    existing = {str(row.get("document_id") or ""): row for row in _read_jsonl(queue_path)}
    extraction_by_document: dict[str, list[dict[str, Any]]] = {}
    for row in extraction_manifest:
        document_id = str(row.get("document_id") or "").strip()
        if document_id:
            extraction_by_document.setdefault(document_id, []).append(row)

    rows: list[dict[str, Any]] = []
    for master in master_rows:
        document_id = str(master.get("document_id") or "").strip()
        if not document_id:
            continue
        old = existing.get(document_id) or {}
        screen_flag, text_path, quality_note = _quality_flag(extraction_by_document.get(document_id, []))
        row = {
            "document_id": document_id,
            "title": str(master.get("title") or ""),
            "abstract": str(master.get("abstract") or ""),
            "doi": str(master.get("doi") or ""),
            "pmid": str(master.get("pmid") or ""),
            "year": master.get("year"),
            "source_providers": master.get("source_providers") or [master.get("source_provider")],
            "full_text_path": text_path,
            "screen_flag": screen_flag,
            "quality_note": quality_note,
            "language_original": old.get("language_original") or master.get("language_original") or master.get("language") or "",
            "language_detected": old.get("language_detected") or "",
            # Human-owned fields. Existing values survive rebuilds; blanks are never inferred.
            "reviewer_1": old.get("reviewer_1") or "",
            "reviewer_1_decision": old.get("reviewer_1_decision") or "",
            "reviewer_1_reason": old.get("reviewer_1_reason") or "",
            "reviewer_2": old.get("reviewer_2") or "",
            "reviewer_2_decision": old.get("reviewer_2_decision") or "",
            "reviewer_2_reason": old.get("reviewer_2_reason") or "",
            "adjudicator": old.get("adjudicator") or "",
            "adjudication_decision": old.get("adjudication_decision") or "",
            "adjudication_rationale": old.get("adjudication_rationale") or "",
            "human_decision_inferred": False,
        }
        rows.append(row)

    queue_sha256 = _atomic_jsonl(queue_path, rows)
    summary = {
        "schema_version": 1,
        "queue_path": str(queue_path),
        "queue_sha256": queue_sha256,
        "documents": len(rows),
        "ready_to_screen": sum(row["screen_flag"] == "ready_to_screen" for row in rows),
        "no_full_text": sum(row["screen_flag"] == "no_full_text" for row in rows),
        "poor_ocr": sum(row["screen_flag"] == "poor_ocr" for row in rows),
        "r1_complete": sum(bool(str(row.get("reviewer_1_decision") or "").strip()) for row in rows),
        "r2_complete": sum(bool(str(row.get("reviewer_2_decision") or "").strip()) for row in rows),
        "human_decision_inferred": False,
    }
    summary_path = root / "06_review" / "formal_screening_queue_summary.json"
    _atomic_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


__all__ = ["build_formal_review_queue"]
