"""Review Control Center service: human review state joined to the rank-blind context bundle.

Machine state (routes, profiles, document class, retrieval status) and human review state are kept
strictly separate here. The queue never exposes Bank rank/score/tier or machine relevance, and a
human `REVIEWED` state is never rendered or reported as scientific inclusion.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import article1_context_index as context_index
import human_review_store as review_store


QUEUE_MAX_PAGE = 100
GUARDRAIL = (
    "Human review progress over a reading queue. REVIEWED means read, not included. Route "
    "membership, document class, domains and full-text status remain navigation signals, not "
    "eligibility, quality, risk of bias, certainty or PRISMA decisions."
)


def _route_bucket(routes: Sequence[str]) -> str:
    if "B-NORM" in routes and "C-STRUCT" in routes:
        return "overlap"
    if "B-NORM" in routes:
        return "B-NORM"
    if "C-STRUCT" in routes:
        return "C-STRUCT"
    return "unrouted"


def _empty_counter() -> dict[str, int]:
    return {status: 0 for status in review_store.REVIEW_STATUSES}


def _tally(rows: Sequence[Mapping[str, Any]], states: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    counts = _empty_counter()
    for row in rows:
        state = states.get(row["document_id"])
        counts[str((state or {}).get("status") or "NOT_STARTED")] += 1
    return counts


def review_status(
    *,
    context: context_index.Article1Context,
    states: Mapping[str, Mapping[str, Any]],
    route: str = "all",
    document_class: str = "",
    domain: str = "",
) -> dict[str, Any]:
    rows = context.select(route=route, document_class=document_class, domain=domain)
    totals = _tally(rows, states)

    by_route: dict[str, dict[str, Any]] = {}
    for bucket in ("B-NORM", "C-STRUCT", "overlap", "unrouted"):
        bucket_rows = [row for row in rows if _route_bucket(row["routes"]) == bucket]
        counts = _tally(bucket_rows, states)
        touched = len(bucket_rows) - counts["NOT_STARTED"]
        by_route[bucket] = {
            "queue": len(bucket_rows),
            "counts": counts,
            "reviewed": counts["REVIEWED"] + counts["RESOLVED"],
            "started": touched,
        }

    by_class: list[dict[str, Any]] = []
    for key in context.document_classes:
        class_rows = [row for row in rows if row["document_class"] == key]
        if not class_rows:
            continue
        by_class.append(
            {
                "key": key,
                "label": context_index.document_class_label(key),
                "queue": len(class_rows),
                "counts": _tally(class_rows, states),
            }
        )

    reviewer_counter: Counter[str] = Counter()
    reviewer_status: dict[str, Counter[str]] = {}
    for state in states.values():
        for reviewer in state.get("reviewers") or []:
            reviewer_id = str(reviewer.get("reviewer_id") or "")
            if not reviewer_id:
                continue
            reviewer_counter[reviewer_id] += 1
            reviewer_status.setdefault(reviewer_id, Counter())[str(reviewer.get("status"))] += 1

    return {
        "status": "ready",
        "universe": {
            "label": context_index.UNIVERSE_LABEL,
            "documents": len(context.records),
            "queue": len(rows),
        },
        "filters": {"route": route, "document_class": document_class, "domain": domain},
        "totals": {
            "queue": len(rows),
            "counts": totals,
            "reviewed": totals["REVIEWED"] + totals["RESOLVED"],
            "not_started": totals["NOT_STARTED"],
            "conflicts": totals["CONFLICT"],
            "adjudication_required": totals["ADJUDICATION_REQUIRED"],
            "resolved": totals["RESOLVED"],
        },
        "by_route": by_route,
        "by_document_class": by_class,
        "by_reviewer": [
            {
                "reviewer_id": reviewer_id,
                "documents": reviewer_counter[reviewer_id],
                "counts": dict(sorted(reviewer_status[reviewer_id].items())),
            }
            for reviewer_id in sorted(reviewer_counter)
        ],
        "vocabulary": {
            "statuses": list(review_store.REVIEW_STATUSES),
            "decisions": list(review_store.REVIEW_DECISIONS),
            "stages": list(review_store.REVIEW_STAGES),
        },
        "provenance": context.provenance(),
        "guardrail": GUARDRAIL,
    }


def review_queue(
    *,
    context: context_index.Article1Context,
    states: Mapping[str, Mapping[str, Any]],
    route: str = "all",
    document_class: str = "",
    domain: str = "",
    full_text_status: str = "",
    review_status_filter: str = "",
    reviewer_id: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows = context.select(
        route=route,
        document_class=document_class,
        domain=domain,
        full_text_status=full_text_status,
    )
    if review_status_filter:
        wanted = review_status_filter.strip().upper()
        if wanted not in review_store.REVIEW_STATUSES:
            raise ValueError(f"unknown review status filter: {review_status_filter!r}")
        rows = [
            row
            for row in rows
            if str((states.get(row["document_id"]) or {}).get("status") or "NOT_STARTED") == wanted
        ]
    if reviewer_id:
        wanted_reviewer = reviewer_id.strip()
        rows = [
            row
            for row in rows
            if any(
                str(entry.get("reviewer_id")) == wanted_reviewer
                for entry in (states.get(row["document_id"]) or {}).get("reviewers") or []
            )
        ]

    rows = sorted(rows, key=lambda row: (-(row["year"] or 0), row["document_id"]))
    page_limit = max(1, min(int(limit), QUEUE_MAX_PAGE))
    page_offset = max(0, int(offset))
    page = rows[page_offset : page_offset + page_limit]
    return {
        "status": "ready",
        "total_filtered": len(rows),
        "page_size": len(page),
        "offset": page_offset,
        "next_offset": page_offset + page_limit if page_offset + page_limit < len(rows) else None,
        "max_page_size": QUEUE_MAX_PAGE,
        "filters": {
            "route": route,
            "document_class": document_class,
            "domain": domain,
            "full_text_status": full_text_status,
            "review_status": review_status_filter,
            "reviewer_id": reviewer_id,
        },
        "documents": [
            {
                "document_id": row["document_id"],
                "title": row["title"],
                "year": row["year"],
                "document_class": row["document_class"],
                "document_class_label": context_index.document_class_label(row["document_class"]),
                "routes": row["routes"],
                "route_bucket": _route_bucket(row["routes"]),
                "domains": row["domains"],
                "source_provider": row["source_provider"],
                "full_text_status": row["full_text_status"],
                "review": states.get(row["document_id"])
                or {"status": "NOT_STARTED", "reviewers": [], "events": 0},
            }
            for row in page
        ],
        "machine_signals_in_queue": False,
        "provenance": context.provenance(),
        "guardrail": GUARDRAIL,
    }


def conflicts(
    *,
    context: context_index.Article1Context,
    states: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Documents whose independent human reviewers disagree, with both sides preserved."""
    rows: list[dict[str, Any]] = []
    for document_id, state in sorted(states.items()):
        if not (state.get("conflict") or state.get("adjudication_required")):
            continue
        record = context.get(document_id)
        rows.append(
            {
                "document_id": document_id,
                "title": (record or {}).get("title") or "",
                "year": (record or {}).get("year"),
                "routes": (record or {}).get("routes") or [],
                "status": state.get("status"),
                "reviewers": state.get("reviewers") or [],
                "adjudication_required": bool(state.get("adjudication_required")),
                "resolved": state.get("status") == "RESOLVED",
                "last_event_at": state.get("last_event_at"),
            }
        )
    # Open conflicts first; resolved ones stay visible so the adjudication trail is not hidden.
    return sorted(rows, key=lambda row: (row["resolved"], row["document_id"]))
