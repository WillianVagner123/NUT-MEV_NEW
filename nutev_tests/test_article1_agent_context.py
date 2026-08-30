from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from nutev.science.article1_agent_context import build_article1_agent_context


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_article1_agent_context_is_verified_rank_blind_and_full_text_free(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_root = tmp_path / "output"
    search_id = "web_test_article1"

    master = {
        "master_type": "NUTEV_ARTICLE1_SEARCH_MASTER",
        "status": "DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE",
        "production_search_id": search_id,
        "question": "question",
        "formal_search": {
            "press_status": "NOT_YET_RECORDED_AS_PASS",
            "gf10_authorized": False,
            "query_freeze_complete": False,
            "formal_provider_search_executed": False,
            "prisma_search_event_emitted": False,
        },
    }
    _write_json(repo_root / "config/nutev/article1_search_master_v1.json", master)

    workbench_root = output_root / "scientific/workbench"
    workbench_root.mkdir(parents=True, exist_ok=True)
    database = workbench_root / "evidence_workbench_review.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
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
              reference_stub TEXT,
              reference_tier TEXT,
              reference_rank INTEGER,
              reference_score REAL,
              review_profile_json TEXT,
              machine_relevance_score REAL,
              machine_relevance_band TEXT
            );
            CREATE TABLE evidence_excerpts (document_id TEXT, excerpt_id TEXT);
            CREATE TABLE result_bundles (document_id TEXT, result_id TEXT);
            """
        )
        profile_a = json.dumps(
            {
                "profile_version": "nutev_review_profile_rule_v2",
                "primary_document_class": "clinical_practice_guideline",
                "document_classification_basis": "title_specific_rule",
                "document_class_confidence": "high",
                "operational_domains": ["food_based_guidance"],
                "operational_domain_matches": {"food_based_guidance": ["dietary guideline"]},
            }
        )
        profile_b = json.dumps(
            {
                "profile_version": "nutev_review_profile_rule_v2",
                "primary_document_class": "unclassified",
                "document_classification_basis": "insufficient_document_shape_signal",
                "document_class_confidence": "low",
                "operational_domains": ["food_literacy"],
                "operational_domain_matches": {"food_literacy": ["food literacy"]},
            }
        )
        connection.execute(
            "INSERT INTO article_cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "doc-a", "Guideline A", 2025, "10.1/a", "1", "pubmed",
                "clinical_practice_guideline", "retrieved", "Ref A",
                "BANK_A_PROCESSING_PRIORITY", 1, 99.0, profile_a, 88.0, "high",
            ),
        )
        connection.execute(
            "INSERT INTO article_cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "doc-b", "Food literacy B", 2024, "10.1/b", "2", "openalex",
                "unclassified", "partial", "Ref B",
                "BANK_A_PROCESSING_PRIORITY", 2, 80.0, profile_b, 44.0, "medium",
            ),
        )
        connection.executemany(
            "INSERT INTO evidence_excerpts VALUES (?,?)",
            [("doc-a", "e1"), ("doc-a", "e2"), ("doc-b", "e3")],
        )
        connection.executemany(
            "INSERT INTO result_bundles VALUES (?,?)",
            [("doc-a", "r1"), ("doc-b", "r2")],
        )

    _write_json(
        workbench_root / "WORKBENCH_MANIFEST.json",
        {
            "workbench_type": "NUTEV_ARTICLE_WORKBENCH_V1",
            "status": "PASS",
            "counts": {"articles": 2, "evidence_excerpts": 3, "result_bundles": 2},
            "outputs": {"database": {"path": str(database), "sha256": _sha(database)}},
        },
    )

    route_root = output_root / "scientific/review_routes" / search_id / "article1"
    b_norm = route_root / "B-NORM.jsonl"
    c_struct = route_root / "C-STRUCT.jsonl"
    _write_jsonl(
        b_norm,
        [{"route": "B-NORM", "document_id": "doc-a", "title": "Guideline A"}],
    )
    _write_jsonl(
        c_struct,
        [{"route": "C-STRUCT", "document_id": "doc-b", "title": "Food literacy B"}],
    )
    _write_json(
        route_root / "ROUTE_QUEUE_MANIFEST.json",
        {
            "queue_type": "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE",
            "queue_version": "nutev_article1_route_queue_v1",
            "status": "PASS",
            "counts": {
                "tier_records": 2,
                "B-NORM": 1,
                "C-STRUCT": 1,
                "route_union_documents": 2,
                "route_overlap_documents": 0,
                "unrouted_documents": 0,
            },
            "outputs": {
                "B-NORM": {"path": str(b_norm), "sha256": _sha(b_norm)},
                "C-STRUCT": {"path": str(c_struct), "sha256": _sha(c_struct)},
            },
        },
    )

    result = build_article1_agent_context(
        search_id,
        output_root=output_root,
        repo_root=repo_root,
    )
    assert result["status"] == "COMPLETE"
    assert result["article_summaries"] == 2
    assert result["B-NORM"] == 1
    assert result["C-STRUCT"] == 1
    assert result["rank_blind"] is True
    assert result["full_text_included"] is False

    bundle_root = output_root / "agent_context/article1"
    rows = [
        json.loads(line)
        for line in (bundle_root / "ARTICLE_SUMMARIES.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    by_id = {row["document_id"]: row for row in rows}
    assert by_id["doc-a"]["routes"] == ["B-NORM"]
    assert by_id["doc-b"]["routes"] == ["C-STRUCT"]
    assert by_id["doc-a"]["evidence_excerpt_count"] == 2
    assert by_id["doc-a"]["result_bundle_count"] == 1
    for row in rows:
        assert "reference_rank" not in row
        assert "reference_score" not in row
        assert "reference_tier" not in row
        assert "machine_relevance_score" not in row
        assert "machine_relevance_band" not in row
        assert "full_text" not in row

    manifest = json.loads((bundle_root / "CONTEXT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["safety"]["rank_blind"] is True
    assert manifest["safety"]["full_text_included"] is False
    assert manifest["safety"]["eligibility_decisions_included"] is False
    assert manifest["safety"]["prisma_events_included"] is False
