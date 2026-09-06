from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from radar_data import RadarDataError, load_radar_state


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Path]]:
    topic_dir = tmp_path / "scientific" / "topics"
    watch_dir = tmp_path / "scientific" / "watch"
    profile_path = tmp_path / "config" / "topic_profile.json"
    profile = {
        "schema_version": 1,
        "profile_kind": "NUTEV_TOPIC_COMPETENCY_REGISTRY",
        "profile_id": "radar-test",
        "version": "1.0.0-prefreeze",
        "status": "PREFREEZE",
        "formal_gate": {"authorized": False},
        "topics": [
            {
                "id": "food_competence",
                "label": "Food competence",
                "kind": "competency",
                "terms": ["food literacy"],
            },
            {
                "id": "implementation",
                "label": "Implementation and monitoring",
                "kind": "implementation",
                "terms": ["monitoring"],
            },
        ],
    }
    _write_json(profile_path, profile)

    assignments_path = topic_dir / "topic_assignments.jsonl"
    audits_path = topic_dir / "topic_audits.jsonl"
    plan_path = topic_dir / "active_search_plan.json"
    runs_path = topic_dir / "active_search_runs.jsonl"
    manifest_path = topic_dir / "TOPIC_AUDIT_MANIFEST.json"

    _write_jsonl(
        assignments_path,
        [
            {"id": "a1", "topic_id": "food_competence", "document_id": "doi:1"},
            {"id": "a2", "topic_id": "food_competence", "document_id": "doi:2"},
            {"id": "a3", "topic_id": "implementation", "document_id": "doi:2"},
        ],
    )
    _write_jsonl(
        audits_path,
        [
            {
                "topic_id": "food_competence",
                "topic_kind": "competency",
                "document_count": 2,
                "provider_count": 2,
                "providers": ["pubmed", "scielo"],
                "full_text_count": 1,
                "semantic_count": 1,
                "relational_count": 1,
                "latest_year": 2026,
                "flags": ["semantic_incomplete"],
                "active_search_priority": "P3_LOW",
                "active_search_required": True,
            },
            {
                "topic_id": "implementation",
                "topic_kind": "implementation",
                "document_count": 1,
                "provider_count": 1,
                "providers": ["pubmed"],
                "full_text_count": 1,
                "semantic_count": 1,
                "relational_count": 0,
                "latest_year": 2024,
                "flags": ["low_provider_diversity", "relational_incomplete"],
                "active_search_priority": "P3_LOW",
                "active_search_required": True,
            },
        ],
    )
    _write_json(
        plan_path,
        {
            "schema_version": 2,
            "plan_type": "NUTEV_ACTIVE_TOPIC_SEARCH_PLAN",
            "profile_id": "radar-test",
            "searches": [
                {
                    "topic_id": "food_competence",
                    "provider": "pubmed",
                    "query": "nutrition AND food literacy",
                    "execution": "EXECUTABLE_STATUS_AWARE",
                },
                {
                    "topic_id": "food_competence",
                    "provider": "scopus",
                    "query": "nutrition AND food literacy",
                    "execution": "MANUAL_LICENSED",
                },
                {
                    "topic_id": "implementation",
                    "provider": "pubmed",
                    "query": "nutrition AND monitoring",
                    "execution": "EXECUTABLE_STATUS_AWARE",
                },
            ],
        },
    )
    _write_jsonl(
        runs_path,
        [
            {
                "topic_id": "food_competence",
                "provider": "pubmed",
                "status": "completed",
                "total_found": 12,
                "total_returned": 3,
                "error": None,
            },
            {
                "topic_id": "food_competence",
                "provider": "scopus",
                "status": "planned_not_executed",
                "total_found": None,
                "total_returned": 0,
                "error": "manual_licensed_provider",
            },
            {
                "topic_id": "implementation",
                "provider": "pubmed",
                "status": "empty",
                "total_found": 0,
                "total_returned": 0,
                "error": None,
            },
        ],
    )
    _write_json(
        manifest_path,
        {
            "schema_version": 1,
            "audit_type": "NUTEV_TOPIC_COMPETENCY_AUDIT",
            "status": "PASS",
            "created_at": "2026-08-27T18:00:00+00:00",
            "profile": {
                "path": str(profile_path),
                "profile_id": "radar-test",
                "version": "1.0.0-prefreeze",
                "status": "PREFREEZE",
                "sha256": _sha(profile_path),
            },
            "outputs": {
                "topic_assignments": {"path": str(assignments_path), "sha256": _sha(assignments_path)},
                "topic_audits": {"path": str(audits_path), "sha256": _sha(audits_path)},
                "active_search_plan": {"path": str(plan_path), "sha256": _sha(plan_path)},
                "active_search_runs": {"path": str(runs_path), "sha256": _sha(runs_path)},
            },
            "execution_contract": {
                "version": "explicit_provider_result_v1",
                "status_aware_providers": ["pubmed"],
                "manual_licensed_providers": ["scopus", "wos"],
                "empty_is_distinct_from_failure": True,
            },
        },
    )

    snapshot_path = watch_dir / "WATCH_SNAPSHOT.json"
    events_path = watch_dir / "watch_events.jsonl"
    cases_path = watch_dir / "watch_cases.jsonl"
    watch_manifest_path = watch_dir / "WATCH_MANIFEST.json"
    _write_json(
        snapshot_path,
        {
            "schema_version": 1,
            "snapshot_type": "NUTEV_LONGITUDINAL_TOPIC_SNAPSHOT",
            "profile": {"profile_id": "radar-test", "version": "1.0.0-prefreeze", "status": "PREFREEZE"},
            "topics": {
                "food_competence": {"topic_id": "food_competence"},
                "implementation": {"topic_id": "implementation"},
            },
        },
    )
    _write_jsonl(
        events_path,
        [
            {
                "id": "event-1",
                "event_type": "document_added",
                "topic_id": "food_competence",
                "topic_kind": "competency",
                "direction": "increased",
                "before": False,
                "after": True,
                "basis": "test",
                "document_id": "doi:2",
            }
        ],
    )
    _write_jsonl(
        cases_path,
        [
            {
                "id": "case-1",
                "topic_id": "food_competence",
                "topic_kind": "competency",
                "watch_priority": "W2_MEDIUM",
                "case_type": "NEW_MATERIAL_REVIEW",
                "trigger_event_ids": ["event-1"],
                "action": "review_new_material_through_normal_nutev_core_pipeline",
                "status": "review_required",
                "feeds_prisma": False,
                "auto_accepts_evidence": False,
            }
        ],
    )
    _write_json(
        watch_manifest_path,
        {
            "schema_version": 1,
            "watch_type": "NUTEV_LONGITUDINAL_TOPIC_WATCH",
            "status": "PASS",
            "created_at": "2026-08-27T18:05:00+00:00",
            "comparability": "full",
            "baseline": False,
            "current": {
                "topic_audit_manifest": str(manifest_path),
                "topic_audit_manifest_sha256": _sha(manifest_path),
                "profile": {"profile_id": "radar-test", "version": "1.0.0-prefreeze"},
            },
            "counts": {
                "topics": 2,
                "events": 1,
                "event_counts": {"document_added": 1},
                "cases": 1,
                "case_priority_counts": {"W2_MEDIUM": 1},
            },
            "outputs": {
                "watch_snapshot": {"path": str(snapshot_path), "sha256": _sha(snapshot_path)},
                "watch_events": {"path": str(events_path), "sha256": _sha(events_path)},
                "watch_cases": {"path": str(cases_path), "sha256": _sha(cases_path)},
            },
        },
    )
    return topic_dir, watch_dir, {
        "profile": profile_path,
        "audits": audits_path,
        "topic_manifest": manifest_path,
        "watch_manifest": watch_manifest_path,
    }


def test_radar_returns_not_ready_without_topic_audit(tmp_path: Path) -> None:
    result = load_radar_state(topic_dir=tmp_path / "topics", watch_dir=tmp_path / "watch")
    assert result["status"] == "not_ready"
    assert "Ainda não há snapshot científico publicado" in result["message"]
    assert "paths" not in result
    assert "next_commands" not in result
    assert "project_output_reference" not in json.dumps(result)


def test_radar_builds_verified_summary_and_topic_dossiers(tmp_path: Path) -> None:
    topic_dir, watch_dir, _ = _fixture(tmp_path)
    result = load_radar_state(topic_dir=topic_dir, watch_dir=watch_dir)

    assert result["status"] == "ready"
    assert result["summary"]["topics"] == 2
    assert result["summary"]["assignments"] == 3
    assert result["summary"]["unique_documents"] == 2
    assert result["summary"]["providers_observed"] == 2
    assert result["watch"]["available"] is True
    assert result["watch"]["stale"] is False

    food = next(topic for topic in result["topics"] if topic["topic_id"] == "food_competence")
    assert food["label"] == "Food competence"
    assert food["coverage"]["full_text_pct"] == 50.0
    assert food["watch"]["events"][0]["event_type"] == "document_added"
    assert food["watch"]["cases"][0]["case_type"] == "NEW_MATERIAL_REVIEW"

    scopus = next(provider for provider in result["providers"] if provider["provider"] == "scopus")
    assert scopus["manual_licensed"] is True
    assert scopus["state"] == "manual"
    assert scopus["status_counts"]["planned_not_executed"] == 1


def test_radar_fails_closed_on_tampered_topic_output(tmp_path: Path) -> None:
    topic_dir, watch_dir, paths = _fixture(tmp_path)
    paths["audits"].write_text(paths["audits"].read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(RadarDataError, match="SHA-256 mismatch"):
        load_radar_state(topic_dir=topic_dir, watch_dir=watch_dir)


def test_stale_watch_is_reported_but_not_attached_to_current_topics(tmp_path: Path) -> None:
    topic_dir, watch_dir, paths = _fixture(tmp_path)
    manifest = json.loads(paths["watch_manifest"].read_text(encoding="utf-8"))
    manifest["current"]["topic_audit_manifest_sha256"] = "0" * 64
    _write_json(paths["watch_manifest"], manifest)

    result = load_radar_state(topic_dir=topic_dir, watch_dir=watch_dir)
    assert result["watch"]["stale"] is True
    food = next(topic for topic in result["topics"] if topic["topic_id"] == "food_competence")
    assert food["watch"]["events"] == []
    assert food["watch"]["cases"] == []
