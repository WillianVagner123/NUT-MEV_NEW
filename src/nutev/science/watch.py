"""Longitudinal/watch layer for NutEV topic and competency audits.

This module compares verified topic-audit snapshots over time. It detects operational
changes such as newly mapped documents, coverage gains/losses, freshness changes,
provider diversity changes, audit-flag changes and search-priority changes.

Watch events and cases are machine-operational artifacts. They are not scientific
claims, evidence quality, certainty, eligibility decisions, causal conclusions,
clinical recommendations or PRISMA events.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from nutev.audit_guardrails import sha256_file


class LongitudinalWatchError(RuntimeError):
    """Raised when longitudinal watch inputs are invalid or unverifiable."""


_PRIORITY_RANK = {
    "P1_HIGH": 1,
    "P2_MEDIUM": 2,
    "P3_LOW": 3,
    "P4_MONITOR": 4,
}


@dataclass(frozen=True, slots=True)
class WatchEvent:
    id: str
    event_type: str
    topic_id: str
    topic_kind: str
    direction: str
    before: Any
    after: Any
    basis: str
    document_id: str | None = None
    status: str = "machine_watch_event"


@dataclass(frozen=True, slots=True)
class WatchCase:
    id: str
    topic_id: str
    topic_kind: str
    watch_priority: str
    case_type: str
    trigger_event_ids: tuple[str, ...]
    action: str
    status: str = "review_required"
    feeds_prisma: bool = False
    auto_accepts_evidence: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LongitudinalWatchError(f"missing JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LongitudinalWatchError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LongitudinalWatchError(f"expected JSON object at {path}")
    return value


def _read_jsonl(path: Path, *, label: str, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not path.is_file():
        raise LongitudinalWatchError(f"missing {label} JSONL: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LongitudinalWatchError(
                    f"invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise LongitudinalWatchError(
                    f"non-object JSONL row at {path}:{line_number}"
                )
            rows.append(value)
    if not rows and not allow_empty:
        raise LongitudinalWatchError(f"{label} JSONL is empty: {path}")
    return rows


def _atomic_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return sha256_file(path)


def _write_json(path: Path, value: Any) -> str:
    return _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        for row in rows
    )
    return _atomic_text(path, payload)


def _verify_topic_audit_inputs(
    topic_audits_jsonl: Path,
    topic_assignments_jsonl: Path,
    topic_audit_manifest: Path,
) -> tuple[dict[str, Any], dict[str, str]]:
    manifest = _read_json(topic_audit_manifest)
    if (
        manifest.get("audit_type") != "NUTEV_TOPIC_COMPETENCY_AUDIT"
        or manifest.get("status") != "PASS"
    ):
        raise LongitudinalWatchError(
            "topic audit manifest is not a passing NutEV topic/competency audit"
        )
    outputs = manifest.get("outputs") or {}
    if not isinstance(outputs, Mapping):
        raise LongitudinalWatchError("topic audit manifest outputs must be an object")
    expected_audits = str(
        ((outputs.get("topic_audits") or {}).get("sha256")) or ""
    ).strip().lower()
    expected_assignments = str(
        ((outputs.get("topic_assignments") or {}).get("sha256")) or ""
    ).strip().lower()
    if not expected_audits or not expected_assignments:
        raise LongitudinalWatchError(
            "topic audit manifest is missing audit/assignment SHA-256 values"
        )
    actual_audits = sha256_file(topic_audits_jsonl)
    actual_assignments = sha256_file(topic_assignments_jsonl)
    if actual_audits != expected_audits:
        raise LongitudinalWatchError(
            "topic audits SHA-256 mismatch: "
            f"expected {expected_audits}, got {actual_audits}"
        )
    if actual_assignments != expected_assignments:
        raise LongitudinalWatchError(
            "topic assignments SHA-256 mismatch: "
            f"expected {expected_assignments}, got {actual_assignments}"
        )
    profile = manifest.get("profile") or {}
    if not isinstance(profile, Mapping):
        raise LongitudinalWatchError("topic audit manifest profile must be an object")
    if not str(profile.get("profile_id") or "").strip():
        raise LongitudinalWatchError("topic audit manifest profile_id is missing")
    return manifest, {
        "topic_audits": actual_audits,
        "topic_assignments": actual_assignments,
        "topic_audit_manifest": sha256_file(topic_audit_manifest),
    }


def _index_audits(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        topic_id = str(row.get("topic_id") or "").strip()
        if not topic_id:
            raise LongitudinalWatchError("topic audit row missing topic_id")
        if topic_id in indexed:
            raise LongitudinalWatchError(f"duplicate topic audit row: {topic_id}")
        indexed[topic_id] = dict(row)
    return indexed


def _assignments_by_topic(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    seen_assignment_ids: set[str] = set()
    for row in rows:
        assignment_id = str(row.get("id") or "").strip()
        topic_id = str(row.get("topic_id") or "").strip()
        document_id = str(row.get("document_id") or "").strip()
        if not assignment_id or not topic_id or not document_id:
            raise LongitudinalWatchError(
                "topic assignment row requires id, topic_id and document_id"
            )
        if assignment_id in seen_assignment_ids:
            raise LongitudinalWatchError(
                f"duplicate topic assignment id: {assignment_id}"
            )
        seen_assignment_ids.add(assignment_id)
        grouped[topic_id].add(document_id)
    return {topic_id: tuple(sorted(ids)) for topic_id, ids in grouped.items()}


def build_watch_snapshot(
    topic_audits_jsonl: Path,
    topic_assignments_jsonl: Path,
    topic_audit_manifest: Path,
) -> dict[str, Any]:
    """Build a compact, verified longitudinal snapshot from one topic-audit run."""

    manifest, source_shas = _verify_topic_audit_inputs(
        topic_audits_jsonl,
        topic_assignments_jsonl,
        topic_audit_manifest,
    )
    audits = _index_audits(
        _read_jsonl(topic_audits_jsonl, label="topic audits")
    )
    assignments = _assignments_by_topic(
        _read_jsonl(
            topic_assignments_jsonl,
            label="topic assignments",
            allow_empty=True,
        )
    )
    unknown_assignment_topics = sorted(set(assignments) - set(audits))
    if unknown_assignment_topics:
        raise LongitudinalWatchError(
            "topic assignments reference unknown audit topics: "
            f"{unknown_assignment_topics[:5]}"
        )

    topic_states: dict[str, dict[str, Any]] = {}
    for topic_id in sorted(audits):
        audit = audits[topic_id]
        document_ids = assignments.get(topic_id, ())
        document_count = int(audit.get("document_count") or 0)
        if document_count != len(document_ids):
            raise LongitudinalWatchError(
                f"topic {topic_id} audit document_count={document_count} "
                f"does not match assignment count={len(document_ids)}"
            )
        providers_raw = audit.get("providers") or []
        flags_raw = audit.get("flags") or []
        if not isinstance(providers_raw, (list, tuple)):
            raise LongitudinalWatchError(
                f"topic {topic_id} providers must be a list"
            )
        if not isinstance(flags_raw, (list, tuple)):
            raise LongitudinalWatchError(f"topic {topic_id} flags must be a list")
        latest_year_raw = audit.get("latest_year")
        latest_year = int(latest_year_raw) if latest_year_raw not in (None, "") else None
        topic_states[topic_id] = {
            "topic_id": topic_id,
            "topic_kind": str(audit.get("topic_kind") or "topic"),
            "document_count": document_count,
            "document_ids": list(document_ids),
            "provider_count": int(audit.get("provider_count") or 0),
            "providers": sorted(str(value) for value in providers_raw),
            "full_text_count": int(audit.get("full_text_count") or 0),
            "semantic_count": int(audit.get("semantic_count") or 0),
            "relational_count": int(audit.get("relational_count") or 0),
            "latest_year": latest_year,
            "flags": sorted(str(value) for value in flags_raw),
            "active_search_priority": str(
                audit.get("active_search_priority") or "P4_MONITOR"
            ),
            "active_search_required": bool(audit.get("active_search_required")),
        }

    profile = manifest.get("profile") or {}
    return {
        "schema_version": 1,
        "snapshot_type": "NUTEV_LONGITUDINAL_TOPIC_SNAPSHOT",
        "created_at": _now(),
        "topic_audit_created_at": manifest.get("created_at"),
        "profile": {
            "profile_id": profile.get("profile_id"),
            "version": profile.get("version"),
            "status": profile.get("status"),
            "sha256": profile.get("sha256"),
        },
        "source": {
            "topic_audit_manifest": str(topic_audit_manifest),
            "source_sha256": source_shas,
        },
        "topics": topic_states,
        "guardrails": {
            "snapshot_is_operational_state": True,
            "topic_changes_are_not_scientific_claims": True,
            "document_addition_does_not_imply_importance": True,
            "document_removal_does_not_imply_retraction": True,
            "prisma_not_required": True,
        },
    }


def _verify_previous_snapshot(
    snapshot_path: Path,
    watch_manifest_path: Path,
) -> dict[str, Any]:
    manifest = _read_json(watch_manifest_path)
    if (
        manifest.get("watch_type") != "NUTEV_LONGITUDINAL_TOPIC_WATCH"
        or manifest.get("status") != "PASS"
    ):
        raise LongitudinalWatchError(
            "previous watch manifest is not a passing NutEV longitudinal watch manifest"
        )
    outputs = manifest.get("outputs") or {}
    expected = str(
        ((outputs.get("watch_snapshot") or {}).get("sha256")) or ""
    ).strip().lower()
    if not expected:
        raise LongitudinalWatchError(
            "previous watch manifest is missing watch_snapshot SHA-256"
        )
    actual = sha256_file(snapshot_path)
    if actual != expected:
        raise LongitudinalWatchError(
            f"previous watch snapshot SHA-256 mismatch: expected {expected}, got {actual}"
        )
    snapshot = _read_json(snapshot_path)
    if snapshot.get("snapshot_type") != "NUTEV_LONGITUDINAL_TOPIC_SNAPSHOT":
        raise LongitudinalWatchError("previous snapshot has unsupported snapshot_type")
    return snapshot


def _event(
    event_type: str,
    topic_id: str,
    topic_kind: str,
    direction: str,
    before: Any,
    after: Any,
    basis: str,
    *,
    document_id: str | None = None,
) -> WatchEvent:
    digest = sha256(
        json.dumps(
            {
                "event_type": event_type,
                "topic_id": topic_id,
                "document_id": document_id,
                "before": before,
                "after": after,
                "basis": basis,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:20]
    return WatchEvent(
        id=f"watch-event:{digest}",
        event_type=event_type,
        topic_id=topic_id,
        topic_kind=topic_kind,
        direction=direction,
        before=before,
        after=after,
        basis=basis,
        document_id=document_id,
    )


def _profile_comparability(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
) -> tuple[str, list[WatchEvent]]:
    previous_profile = previous.get("profile") or {}
    current_profile = current.get("profile") or {}
    previous_id = str(previous_profile.get("profile_id") or "")
    current_id = str(current_profile.get("profile_id") or "")
    previous_version = str(previous_profile.get("version") or "")
    current_version = str(current_profile.get("version") or "")
    previous_status = str(previous_profile.get("status") or "")
    current_status = str(current_profile.get("status") or "")
    events: list[WatchEvent] = []
    if previous_id != current_id:
        events.append(
            _event(
                "profile_changed",
                "__profile__",
                "registry",
                "changed",
                {"profile_id": previous_id, "version": previous_version},
                {"profile_id": current_id, "version": current_version},
                "different_profile_id_blocks_direct_topic_trend_comparison",
            )
        )
        return "incompatible", events
    comparability = "full"
    if previous_version != current_version:
        comparability = "limited_profile_version_changed"
        events.append(
            _event(
                "profile_version_changed",
                "__profile__",
                "registry",
                "changed",
                previous_version,
                current_version,
                "same_profile_id_but_version_changed",
            )
        )
    if previous_status != current_status:
        events.append(
            _event(
                "profile_status_changed",
                "__profile__",
                "registry",
                "changed",
                previous_status,
                current_status,
                "profile_lifecycle_status_changed",
            )
        )
    return comparability, events


def compare_watch_snapshots(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
) -> tuple[str, tuple[WatchEvent, ...]]:
    """Compare two snapshots without converting operational change into evidence truth."""

    if previous is None:
        baseline = _event(
            "baseline_created",
            "__watch__",
            "watch",
            "baseline",
            None,
            current.get("created_at"),
            "first_verified_watch_snapshot",
        )
        return "baseline", (baseline,)

    comparability, profile_events = _profile_comparability(previous, current)
    if comparability == "incompatible":
        return comparability, tuple(profile_events)

    previous_topics = previous.get("topics") or {}
    current_topics = current.get("topics") or {}
    if not isinstance(previous_topics, Mapping) or not isinstance(current_topics, Mapping):
        raise LongitudinalWatchError("watch snapshot topics must be objects")

    events: list[WatchEvent] = list(profile_events)
    metric_names = (
        "document_count",
        "provider_count",
        "full_text_count",
        "semantic_count",
        "relational_count",
    )

    for topic_id in sorted(set(previous_topics) | set(current_topics)):
        before = previous_topics.get(topic_id)
        after = current_topics.get(topic_id)
        if before is None:
            if not isinstance(after, Mapping):
                continue
            events.append(
                _event(
                    "topic_added",
                    topic_id,
                    str(after.get("topic_kind") or "topic"),
                    "added",
                    None,
                    dict(after),
                    "topic_present_only_in_current_snapshot",
                )
            )
            continue
        if after is None:
            if not isinstance(before, Mapping):
                continue
            events.append(
                _event(
                    "topic_removed",
                    topic_id,
                    str(before.get("topic_kind") or "topic"),
                    "removed",
                    dict(before),
                    None,
                    "topic_present_only_in_previous_snapshot",
                )
            )
            continue
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise LongitudinalWatchError(f"invalid topic state for {topic_id}")
        topic_kind = str(after.get("topic_kind") or before.get("topic_kind") or "topic")

        before_docs = set(str(value) for value in before.get("document_ids") or [])
        after_docs = set(str(value) for value in after.get("document_ids") or [])
        for document_id in sorted(after_docs - before_docs):
            events.append(
                _event(
                    "document_added",
                    topic_id,
                    topic_kind,
                    "increased",
                    False,
                    True,
                    "document_assignment_present_only_in_current_snapshot",
                    document_id=document_id,
                )
            )
        for document_id in sorted(before_docs - after_docs):
            events.append(
                _event(
                    "document_removed",
                    topic_id,
                    topic_kind,
                    "decreased",
                    True,
                    False,
                    "document_assignment_absent_from_current_snapshot; not a retraction claim",
                    document_id=document_id,
                )
            )

        for metric in metric_names:
            old_value = int(before.get(metric) or 0)
            new_value = int(after.get(metric) or 0)
            if old_value == new_value:
                continue
            direction = "increased" if new_value > old_value else "decreased"
            events.append(
                _event(
                    f"{metric}_changed",
                    topic_id,
                    topic_kind,
                    direction,
                    old_value,
                    new_value,
                    f"verified_topic_audit_metric:{metric}",
                )
            )

        before_providers = set(str(value) for value in before.get("providers") or [])
        after_providers = set(str(value) for value in after.get("providers") or [])
        for provider in sorted(after_providers - before_providers):
            events.append(
                _event(
                    "provider_added",
                    topic_id,
                    topic_kind,
                    "increased",
                    None,
                    provider,
                    "provider_present_only_in_current_topic_audit",
                )
            )
        for provider in sorted(before_providers - after_providers):
            events.append(
                _event(
                    "provider_removed",
                    topic_id,
                    topic_kind,
                    "decreased",
                    provider,
                    None,
                    "provider_absent_from_current_topic_audit",
                )
            )

        old_year = before.get("latest_year")
        new_year = after.get("latest_year")
        if old_year != new_year:
            direction = "changed"
            if old_year is None and new_year is not None:
                direction = "advanced"
            elif old_year is not None and new_year is not None:
                direction = "advanced" if int(new_year) > int(old_year) else "receded"
            events.append(
                _event(
                    "latest_year_changed",
                    topic_id,
                    topic_kind,
                    direction,
                    old_year,
                    new_year,
                    "verified_latest_publication_year_changed",
                )
            )

        before_flags = set(str(value) for value in before.get("flags") or [])
        after_flags = set(str(value) for value in after.get("flags") or [])
        for flag in sorted(after_flags - before_flags):
            events.append(
                _event(
                    "flag_added",
                    topic_id,
                    topic_kind,
                    "worsened",
                    None,
                    flag,
                    "topic_audit_gap_flag_newly_present",
                )
            )
        for flag in sorted(before_flags - after_flags):
            events.append(
                _event(
                    "flag_resolved",
                    topic_id,
                    topic_kind,
                    "improved",
                    flag,
                    None,
                    "topic_audit_gap_flag_no_longer_present",
                )
            )

        old_priority = str(before.get("active_search_priority") or "P4_MONITOR")
        new_priority = str(after.get("active_search_priority") or "P4_MONITOR")
        if old_priority != new_priority:
            old_rank = _PRIORITY_RANK.get(old_priority, 99)
            new_rank = _PRIORITY_RANK.get(new_priority, 99)
            if new_rank < old_rank:
                event_type = "priority_escalated"
                direction = "worsened"
            elif new_rank > old_rank:
                event_type = "priority_deescalated"
                direction = "improved"
            else:
                event_type = "priority_changed"
                direction = "changed"
            events.append(
                _event(
                    event_type,
                    topic_id,
                    topic_kind,
                    direction,
                    old_priority,
                    new_priority,
                    "active_search_priority_changed_between_verified_audits",
                )
            )

    return comparability, tuple(
        sorted(events, key=lambda item: (item.topic_id, item.event_type, item.id))
    )


def build_watch_cases(
    events: Iterable[WatchEvent],
    current_snapshot: Mapping[str, Any],
) -> tuple[WatchCase, ...]:
    """Turn operational watch events into human-review cases, never auto-decisions."""

    grouped: dict[str, list[WatchEvent]] = defaultdict(list)
    for event in events:
        if event.event_type == "baseline_created":
            continue
        grouped[event.topic_id].append(event)

    topics = current_snapshot.get("topics") or {}
    cases: list[WatchCase] = []
    for topic_id in sorted(grouped):
        topic_events = grouped[topic_id]
        event_types = {event.event_type for event in topic_events}
        if topic_id == "__profile__":
            watch_priority = "W1_HIGH"
            case_type = "PROFILE_CHANGE_REVIEW"
            action = "review_registry_change_before_interpreting_longitudinal_deltas"
            topic_kind = "registry"
        elif event_types & {
            "document_removed",
            "topic_removed",
            "flag_added",
            "priority_escalated",
            "document_count_changed",
            "provider_count_changed",
            "full_text_count_changed",
            "semantic_count_changed",
            "relational_count_changed",
        } and any(event.direction in {"decreased", "worsened", "removed"} for event in topic_events):
            watch_priority = "W1_HIGH"
            case_type = "COVERAGE_REGRESSION_REVIEW"
            action = "review_coverage_change_and_reaudit_topic"
            topic_kind = topic_events[0].topic_kind
        elif event_types & {"document_added", "topic_added", "latest_year_changed", "provider_added"}:
            watch_priority = "W2_MEDIUM"
            case_type = "NEW_MATERIAL_REVIEW"
            action = "review_new_material_through_normal_nutev_core_pipeline"
            topic_kind = topic_events[0].topic_kind
        else:
            watch_priority = "W3_LOW"
            case_type = "GAP_RESOLUTION_REVIEW"
            action = "confirm_operational_gap_resolution"
            topic_kind = topic_events[0].topic_kind

        current_topic = topics.get(topic_id) if isinstance(topics, Mapping) else None
        if isinstance(current_topic, Mapping):
            current_priority = str(
                current_topic.get("active_search_priority") or "P4_MONITOR"
            )
            if current_priority == "P1_HIGH":
                watch_priority = "W1_HIGH"

        trigger_ids = tuple(sorted(event.id for event in topic_events))
        digest = sha256(
            f"{topic_id}|{case_type}|{'|'.join(trigger_ids)}".encode("utf-8")
        ).hexdigest()[:20]
        cases.append(
            WatchCase(
                id=f"watch-case:{digest}",
                topic_id=topic_id,
                topic_kind=topic_kind,
                watch_priority=watch_priority,
                case_type=case_type,
                trigger_event_ids=trigger_ids,
                action=action,
            )
        )
    return tuple(cases)


def run_longitudinal_watch(
    topic_audits_jsonl: Path,
    topic_assignments_jsonl: Path,
    topic_audit_manifest: Path,
    output_dir: Path,
    *,
    previous_snapshot: Path | None = None,
    previous_watch_manifest: Path | None = None,
) -> dict[str, Any]:
    """Materialize one verified longitudinal topic/competency watch snapshot."""

    if (previous_snapshot is None) != (previous_watch_manifest is None):
        raise LongitudinalWatchError(
            "previous_snapshot and previous_watch_manifest must be provided together"
        )

    current_snapshot = build_watch_snapshot(
        topic_audits_jsonl,
        topic_assignments_jsonl,
        topic_audit_manifest,
    )
    previous: dict[str, Any] | None = None
    previous_source: dict[str, Any] | None = None
    if previous_snapshot is not None and previous_watch_manifest is not None:
        previous = _verify_previous_snapshot(
            previous_snapshot,
            previous_watch_manifest,
        )
        previous_source = {
            "snapshot_path": str(previous_snapshot),
            "snapshot_sha256": sha256_file(previous_snapshot),
            "watch_manifest_path": str(previous_watch_manifest),
            "watch_manifest_sha256": sha256_file(previous_watch_manifest),
        }

    comparability, events = compare_watch_snapshots(previous, current_snapshot)
    cases = build_watch_cases(events, current_snapshot)

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / "WATCH_SNAPSHOT.json"
    events_path = output_dir / "watch_events.jsonl"
    cases_path = output_dir / "watch_cases.jsonl"
    manifest_path = output_dir / "WATCH_MANIFEST.json"

    snapshot_sha = _write_json(snapshot_path, current_snapshot)
    events_sha = _write_jsonl(events_path, (asdict(item) for item in events))
    cases_sha = _write_jsonl(cases_path, (asdict(item) for item in cases))

    event_counts: dict[str, int] = defaultdict(int)
    for event in events:
        event_counts[event.event_type] += 1
    case_counts: dict[str, int] = defaultdict(int)
    for case in cases:
        case_counts[case.watch_priority] += 1

    manifest = {
        "schema_version": 1,
        "watch_type": "NUTEV_LONGITUDINAL_TOPIC_WATCH",
        "status": "PASS",
        "created_at": _now(),
        "comparability": comparability,
        "baseline": previous is None,
        "current": {
            "topic_audit_manifest": str(topic_audit_manifest),
            "topic_audit_manifest_sha256": sha256_file(topic_audit_manifest),
            "profile": current_snapshot.get("profile"),
        },
        "previous": previous_source,
        "counts": {
            "topics": len(current_snapshot.get("topics") or {}),
            "events": len(events),
            "event_counts": dict(sorted(event_counts.items())),
            "cases": len(cases),
            "case_priority_counts": dict(sorted(case_counts.items())),
        },
        "outputs": {
            "watch_snapshot": {"path": str(snapshot_path), "sha256": snapshot_sha},
            "watch_events": {"path": str(events_path), "sha256": events_sha},
            "watch_cases": {"path": str(cases_path), "sha256": cases_sha},
        },
        "assertions": [
            {"name": "current_topic_audit_hash_verified", "status": "PASS"},
            {"name": "assignment_counts_align_with_audits", "status": "PASS"},
            {
                "name": "previous_snapshot_hash_verified_if_present",
                "status": "PASS",
            },
            {"name": "profile_change_limits_comparability", "status": "PASS"},
            {"name": "watch_events_are_not_evidence_claims", "status": "PASS"},
            {"name": "watch_cases_require_review", "status": "PASS"},
            {"name": "watch_does_not_feed_prisma", "status": "PASS"},
            {"name": "prisma_not_required", "status": "PASS"},
        ],
        "guardrail": (
            "Longitudinal changes are operational differences between verified NutEV topic audits. "
            "They do not prove scientific importance, retraction, consensus, causality, evidence "
            "quality or recommendation strength. Watch cases require review and PRISMA remains optional."
        ),
    }
    manifest_sha = _write_json(manifest_path, manifest)
    return {
        "mode": "NUTEV_LONGITUDINAL_TOPIC_WATCH",
        "status": "COMPLETE",
        "baseline": previous is None,
        "comparability": comparability,
        "topics": len(current_snapshot.get("topics") or {}),
        "events": len(events),
        "cases": len(cases),
        "prisma_required": False,
        "outputs": {
            "snapshot": str(snapshot_path),
            "events": str(events_path),
            "cases": str(cases_path),
            "manifest": str(manifest_path),
        },
        "output_sha256": {
            "snapshot": snapshot_sha,
            "events": events_sha,
            "cases": cases_sha,
            "manifest": manifest_sha,
        },
    }
