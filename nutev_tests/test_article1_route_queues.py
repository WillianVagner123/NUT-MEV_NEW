from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from nutev.science.article1_routes import build_article1_route_queues, route_profile


def _sha(path: Path) -> str:
    digest = sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return _sha(path)


def test_route_profile_keeps_navigation_separate_from_screening() -> None:
    profile = {
        "primary_document_class": "clinical_practice_guideline",
        "operational_domains": ["nutrition_care_process", "lifestyle_medicine"],
    }
    routes = route_profile(profile)
    assert "B-NORM" in routes
    assert "C-STRUCT" in routes
    assert any(value.startswith("document_class:") for value in routes["B-NORM"])
    assert "domain:nutrition_care_process" in routes["C-STRUCT"]


def test_build_article1_route_queues_are_rank_blind_and_non_exclusionary(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "project_output_reference"
    search_id = "search-article1"
    review_root = output_root / "scientific" / "review_queue" / search_id / "tier-A"
    profiles_path = review_root / "review_profiles.jsonl"
    profiles = [
        {
            "profile_version": "nutev_review_profile_rule_v2",
            "document_id": "doi:10.test/fbdg",
            "reference_rank": 1,
            "reference_score": 100.0,
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
            "title": "National Food-Based Dietary Guideline",
            "primary_document_class": "food_based_dietary_guideline",
            "document_class_confidence": "high",
            "operational_domains": ["food_based_guidance"],
            "machine_relevance_score": 40,
            "machine_relevance_band": "medium",
            "full_text_status": "retrieved",
        },
        {
            "profile_version": "nutev_review_profile_rule_v2",
            "document_id": "doi:10.test/skills",
            "reference_rank": 2,
            "reference_score": 90.0,
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
            "title": "Culinary skills in lifestyle medicine practice",
            "primary_document_class": "primary_observational",
            "document_class_confidence": "medium",
            "operational_domains": [
                "food_skills_competencies",
                "lifestyle_medicine",
                "dietary_counseling",
            ],
            "machine_relevance_score": 70,
            "machine_relevance_band": "high",
            "full_text_status": "retrieved",
        },
        {
            "profile_version": "nutev_review_profile_rule_v2",
            "document_id": "doi:10.test/guideline-ncp",
            "reference_rank": 3,
            "reference_score": 80.0,
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
            "title": "Clinical Practice Guideline for Nutrition Care",
            "primary_document_class": "clinical_practice_guideline",
            "document_class_confidence": "high",
            "operational_domains": ["nutrition_care_process", "nutrition_assessment"],
            "machine_relevance_score": 60,
            "machine_relevance_band": "high",
            "full_text_status": "retrieved",
        },
        {
            "profile_version": "nutev_review_profile_rule_v2",
            "document_id": "doi:10.test/support",
            "reference_rank": 4,
            "reference_score": 70.0,
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
            "title": "Systematic review of unrelated evidence",
            "primary_document_class": "evidence_synthesis",
            "document_class_confidence": "high",
            "operational_domains": [],
            "machine_relevance_score": 15,
            "machine_relevance_band": "low",
            "full_text_status": "retrieved",
        },
    ]
    profiles_sha = _write_jsonl(profiles_path, profiles)
    review_manifest = {
        "schema_version": 1,
        "review_queue_type": "NUTEV_TIER_REVIEW_PROFILE",
        "status": "PASS",
        "search_id": search_id,
        "tier": "A",
        "profile_version": "nutev_review_profile_rule_v2",
        "outputs": {
            "review_profiles": {"path": str(profiles_path), "sha256": profiles_sha}
        },
    }
    (review_root / "REVIEW_QUEUE_MANIFEST.json").write_text(
        json.dumps(review_manifest), encoding="utf-8"
    )

    workbench_root = output_root / "scientific" / "workbench"
    workbench_root.mkdir(parents=True)
    database = workbench_root / "evidence_workbench_review.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE article_cards (
                document_id TEXT PRIMARY KEY,
                title TEXT,
                year INTEGER,
                doi TEXT,
                pmid TEXT,
                source_provider TEXT,
                document_class TEXT,
                full_text_status TEXT,
                reference_stub TEXT
            )
            """
        )
        for index, profile in enumerate(profiles, start=1):
            connection.execute(
                "INSERT INTO article_cards VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    profile["document_id"],
                    profile["title"],
                    2020 + index,
                    str(profile["document_id"]).removeprefix("doi:"),
                    None,
                    "pubmed",
                    profile["primary_document_class"],
                    profile["full_text_status"],
                    f"Reference {index}",
                ),
            )
        connection.commit()
    workbench_manifest = {
        "schema_version": 1,
        "workbench_type": "NUTEV_ARTICLE_WORKBENCH_V1",
        "status": "PASS",
        "outputs": {"database": {"path": str(database), "sha256": _sha(database)}},
    }
    (workbench_root / "WORKBENCH_MANIFEST.json").write_text(
        json.dumps(workbench_manifest), encoding="utf-8"
    )

    result = build_article1_route_queues(
        search_id,
        output_root=output_root,
        tier="A",
    )

    assert result["status"] == "COMPLETE"
    assert result["tier_records"] == 4
    assert result["B-NORM"] == 2
    assert result["C-STRUCT"] == 2
    assert result["route_union_documents"] == 3
    assert result["route_overlap_documents"] == 1
    assert result["unrouted_documents"] == 1
    assert result["external_llm_calls"] == 0

    b_path = Path(result["outputs"]["B-NORM"]["path"])
    b_rows = [json.loads(line) for line in b_path.read_text(encoding="utf-8").splitlines()]
    assert {row["document_id"] for row in b_rows} == {
        "doi:10.test/fbdg",
        "doi:10.test/guideline-ncp",
    }
    for row in b_rows:
        assert "reference_rank" not in row
        assert "reference_score" not in row
        assert "reference_tier" not in row
        assert "machine_relevance_score" not in row
        assert "machine_relevance_band" not in row
        assert row["review_state"] == "unreviewed"
        assert row["queue_order"] >= 1

    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["blindness"]["reference_rank_exposed"] is False
    assert manifest["guardrails"]["unrouted_is_not_excluded"] is True
    assert manifest["guardrails"]["no_prisma_event_emitted"] is True

    first_hash = result["outputs"]["B-NORM"]["sha256"]
    repeated = build_article1_route_queues(
        search_id,
        output_root=output_root,
        tier="A",
    )
    assert repeated["outputs"]["B-NORM"]["sha256"] == first_hash
