"""Full-text retrieval, eligibility assessment, and PRISMA export services."""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.review.article_screening import (
    effective_master_records,
    load_verified_master_records,
)
from nutev.review.article_screening_ledger import (
    get_screening_session,
    list_article_catalog,
    list_latest_article_screening_decisions,
)
from nutev.review.full_text_assessment_ledger import (
    FULL_TEXT_EXCLUSION_REASONS,
    TERMINAL_NOT_RETRIEVED,
    list_latest_full_text_eligibility_decisions,
    list_latest_full_text_retrievals,
    record_full_text_eligibility_decision,
    record_full_text_export,
    record_full_text_retrieval,
)
from nutev.search.strategy_registry import get_strategy_version

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
TITLE_ABSTRACT_ELIGIBLE = ("INCLUDE", "MAYBE")


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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return _sha256_file(path)


def _session_context(
    db_path: Path,
    session_id: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    session = get_screening_session(db_path, session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")
    build, records, manifest = load_verified_master_records(
        db_path,
        build_id=str(session["build_id"]),
    )
    return session, build, records, manifest


def _candidate_map(
    db_path: Path,
    *,
    session_id: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    effective, _ = effective_master_records(db_path, session_id=session_id)
    by_document = {str(row["document_id"]): row for row in effective}
    active_articles = {
        str(row["article_id"])
        for row in list_article_catalog(db_path, active_only=True)
    }
    decisions = list_latest_article_screening_decisions(
        db_path,
        session_id=session_id,
        stage="TITLE_ABSTRACT",
    )
    candidates: dict[str, dict[str, str]] = {}
    for decision in decisions:
        document_id = str(decision["document_id"])
        article_id = str(decision["article_id"])
        if (
            document_id in by_document
            and article_id in active_articles
            and decision["decision"] in TITLE_ABSTRACT_ELIGIBLE
        ):
            candidates.setdefault(document_id, {})[article_id] = str(decision["decision"])
    return by_document, candidates


def _artifact_integrity(retrieval: dict[str, Any] | None) -> str:
    if not retrieval or retrieval.get("status") != "AVAILABLE":
        return "NOT_APPLICABLE"
    artifact_path = str(retrieval.get("artifact_path") or "").strip()
    artifact_sha = str(retrieval.get("artifact_sha256") or "").strip()
    if not artifact_path:
        return "EXTERNAL_SOURCE"
    path = Path(artifact_path)
    if not path.is_file():
        return "MISSING"
    if artifact_sha and _sha256_file(path) != artifact_sha:
        return "MISMATCH"
    return "OK"


def _validate_available_artifact(retrieval: dict[str, Any]) -> None:
    integrity = _artifact_integrity(retrieval)
    if integrity in {"MISSING", "MISMATCH"}:
        raise ValueError(
            f"full-text artifact integrity is {integrity.lower()} for "
            f"{retrieval['document_id']}"
        )


def full_text_retrieval_queue(
    db_path: Path,
    *,
    session_id: str,
    status_filter: str = "ALL",
) -> list[dict[str, Any]]:
    by_document, candidates = _candidate_map(db_path, session_id=session_id)
    retrievals = {
        str(row["document_id"]): row
        for row in list_latest_full_text_retrievals(db_path, session_id=session_id)
    }
    article_catalog = {
        str(row["article_id"]): row
        for row in list_article_catalog(db_path, active_only=False)
    }
    normalized_filter = status_filter.strip().upper()
    allowed = {"ALL", "PENDING", "AVAILABLE", "REQUESTED", *TERMINAL_NOT_RETRIEVED}
    if normalized_filter not in allowed:
        raise ValueError(f"status_filter must be one of {sorted(allowed)}")

    queue: list[dict[str, Any]] = []
    for document_id, article_decisions in candidates.items():
        record = by_document[document_id]
        retrieval = retrievals.get(document_id)
        status = str(retrieval["status"]) if retrieval else "PENDING"
        if normalized_filter != "ALL" and status != normalized_filter:
            continue
        target_articles = sorted(article_decisions)
        target_labels = [
            str(article_catalog.get(article_id, {}).get("label") or article_id)
            for article_id in target_articles
        ]
        existing_artifact = record.get("artifact_paths")
        suggested = "AVAILABLE" if (
            record.get("download_status") in {"pdf", "html_snapshot"}
            or existing_artifact not in (None, "", {}, [])
        ) else "PENDING"
        queue.append(
            {
                **record,
                "target_article_ids": "|".join(target_articles),
                "target_article_labels": "|".join(target_labels),
                "title_abstract_decisions": json.dumps(
                    article_decisions,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "retrieval_status": status,
                "retrieval_id": str(retrieval["retrieval_id"]) if retrieval else "",
                "retrieval_revision": int(retrieval["revision"]) if retrieval else 0,
                "retrieval_source_url": str(retrieval["source_url"]) if retrieval else "",
                "retrieval_artifact_path": str(retrieval["artifact_path"]) if retrieval else "",
                "retrieval_artifact_sha256": str(retrieval["artifact_sha256"]) if retrieval else "",
                "retrieval_content_type": str(retrieval["content_type"]) if retrieval else "",
                "retrieval_notes": str(retrieval["notes"]) if retrieval else "",
                "retrieval_reviewer_name": str(retrieval["reviewer_name"]) if retrieval else "",
                "retrieval_reviewer_role": str(retrieval["reviewer_role"]) if retrieval else "",
                "retrieval_decided_at": str(retrieval["decided_at"]) if retrieval else "",
                "artifact_integrity": _artifact_integrity(retrieval),
                "system_suggested_retrieval_status": suggested,
            }
        )
    queue.sort(
        key=lambda row: (
            row["retrieval_status"] != "PENDING",
            str(row.get("title") or "").casefold(),
            str(row["document_id"]),
        )
    )
    return queue


def save_full_text_retrieval(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    status: str,
    reviewer_name: str,
    reviewer_role: str,
    source_url: str = "",
    artifact_path: str = "",
    content_type: str = "",
    notes: str = "",
) -> dict[str, Any]:
    queue = {
        str(row["document_id"]): row
        for row in full_text_retrieval_queue(db_path, session_id=session_id)
    }
    record = queue.get(document_id)
    if record is None:
        raise ValueError("document is not eligible for full-text retrieval")

    resolved_path = artifact_path.strip()
    artifact_sha = ""
    resolved_type = content_type.strip()
    if resolved_path:
        path = Path(resolved_path)
        if not path.is_absolute():
            project_root = Path(db_path).parent.parent
            path = (project_root / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"full-text artifact not found: {path}")
        resolved_path = str(path)
        artifact_sha = _sha256_file(path)
        if not resolved_type:
            resolved_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    resolved_url = source_url.strip()
    return record_full_text_retrieval(
        db_path,
        session_id=session_id,
        document_id=document_id,
        status=status,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        source_url=resolved_url,
        artifact_path=resolved_path,
        artifact_sha256=artifact_sha,
        content_type=resolved_type,
        notes=notes,
    )


def full_text_assessment_queue(
    db_path: Path,
    *,
    session_id: str,
    article_id: str,
    status_filter: str = "ALL",
) -> list[dict[str, Any]]:
    by_document, candidates = _candidate_map(db_path, session_id=session_id)
    article_key = article_id.strip().lower()
    candidate_ids = {
        document_id
        for document_id, article_decisions in candidates.items()
        if article_key in article_decisions
    }
    retrievals = {
        str(row["document_id"]): row
        for row in list_latest_full_text_retrievals(db_path, session_id=session_id)
    }
    decisions = {
        str(row["document_id"]): row
        for row in list_latest_full_text_eligibility_decisions(
            db_path,
            session_id=session_id,
            article_id=article_key,
        )
    }
    allowed = {
        "ALL",
        "WAITING_RETRIEVAL",
        "NOT_RETRIEVED",
        "PENDING_ELIGIBILITY",
        "INCLUDE",
        "EXCLUDE",
        "MAYBE",
    }
    normalized_filter = status_filter.strip().upper()
    if normalized_filter not in allowed:
        raise ValueError(f"status_filter must be one of {sorted(allowed)}")

    queue: list[dict[str, Any]] = []
    for document_id in candidate_ids:
        record = by_document[document_id]
        retrieval = retrievals.get(document_id)
        retrieval_status = str(retrieval["status"]) if retrieval else "PENDING"
        eligibility = decisions.get(document_id)
        if eligibility:
            workflow_status = str(eligibility["decision"])
        elif retrieval_status == "AVAILABLE":
            workflow_status = "PENDING_ELIGIBILITY"
        elif retrieval_status in TERMINAL_NOT_RETRIEVED:
            workflow_status = "NOT_RETRIEVED"
        else:
            workflow_status = "WAITING_RETRIEVAL"
        if normalized_filter != "ALL" and workflow_status != normalized_filter:
            continue
        queue.append(
            {
                **record,
                "article_id": article_key,
                "title_abstract_decision": candidates[document_id][article_key],
                "retrieval_status": retrieval_status,
                "retrieval_source_url": str(retrieval["source_url"]) if retrieval else "",
                "retrieval_artifact_path": str(retrieval["artifact_path"]) if retrieval else "",
                "retrieval_artifact_sha256": str(retrieval["artifact_sha256"]) if retrieval else "",
                "artifact_integrity": _artifact_integrity(retrieval),
                "full_text_status": workflow_status,
                "full_text_decision_id": str(eligibility["decision_id"]) if eligibility else "",
                "full_text_revision": int(eligibility["revision"]) if eligibility else 0,
                "full_text_exclusion_reason": str(eligibility["exclusion_reason"]) if eligibility else "",
                "full_text_notes": str(eligibility["notes"]) if eligibility else "",
                "full_text_reviewer_name": str(eligibility["reviewer_name"]) if eligibility else "",
                "full_text_reviewer_role": str(eligibility["reviewer_role"]) if eligibility else "",
                "full_text_decided_at": str(eligibility["decided_at"]) if eligibility else "",
            }
        )
    queue.sort(
        key=lambda row: (
            row["full_text_status"] != "PENDING_ELIGIBILITY",
            str(row.get("title") or "").casefold(),
            str(row["document_id"]),
        )
    )
    return queue


def save_full_text_eligibility_decision(
    db_path: Path,
    *,
    session_id: str,
    document_id: str,
    article_id: str,
    decision: str,
    reviewer_name: str,
    reviewer_role: str,
    exclusion_reason: str = "",
    notes: str = "",
) -> dict[str, Any]:
    queue = {
        str(row["document_id"]): row
        for row in full_text_assessment_queue(
            db_path,
            session_id=session_id,
            article_id=article_id,
        )
    }
    row = queue.get(document_id)
    if row is None:
        raise ValueError("document is not a title/abstract candidate for this article")
    if row["retrieval_status"] != "AVAILABLE":
        raise ValueError("full-text eligibility requires an AVAILABLE report")
    retrievals = {
        str(item["document_id"]): item
        for item in list_latest_full_text_retrievals(db_path, session_id=session_id)
    }
    _validate_available_artifact(retrievals[document_id])
    return record_full_text_eligibility_decision(
        db_path,
        session_id=session_id,
        document_id=document_id,
        article_id=article_id,
        decision=decision,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        exclusion_reason=exclusion_reason,
        notes=notes,
    )


def summarize_full_text_assessment(
    db_path: Path,
    *,
    session_id: str,
) -> dict[str, Any]:
    session, build, _, _ = _session_context(db_path, session_id)
    version = get_strategy_version(db_path, str(build["version_id"]))
    if version is None:
        raise ValueError("strategy version for corpus build is missing")
    prisma_eligible = bool(version["prisma_eligible"])
    by_document, candidates = _candidate_map(db_path, session_id=session_id)
    retrievals = {
        str(row["document_id"]): row
        for row in list_latest_full_text_retrievals(db_path, session_id=session_id)
    }
    eligibility_rows = list_latest_full_text_eligibility_decisions(
        db_path,
        session_id=session_id,
    )
    eligibility = {
        (str(row["document_id"]), str(row["article_id"])): row
        for row in eligibility_rows
    }
    articles = list_article_catalog(db_path, active_only=True)
    article_summaries: list[dict[str, Any]] = []

    for article in articles:
        article_id = str(article["article_id"])
        document_ids = sorted(
            document_id
            for document_id, article_decisions in candidates.items()
            if article_id in article_decisions
        )
        retrieved_ids = {
            document_id
            for document_id in document_ids
            if retrievals.get(document_id, {}).get("status") == "AVAILABLE"
        }
        not_retrieved_ids = {
            document_id
            for document_id in document_ids
            if retrievals.get(document_id, {}).get("status") in TERMINAL_NOT_RETRIEVED
        }
        pending_retrieval_ids = set(document_ids) - retrieved_ids - not_retrieved_ids
        decisions = [
            eligibility[(document_id, article_id)]
            for document_id in document_ids
            if (document_id, article_id) in eligibility
        ]
        include_count = sum(row["decision"] == "INCLUDE" for row in decisions)
        exclude_count = sum(row["decision"] == "EXCLUDE" for row in decisions)
        maybe_count = sum(row["decision"] == "MAYBE" for row in decisions)
        assessed_count = len(decisions)
        pending_eligibility = max(0, len(retrieved_ids) - assessed_count)
        reasons = {
            reason: sum(
                row["decision"] == "EXCLUDE" and row["exclusion_reason"] == reason
                for row in decisions
            )
            for reason in FULL_TEXT_EXCLUSION_REASONS
        }
        reasons = {key: value for key, value in reasons.items() if value}
        article_summaries.append(
            {
                "article_id": article_id,
                "article_number": article["article_number"],
                "article_label": article["label"],
                "reports_sought_for_retrieval": len(document_ids),
                "reports_retrieved": len(retrieved_ids),
                "reports_not_retrieved": len(not_retrieved_ids),
                "reports_pending_retrieval": len(pending_retrieval_ids),
                "reports_assessed_for_eligibility": assessed_count,
                "reports_excluded_at_full_text": exclude_count,
                "reports_included": include_count,
                "reports_maybe": maybe_count,
                "reports_pending_eligibility": pending_eligibility,
                "full_text_exclusion_reasons": reasons,
                "prisma_eligible": prisma_eligible,
                "prisma_reports_sought_for_retrieval": len(document_ids) if prisma_eligible else 0,
                "prisma_reports_not_retrieved": len(not_retrieved_ids) if prisma_eligible else 0,
                "prisma_reports_assessed_for_eligibility": assessed_count if prisma_eligible else 0,
                "prisma_reports_excluded": exclude_count if prisma_eligible else 0,
                "prisma_studies_included": include_count if prisma_eligible else 0,
            }
        )

    distinct_sought = set(candidates)
    distinct_retrieved = {
        document_id
        for document_id in distinct_sought
        if retrievals.get(document_id, {}).get("status") == "AVAILABLE"
    }
    distinct_not_retrieved = {
        document_id
        for document_id in distinct_sought
        if retrievals.get(document_id, {}).get("status") in TERMINAL_NOT_RETRIEVED
    }
    distinct_included = {
        str(row["document_id"])
        for row in eligibility_rows
        if row["decision"] == "INCLUDE"
    }
    return {
        "session_id": session_id,
        "build_id": session["build_id"],
        "version_id": build["version_id"],
        "search_run_id": build["run_id"],
        "search_type": version["search_type"],
        "prisma_eligible": prisma_eligible,
        "distinct_reports_sought": len(distinct_sought),
        "distinct_reports_retrieved": len(distinct_retrieved),
        "distinct_reports_not_retrieved": len(distinct_not_retrieved),
        "distinct_reports_pending_retrieval": (
            len(distinct_sought) - len(distinct_retrieved) - len(distinct_not_retrieved)
        ),
        "distinct_documents_included": len(distinct_included),
        "article_inclusions": sum(row["reports_included"] for row in article_summaries),
        "articles": article_summaries,
        "candidate_document_ids": sorted(distinct_sought),
        "record_count": len(by_document),
    }


def export_full_text_snapshot(
    db_path: Path,
    *,
    session_id: str,
    export_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    session, build, _, corpus_manifest = _session_context(db_path, session_id)
    summary = summarize_full_text_assessment(db_path, session_id=session_id)
    retrievals = list_latest_full_text_retrievals(db_path, session_id=session_id)
    for retrieval in retrievals:
        if retrieval["status"] == "AVAILABLE":
            _validate_available_artifact(retrieval)
    eligibility = list_latest_full_text_eligibility_decisions(
        db_path,
        session_id=session_id,
    )
    articles = {
        str(row["article_id"]): row
        for row in list_article_catalog(db_path, active_only=False)
    }
    queue_rows: list[dict[str, Any]] = []
    included_rows: list[dict[str, Any]] = []
    for article_id in sorted(articles):
        for row in full_text_assessment_queue(
            db_path,
            session_id=session_id,
            article_id=article_id,
        ):
            export_row = {
                "document_id": row["document_id"],
                "article_id": article_id,
                "article_label": articles[article_id]["label"],
                "title_abstract_decision": row["title_abstract_decision"],
                "retrieval_status": row["retrieval_status"],
                "artifact_integrity": row["artifact_integrity"],
                "full_text_status": row["full_text_status"],
                "full_text_exclusion_reason": row["full_text_exclusion_reason"],
                "full_text_notes": row["full_text_notes"],
                "full_text_revision": row["full_text_revision"],
                "full_text_reviewer_name": row["full_text_reviewer_name"],
                "full_text_reviewer_role": row["full_text_reviewer_role"],
                "full_text_decided_at": row["full_text_decided_at"],
                "title": row.get("title", ""),
                "year": row.get("year", ""),
                "doi": row.get("doi", ""),
                "pmid": row.get("pmid", ""),
                "pmcid": row.get("pmcid", ""),
                "url": row.get("url", ""),
                "matched_providers": row.get("matched_providers", ""),
                "retrieval_source_url": row["retrieval_source_url"],
                "retrieval_artifact_path": row["retrieval_artifact_path"],
                "retrieval_artifact_sha256": row["retrieval_artifact_sha256"],
            }
            queue_rows.append(export_row)
            if row["full_text_status"] == "INCLUDE":
                included_rows.append(export_row)

    resolved_export_id = export_id or f"full_text_export_{uuid4().hex}"
    timestamp = created_at or _now_iso()
    build_dir = Path(str(build["manifest_path"])).parent
    export_dir = build_dir / "full_text" / session_id / resolved_export_id
    retrieval_path = export_dir / "full_text_retrieval_reviews.csv"
    eligibility_path = export_dir / "full_text_eligibility_decisions.csv"
    queue_path = export_dir / "full_text_queue.csv"
    included_path = export_dir / "included_documents_by_article.csv"
    prisma_csv_path = export_dir / "prisma_full_text_by_article.csv"
    prisma_json_path = export_dir / "prisma_full_text_by_article.json"
    manifest_path = export_dir / "full_text_manifest.json"

    retrieval_fields = [
        "retrieval_id", "session_id", "document_id", "status", "source_url",
        "artifact_path", "artifact_sha256", "content_type", "reviewer_name",
        "reviewer_role", "notes", "revision", "decided_at",
    ]
    eligibility_fields = [
        "decision_id", "session_id", "document_id", "article_id", "decision",
        "exclusion_reason", "reviewer_name", "reviewer_role", "notes",
        "revision", "decided_at",
    ]
    queue_fields = [
        "document_id", "article_id", "article_label", "title_abstract_decision",
        "retrieval_status", "artifact_integrity", "full_text_status",
        "full_text_exclusion_reason", "full_text_notes", "full_text_revision",
        "full_text_reviewer_name", "full_text_reviewer_role", "full_text_decided_at",
        "title", "year", "doi", "pmid", "pmcid", "url", "matched_providers",
        "retrieval_source_url", "retrieval_artifact_path", "retrieval_artifact_sha256",
    ]
    prisma_rows: list[dict[str, Any]] = []
    for row in summary["articles"]:
        output = dict(row)
        output["full_text_exclusion_reasons"] = json.dumps(
            output["full_text_exclusion_reasons"],
            ensure_ascii=False,
            sort_keys=True,
        )
        prisma_rows.append(output)
    prisma_fields = [
        "article_id", "article_number", "article_label",
        "reports_sought_for_retrieval", "reports_retrieved",
        "reports_not_retrieved", "reports_pending_retrieval",
        "reports_assessed_for_eligibility", "reports_excluded_at_full_text",
        "reports_included", "reports_maybe", "reports_pending_eligibility",
        "full_text_exclusion_reasons", "prisma_eligible",
        "prisma_reports_sought_for_retrieval", "prisma_reports_not_retrieved",
        "prisma_reports_assessed_for_eligibility", "prisma_reports_excluded",
        "prisma_studies_included",
    ]

    hashes = {
        "retrieval_csv_sha256": _atomic_csv(retrieval_path, retrievals, retrieval_fields),
        "eligibility_csv_sha256": _atomic_csv(eligibility_path, eligibility, eligibility_fields),
        "queue_csv_sha256": _atomic_csv(queue_path, queue_rows, queue_fields),
        "included_csv_sha256": _atomic_csv(included_path, included_rows, queue_fields),
        "prisma_csv_sha256": _atomic_csv(prisma_csv_path, prisma_rows, prisma_fields),
        "prisma_json_sha256": _atomic_json(prisma_json_path, summary),
    }
    manifest = {
        "export_id": resolved_export_id,
        "session_id": session_id,
        "build_id": session["build_id"],
        "version_id": build["version_id"],
        "created_at": timestamp,
        "status": "SUCCEEDED",
        "summary": summary,
        "inputs": {
            "corpus_manifest_path": build["manifest_path"],
            "corpus_manifest_sha256": build["manifest_sha256"],
            "master_records_path": build["master_jsonl_path"],
            "master_records_sha256": (
                (corpus_manifest.get("outputs") or {}).get("master_records_sha256", "")
            ),
        },
        "outputs": {
            "retrieval_csv_path": str(retrieval_path),
            "eligibility_csv_path": str(eligibility_path),
            "queue_csv_path": str(queue_path),
            "included_csv_path": str(included_path),
            "prisma_csv_path": str(prisma_csv_path),
            "prisma_json_path": str(prisma_json_path),
            **hashes,
        },
        "governance": {
            "retrieval_recorded_once_per_document": True,
            "eligibility_independent_per_article": True,
            "human_decisions_are_authoritative": True,
            "exclusion_requires_reason": True,
            "revisions_are_append_only": True,
            "available_local_artifacts_are_checksum_verified": True,
        },
    }
    manifest_sha = _atomic_json(manifest_path, manifest)
    paths = {
        "retrieval_csv_path": str(retrieval_path),
        "eligibility_csv_path": str(eligibility_path),
        "queue_csv_path": str(queue_path),
        "included_csv_path": str(included_path),
        "prisma_csv_path": str(prisma_csv_path),
        "prisma_json_path": str(prisma_json_path),
        "manifest_path": str(manifest_path),
    }
    export_row = record_full_text_export(
        db_path,
        session_id=session_id,
        distinct_reports_sought=summary["distinct_reports_sought"],
        distinct_reports_retrieved=summary["distinct_reports_retrieved"],
        distinct_reports_not_retrieved=summary["distinct_reports_not_retrieved"],
        article_inclusions=summary["article_inclusions"],
        paths=paths,
        manifest_sha256=manifest_sha,
        export_id=resolved_export_id,
        created_at=timestamp,
    )
    return {
        **export_row,
        "summary": summary,
        "paths": paths,
        "hashes": hashes,
    }
