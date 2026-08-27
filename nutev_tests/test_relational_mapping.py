from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest

from nutev.cli import main as cli_main
from nutev.science import (
    RelationalMappingError,
    build_relational_layer,
    run_relational_mapping,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _sentence_sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fact(
    document_id: str,
    fact_id: str,
    field: str,
    value: str,
    sentence: str,
    locator: str,
    section: str,
) -> dict:
    return {
        "id": fact_id,
        "document_id": document_id,
        "field": field,
        "value": value,
        "section": section,
        "locator": locator,
        "source_excerpt": sentence,
        "source_sha256": _sentence_sha(sentence),
        "extraction_method": "rule_v1",
        "extraction_confidence": 0.9,
        "status": "machine_candidate",
    }


def _fixture(tmp_path: Path) -> dict[str, Path]:
    document_id = "doi:10.1000/relations.1"
    method_sentence = (
        "Participants were randomized to receive a protein supplement or placebo control."
    )
    result_sentence = (
        "At 12-week follow-up the primary outcome improved with OR=1.42, "
        "95% CI 1.05 to 1.92 and p=0.03 as reported in Table 2."
    )
    facts = [
        _fact(
            document_id,
            "fact-pop",
            "population",
            "Participants were adult athletes.",
            "Participants were adult athletes.",
            "section:Methods",
            "Methods",
        ),
        _fact(
            document_id,
            "fact-n",
            "sample_size",
            "84",
            "The study enrolled n=84 participants.",
            "section:Methods",
            "Methods",
        ),
        _fact(
            document_id,
            "fact-int",
            "intervention",
            method_sentence,
            method_sentence,
            "section:Methods",
            "Methods",
        ),
        _fact(
            document_id,
            "fact-comp",
            "comparator",
            method_sentence,
            method_sentence,
            "section:Methods",
            "Methods",
        ),
        _fact(
            document_id,
            "fact-outcome",
            "outcome",
            result_sentence,
            result_sentence,
            "section:Results",
            "Results",
        ),
        _fact(
            document_id,
            "fact-followup",
            "follow_up",
            result_sentence,
            result_sentence,
            "section:Results",
            "Results",
        ),
        _fact(
            document_id,
            "fact-effect",
            "effect_measure",
            "OR=1.42",
            result_sentence,
            "section:Results",
            "Results",
        ),
        _fact(
            document_id,
            "fact-ci",
            "confidence_interval",
            "95% CI 1.05 to 1.92",
            result_sentence,
            "section:Results",
            "Results",
        ),
        _fact(
            document_id,
            "fact-p",
            "p_value",
            "p=0.03",
            result_sentence,
            "section:Results",
            "Results",
        ),
        _fact(
            document_id,
            "fact-table",
            "table_reference",
            "Table 2",
            result_sentence,
            "section:Results",
            "Results",
        ),
    ]
    record = {
        "id": f"nutev-core:{document_id}",
        "document_id": document_id,
        "schema_version": 2,
        "identity": {"title": "Example relation study", "doi": "10.1000/relations.1"},
        "classification": {"document_class": "primary_randomized"},
        "semantic": {
            "schema_version": 1,
            "status": "machine_candidates_materialized",
            "facts": facts,
            "guardrails": {"facts_are_machine_candidates": True},
        },
        "workflow": {"semantic_deconstruction": "materialized", "prisma": "optional_downstream"},
        "guardrails": {"prisma_is_optional": True},
    }

    records = tmp_path / "nutev_core_records_semantic.jsonl"
    facts_path = tmp_path / "semantic_fact_candidates.jsonl"
    _write_jsonl(records, [record])
    _write_jsonl(facts_path, facts)
    manifest = tmp_path / "SEMANTIC_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "semantic_type": "NUTEV_CORE_SEMANTIC_DECONSTRUCTION",
                "status": "PASS",
                "outputs": {
                    "semantic_core_records": {
                        "path": str(records),
                        "sha256": _sha(records),
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
    return {"records": records, "facts": facts_path, "manifest": manifest}


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_relations_link_arms_outcome_timepoint_and_effect_bundle(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "relations"

    result = run_relational_mapping(
        paths["records"], paths["facts"], paths["manifest"], output
    )

    assert result["status"] == "COMPLETE"
    assert result["prisma_required"] is False
    relation_rows = _read_jsonl(output / "scientific_relation_candidates.jsonl")
    relation_types = {row["relation_type"] for row in relation_rows}
    assert "compared_with" in relation_types
    assert "effect_estimate_for" in relation_types
    assert "effect_has_confidence_interval" in relation_types
    assert "effect_has_p_value" in relation_types
    assert "measured_at" in relation_types
    assert "reported_in" in relation_types
    assert all(row["status"] == "machine_candidate" for row in relation_rows)
    assert all(row["source_sha256"] for row in relation_rows)

    entities = _read_jsonl(output / "scientific_entity_candidates.jsonl")
    effect = next(row for row in entities if row["entity_type"] == "effect_estimate")
    assert effect["normalized"]["measure"] == "OR"
    assert effect["normalized"]["value"] == 1.42

    record = _read_jsonl(output / "nutev_core_records_relational.jsonl")[0]
    assert record["schema_version"] == 3
    assert record["workflow"]["relational_mapping"] == "materialized"
    assert record["workflow"]["prisma"] == "optional_downstream"
    assert record["relational"]["coverage_score"]["semantic_kind"] == "technical_relational_coverage"


def test_locator_fallback_does_not_cross_product_ambiguous_outcomes():
    document_id = "doi:10.1000/ambiguous"
    facts = [
        _fact(document_id, "o1", "outcome", "Outcome A", "Outcome A was assessed.", "section:Results", "Results"),
        _fact(document_id, "o2", "outcome", "Outcome B", "Outcome B was assessed.", "section:Results", "Results"),
        _fact(document_id, "e1", "effect_measure", "OR=1.20", "OR=1.20 was reported.", "section:Results", "Results"),
    ]

    relational = build_relational_layer(document_id, facts)

    assert not any(
        row["relation_type"] == "effect_estimate_for"
        for row in relational["relations"]
    )


def test_relational_sqlite_is_queryable(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "relations"
    run_relational_mapping(paths["records"], paths["facts"], paths["manifest"], output)

    connection = sqlite3.connect(output / "nutev_relations.sqlite")
    try:
        linked = connection.execute(
            "SELECT COUNT(*) FROM relations WHERE relation_type = 'effect_estimate_for'"
        ).fetchone()[0]
        arms = connection.execute(
            "SELECT COUNT(*) FROM entities WHERE entity_type = 'study_arm'"
        ).fetchone()[0]
        prisma = connection.execute(
            "SELECT value FROM relation_meta WHERE key = 'prisma_dependency'"
        ).fetchone()[0]
    finally:
        connection.close()

    assert linked >= 1
    assert arms >= 2
    assert prisma == "optional_downstream"


def test_relational_mapping_fails_closed_on_hash_mismatch(tmp_path: Path):
    paths = _fixture(tmp_path)
    paths["facts"].write_text("{}\n", encoding="utf-8")

    with pytest.raises(RelationalMappingError, match="SHA-256 mismatch"):
        run_relational_mapping(
            paths["records"], paths["facts"], paths["manifest"], tmp_path / "out"
        )


def test_relational_cli(tmp_path: Path):
    paths = _fixture(tmp_path)
    output = tmp_path / "relations"

    code = cli_main(
        [
            "science-relations",
            "--semantic-records-jsonl",
            str(paths["records"]),
            "--semantic-facts-jsonl",
            str(paths["facts"]),
            "--semantic-manifest",
            str(paths["manifest"]),
            "--output-dir",
            str(output),
        ]
    )

    assert code == 0
    assert (output / "RELATIONS_MANIFEST.json").is_file()
