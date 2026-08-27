from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest

from nutev.cli import main as cli_main
from nutev.science import NutEVCoreError, run_core_bank_export


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> dict[str, Path]:
    document_id = "doi:10.1000/core.1"
    documents = tmp_path / "document_candidates.jsonl"
    evidence = tmp_path / "evidence_records.jsonl"
    artifacts = tmp_path / "full_text_artifacts.jsonl"
    enrichments = tmp_path / "document_enrichments.jsonl"
    dossiers = tmp_path / "reviewer_dossiers.jsonl"

    _jsonl(
        documents,
        [
            {
                "id": document_id,
                "source_provider": "pubmed",
                "title": "Nutrition intervention and performance outcomes",
                "doi": "10.1000/core.1",
                "pmid": "12345678",
                "url": "https://example.org/article",
                "year": 2025,
                "metadata": {
                    "abstract": "A randomized controlled trial evaluated nutrition outcomes.",
                    "journal": "Example Journal",
                    "authors": "A Author; B Author",
                    "article_type": "Randomized Controlled Trial",
                    "keywords": ["nutrition", "performance"],
                    "reference_rank": 3,
                    "reference_score": 87.5,
                    "reference_tier": "A_TOP_REFERENCE",
                    "audit_traceability": {"status": "PASS"},
                },
            }
        ],
    )
    _jsonl(
        evidence,
        [
            {
                "id": f"evidence:{document_id}",
                "document_id": document_id,
                "source_provider": "pubmed",
                "source_run_id": "run-1",
                "origin_sha256": "a" * 64,
                "taxonomy": ["nutrition", "performance"],
                "metadata": {"audit_source_manifest_path": "manifest.json"},
            }
        ],
    )
    _jsonl(
        artifacts,
        [
            {
                "id": f"artifact:{document_id}",
                "document_id": document_id,
                "retrieval_status": "retrieved",
                "source_url": "https://example.org/article.pdf",
                "local_path": str(tmp_path / "private.pdf"),
                "media_type": "application/pdf",
                "sha256": "b" * 64,
                "retrieved_at": "2026-08-26T20:00:00+00:00",
                "metadata": {"retrieval_route": "provided_local_asset"},
            }
        ],
    )
    _jsonl(
        enrichments,
        [
            {
                "id": f"enrichment:{document_id}",
                "document_id": document_id,
                "artifact_id": f"artifact:{document_id}",
                "extraction_method": "pdf_text",
                "text_sha256": "c" * 64,
                "text_chars": 9000,
                "ocr_used": False,
                "ocr_engine": None,
                "blocks": [
                    {
                        "id": f"{document_id}:block:1",
                        "kind": "section",
                        "heading": "Introduction",
                        "text": "Nutrition strategies are commonly evaluated in athletes.",
                        "locator": "section:Introduction",
                        "page": 1,
                    },
                    {
                        "id": f"{document_id}:block:2",
                        "kind": "section",
                        "heading": "Methods",
                        "text": "This randomized controlled trial enrolled n=84 adults and compared two nutrition strategies.",
                        "locator": "section:Methods",
                        "page": 2,
                    },
                    {
                        "id": f"{document_id}:block:3",
                        "kind": "section",
                        "heading": "Results",
                        "text": (
                            "The intervention group had significantly higher performance scores compared with control. "
                            "Mean dietary adherence increased by 18% during follow-up. "
                            "No difference was observed for body mass between groups."
                        ),
                        "locator": "section:Results",
                        "page": 6,
                    },
                    {
                        "id": f"{document_id}:block:4",
                        "kind": "section",
                        "heading": "Conclusion",
                        "text": "The nutrition intervention improved adherence and performance outcomes in this sample.",
                        "locator": "section:Conclusion",
                        "page": 9,
                    },
                ],
                "content_signals": {
                    "section_headings": ["Introduction", "Methods", "Results", "Conclusion"],
                    "study_design_signals": ["randomized controlled trial"],
                    "sample_size_mentions": ["n=84"],
                    "table_mentions": ["Table 1", "Table 2"],
                    "figure_mentions": ["Figure 1"],
                    "frequent_terms": [
                        {"term": "nutrition", "count": 12},
                        {"term": "performance", "count": 10},
                        {"term": "intervention", "count": 8},
                        {"term": "adherence", "count": 7},
                        {"term": "outcomes", "count": 5},
                    ],
                },
                "warnings": [],
                "metadata": {"private_text_path": str(tmp_path / "article.txt")},
            }
        ],
    )
    _jsonl(
        dossiers,
        [
            {
                "id": f"dossier:{document_id}",
                "document_id": document_id,
                "title": "Nutrition intervention and performance outcomes",
                "source_provider": "pubmed",
                "year": 2025,
                "doi": "10.1000/core.1",
                "pmid": "12345678",
                "url": "https://example.org/article",
                "abstract": "A randomized controlled trial evaluated nutrition outcomes.",
                "journal": "Example Journal",
                "authors": "A Author; B Author",
                "article_type": "Randomized Controlled Trial",
                "full_text_status": "retrieved",
                "extraction_method": "pdf_text",
                "ocr_used": False,
                "text_chars": 9000,
                "section_map": [
                    {"heading": "Methods", "locator": "section:Methods", "chars": 100},
                    {"heading": "Results", "locator": "section:Results", "chars": 250},
                    {"heading": "Conclusion", "locator": "section:Conclusion", "chars": 100},
                ],
                "content_signals": {},
                "warnings": [],
                "guardrails": {
                    "blind_to_nutev_rank": True,
                    "blind_to_nutev_taxonomy": True,
                },
            }
        ],
    )

    science_manifest = tmp_path / "SCIENTIFIC_EXPORT_MANIFEST.json"
    science_manifest.write_text(
        json.dumps(
            {
                "export_type": "NUTEV_SCIENTIFIC_OBJECT_EXPORT",
                "status": "PASS",
                "outputs": {
                    "document_candidates": {
                        "path": str(documents),
                        "sha256": _sha(documents),
                    },
                    "evidence_records": {
                        "path": str(evidence),
                        "sha256": _sha(evidence),
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    enrichment_manifest = tmp_path / "ENRICHMENT_MANIFEST.json"
    enrichment_manifest.write_text(
        json.dumps(
            {
                "enrichment_type": "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT",
                "status": "PASS",
                "outputs": {
                    "full_text_artifacts": {
                        "path": str(artifacts),
                        "sha256": _sha(artifacts),
                    },
                    "document_enrichments": {
                        "path": str(enrichments),
                        "sha256": _sha(enrichments),
                    },
                    "reviewer_dossiers": {
                        "path": str(dossiers),
                        "sha256": _sha(dossiers),
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    return {
        "documents": documents,
        "evidence": evidence,
        "science_manifest": science_manifest,
        "artifacts": artifacts,
        "enrichments": enrichments,
        "dossiers": dossiers,
        "enrichment_manifest": enrichment_manifest,
    }


def _run(paths: dict[str, Path], output: Path, *, mev_profile: Path | None = None):
    return run_core_bank_export(
        paths["documents"],
        paths["evidence"],
        paths["science_manifest"],
        paths["artifacts"],
        paths["enrichments"],
        paths["dossiers"],
        paths["enrichment_manifest"],
        output,
        mev_profile=mev_profile,
    )


def _first_jsonl(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def test_core_record_is_macro_bank_record_and_prisma_is_optional(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "core"

    result = _run(paths, output)

    assert result["status"] == "COMPLETE"
    assert result["prisma_required"] is False
    record = _first_jsonl(output / "nutev_core_records.jsonl")
    assert record["identity"]["doi"] == "10.1000/core.1"
    assert record["provenance"]["source_run_id"] == "run-1"
    assert record["acquisition"]["extraction_method"] == "pdf_text"
    assert record["classification"]["document_class"] == "primary_randomized"
    assert record["workflow"]["prisma"] == "optional_downstream"
    assert record["workflow"]["screening_required_for_core"] is False
    assert record["reference_layer"]["reference_rank"] == 3
    assert record["scores"]["mev"]["status"] == "not_scored"
    assert record["scores"]["core_readiness"]["semantic_kind"] == "technical_record_readiness"
    assert record["scores"]["core_readiness"]["normalized_score"] > 80


def test_core_extracts_traceable_major_finding_candidates(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "core"

    _run(paths, output)

    findings = [
        json.loads(line)
        for line in (output / "finding_candidates.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert findings
    assert any(item["section"] == "Results" for item in findings)
    assert all(item["status"] == "machine_candidate" for item in findings)
    assert all(item["locator"] for item in findings)
    assert all(len(item["sentence_sha256"]) == 64 for item in findings)


def test_core_writes_queryable_sqlite_bank(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "core"

    _run(paths, output)

    database = output / "nutev_core.sqlite"
    connection = sqlite3.connect(database)
    try:
        record = connection.execute(
            "SELECT document_class, core_readiness_score FROM core_records"
        ).fetchone()
        finding_count = connection.execute(
            "SELECT COUNT(*) FROM finding_candidates"
        ).fetchone()[0]
        prisma_dependency = connection.execute(
            "SELECT value FROM bank_meta WHERE key = 'prisma_dependency'"
        ).fetchone()[0]
    finally:
        connection.close()

    assert record[0] == "primary_randomized"
    assert record[1] > 80
    assert finding_count >= 1
    assert prisma_dependency == "optional_downstream"


def test_mev_scoring_requires_and_preserves_versioned_profile(tmp_path: Path):
    paths = _fixture(tmp_path)
    profile = tmp_path / "mev.json"
    profile.write_text(
        json.dumps(
            {
                "profile_id": "MEV_CANONICAL_TEST",
                "version": "1.0.0",
                "semantic_kind": "mev_test_score",
                "blocks": [
                    {
                        "id": "structure",
                        "label": "Structure",
                        "max_score": 10,
                        "rules": [
                            {
                                "field": "classification.section_coverage.has_methods",
                                "operator": "truthy",
                                "points": 5,
                            },
                            {
                                "field": "classification.document_class",
                                "operator": "equals",
                                "value": "primary_randomized",
                                "points": 5,
                            },
                        ],
                    },
                    {
                        "id": "access",
                        "label": "Access",
                        "max_score": 5,
                        "rules": [
                            {
                                "field": "acquisition.full_text_status",
                                "operator": "equals",
                                "value": "retrieved",
                                "points": 5,
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "core"

    result = _run(paths, output, mev_profile=profile)

    assert result["mev_scored_records"] == 1
    record = _first_jsonl(output / "nutev_core_records.jsonl")
    mev = record["scores"]["mev"]
    assert mev["status"] == "scored_configured_profile"
    assert mev["profile_id"] == "MEV_CANONICAL_TEST"
    assert mev["profile_version"] == "1.0.0"
    assert mev["normalized_score"] == 100.0
    assert [block["id"] for block in mev["blocks"]] == ["structure", "access"]


def test_core_fails_closed_when_enrichment_hash_changes(tmp_path: Path):
    paths = _fixture(tmp_path)
    with paths["enrichments"].open("a", encoding="utf-8") as handle:
        handle.write("{}\n")

    with pytest.raises(NutEVCoreError, match="SHA-256 mismatch"):
        _run(paths, tmp_path / "core")


def test_cli_science_core_materializes_bank_without_prisma(tmp_path: Path, capsys):
    paths = _fixture(tmp_path)
    output = tmp_path / "core"

    code = cli_main(
        [
            "science-core",
            "--documents-jsonl",
            str(paths["documents"]),
            "--evidence-records-jsonl",
            str(paths["evidence"]),
            "--science-manifest",
            str(paths["science_manifest"]),
            "--artifacts-jsonl",
            str(paths["artifacts"]),
            "--enrichments-jsonl",
            str(paths["enrichments"]),
            "--dossiers-jsonl",
            str(paths["dossiers"]),
            "--enrichment-manifest",
            str(paths["enrichment_manifest"]),
            "--output-dir",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "NUTEV_CORE_EVIDENCE_BANK"' in captured.out
    assert '"prisma_required": false' in captured.out
    assert (output / "nutev_core_records.jsonl").is_file()
    assert (output / "nutev_core.sqlite").is_file()
    assert (output / "CORE_MANIFEST.json").is_file()
