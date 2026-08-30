from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.science.article1_vocabulary import (
    Article1VocabularyAuditError,
    audit_article1_route_vocabulary,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return sha256(payload.encode("utf-8")).hexdigest()


def _write_fixture(tmp_path: Path, *, leak_rank: bool = False) -> tuple[Path, str]:
    output_root = tmp_path / "project_output_reference"
    search_id = "web_test"
    route_root = output_root / "scientific" / "review_routes" / search_id / "article1"

    b_rows = []
    for index in range(3):
        row: dict[str, object] = {
            "queue_version": "nutev_article1_route_queue_v1",
            "route": "B-NORM",
            "document_id": f"doi:10.1/b{index}",
            "title": "Healthy plate implementation in a clinical practice guideline",
            "document_class": "clinical_practice_guideline",
            "operational_domains": ["food_based_guidance"],
        }
        if leak_rank and index == 0:
            row["reference_rank"] = 1
        b_rows.append(row)

    c_rows = [
        {
            "queue_version": "nutev_article1_route_queue_v1",
            "route": "C-STRUCT",
            "document_id": f"doi:10.1/c{index}",
            "title": "Shared meal planning competencies for community nutrition practice",
            "document_class": "framework_model",
            "operational_domains": ["food_skills_competencies", "social_context"],
        }
        for index in range(3)
    ]

    b_path = route_root / "B-NORM.jsonl"
    c_path = route_root / "C-STRUCT.jsonl"
    b_sha = _write_jsonl(b_path, b_rows)
    c_sha = _write_jsonl(c_path, c_rows)

    manifest = {
        "queue_type": "NUTEV_ARTICLE1_ROUTE_REVIEW_QUEUE",
        "queue_version": "nutev_article1_route_queue_v1",
        "status": "PASS",
        "outputs": {
            "B-NORM": {"path": str(b_path), "sha256": b_sha},
            "C-STRUCT": {"path": str(c_path), "sha256": c_sha},
        },
    }
    (route_root / "ROUTE_QUEUE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_root, search_id


def test_vocabulary_audit_is_deterministic_and_does_not_modify_queries(tmp_path: Path) -> None:
    output_root, search_id = _write_fixture(tmp_path)
    result = audit_article1_route_vocabulary(search_id, output_root=output_root)

    assert result["status"] == "COMPLETE"
    assert result["B-NORM_documents"] == 3
    assert result["C-STRUCT_documents"] == 3
    assert result["external_llm_calls"] == 0

    report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
    assert report["guardrails"]["formal_query_not_auto_modified"] is True
    assert report["guardrails"]["discovery_corpus_does_not_retroactively_validate_formal_search"] is True

    b_candidates = {
        item["phrase"]
        for item in report["routes"]["B-NORM"]["top_title_phrases"]
        if item["manual_query_review_candidate"]
    }
    c_candidates = {
        item["phrase"]
        for item in report["routes"]["C-STRUCT"]["top_title_phrases"]
        if item["manual_query_review_candidate"]
    }
    assert any("healthy plate" in phrase for phrase in b_candidates)
    assert any("shared meal planning" in phrase for phrase in c_candidates)

    first_sha = result["report_sha256"]
    second = audit_article1_route_vocabulary(search_id, output_root=output_root)
    assert second["report_sha256"] != ""
    assert Path(second["report"]).is_file()
    # created_at changes, so the report hash may change; the mined route content must not.
    second_report = json.loads(Path(second["report"]).read_text(encoding="utf-8"))
    assert report["routes"] == second_report["routes"]
    assert first_sha


def test_vocabulary_audit_fails_closed_if_blinded_rank_leaks(tmp_path: Path) -> None:
    output_root, search_id = _write_fixture(tmp_path, leak_rank=True)
    with pytest.raises(Article1VocabularyAuditError, match="exposes blinded fields"):
        audit_article1_route_vocabulary(search_id, output_root=output_root)
