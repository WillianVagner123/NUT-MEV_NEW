from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.science import ScientificExportError, run_scientific_export


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_ranking(path: Path) -> None:
    row = {
        "reference_rank": 1,
        "reference_tier": "A_TOP_REFERENCE",
        "reference_score": 87.0,
        "reference_provider": "pubmed",
        "reference_year": 2024,
        "title": "Protein intake and fat-free mass retention",
        "doi": "10.1000/example.1",
        "url": "https://doi.org/10.1000/example.1",
        "taxonomy_primary": "domain.protein",
        "taxonomy_secondary": ["outcome.fat_free_mass"],
        "audit_traceability": "A_IDENTIFIER",
        "audit_quarantined": False,
        "audit_origin_sha256": "origin-sha",
        "audit_source_run_id": "run-123",
        "audit_source_master_sha256": "master-sha",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _write_manifest(path: Path, ranking: Path, *, ranking_sha: str | None = None) -> None:
    manifest = {
        "audit_type": "REFERENCE_RANKING_AUDIT",
        "status": "PASS",
        "outputs": {
            "ranking_jsonl": {
                "path": str(ranking),
                "sha256": ranking_sha or _sha(ranking),
            }
        },
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_scientific_export_creates_traceable_objects_without_claims(tmp_path: Path):
    ranking = tmp_path / "reference_ranking.jsonl"
    audit = tmp_path / "AUDIT_MANIFEST.json"
    output = tmp_path / "scientific"
    _write_ranking(ranking)
    _write_manifest(audit, ranking)

    result = run_scientific_export(ranking, audit, output)

    assert result["status"] == "COMPLETE"
    document = json.loads((output / "document_candidates.jsonl").read_text().strip())
    evidence = json.loads((output / "evidence_records.jsonl").read_text().strip())
    event = json.loads((output / "scientific_events.jsonl").read_text().strip())
    manifest = json.loads((output / "SCIENTIFIC_EXPORT_MANIFEST.json").read_text())

    assert document["id"] == "doi:10.1000/example.1"
    assert document["source_provider"] == "pubmed"
    assert document["year"] == 2024
    assert evidence["document_id"] == document["id"]
    assert evidence["source_run_id"] == "run-123"
    assert evidence["taxonomy"] == ["domain.protein", "outcome.fat_free_mass"]
    assert event["action"] == "entered_scientific_layer"
    assert manifest["counts"]["evidence_claims"] == 0
    assert manifest["counts"]["recommendation_candidates"] == 0
    assert manifest["prisma_from_explicit_events"]["identified"] == 0
    assert manifest["prisma_from_explicit_events"]["included"] == 0


def test_scientific_export_fails_closed_on_ranking_hash_mismatch(tmp_path: Path):
    ranking = tmp_path / "reference_ranking.jsonl"
    audit = tmp_path / "AUDIT_MANIFEST.json"
    _write_ranking(ranking)
    _write_manifest(audit, ranking, ranking_sha="0" * 64)

    with pytest.raises(ScientificExportError, match="SHA-256 mismatch"):
        run_scientific_export(ranking, audit, tmp_path / "scientific")


def test_scientific_export_rejects_quarantined_ranked_row(tmp_path: Path):
    ranking = tmp_path / "reference_ranking.jsonl"
    audit = tmp_path / "AUDIT_MANIFEST.json"
    row = {
        "reference_rank": 1,
        "reference_provider": "pubmed",
        "title": "Should not pass",
        "doi": "10.1000/example.2",
        "audit_quarantined": True,
    }
    ranking.write_text(json.dumps(row) + "\n", encoding="utf-8")
    _write_manifest(audit, ranking)

    with pytest.raises(ScientificExportError, match="marked quarantined"):
        run_scientific_export(ranking, audit, tmp_path / "scientific")
