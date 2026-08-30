from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from nutev.science.review_profiles import build_review_profile, build_tier_review_profiles


def _sha(path: Path) -> str:
    digest = sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_review_profile_detects_guidance_domains_without_scientific_decision() -> None:
    profile = build_review_profile(
        {
            "document_id": "doi:10.test/fbdg",
            "title": "Food-Based Dietary Guidelines for Lifestyle Medicine Practice",
            "reference_stub": "National dietary guideline with nutrition assessment and dietary counseling.",
            "search_text": (
                "food-based dietary guideline lifestyle medicine nutrition assessment "
                "dietary counseling food literacy social determinants monitoring"
            ),
            "card_json": json.dumps(
                {
                    "study_snapshot": {
                        "objective": ["Support nutrition care and monitoring in clinical practice"]
                    }
                }
            ),
            "document_class": "unclassified",
            "full_text_status": "retrieved",
            "reference_rank": 1,
            "reference_score": 100.0,
            "reference_tier": "BANK_A_PROCESSING_PRIORITY",
        }
    )

    assert profile["primary_document_class"] == "food_based_dietary_guideline"
    assert profile["machine_relevance_band"] == "high"
    assert "nutrition_assessment" in profile["operational_domains"]
    assert "dietary_counseling" in profile["operational_domains"]
    assert "food_literacy" in profile["operational_domains"]
    assert "social_context" in profile["operational_domains"]
    assert "lifestyle_medicine" in profile["operational_domains"]
    assert profile["guardrails"]["no_prisma_event_emitted"] is True
    assert "decision" not in profile
    assert "eligible" not in profile


def test_build_tier_review_profiles_atomically_updates_workbench(tmp_path: Path) -> None:
    output_root = tmp_path / "project_output_reference"
    workbench_root = output_root / "scientific" / "workbench"
    workbench_root.mkdir(parents=True)
    database = workbench_root / "evidence_workbench_priority.sqlite"

    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE article_cards (
                document_id TEXT PRIMARY KEY,
                title TEXT,
                reference_stub TEXT,
                search_text TEXT,
                card_json TEXT NOT NULL,
                document_class TEXT,
                full_text_status TEXT,
                reference_rank INTEGER,
                reference_score REAL,
                reference_tier TEXT
            );
            CREATE TABLE workbench_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        connection.execute(
            """
            INSERT INTO article_cards(
                document_id,title,reference_stub,search_text,card_json,document_class,
                full_text_status,reference_rank,reference_score,reference_tier
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "doi:10.test/1",
                "Clinical Practice Guideline for Nutrition Care in Lifestyle Medicine",
                "Guideline for dietary counseling and nutrition monitoring.",
                "clinical practice guideline lifestyle medicine nutrition care dietary counseling monitoring",
                json.dumps({"identity": {"title": "Clinical Practice Guideline"}}),
                "unclassified",
                "retrieved",
                1,
                99.0,
                "BANK_A_PROCESSING_PRIORITY",
            ),
        )
        connection.execute(
            """
            INSERT INTO article_cards(
                document_id,title,reference_stub,search_text,card_json,document_class,
                full_text_status,reference_rank,reference_score,reference_tier
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "doi:10.test/2",
                "Unrelated trial",
                "Trial reference.",
                "randomized controlled trial",
                json.dumps({"identity": {"title": "Unrelated trial"}}),
                "primary_randomized",
                "retrieved",
                663,
                10.0,
                "BANK_B_PROCESSING_PRIORITY",
            ),
        )
        connection.commit()

    manifest = {
        "schema_version": 1,
        "workbench_type": "NUTEV_ARTICLE_WORKBENCH_V1",
        "status": "PASS",
        "counts": {"articles": 2, "evidence_excerpts": 0, "result_bundles": 0},
        "outputs": {"database": {"path": str(database), "sha256": _sha(database)}},
        "extensions": {
            "bank_priority": {
                "status": "PASS",
                "search_id": "search-1",
            }
        },
    }
    manifest_path = workbench_root / "WORKBENCH_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = build_tier_review_profiles(
        "search-1",
        output_root=output_root,
        tier="A",
    )

    assert result["status"] == "COMPLETE"
    assert result["records"] == 1
    assert result["external_llm_calls"] == 0
    target = Path(result["database"])
    assert target.is_file()
    assert _sha(target) == result["database_sha256"]

    with sqlite3.connect(target) as connection:
        row = connection.execute(
            """
            SELECT document_class, machine_relevance_band, review_profile_json
            FROM article_cards WHERE document_id='doi:10.test/1'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == "clinical_practice_guideline"
        assert row[1] in {"medium", "high"}
        profile = json.loads(row[2])
        assert profile["guardrails"]["machine_profile_not_eligibility"] is True

        untouched = connection.execute(
            "SELECT document_class, review_profile_json FROM article_cards WHERE document_id='doi:10.test/2'"
        ).fetchone()
        assert untouched == ("primary_randomized", None)

        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        assert integrity == ("ok",)

    updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    extension = updated_manifest["extensions"]["review_profile_tier_A"]
    assert extension["status"] == "PASS"
    assert extension["records"] == 1
    assert updated_manifest["outputs"]["database"]["sha256"] == result["database_sha256"]
