"""Regression tests for GF-02 sentinel/noise/manual-execution evidence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.search.gf02_evidence import (
    ManualProviderEvidence,
    NoiseSampleRecord,
    SentinelRecord,
    compute_sentinel_recall,
    evaluate_gf02_gate,
    manual_execution_from_export,
    sentinel_matches_row,
    summarize_noise_sample,
    validate_gf02_pilot_strategy,
    validate_manual_provider_evidence,
    validate_sentinel_registry,
)


def _resolved(sentinel_id: str, *, doi: str) -> SentinelRecord:
    return SentinelRecord(
        sentinel_id=sentinel_id,
        canonical_title=f"Canonical {sentinel_id}",
        doi=doi,
        document_unit_rule="Canonical guideline publication only",
        identity_status="RESOLVED",
    )


def _manual(provider: str) -> ManualProviderEvidence:
    return ManualProviderEvidence(
        provider=provider,
        status="IMPORTED",
        expression="validated licensed-database expression",
        executed_at="2026-08-12T10:00:00-03:00",
        executor="R1",
        interface_name="licensed database web interface",
        total_reported=42,
        export_file="export.ris",
        export_sha256="a" * 64,
        sentinel_results={"NORM-035": True, "NORM-063": False},
        limitations="Manual licensed execution imported with audit metadata.",
    )


def test_unresolved_sentinel_never_counts_as_recovered_or_denominator():
    unresolved = SentinelRecord(sentinel_id="NORM-035", identity_status="UNRESOLVED")
    resolved = _resolved("NORM-063", doi="10.1000/norm063")

    report = compute_sentinel_recall(
        [unresolved, resolved],
        [
            {"title": "anything called NORM-035", "doi": "10.1000/other"},
            {"doi": "https://doi.org/10.1000/NORM063"},
        ],
        provider="pubmed",
        strategy_version="v0.3",
        route="indexed_database",
    )

    assert report["sentinels_declared"] == 2
    assert report["sentinels_resolved"] == 1
    assert report["sentinels_unresolved"] == 1
    assert report["recovered"] == 1
    assert report["recall"] == 1.0
    assert report["recovered_sentinel_ids"] == ["NORM-063"]
    assert report["unresolved_sentinel_ids"] == ["NORM-035"]


def test_resolved_sentinel_requires_canonical_identity():
    with pytest.raises(ValueError, match="lacks a complete canonical identity"):
        validate_sentinel_registry(
            [SentinelRecord(sentinel_id="NORM-035", identity_status="RESOLVED")]
        )


def test_duplicate_sentinel_ids_are_rejected_case_insensitively():
    with pytest.raises(ValueError, match="duplicate sentinel_id"):
        validate_sentinel_registry(
            [
                SentinelRecord(sentinel_id="NORM-035"),
                SentinelRecord(sentinel_id="norm-035"),
            ]
        )


def test_explicit_doi_prevents_derivative_title_from_satisfying_sentinel():
    sentinel = SentinelRecord(
        sentinel_id="NORM-035",
        canonical_title="Canonical guideline",
        doi="10.1000/canonical",
        document_unit_rule="Canonical guideline only; editorial is derivative",
        identity_status="RESOLVED",
        allow_title_match=True,
    )

    assert sentinel_matches_row(sentinel, {"doi": "10.1000/canonical"}) is True
    assert (
        sentinel_matches_row(
            sentinel,
            {"title": "Canonical guideline", "doi": "10.1000/editorial"},
        )
        is False
    )


def test_title_matching_requires_explicit_opt_in_and_identity_constraints():
    sentinel = SentinelRecord(
        sentinel_id="NORM-X",
        canonical_title="Official food guideline",
        issuer="Ministry of Health",
        version_year="2025",
        document_unit_rule="Current official version",
        identity_status="RESOLVED",
        allow_title_match=True,
    )

    assert sentinel_matches_row(
        sentinel,
        {
            "title": "Official Food Guideline",
            "issuer": "Ministry of Health",
            "year": "2025",
        },
    )
    assert not sentinel_matches_row(
        sentinel,
        {
            "title": "Official Food Guideline",
            "issuer": "Different publisher",
            "year": "2025",
        },
    )


def test_noise_summary_uses_frozen_classifications():
    rows = [
        NoiseSampleRecord(
            sample_id="sample-v03",
            record_id="1",
            provider="pubmed",
            strategy_version="v0.3",
            sampling_rule="first 4 records after deterministic sort",
            classification="likely_eligible",
            reviewer="R1",
        ),
        NoiseSampleRecord(
            sample_id="sample-v03",
            record_id="2",
            provider="pubmed",
            strategy_version="v0.3",
            sampling_rule="first 4 records after deterministic sort",
            classification="possibly_eligible",
            reviewer="R1",
        ),
        NoiseSampleRecord(
            sample_id="sample-v03",
            record_id="3",
            provider="pubmed",
            strategy_version="v0.3",
            sampling_rule="first 4 records after deterministic sort",
            classification="editorial",
            reviewer="R1",
        ),
        NoiseSampleRecord(
            sample_id="sample-v03",
            record_id="4",
            provider="pubmed",
            strategy_version="v0.3",
            sampling_rule="first 4 records after deterministic sort",
            classification="irrelevant",
            reviewer="R1",
        ),
    ]

    summary = summarize_noise_sample(rows)
    assert summary["sample_size"] == 4
    assert summary["estimated_precision"] == 0.5
    assert summary["noise_rate"] == 0.5
    assert summary["classification_counts"]["editorial"] == 1


def test_manual_required_status_is_not_executed_evidence():
    pending = ManualProviderEvidence(
        provider="scopus",
        status="MANUAL_EXECUTION_REQUIRED",
        expression="planned Scopus expression",
    )
    assert validate_manual_provider_evidence(pending) == pending

    strategy = {"search_type": "PILOT", "prisma_eligible": False}
    recall = {
        "recovered_sentinel_ids": ["NORM-035", "NORM-063"],
        "missing_resolved_sentinel_ids": [],
        "unresolved_sentinel_ids": [],
    }
    status = evaluate_gf02_gate(
        strategy_version=strategy,
        pubmed_recall=recall,
        noise_summary={"sample_size": 10},
        scopus_evidence=pending,
        wos_evidence=_manual("wos"),
    )
    assert status["decision"] == "NOT_READY_FOR_PRESS"
    assert "scopus_manual_evidence_incomplete" in status["blockers"]


def test_imported_manual_evidence_requires_real_execution_metadata_and_hash():
    bad = ManualProviderEvidence(provider="scopus", status="IMPORTED")
    with pytest.raises(ValueError, match="missing required evidence"):
        validate_manual_provider_evidence(bad)


def test_manual_execution_from_export_hashes_actual_file(tmp_path: Path):
    export = tmp_path / "scopus.csv"
    export.write_text("title,doi\nExample,10.1/x\n", encoding="utf-8")

    evidence = manual_execution_from_export(
        provider="scopus",
        expression="TITLE-ABS-KEY(example)",
        executed_at="2026-08-12T10:00:00-03:00",
        executor="R1",
        interface_name="Scopus web",
        total_reported=1,
        export_path=export,
        sentinel_results={"NORM-035": False, "NORM-063": False},
    )

    assert evidence.status == "IMPORTED"
    assert evidence.export_file == "scopus.csv"
    assert len(evidence.export_sha256) == 64


def test_gf02_cannot_use_formal_or_prisma_eligible_strategy():
    with pytest.raises(ValueError, match="PILOT"):
        validate_gf02_pilot_strategy({"search_type": "FORMAL", "prisma_eligible": True})
    with pytest.raises(ValueError, match="must not be PRISMA-eligible"):
        validate_gf02_pilot_strategy({"search_type": "PILOT", "prisma_eligible": True})


def test_gate_waits_for_explicit_human_decision_even_when_evidence_complete():
    strategy = {"search_type": "PILOT", "prisma_eligible": False}
    recall = {
        "recovered_sentinel_ids": ["NORM-035"],
        "missing_resolved_sentinel_ids": ["NORM-063"],
        "unresolved_sentinel_ids": [],
    }

    awaiting = evaluate_gf02_gate(
        strategy_version=strategy,
        pubmed_recall=recall,
        noise_summary={"sample_size": 20},
        scopus_evidence=_manual("scopus"),
        wos_evidence=_manual("web_of_science"),
    )
    assert awaiting["evidence_complete"] is True
    assert awaiting["decision"] == "EVIDENCE_COMPLETE_AWAITING_HUMAN_DECISION"
    assert awaiting["press_approval_inferred"] is False
    assert awaiting["formal_execution_authorized"] is False
    assert awaiting["prisma_eligible"] is False

    ready = evaluate_gf02_gate(
        strategy_version=strategy,
        pubmed_recall=recall,
        noise_summary={"sample_size": 20},
        scopus_evidence=_manual("scopus"),
        wos_evidence=_manual("web_of_science"),
        human_decision="READY_FOR_PRESS",
        human_decision_by="Methodological reviewer",
    )
    assert ready["decision"] == "READY_FOR_PRESS"
    assert ready["press_approval_inferred"] is False


def test_unresolved_priority_identity_blocks_gate():
    status = evaluate_gf02_gate(
        strategy_version={"search_type": "PILOT", "prisma_eligible": False},
        pubmed_recall={
            "recovered_sentinel_ids": [],
            "missing_resolved_sentinel_ids": [],
            "unresolved_sentinel_ids": ["NORM-035", "NORM-063"],
        },
        noise_summary={"sample_size": 20},
        scopus_evidence=_manual("scopus"),
        wos_evidence=_manual("wos"),
    )
    assert status["decision"] == "NOT_READY_FOR_PRESS"
    assert "NORM-035:identity_unresolved" in status["blockers"]
    assert "NORM-063:identity_unresolved" in status["blockers"]


def test_repository_priority_sentinel_file_is_explicitly_unresolved():
    path = Path("config/article1_sentinel_registry.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    by_id = {row["sentinel_id"]: row for row in data["sentinels"]}
    assert by_id["NORM-035"]["identity_status"] == "UNRESOLVED"
    assert by_id["NORM-063"]["identity_status"] == "UNRESOLVED"
    assert by_id["NORM-035"]["canonical_title"] == ""
    assert by_id["NORM-063"]["canonical_title"] == ""
