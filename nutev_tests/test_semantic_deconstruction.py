from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.cli import main as cli_main
from nutev.science import (
    SemanticDeconstructionError,
    build_semantic_layer,
    extract_semantic_facts,
    run_semantic_deconstruction,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _enrichment(document_id: str = "doi:10.1000/semantic.1") -> dict:
    return {
        "id": f"enrichment:{document_id}",
        "document_id": document_id,
        "extraction_method": "pdf_text",
        "text_sha256": "abc123",
        "text_chars": 12000,
        "ocr_used": False,
        "blocks": [
            {
                "id": f"{document_id}:block:1",
                "kind": "section",
                "heading": "Abstract",
                "locator": "section:Abstract",
                "text": (
                    "The objective was to evaluate a nutrition intervention in adult athletes. "
                    "The primary outcome was change in recovery score."
                ),
            },
            {
                "id": f"{document_id}:block:2",
                "kind": "section",
                "heading": "Methods",
                "locator": "section:Methods",
                "text": (
                    "We enrolled 84 adult athletes from two training centers. "
                    "Participants were randomized to receive a nutrition intervention. "
                    "The control group received placebo and usual care. "
                    "The intervention lasted 12 weeks. "
                    "The primary outcome was recovery score measured at week 12. "
                    "Participants were eligible if they were 18 years or older."
                ),
            },
            {
                "id": f"{document_id}:block:3",
                "kind": "section",
                "heading": "Results",
                "locator": "section:Results",
                "text": (
                    "The intervention improved the primary outcome compared with control "
                    "(OR=1.42, 95% CI 1.05 to 1.92, p=0.03). "
                    "Table 2 summarizes the primary outcome and Figure 1 shows change over time."
                ),
            },
            {
                "id": f"{document_id}:block:4",
                "kind": "section",
                "heading": "Discussion",
                "locator": "section:Discussion",
                "text": (
                    "A limitation was the small sample and single-center recruitment. "
                    "The study was funded by the Example Foundation. "
                    "The authors declare no conflict of interest."
                ),
            },
        ],
        "content_signals": {
            "study_design_signals": ["randomized controlled trial"],
        },
        "warnings": [],
    }


def _classification() -> dict:
    return {
        "document_class": "primary_randomized",
        "study_design_candidates": ["randomized controlled trial"],
    }


def test_semantic_facts_are_traceable_and_cover_core_fields():
    facts = extract_semantic_facts(
        "doi:10.1000/semantic.1",
        _enrichment(),
        _classification(),
    )
    fields = {fact.field for fact in facts}

    assert {
        "objective",
        "population",
        "sample_size",
        "intervention",
        "comparator",
        "outcome",
        "duration",
        "effect_measure",
        "p_value",
        "confidence_interval",
        "eligibility_criteria",
        "limitation",
        "funding",
        "conflict_of_interest",
        "table_reference",
        "figure_reference",
    }.issubset(fields)
    assert all(fact.source_excerpt for fact in facts)
    assert all(len(fact.source_sha256) == 64 for fact in facts)
    assert all(fact.status == "machine_candidate" for fact in facts)


def test_semantic_layer_marks_pico_as_candidate_not_truth():
    semantic = build_semantic_layer(
        "doi:10.1000/semantic.1",
        _enrichment(),
        _classification(),
    )

    assert semantic["status"] == "machine_candidates_materialized"
    assert any(item["framework"] == "PICO" for item in semantic["framework_candidates"])
    assert semantic["guardrails"]["no_fact_is_an_accepted_evidence_claim"] is True
    assert semantic["guardrails"]["prisma_not_required"] is True
    assert semantic["coverage_score"]["semantic_kind"] == "technical_semantic_coverage"
    assert semantic["coverage_score"]["normalized_score"] > 70


def test_semantic_does_not_fabricate_comparator_when_not_present():
    enrichment = _enrichment()
    methods = enrichment["blocks"][1]
    methods["text"] = (
        "We enrolled 84 adult athletes. Participants received a nutrition intervention for 12 weeks. "
        "The primary outcome was recovery score."
    )
    facts = extract_semantic_facts(
        "doi:10.1000/semantic.1",
        enrichment,
        _classification(),
    )
    assert "comparator" not in {fact.field for fact in facts}


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    document_id = "doi:10.1000/semantic.1"
    records = tmp_path / "nutev_core_records.jsonl"
    core_record = {
        "id": f"nutev-core:{document_id}",
        "document_id": document_id,
        "schema_version": 1,
        "identity": {"title": "Semantic trial", "doi": "10.1000/semantic.1"},
        "classification": _classification(),
        "workflow": {"prisma": "optional_downstream"},
        "guardrails": {"prisma_is_optional": True},
    }
    records.write_text(json.dumps(core_record) + "\n", encoding="utf-8")
    core_manifest = tmp_path / "CORE_MANIFEST.json"
    core_manifest.write_text(
        json.dumps(
            {
                "core_type": "NUTEV_CORE_EVIDENCE_BANK",
                "status": "PASS",
                "outputs": {
                    "core_records": {"path": str(records), "sha256": _sha(records)}
                },
            }
        ),
        encoding="utf-8",
    )

    enrichments = tmp_path / "document_enrichments.jsonl"
    enrichments.write_text(json.dumps(_enrichment()) + "\n", encoding="utf-8")
    enrichment_manifest = tmp_path / "ENRICHMENT_MANIFEST.json"
    enrichment_manifest.write_text(
        json.dumps(
            {
                "enrichment_type": "NUTEV_PRE_SCREENING_DOCUMENT_ENRICHMENT",
                "status": "PASS",
                "outputs": {
                    "document_enrichments": {
                        "path": str(enrichments),
                        "sha256": _sha(enrichments),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return records, core_manifest, enrichments, enrichment_manifest


def test_run_semantic_deconstruction_creates_macro_record_v2(tmp_path: Path):
    records, core_manifest, enrichments, enrichment_manifest = _write_inputs(tmp_path)
    output = tmp_path / "semantic"

    result = run_semantic_deconstruction(
        records,
        core_manifest,
        enrichments,
        enrichment_manifest,
        output,
    )

    assert result["status"] == "COMPLETE"
    assert result["prisma_required"] is False
    row = json.loads((output / "nutev_core_records_semantic.jsonl").read_text().strip())
    assert row["schema_version"] == 2
    assert row["semantic"]["status"] == "machine_candidates_materialized"
    assert row["workflow"]["semantic_deconstruction"] == "materialized"
    assert row["workflow"]["prisma"] == "optional_downstream"
    assert (output / "semantic_fact_candidates.jsonl").is_file()
    assert (output / "semantic_scorecards.jsonl").is_file()
    assert (output / "SEMANTIC_MANIFEST.json").is_file()


def test_semantic_hash_mismatch_fails_closed(tmp_path: Path):
    records, core_manifest, enrichments, enrichment_manifest = _write_inputs(tmp_path)
    records.write_text(records.read_text() + "\n", encoding="utf-8")

    with pytest.raises(SemanticDeconstructionError, match="SHA-256 mismatch"):
        run_semantic_deconstruction(
            records,
            core_manifest,
            enrichments,
            enrichment_manifest,
            tmp_path / "semantic",
        )


def test_cli_science_semantic(tmp_path: Path, capsys):
    records, core_manifest, enrichments, enrichment_manifest = _write_inputs(tmp_path)
    output = tmp_path / "semantic"

    code = cli_main(
        [
            "science-semantic",
            "--core-records-jsonl",
            str(records),
            "--core-manifest",
            str(core_manifest),
            "--enrichments-jsonl",
            str(enrichments),
            "--enrichment-manifest",
            str(enrichment_manifest),
            "--output-dir",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "NUTEV_CORE_SEMANTIC_DECONSTRUCTION"' in captured.out
    assert '"prisma_required": false' in captured.out
