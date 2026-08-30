from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.science.search_bank import SearchBankError, prepare_search_for_bank, tier_boundaries


def _write_search(root: Path, *, n: int = 100, status: str = "COMPLETE_WITH_PROVIDER_GAPS") -> str:
    search_id = "web_20260830T180000-0300_testbank"
    run_dir = root / "15_web_searches" / search_id
    run_dir.mkdir(parents=True)
    rows = []
    for index in range(1, n + 1):
        rows.append(
            {
                "reference_rank": index,
                "reference_score": 101.0 - index / 10,
                "title": f"Article {index}",
                "doi": f"10.1000/test.{index}",
                "url": f"https://doi.org/10.1000/test.{index}",
                "year": 2020 + (index % 6),
                "source_provider": "pubmed" if index % 2 else "openalex",
                "abstract": f"Abstract {index}",
            }
        )
    payload = {
        "schema_version": 4,
        "search_id": search_id,
        "query": "test question",
        "status": status,
        "search_mode": "structured_review_global_exhaustive",
        "returned_records": n,
        "unique_records": n,
        "failed_providers": [],
        "unavailable_providers": ["scielo_native"],
        "non_exhaustive_providers": ["openalex"],
        "results": rows,
    }
    (run_dir / "result.json").write_text(json.dumps(payload), encoding="utf-8")
    return search_id


def test_tier_boundaries_are_operational_percentiles() -> None:
    assert tier_boundaries(100) == {"A": 2, "B": 10, "C": 40, "D": 100}
    assert tier_boundaries(1) == {"A": 1, "B": 1, "C": 1, "D": 1}
    assert tier_boundaries(0) == {"A": 0, "B": 0, "C": 0, "D": 0}


def test_prepare_search_for_bank_preserves_all_rows_and_gaps(tmp_path: Path) -> None:
    search_id = _write_search(tmp_path)
    result = prepare_search_for_bank(search_id, output_root=tmp_path)

    assert result["status"] == "PREPARED"
    assert result["records"] == 100
    assert result["tier_counts"] == {"A": 2, "B": 8, "C": 30, "D": 60}
    assert result["provider_gaps"] == ["openalex", "scielo_native"]

    ranking = Path(result["ranking_jsonl"])
    rows = [json.loads(line) for line in ranking.read_text().splitlines()]
    assert len(rows) == 100
    assert rows[0]["bank_processing_tier"] == "A"
    assert rows[1]["bank_processing_tier"] == "A"
    assert rows[2]["bank_processing_tier"] == "B"
    assert rows[39]["bank_processing_tier"] == "C"
    assert rows[40]["bank_processing_tier"] == "D"
    assert all(row["audit_quarantined"] is False for row in rows)
    assert all(row["audit_source_run_id"] == search_id for row in rows)

    manifest = json.loads(Path(result["bank_import_manifest"]).read_text())
    assert manifest["initial_materialization"]["network_full_text_retrieval"] is False
    assert manifest["initial_materialization"]["external_llm_calls"] == 0
    assert manifest["guardrails"] if "guardrails" in manifest else True

    audit = json.loads(Path(result["audit_manifest"]).read_text())
    expected = audit["outputs"]["ranking_jsonl"]["sha256"]
    assert expected == sha256(ranking.read_bytes()).hexdigest()
    assert audit["guardrails"]["prisma_event_not_created"] is True


def test_prepare_search_for_bank_rejects_unfinished_run(tmp_path: Path) -> None:
    search_id = _write_search(tmp_path, n=2, status="RUNNING")
    with pytest.raises(SearchBankError, match="não está concluída"):
        prepare_search_for_bank(search_id, output_root=tmp_path)
