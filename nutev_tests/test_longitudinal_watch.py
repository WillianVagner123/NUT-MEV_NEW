from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.cli import main as cli_main
from nutev.science import LongitudinalWatchError, run_longitudinal_watch


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _audit_fixture(
    root: Path,
    *,
    profile_id: str = "test-profile",
    version: str = "1.0.0-prefreeze",
    food_docs: list[str] | None = None,
    food_providers: list[str] | None = None,
    food_latest_year: int | None = 2025,
    food_flags: list[str] | None = None,
    food_priority: str = "P2_MEDIUM",
) -> tuple[Path, Path, Path]:
    food_docs = food_docs if food_docs is not None else ["doi:10.1000/food.1"]
    food_providers = food_providers if food_providers is not None else ["pubmed"]
    food_flags = (
        food_flags
        if food_flags is not None
        else ["low_document_count", "low_provider_diversity"]
    )

    audits = root / "topic_audits.jsonl"
    assignments = root / "topic_assignments.jsonl"
    manifest = root / "TOPIC_AUDIT_MANIFEST.json"

    _write_jsonl(
        audits,
        [
            {
                "topic_id": "food_competence",
                "topic_kind": "competency",
                "document_count": len(food_docs),
                "provider_count": len(food_providers),
                "providers": food_providers,
                "full_text_count": len(food_docs),
                "semantic_count": len(food_docs),
                "relational_count": len(food_docs),
                "latest_year": food_latest_year,
                "flags": food_flags,
                "active_search_priority": food_priority,
                "active_search_required": bool(food_flags),
                "status": "machine_audit",
            },
            {
                "topic_id": "implementation",
                "topic_kind": "implementation",
                "document_count": 0,
                "provider_count": 0,
                "providers": [],
                "full_text_count": 0,
                "semantic_count": 0,
                "relational_count": 0,
                "latest_year": None,
                "flags": ["no_documents"],
                "active_search_priority": "P1_HIGH",
                "active_search_required": True,
                "status": "machine_audit",
            },
        ],
    )
    assignment_rows = []
    for index, document_id in enumerate(food_docs, start=1):
        assignment_rows.append(
            {
                "id": f"assignment:{index}:{document_id}",
                "document_id": document_id,
                "topic_id": "food_competence",
                "topic_kind": "competency",
                "matched_terms": ["food literacy"],
                "matched_sources": ["abstract"],
                "lexical_match_score": 0.5,
                "status": "machine_candidate",
            }
        )
    _write_jsonl(assignments, assignment_rows)
    _write_json(
        manifest,
        {
            "schema_version": 1,
            "audit_type": "NUTEV_TOPIC_COMPETENCY_AUDIT",
            "status": "PASS",
            "created_at": "2026-08-27T00:00:00+00:00",
            "profile": {
                "profile_id": profile_id,
                "version": version,
                "status": "PREFREEZE",
                "sha256": "a" * 64,
            },
            "outputs": {
                "topic_audits": {
                    "path": str(audits),
                    "sha256": _sha(audits),
                },
                "topic_assignments": {
                    "path": str(assignments),
                    "sha256": _sha(assignments),
                },
            },
        },
    )
    return audits, assignments, manifest


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_first_watch_run_creates_verified_baseline_without_review_case(tmp_path: Path):
    audits, assignments, manifest = _audit_fixture(tmp_path / "topic-run")
    output = tmp_path / "watch-1"

    result = run_longitudinal_watch(audits, assignments, manifest, output)

    assert result["status"] == "COMPLETE"
    assert result["baseline"] is True
    assert result["comparability"] == "baseline"
    assert result["prisma_required"] is False
    events = _jsonl(output / "watch_events.jsonl")
    assert [event["event_type"] for event in events] == ["baseline_created"]
    assert _jsonl(output / "watch_cases.jsonl") == []
    assert (output / "WATCH_SNAPSHOT.json").is_file()
    assert (output / "WATCH_MANIFEST.json").is_file()


def test_new_material_and_freshness_change_create_review_case(tmp_path: Path):
    old_audits, old_assignments, old_manifest = _audit_fixture(tmp_path / "old")
    old_watch = tmp_path / "watch-old"
    run_longitudinal_watch(old_audits, old_assignments, old_manifest, old_watch)

    new_audits, new_assignments, new_manifest = _audit_fixture(
        tmp_path / "new",
        food_docs=["doi:10.1000/food.1", "doi:10.1000/food.2"],
        food_providers=["pubmed", "openalex"],
        food_latest_year=2026,
        food_flags=[],
        food_priority="P4_MONITOR",
    )
    new_watch = tmp_path / "watch-new"
    result = run_longitudinal_watch(
        new_audits,
        new_assignments,
        new_manifest,
        new_watch,
        previous_snapshot=old_watch / "WATCH_SNAPSHOT.json",
        previous_watch_manifest=old_watch / "WATCH_MANIFEST.json",
    )

    assert result["baseline"] is False
    assert result["comparability"] == "full"
    events = _jsonl(new_watch / "watch_events.jsonl")
    event_types = {event["event_type"] for event in events}
    assert "document_added" in event_types
    assert "latest_year_changed" in event_types
    assert "provider_added" in event_types
    assert "flag_resolved" in event_types
    assert "priority_deescalated" in event_types
    added = next(event for event in events if event["event_type"] == "document_added")
    assert added["document_id"] == "doi:10.1000/food.2"

    cases = _jsonl(new_watch / "watch_cases.jsonl")
    food_case = next(case for case in cases if case["topic_id"] == "food_competence")
    assert food_case["case_type"] == "NEW_MATERIAL_REVIEW"
    assert food_case["watch_priority"] == "W2_MEDIUM"
    assert food_case["feeds_prisma"] is False
    assert food_case["auto_accepts_evidence"] is False


def test_coverage_regression_escalates_human_review(tmp_path: Path):
    old_audits, old_assignments, old_manifest = _audit_fixture(
        tmp_path / "old",
        food_docs=["doi:10.1000/food.1", "doi:10.1000/food.2"],
        food_providers=["pubmed", "openalex"],
        food_latest_year=2026,
        food_flags=[],
        food_priority="P4_MONITOR",
    )
    old_watch = tmp_path / "watch-old"
    run_longitudinal_watch(old_audits, old_assignments, old_manifest, old_watch)

    new_audits, new_assignments, new_manifest = _audit_fixture(tmp_path / "new")
    new_watch = tmp_path / "watch-new"
    run_longitudinal_watch(
        new_audits,
        new_assignments,
        new_manifest,
        new_watch,
        previous_snapshot=old_watch / "WATCH_SNAPSHOT.json",
        previous_watch_manifest=old_watch / "WATCH_MANIFEST.json",
    )

    events = _jsonl(new_watch / "watch_events.jsonl")
    event_types = {event["event_type"] for event in events}
    assert "document_removed" in event_types
    assert "flag_added" in event_types
    assert "priority_escalated" in event_types
    cases = _jsonl(new_watch / "watch_cases.jsonl")
    food_case = next(case for case in cases if case["topic_id"] == "food_competence")
    assert food_case["case_type"] == "COVERAGE_REGRESSION_REVIEW"
    assert food_case["watch_priority"] == "W1_HIGH"


def test_profile_id_change_blocks_direct_topic_trend_comparison(tmp_path: Path):
    old_audits, old_assignments, old_manifest = _audit_fixture(
        tmp_path / "old", profile_id="profile-a"
    )
    old_watch = tmp_path / "watch-old"
    run_longitudinal_watch(old_audits, old_assignments, old_manifest, old_watch)

    new_audits, new_assignments, new_manifest = _audit_fixture(
        tmp_path / "new",
        profile_id="profile-b",
        food_docs=["doi:10.1000/food.1", "doi:10.1000/food.2"],
    )
    new_watch = tmp_path / "watch-new"
    result = run_longitudinal_watch(
        new_audits,
        new_assignments,
        new_manifest,
        new_watch,
        previous_snapshot=old_watch / "WATCH_SNAPSHOT.json",
        previous_watch_manifest=old_watch / "WATCH_MANIFEST.json",
    )

    assert result["comparability"] == "incompatible"
    events = _jsonl(new_watch / "watch_events.jsonl")
    assert [event["event_type"] for event in events] == ["profile_changed"]
    cases = _jsonl(new_watch / "watch_cases.jsonl")
    assert cases[0]["case_type"] == "PROFILE_CHANGE_REVIEW"
    assert cases[0]["watch_priority"] == "W1_HIGH"


def test_current_topic_audit_hash_mismatch_fails_closed(tmp_path: Path):
    audits, assignments, manifest = _audit_fixture(tmp_path / "topic-run")
    audits.write_text(audits.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(LongitudinalWatchError, match="topic audits SHA-256 mismatch"):
        run_longitudinal_watch(
            audits,
            assignments,
            manifest,
            tmp_path / "watch",
        )


def test_previous_snapshot_tampering_fails_closed(tmp_path: Path):
    audits, assignments, manifest = _audit_fixture(tmp_path / "old")
    old_watch = tmp_path / "watch-old"
    run_longitudinal_watch(audits, assignments, manifest, old_watch)
    snapshot = old_watch / "WATCH_SNAPSHOT.json"
    snapshot.write_text(snapshot.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    new_audits, new_assignments, new_manifest = _audit_fixture(tmp_path / "new")
    with pytest.raises(LongitudinalWatchError, match="previous watch snapshot SHA-256 mismatch"):
        run_longitudinal_watch(
            new_audits,
            new_assignments,
            new_manifest,
            tmp_path / "watch-new",
            previous_snapshot=snapshot,
            previous_watch_manifest=old_watch / "WATCH_MANIFEST.json",
        )


def test_cli_science_watch_baseline(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    audits, assignments, manifest = _audit_fixture(tmp_path / "topic-run")
    output = tmp_path / "watch-cli"
    code = cli_main(
        [
            "science-watch",
            "--topic-audits-jsonl",
            str(audits),
            "--topic-assignments-jsonl",
            str(assignments),
            "--topic-audit-manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "NUTEV_LONGITUDINAL_TOPIC_WATCH"
    assert payload["baseline"] is True
    assert payload["prisma_required"] is False
