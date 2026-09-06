from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
DEFAULT_TOPIC_DIR = REPO_ROOT / "project_output_reference" / "scientific" / "topics"
DEFAULT_WATCH_DIR = REPO_ROOT / "project_output_reference" / "scientific" / "watch"


class RadarDataError(RuntimeError):
    """Raised when canonical Radar inputs exist but fail integrity/shape checks."""


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RadarDataError(f"missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RadarDataError(f"invalid JSON in {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RadarDataError(f"{label} must be a JSON object: {path}")
    return value


def _read_jsonl(path: Path, *, label: str, allow_empty: bool = True) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RadarDataError(f"missing {label}: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RadarDataError(
                f"invalid JSONL in {label}: {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise RadarDataError(f"non-object row in {label}: {path}:{line_number}")
        rows.append(value)
    if not rows and not allow_empty:
        raise RadarDataError(f"{label} is empty: {path}")
    return rows


def _resolve_path(raw_path: object, *, manifest_path: Path, fallback_name: str | None = None) -> Path:
    candidates: list[Path] = []
    raw = str(raw_path or "").strip()
    if raw:
        path = Path(raw)
        if path.is_absolute():
            candidates.append(path)
        else:
            candidates.append(REPO_ROOT / path)
            candidates.append(manifest_path.parent / path)
            candidates.append(manifest_path.parent / path.name)
    if fallback_name:
        candidates.append(manifest_path.parent / fallback_name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    attempted = ", ".join(str(path) for path in candidates) or "(none)"
    raise RadarDataError(f"unable to resolve referenced file; attempted: {attempted}")


def _verified_output(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    *,
    key: str,
    fallback_name: str,
) -> Path:
    outputs = manifest.get("outputs") or {}
    if not isinstance(outputs, Mapping):
        raise RadarDataError("manifest outputs must be an object")
    spec = outputs.get(key) or {}
    if not isinstance(spec, Mapping):
        raise RadarDataError(f"manifest output {key} must be an object")
    expected = str(spec.get("sha256") or "").strip().lower()
    if not expected:
        raise RadarDataError(f"manifest output {key} is missing SHA-256")
    path = _resolve_path(spec.get("path"), manifest_path=manifest_path, fallback_name=fallback_name)
    actual = _sha256_file(path)
    if actual != expected:
        raise RadarDataError(
            f"SHA-256 mismatch for {key}: expected {expected}, got {actual}"
        )
    return path


def _load_profile(manifest: Mapping[str, Any], manifest_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    spec = manifest.get("profile") or {}
    if not isinstance(spec, Mapping):
        raise RadarDataError("topic audit manifest profile must be an object")
    expected = str(spec.get("sha256") or "").strip().lower()
    if not expected:
        raise RadarDataError("topic audit manifest profile is missing SHA-256")
    profile_path = _resolve_path(spec.get("path"), manifest_path=manifest_path)
    actual = _sha256_file(profile_path)
    if actual != expected:
        raise RadarDataError(
            f"topic profile SHA-256 mismatch: expected {expected}, got {actual}"
        )
    profile = _read_json(profile_path, label="topic profile")
    raw_topics = profile.get("topics") or []
    if not isinstance(raw_topics, list):
        raise RadarDataError("topic profile topics must be a list")
    topic_index: dict[str, dict[str, Any]] = {}
    for raw in raw_topics:
        if not isinstance(raw, Mapping):
            continue
        topic_id = str(raw.get("id") or "").strip()
        if not topic_id:
            continue
        topic_index[topic_id] = {
            "label": str(raw.get("label") or topic_id),
            "kind": str(raw.get("kind") or "topic"),
            "enabled": bool(raw.get("enabled", True)),
        }
    return profile, topic_index


def _priority_order(value: str) -> int:
    return {"P1_HIGH": 1, "P2_MEDIUM": 2, "P3_LOW": 3, "P4_MONITOR": 4}.get(value, 99)


def _provider_state(status_counts: Mapping[str, int], *, manual: bool) -> str:
    if manual:
        return "manual"
    if status_counts.get("failed"):
        return "failed"
    if status_counts.get("partial"):
        return "partial"
    if status_counts.get("skipped") and not (
        status_counts.get("completed") or status_counts.get("empty")
    ):
        return "skipped"
    if status_counts.get("running") or status_counts.get("queued"):
        return "running"
    if status_counts.get("completed") or status_counts.get("empty"):
        return "completed"
    if status_counts.get("planned_not_executed"):
        return "planned"
    return "unknown"


def _load_watch(watch_dir: Path, *, current_topic_manifest_sha: str) -> dict[str, Any]:
    manifest_path = watch_dir / "WATCH_MANIFEST.json"
    if not manifest_path.is_file():
        return {
            "available": False,
            "stale": False,
            "status": "not_ready",
            "message": "Nenhum WATCH_MANIFEST.json verificado foi encontrado.",
            "events": [],
            "cases": [],
        }

    manifest = _read_json(manifest_path, label="watch manifest")
    if (
        manifest.get("watch_type") != "NUTEV_LONGITUDINAL_TOPIC_WATCH"
        or manifest.get("status") != "PASS"
    ):
        raise RadarDataError("watch manifest is not a passing NutEV longitudinal watch manifest")

    snapshot_path = _verified_output(
        manifest, manifest_path, key="watch_snapshot", fallback_name="WATCH_SNAPSHOT.json"
    )
    events_path = _verified_output(
        manifest, manifest_path, key="watch_events", fallback_name="watch_events.jsonl"
    )
    cases_path = _verified_output(
        manifest, manifest_path, key="watch_cases", fallback_name="watch_cases.jsonl"
    )
    snapshot = _read_json(snapshot_path, label="watch snapshot")
    if snapshot.get("snapshot_type") != "NUTEV_LONGITUDINAL_TOPIC_SNAPSHOT":
        raise RadarDataError("watch snapshot has unsupported snapshot_type")
    events = _read_jsonl(events_path, label="watch events")
    cases = _read_jsonl(cases_path, label="watch cases")

    current = manifest.get("current") or {}
    watch_topic_sha = str(
        current.get("topic_audit_manifest_sha256") if isinstance(current, Mapping) else ""
    ).strip().lower()
    stale = not watch_topic_sha or watch_topic_sha != current_topic_manifest_sha

    return {
        "available": True,
        "stale": stale,
        "status": "stale" if stale else "verified",
        "created_at": manifest.get("created_at"),
        "baseline": bool(manifest.get("baseline")),
        "comparability": manifest.get("comparability"),
        "counts": manifest.get("counts") or {},
        "profile": (manifest.get("current") or {}).get("profile")
        if isinstance(manifest.get("current"), Mapping)
        else None,
        "events": events,
        "cases": cases,
        "snapshot_topic_count": len(snapshot.get("topics") or {}),
        "message": (
            "O Watch foi gerado para uma auditoria anterior; deltas não foram anexados aos tópicos atuais."
            if stale
            else "Watch verificado para a auditoria atual."
        ),
    }


def load_radar_state(
    *,
    topic_dir: Path | None = None,
    watch_dir: Path | None = None,
) -> dict[str, Any]:
    """Build the UI-facing Radar state from verified canonical topic/watch artifacts."""

    topic_dir = Path(topic_dir or DEFAULT_TOPIC_DIR)
    watch_dir = Path(watch_dir or DEFAULT_WATCH_DIR)
    manifest_path = topic_dir / "TOPIC_AUDIT_MANIFEST.json"
    if not manifest_path.is_file():
        return {
            "status": "not_ready",
            "message": (
                "Ainda não há snapshot científico publicado. "
                "O Radar será preenchido quando uma curadoria científica válida estiver disponível."
            ),
        }

    manifest = _read_json(manifest_path, label="topic audit manifest")
    if (
        manifest.get("audit_type") != "NUTEV_TOPIC_COMPETENCY_AUDIT"
        or manifest.get("status") != "PASS"
    ):
        raise RadarDataError("topic audit manifest is not a passing NutEV topic/competency audit")

    topic_manifest_sha = _sha256_file(manifest_path)
    audits_path = _verified_output(
        manifest, manifest_path, key="topic_audits", fallback_name="topic_audits.jsonl"
    )
    assignments_path = _verified_output(
        manifest,
        manifest_path,
        key="topic_assignments",
        fallback_name="topic_assignments.jsonl",
    )
    search_plan_path = _verified_output(
        manifest,
        manifest_path,
        key="gap_search_plan",
        fallback_name="gap_search_plan.jsonl",
    )
    audits = _read_jsonl(audits_path, label="topic audits", allow_empty=False)
    assignments = _read_jsonl(assignments_path, label="topic assignments")
    search_plan = _read_jsonl(search_plan_path, label="gap search plan")
    profile, topic_index = _load_profile(manifest, manifest_path)

    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    manual_sources: set[str] = set()
    for row in search_plan:
        provider = str(row.get("provider") or "unknown")
        status = str(row.get("status") or "planned_not_executed")
        source_counts[provider][status] += 1
        if bool(row.get("manual")):
            manual_sources.add(provider)

    source_status = []
    for provider in sorted(source_counts):
        counts = dict(source_counts[provider])
        source_status.append(
            {
                "provider": provider,
                "status": _provider_state(counts, manual=provider in manual_sources),
                "counts": counts,
            }
        )

    assignments_by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assignments:
        topic_id = str(row.get("topic_id") or "")
        if topic_id:
            assignments_by_topic[topic_id].append(row)

    topics = []
    for row in audits:
        topic_id = str(row.get("topic_id") or "")
        meta = topic_index.get(topic_id, {})
        topics.append(
            {
                "topic_id": topic_id,
                "label": str(row.get("label") or meta.get("label") or topic_id),
                "kind": str(row.get("kind") or meta.get("kind") or "topic"),
                "enabled": bool(meta.get("enabled", True)),
                "coverage_status": row.get("coverage_status"),
                "priority": row.get("priority"),
                "gap_count": row.get("gap_count", 0),
                "assignment_count": len(assignments_by_topic.get(topic_id, [])),
                "assignments": assignments_by_topic.get(topic_id, []),
                "notes": row.get("notes") or [],
            }
        )
    topics.sort(key=lambda item: (_priority_order(str(item.get("priority") or "")), str(item.get("label") or "").casefold()))

    watch = _load_watch(watch_dir, current_topic_manifest_sha=topic_manifest_sha)
    return {
        "status": "ready",
        "created_at": manifest.get("created_at"),
        "profile": profile,
        "counts": manifest.get("counts") or {},
        "topics": topics,
        "source_status": source_status,
        "watch": watch,
    }
