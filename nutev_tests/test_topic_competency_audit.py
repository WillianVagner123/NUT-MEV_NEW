from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.cli import main as cli_main
from nutev.science import (
    TopicAuditError,
    assign_topics,
    audit_topics,
    build_active_search_plan,
    load_topic_profile,
    run_topic_competency_audit,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _profile(tmp_path: Path) -> Path:
    path = tmp_path / "topics.json"
    _write_json(
        path,
        {
            "schema_version": 1,
            "profile_kind": "NUTEV_TOPIC_COMPETENCY_REGISTRY",
            "profile_id": "test-profile",
            "version": "1.0.0-prefreeze",
            "status": "PREFREEZE",
            "formal_gate": {"authorized": False},
            "audit": {
                "min_documents": 2,
                "min_providers": 2,
                "freshness_years": 5,
            },
            "topics": [
                {
                    "id": "food_competence",
                    "label": "Food competence",
                    "kind": "competency",
                    "terms": ["food literacy", "cooking skill*"],
                    "anchor_terms": ["nutrition*"],
                    "qualifier_terms": ["framework*"],
                    "query_mode": "anchor_terms_qualifiers",
                },
                {
                    "id": "professional_competence",
                    "label": "Professional competence",
                    "kind": "competency",
                    "terms": ["dietitian competenc*", "nutrition counseling skill*"],
                    "anchor_terms": ["nutrition*"],
                    "qualifier_terms": ["framework*"],
                    "query_mode": "anchor_terms_qualifiers",
                },
                {
                    "id": "implementation",
                    "label": "Implementation",
                    "kind": "implementation",
                    "terms": ["implementation framework*"],
                    "anchor_terms": ["nutrition*"],
                    "query_mode": "anchor_and_terms",
                },
            ],
        },
    )
    return path


def _record(
    document_id: str,
    *,
    provider: str,
    year: int,
    abstract: str,
    semantic_values: list[str] | None = None,
) -> dict:
    semantic_values = semantic_values or []
    facts = [
        {
            "id": f"fact:{document_id}:{index}",
            "field": "outcome",
            "value": value,
            "source_excerpt": value,
            "source_sha256": "a" * 64,
        }
        for index, value in enumerate(semantic_values, start=1)
    ]
    return {
        "id": f"record:{document_id}",
        "document_id": document_id,
        "schema_version": 3,
        "identity": {
            "title": "Nutrition competencies in practice",
            "source_provider": provider,
            "year": year,
        },
        "bibliography": {
            "abstract": abstract,
            "keywords": ["nutrition", "competency"],
        },
        "acquisition": {"full_text_status": "retrieved"},
        "semantic": {"facts": facts},
        "relational": {
            "entities": [
                {
                    "id": f"entity:{document_id}",
                    "entity_type": "outcome",
                    "label": semantic_values[0] if semantic_values else abstract,
                }
            ],
            "relations": [],
        },
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    records = tmp_path / "nutev_core_records_relational.jsonl"
    _write_jsonl(
        records,
        [
            _record(
                "doi:10.1000/topic.1",
                provider="pubmed",
                year=2025,
                abstract="Food literacy and cooking skills were mapped in nutrition practice.",
                semantic_values=["Dietitian competencies included nutrition counseling skills."],
            ),
            _record(
                "doi:10.1000/topic.2",
                provider="openalex",
                year=2024,
                abstract="Food literacy framework for healthy eating was evaluated.",
            ),
        ],
    )
    manifest = tmp_path / "RELATIONS_MANIFEST.json"
    _write_json(
        manifest,
        {
            "relations_type": "NUTEV_CORE_RELATIONAL_MAPPING",
            "status": "PASS",
            "outputs": {
                "relational_core_records": {
                    "path": str(records),
                    "sha256": _sha(records),
                }
            },
        },
    )
    return records, manifest, _profile(tmp_path)


def test_prefreeze_profile_loads_but_canonical_requires_authorization(tmp_path: Path):
    profile_path = _profile(tmp_path)
    profile = load_topic_profile(profile_path)
    assert profile["status"] == "PREFREEZE"
    assert len(profile["_topics"]) == 3

    raw = json.loads(profile_path.read_text(encoding="utf-8"))
    raw["status"] = "CANONICAL"
    raw["formal_gate"]["authorized"] = False
    _write_json(profile_path, raw)
    with pytest.raises(TopicAuditError, match="explicit formal_gate"):
        load_topic_profile(profile_path)


def test_competencies_are_machine_assignments_from_traceable_record_text(tmp_path: Path):
    records_path, _, profile_path = _fixture(tmp_path)
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
    ]
    profile = load_topic_profile(profile_path)
    assignments = assign_topics(records, profile["_topics"])

    food = [item for item in assignments if item.topic_id == "food_competence"]
    professional = [
        item for item in assignments if item.topic_id == "professional_competence"
    ]
    assert len(food) == 2
    assert len(professional) == 1
    assert all(item.status == "machine_candidate" for item in assignments)
    assert "abstract" in food[0].matched_sources
    assert professional[0].matched_sources


def test_audit_detects_topic_gap_and_materializes_active_search_plan(tmp_path: Path):
    records_path, _, profile_path = _fixture(tmp_path)
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
    ]
    profile = load_topic_profile(profile_path)
    assignments = assign_topics(records, profile["_topics"])
    audits = audit_topics(
        records,
        profile["_topics"],
        assignments,
        min_documents=2,
        min_providers=2,
        freshness_years=5,
    )
    by_topic = {item.topic_id: item for item in audits}
    assert by_topic["food_competence"].document_count == 2
    assert by_topic["food_competence"].provider_count == 2
    assert by_topic["implementation"].flags == ("no_documents",)
    assert by_topic["implementation"].active_search_priority == "P1_HIGH"

    plan = build_active_search_plan(
        profile["_topics"],
        audits,
        profile_id=profile["profile_id"],
        limit=25,
    )
    implementation_pubmed = next(
        item
        for item in plan["searches"]
        if item["topic_id"] == "implementation" and item["provider"] == "pubmed"
    )
    assert implementation_pubmed["execution"] == "EXECUTABLE_STATUS_AWARE"
    assert "[Title/Abstract]" in implementation_pubmed["query"]
    assert implementation_pubmed["feeds_prisma"] is False
    assert implementation_pubmed["auto_ingest"] is False


def test_active_search_network_disabled_is_skipped_not_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    records, manifest, profile = _fixture(tmp_path)
    monkeypatch.setenv("NUTEV_DISABLE_NETWORK", "1")
    output = tmp_path / "topics"

    result = run_topic_competency_audit(
        records,
        manifest,
        profile,
        output,
        execute_search=True,
        limit=5,
    )

    assert result["status"] == "COMPLETE"
    assert result["prisma_required"] is False
    runs = [
        json.loads(line)
        for line in (output / "active_search_runs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    pubmed_runs = [row for row in runs if row["provider"] == "pubmed"]
    assert pubmed_runs
    assert all(row["status"] == "skipped" for row in pubmed_runs)
    assert all(row["total_found"] is None for row in pubmed_runs)
    assert all(row["feeds_prisma"] is False for row in pubmed_runs)
    assert (output / "active_search_results.jsonl").read_text(encoding="utf-8") == ""


def test_hash_mismatch_fails_closed(tmp_path: Path):
    records, manifest, profile = _fixture(tmp_path)
    records.write_text(records.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(TopicAuditError, match="SHA-256 mismatch"):
        run_topic_competency_audit(
            records,
            manifest,
            profile,
            tmp_path / "output",
        )


def test_cli_science_topics_plan_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    records, manifest, profile = _fixture(tmp_path)
    output = tmp_path / "topics-cli"
    code = cli_main(
        [
            "science-topics",
            "--relational-records-jsonl",
            str(records),
            "--relations-manifest",
            str(manifest),
            "--topic-profile",
            str(profile),
            "--output-dir",
            str(output),
            "--limit",
            "7",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "NUTEV_TOPIC_COMPETENCY_AUDIT"
    assert payload["active_search_executed"] is False
    assert payload["profile_status"] == "PREFREEZE"
    assert (output / "TOPIC_AUDIT_MANIFEST.json").is_file()
