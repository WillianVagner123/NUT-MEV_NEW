from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from nutev.cli import main as cli_main
from nutev.science import EvidenceExcerptError, run_evidence_excerpt_extraction


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _sentence_sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _fact(
    document_id: str,
    field: str,
    value: str,
    section: str,
    locator: str,
    sentence: str,
    confidence: float = 0.9,
) -> dict:
    digest = _sentence_sha(sentence)
    return {
        "id": f"semantic:{document_id}:{field}:{digest[:8]}",
        "document_id": document_id,
        "field": field,
        "value": value,
        "section": section,
        "locator": locator,
        "source_excerpt": sentence,
        "source_sha256": digest,
        "extraction_method": "rule_v1",
        "extraction_confidence": confidence,
        "status": "machine_candidate",
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    document_id = "doi:10.1000/excerpts.1"
    objective = "The objective was to evaluate a nutrition intervention in adult athletes."
    method = "We enrolled 84 adult athletes and randomized participants to intervention or control."
    result = (
        "The intervention improved the primary outcome compared with control "
        "(OR=1.42, 95% CI 1.05 to 1.92, p=0.03)."
    )
    secondary = "Recovery score increased by 18% in the intervention group compared with control."
    conclusion = "The nutrition intervention improved recovery outcomes over 12 weeks."
    limitation = "A limitation was the small sample and single-center recruitment."

    record = {
        "id": f"nutev-core:{document_id}",
        "document_id": document_id,
        "schema_version": 2,
        "identity": {
            "title": "Nutrition intervention and recovery",
            "doi": "10.1000/excerpts.1",
            "pmid": "12345678",
            "url": "https://example.org/article",
            "year": 2026,
            "source_provider": "pubmed",
        },
        "bibliographic": {
            "authors": ["Ana Silva", "Bruno Costa"],
            "journal": "Journal of Example Nutrition",
            "article_type": "Randomized Controlled Trial",
        },
        "acquisition": {
            "full_text_status": "retrieved",
            "text_sha256": "abc123fulltextsha",
        },
        "classification": {"document_class": "primary_randomized"},
        "main_findings": [
            {
                "id": f"finding:{document_id}:main",
                "document_id": document_id,
                "section": "Results",
                "locator": "section:Results:p3",
                "source_excerpt": result,
                "sentence_sha256": _sentence_sha(result),
                "importance_score": 10.0,
                "signals": ["effect", "significance"],
                "status": "machine_candidate",
            },
            {
                "id": f"finding:{document_id}:secondary",
                "document_id": document_id,
                "section": "Results",
                "locator": "section:Results:p4",
                "source_excerpt": secondary,
                "sentence_sha256": _sentence_sha(secondary),
                "importance_score": 7.0,
                "signals": ["increase", "percentage"],
                "status": "machine_candidate",
            },
            {
                "id": f"finding:{document_id}:conclusion",
                "document_id": document_id,
                "section": "Conclusion",
                "locator": "section:Conclusion:p1",
                "source_excerpt": conclusion,
                "sentence_sha256": _sentence_sha(conclusion),
                "importance_score": 6.0,
                "signals": ["effect"],
                "status": "machine_candidate",
            },
        ],
        "workflow": {"prisma": "optional_downstream"},
        "guardrails": {"semantic_facts_are_machine_candidates": True},
    }

    facts = [
        _fact(document_id, "objective", objective, "Abstract", "section:Abstract:p1", objective, 0.8),
        _fact(document_id, "population", method, "Methods", "section:Methods:p1", method, 0.7),
        _fact(document_id, "sample_size", "84", "Methods", "section:Methods:p1", method, 0.95),
        _fact(document_id, "intervention", method, "Methods", "section:Methods:p1", method, 0.7),
        _fact(document_id, "outcome", "primary outcome", "Results", "section:Results:p3", result, 0.7),
        _fact(document_id, "effect_measure", "OR=1.42", "Results", "section:Results:p3", result, 0.95),
        _fact(document_id, "confidence_interval", "95% CI 1.05 to 1.92", "Results", "section:Results:p3", result, 0.95),
        _fact(document_id, "p_value", "p=0.03", "Results", "section:Results:p3", result, 0.97),
        _fact(document_id, "limitation", limitation, "Discussion", "section:Discussion:p5", limitation, 0.85),
    ]

    records_path = tmp_path / "nutev_core_records_semantic.jsonl"
    facts_path = tmp_path / "semantic_fact_candidates.jsonl"
    manifest_path = tmp_path / "SEMANTIC_MANIFEST.json"
    records_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    facts_path.write_text(
        "".join(json.dumps(row) + "\n" for row in facts),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "semantic_type": "NUTEV_CORE_SEMANTIC_DECONSTRUCTION",
                "status": "PASS",
                "outputs": {
                    "semantic_core_records": {
                        "path": str(records_path),
                        "sha256": _sha(records_path),
                    },
                    "semantic_fact_candidates": {
                        "path": str(facts_path),
                        "sha256": _sha(facts_path),
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return records_path, facts_path, manifest_path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_evidence_excerpt_stage_builds_quotes_results_and_low_token_card(tmp_path: Path):
    records, facts, manifest = _write_inputs(tmp_path)
    output = tmp_path / "excerpts"

    result = run_evidence_excerpt_extraction(records, facts, manifest, output)

    assert result["status"] == "COMPLETE"
    assert result["cache_hit"] is False
    assert result["llm_calls"] == 0
    assert result["prisma_required"] is False

    excerpts = _read_jsonl(output / "evidence_excerpts.jsonl")
    kinds = {row["kind"] for row in excerpts}
    assert {"objective", "method", "main_result", "secondary_result", "conclusion", "limitation"}.issubset(kinds)
    assert all(row["verbatim_excerpt"] for row in excerpts)
    assert all(len(row["excerpt_sha256"]) == 64 for row in excerpts)
    assert all(row["reference"]["doi"] == "10.1000/excerpts.1" for row in excerpts)

    bundles = _read_jsonl(output / "result_bundles.jsonl")
    main = next(row for row in bundles if row["result_kind"] == "main_result")
    assert main["effect_measures"] == ["OR=1.42"]
    assert main["confidence_intervals"] == ["95% CI 1.05 to 1.92"]
    assert main["p_values"] == ["p=0.03"]
    assert main["status"] == "machine_candidate_not_evidence_claim"

    cards = _read_jsonl(output / "article_evidence_cards.jsonl")
    assert len(cards) == 1
    card = cards[0]
    assert card["token_cost_policy"]["external_llm_calls"] == 0
    assert card["token_cost_policy"]["full_text_sent_to_llm"] is False
    assert card["llm_context_chars"] <= 6000
    assert card["reference"]["reference_stub"].startswith("Ana Silva, Bruno Costa")
    assert len(card["cache_key"]) == 64
    assert card["workflow"]["claim_promotion"] == "not_performed"

    excerpt_manifest = json.loads((output / "EXCERPT_MANIFEST.json").read_text())
    assert excerpt_manifest["status"] == "PASS"
    assert excerpt_manifest["token_cost_policy"]["llm_calls"] == 0
    assert excerpt_manifest["assertions"][2]["name"] == "result_bundles_not_promoted_to_claims"


def test_evidence_excerpt_stage_reuses_verified_run_cache(tmp_path: Path):
    records, facts, manifest = _write_inputs(tmp_path)
    output = tmp_path / "excerpts"
    first = run_evidence_excerpt_extraction(records, facts, manifest, output)
    second = run_evidence_excerpt_extraction(records, facts, manifest, output)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["llm_calls"] == 0
    assert second["evidence_excerpts"] == first["evidence_excerpts"]
    assert second["result_bundles"] == first["result_bundles"]


def test_evidence_excerpt_stage_fails_closed_on_semantic_hash_mismatch(tmp_path: Path):
    records, facts, manifest = _write_inputs(tmp_path)
    facts.write_text(facts.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(EvidenceExcerptError, match="SHA-256 mismatch"):
        run_evidence_excerpt_extraction(
            records,
            facts,
            manifest,
            tmp_path / "excerpts",
        )


def test_cli_science_excerpts(tmp_path: Path, capsys):
    records, facts, manifest = _write_inputs(tmp_path)
    output = tmp_path / "excerpts"

    code = cli_main(
        [
            "science-excerpts",
            "--semantic-records-jsonl",
            str(records),
            "--semantic-facts-jsonl",
            str(facts),
            "--semantic-manifest",
            str(manifest),
            "--output-dir",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert '"mode": "NUTEV_EVIDENCE_EXCERPTS_RESULTS"' in captured.out
    assert '"llm_calls": 0' in captured.out
