"""Human duplicate review, article screening, and PRISMA snapshot services."""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.review.article_screening_ledger import (
    EXCLUSION_REASONS,
    get_or_create_screening_session,
    get_screening_session,
    list_article_catalog,
    list_duplicate_candidates_with_latest_review,
    list_latest_article_screening_decisions,
    list_latest_duplicate_reviews,
    record_article_screening_decision,
    record_duplicate_candidate_review,
    record_screening_export,
)
from nutev.search.corpus_build_ledger import get_corpus_build
from nutev.search.strategy_registry import get_strategy_version

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)
    return _sha256_file(path)


def _atomic_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return _sha256_file(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return value


def load_verified_master_records(
    db_path: Path,
    *,
    build_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Load one immutable corpus build after validating its manifest and master hash."""
    build = get_corpus_build(db_path, build_id)
    if build is None:
        raise ValueError(f"unknown corpus build: {build_id}")
    if build["status"] != "SUCCEEDED":
        raise ValueError("screening requires a successful corpus build")

    manifest_path = Path(str(build["manifest_path"]))
    master_path = Path(str(build["master_jsonl_path"]))
    if not manifest_path.is_file():
        raise FileNotFoundError(f"corpus manifest not found: {manifest_path}")
    if not master_path.is_file():
        raise FileNotFoundError(f"master corpus not found: {master_path}")
    actual_manifest_sha = _sha256_file(manifest_path)
    if actual_manifest_sha != str(build["manifest_sha256"]):
        raise ValueError(
            "corpus manifest checksum mismatch: "
            f"expected {build['manifest_sha256']}, got {actual_manifest_sha}"
        )
    manifest = _read_json(manifest_path)
    expected_master_sha = str(
        ((manifest.get("outputs") or {}).get("master_records_sha256") or "")
    )
    if not expected_master_sha:
        raise ValueError("corpus manifest does not contain master_records_sha256")
    actual_master_sha = _sha256_file(master_path)
    if actual_master_sha != expected_master_sha:
        raise ValueError(
            "master corpus checksum mismatch: "
            f"expected {expected_master_sha}, got {actual_master_sha}"
        )

    records: list[dict[str, Any]] = []
    with master_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid master JSONL at line {line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"master JSONL row {line_number} is not an object"
                )
            document_id = str(value.get("document_id") or "").strip()
            if not document_id:
                raise ValueError(
                    f"master JSONL row {line_number} has no document_id"
                )
            records.append(value)
    if len({str(row["document_id"]) for row in records}) != len(records):
        raise ValueError("master corpus contains duplicate document_id values")
    return build, records, manifest


def ensure_screening_session(
    db_path: Path,
    *,
    build_id: str,
    protocol_version: str = "v1",
    created_by: str = "",
    notes: str = "",
) -> dict[str, Any]:
    load_verified_master_records(db_path, build_id=build_id)
    return get_or_create_screening_session(
        db_path,
        build_id=build_id,
        protocol_version=protocol_version,
        created_by=created_by,
        notes=notes,
    )


def _confirmed_duplicate_reviews(
    db_path: Path,
    *,
    session_id: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in list_latest_duplicate_reviews(db_path, session_id=session_id)
        if row["decision"] == "CONFIRMED_DUPLICATE"
    ]


def effective_master_records(
    db_path: Path,
    *,
    session_id: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    _, records, _ = load_verified_master_records(
        db_path,
        build_id=str(session["build_id"]),
    )
    removed_to_retained = {
        str(row["removed_document_id"]): str(row["retained_document_id"])
        for row in _confirmed_duplicate_reviews(db_path, session_id=session_id)
    }
    effective = [
        row
        for row in records
        if str(row["document_id"]) not in removed_to_retained
    ]
    return effective, removed_to_retained


def duplicate_review_queue(
    db_path: Path,
    *,
    session_id: str,
) -> list[dict[str, Any]]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    _, records, _ = load_verified_master_records(
        db_path,
        build_id=str(session["build_id"]),
    )
    by_id = {str(row["document_id"]): row for row in records}
    output: list[dict[str, Any]] = []
    for candidate in list_duplicate_candidates_with_latest_review(
        db_path,
        session_id=session_id,
    ):
        row = dict(candidate)
        left = by_id.get(str(candidate["left_document_id"]), {})
        right = by_id.get(str(candidate["right_document_id"]), {})
        row.update(
            {
                "left_title": left.get("title", ""),
                "left_doi": left.get("doi", ""),
                "left_year": left.get("year", ""),
                "left_providers": left.get("matched_providers", ""),
                "right_title": right.get("title", ""),
                "right_doi": right.get("doi", ""),
                "right_year": right.get("year", ""),
                "right_providers": right.get("matched_providers", ""),
                "review_status": candidate.get("review_decision") or "PENDING",
            }
        )
        output.append(row)
    return output


def save_duplicate_review(
    db_path: Path,
    *,
    session_id: str,
    candidate_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    retained_document_id: str = "",
    notes: str = "",
) -> dict[str, Any]:
    candidates = {
        str(row["candidate_id"]): row
        for row in duplicate_review_queue(db_path, session_id=session_id)
    }
    candidate = candidates.get(candidate_id)
    if candidate is None:
        raise ValueError(f"unknown candidate_id: {candidate_id}")
    normalized = decision.strip().upper()
    removed_document_id = ""
    if normalized == "CONFIRMED_DUPLICATE":
        pair = {
            str(candidate["left_document_id"]),
            str(candidate["right_document_id"]),
        }
        retained = retained_document_id.strip()
        if retained not in pair:
            raise ValueError("retained_document_id must be one of the candidate documents")
        removed_document_id = next(item for item in pair if item != retained)
    return record_duplicate_candidate_review(
        db_path,
        session_id=session_id,
        candidate_id=candidate_id,
        decision=normalized,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        retained_document_id=retained_document_id,
        removed_document_id=removed_document_id,
        notes=notes,
    )


def article_screening_queue(
    db_path: Path,
    *,
    session_id: str,
    article_id: str,
    stage: str = "TITLE_ABSTRACT",
    status_filter: str = "ALL",
) -> list[dict[str, Any]]:
    records, _ = effective_master_records(db_path, session_id=session_id)
    decisions = {
        str(row["document_id"]): row
        for row in list_latest_article_screening_decisions(
            db_path,
            session_id=session_id,
            article_id=article_id,
            stage=stage,
        )
    }
    normalized_filter = status_filter.strip().upper()
    allowed_filters = {"ALL", "PENDING", "INCLUDE", "EXCLUDE", "MAYBE"}
    if normalized_filter not in allowed_filters:
        raise ValueError(f"status_filter must be one of {sorted(allowed_filters)}")
    queue: list[dict[str, Any]] = []
    for record in records:
        document_id = str(record["document_id"])
        decision = decisions.get(document_id)
        status = str(decision["decision"]) if decision else "PENDING"
        if normalized_filter != "ALL" and status != normalized_filter:
            continue
        queue.append(
            {
                **record,
                "screening_status": status,
                "screening_decision_id": (
                    str(decision["decision_id"]) if decision else ""
                ),
                "screening_revision": int(decision["revision"]) if decision else 0,
                "exclusion_reason": (
                    str(decision["exclusion_reason"]) if decision else ""
                ),
                "screening_notes": str(decision["notes"]) if decision else "",
                "reviewer_name": str(decision["reviewer_name"]) if decision else "",
                "reviewer_role": str(decision["reviewer_role"]) if decision else "",
                "decided_at": str(decision["decided_at"]) if decision else "",
            }
        )
    queue.sort(
        key=lambda row: (
            row["screening_status"] != "PENDING",
            str(row.get("title") or "").casefold(),
            str(row["document_id"]),
        )
    )
    return queue


def save_article_screening_decision(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    stage: str = "TITLE_ABSTRACT",
    exclusion_reason: str = "",
    notes: str = "",
) -> dict[str, Any]:
    effective, _ = effective_master_records(db_path, session_id=session_id)
    document_ids = {str(row["document_id"]) for row in effective}
    if document_id not in document_ids:
        raise ValueError("document is not available in the effective screening corpus")
    return record_article_screening_decision(
        db_path,
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
        decision=decision,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        stage=stage,
        exclusion_reason=exclusion_reason,
        notes=notes,
    )


def summarize_screening_session(
    db_path: Path,
    *,
    session_id: str,
    stage: str = "TITLE_ABSTRACT",
) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    build, all_records, _ = load_verified_master_records(
        db_path,
        build_id=str(session["build_id"]),
    )
    effective, removed_to_retained = effective_master_records(
        db_path,
        session_id=session_id,
    )
    version = get_strategy_version(db_path, str(build["version_id"]))
    if version is None:
        raise ValueError("strategy version for corpus build is missing")
    prisma_eligible = bool(version["prisma_eligible"])
    article_catalog = list_article_catalog(db_path, active_only=True)
    decisions = list_latest_article_screening_decisions(
        db_path,
        session_id=session_id,
        stage=stage,
    )
    by_article: dict[str, list[dict[str, Any]]] = {
        str(article["article_id"]): [] for article in article_catalog
    }
    for decision in decisions:
        if decision["document_id"] not in removed_to_retained:
            by_article.setdefault(str(decision["article_id"]), []).append(decision)

    article_rows: list[dict[str, Any]] = []
    effective_count = len(effective)
    for article in article_catalog:
        article_id = str(article["article_id"])
        article_decisions = by_article.get(article_id, [])
        include_count = sum(row["decision"] == "INCLUDE" for row in article_decisions)
        exclude_count = sum(row["decision"] == "EXCLUDE" for row in article_decisions)
        maybe_count = sum(row["decision"] == "MAYBE" for row in article_decisions)
        screened_count = include_count + exclude_count + maybe_count
        pending_count = max(0, effective_count - screened_count)
        reasons = {
            reason: sum(
                row["decision"] == "EXCLUDE"
                and row["exclusion_reason"] == reason
                for row in article_decisions
            )
            for reason in EXCLUSION_REASONS
        }
        reasons = {key: value for key, value in reasons.items() if value}
        article_rows.append(
            {
                "article_id": article_id,
                "article_number": article["article_number"],
                "article_label": article["label"],
                "stage": stage,
                "records_after_automatic_deduplication": len(all_records),
                "human_duplicates_removed": len(removed_to_retained),
                "records_available_for_screening": effective_count,
                "records_screened": screened_count,
                "records_included": include_count,
                "records_excluded": exclude_count,
                "records_maybe": maybe_count,
                "records_pending": pending_count,
                "exclusion_reasons": reasons,
                "prisma_eligible": prisma_eligible,
                "prisma_records_screened": screened_count if prisma_eligible else 0,
                "prisma_records_excluded": exclude_count if prisma_eligible else 0,
                "prisma_reports_sought_for_retrieval": (
                    include_count if prisma_eligible else 0
                ),
            }
        )

    candidate_queue = duplicate_review_queue(db_path, session_id=session_id)
    pending_duplicate_reviews = sum(
        row["review_status"] == "PENDING" for row in candidate_queue
    )
    return {
        "session_id": session_id,
        "build_id": session["build_id"],
        "version_id": build["version_id"],
        "search_run_id": build["run_id"],
        "search_type": version["search_type"],
        "prisma_eligible": prisma_eligible,
        "stage": stage,
        "records_after_automatic_deduplication": len(all_records),
        "human_duplicates_removed": len(removed_to_retained),
        "effective_documents": effective_count,
        "possible_duplicate_candidates": len(candidate_queue),
        "pending_duplicate_reviews": pending_duplicate_reviews,
        "articles": article_rows,
    }


def export_screening_snapshot(
    db_path: Path,
    *,
    session_id: str,
    stage: str = "TITLE_ABSTRACT",
    export_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    build, _, corpus_manifest = load_verified_master_records(
        db_path,
        build_id=str(session["build_id"]),
    )
    effective, removed_to_retained = effective_master_records(
        db_path,
        session_id=session_id,
    )
    summary = summarize_screening_session(
        db_path,
        session_id=session_id,
        stage=stage,
    )
    decisions = list_latest_article_screening_decisions(
        db_path,
        session_id=session_id,
        stage=stage,
    )
    duplicate_reviews = list_latest_duplicate_reviews(
        db_path,
        session_id=session_id,
    )
    articles = list_article_catalog(db_path, active_only=True)
    decision_map = {
        (str(row["document_id"]), str(row["article_id"])): row
        for row in decisions
        if str(row["document_id"]) not in removed_to_retained
    }

    queue_rows: list[dict[str, Any]] = []
    for record in effective:
        for article in articles:
            key = (str(record["document_id"]), str(article["article_id"]))
            decision = decision_map.get(key)
            queue_rows.append(
                {
                    "document_id": record["document_id"],
                    "article_id": article["article_id"],
                    "article_label": article["label"],
                    "stage": stage,
                    "decision": decision["decision"] if decision else "PENDING",
                    "exclusion_reason": (
                        decision["exclusion_reason"] if decision else ""
                    ),
                    "reviewer_name": decision["reviewer_name"] if decision else "",
                    "reviewer_role": decision["reviewer_role"] if decision else "",
                    "notes": decision["notes"] if decision else "",
                    "revision": decision["revision"] if decision else 0,
                    "decided_at": decision["decided_at"] if decision else "",
                    "title": record.get("title", ""),
                    "abstract": record.get("abstract", ""),
                    "year": record.get("year", ""),
                    "doi": record.get("doi", ""),
                    "pmid": record.get("pmid", ""),
                    "pmcid": record.get("pmcid", ""),
                    "url": record.get("url", ""),
                    "matched_providers": record.get("matched_providers", ""),
                }
            )

    resolved_export_id = export_id or f"screening_export_{uuid4().hex}"
    timestamp = created_at or _now_iso()
    build_dir = Path(str(build["manifest_path"])).parent
    export_dir = build_dir / "screening" / session_id / resolved_export_id
    decisions_path = export_dir / "article_screening_decisions.csv"
    duplicate_reviews_path = export_dir / "duplicate_review_decisions.csv"
    queue_path = export_dir / "screening_queue.csv"
    prisma_csv_path = export_dir / "prisma_by_article.csv"
    prisma_json_path = export_dir / "prisma_by_article.json"
    manifest_path = export_dir / "screening_manifest.json"

    decision_fields = [
        "decision_id",
        "session_id",
        "document_id",
        "article_id",
        "stage",
        "decision",
        "exclusion_reason",
        "reviewer_name",
        "reviewer_role",
        "notes",
        "revision",
        "decided_at",
    ]
    duplicate_fields = [
        "review_id",
        "session_id",
        "candidate_id",
        "decision",
        "retained_document_id",
        "removed_document_id",
        "reviewer_name",
        "reviewer_role",
        "notes",
        "revision",
        "decided_at",
    ]
    queue_fields = [
        "document_id",
        "article_id",
        "article_label",
        "stage",
        "decision",
        "exclusion_reason",
        "reviewer_name",
        "reviewer_role",
        "notes",
        "revision",
        "decided_at",
        "title",
        "abstract",
        "year",
        "doi",
        "pmid",
        "pmcid",
        "url",
        "matched_providers",
    ]
    prisma_rows = []
    for row in summary["articles"]:
        export_row = dict(row)
        export_row["exclusion_reasons"] = json.dumps(
            export_row["exclusion_reasons"],
            ensure_ascii=False,
            sort_keys=True,
        )
        prisma_rows.append(export_row)
    prisma_fields = [
        "article_id",
        "article_number",
        "article_label",
        "stage",
        "records_after_automatic_deduplication",
        "human_duplicates_removed",
        "records_available_for_screening",
        "records_screened",
        "records_included",
        "records_excluded",
        "records_maybe",
        "records_pending",
        "exclusion_reasons",
        "prisma_eligible",
        "prisma_records_screened",
        "prisma_records_excluded",
        "prisma_reports_sought_for_retrieval",
    ]

    hashes = {
        "article_screening_decisions_sha256": _atomic_csv(
            decisions_path,
            decisions,
            decision_fields,
        ),
        "duplicate_review_decisions_sha256": _atomic_csv(
            duplicate_reviews_path,
            duplicate_reviews,
            duplicate_fields,
        ),
        "screening_queue_sha256": _atomic_csv(
            queue_path,
            queue_rows,
            queue_fields,
        ),
        "prisma_by_article_csv_sha256": _atomic_csv(
            prisma_csv_path,
            prisma_rows,
            prisma_fields,
        ),
        "prisma_by_article_json_sha256": _atomic_json(
            prisma_json_path,
            summary,
        ),
    }
    manifest = {
        "export_id": resolved_export_id,
        "session_id": session_id,
        "build_id": session["build_id"],
        "version_id": build["version_id"],
        "created_at": timestamp,
        "stage": stage,
        "status": "SUCCEEDED",
        "summary": summary,
        "inputs": {
            "corpus_manifest_path": build["manifest_path"],
            "corpus_manifest_sha256": build["manifest_sha256"],
            "master_records_path": build["master_jsonl_path"],
            "master_records_sha256": (
                (corpus_manifest.get("outputs") or {}).get(
                    "master_records_sha256", ""
                )
            ),
        },
        "outputs": {
            "decisions_csv_path": str(decisions_path),
            "duplicate_reviews_csv_path": str(duplicate_reviews_path),
            "queue_csv_path": str(queue_path),
            "prisma_csv_path": str(prisma_csv_path),
            "prisma_json_path": str(prisma_json_path),
            **hashes,
        },
        "governance": {
            "human_decisions_are_authoritative": True,
            "same_document_may_be_included_in_multiple_articles": True,
            "title_year_candidates_require_human_review": True,
            "exclusion_requires_reason": True,
            "screening_decisions_are_append_only_revisions": True,
        },
    }
    manifest_sha256 = _atomic_json(manifest_path, manifest)
    paths = {
        "decisions_csv_path": str(decisions_path),
        "duplicate_reviews_csv_path": str(duplicate_reviews_path),
        "queue_csv_path": str(queue_path),
        "prisma_csv_path": str(prisma_csv_path),
        "prisma_json_path": str(prisma_json_path),
        "manifest_path": str(manifest_path),
    }
    export_row = record_screening_export(
        db_path,
        session_id=session_id,
        effective_documents=summary["effective_documents"],
        human_duplicates_removed=summary["human_duplicates_removed"],
        paths=paths,
        manifest_sha256=manifest_sha256,
        export_id=resolved_export_id,
        created_at=timestamp,
    )
    return {
        **export_row,
        "summary": summary,
        "paths": paths,
        "hashes": hashes,
    }
