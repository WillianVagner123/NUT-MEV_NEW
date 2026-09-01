from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

from governed_publication_manifest import (  # noqa: E402
    MANIFEST_TYPE,
    STATEMENT_TYPE,
    build_publication_manifest,
    prepare_publication_manifest,
    publication_status,
)
from governed_synthesis_release import prepare_governed_release  # noqa: E402
from synthesis_governance import (  # noqa: E402
    BRIEF_TYPE,
    REVIEW_TYPE,
    SynthesisGovernanceError,
    _digest,
    context_fingerprint_source,
    decide_entry,
    stage_brief,
)


def _write_search_state(output_root: Path, *, database_sha: str = "a" * 64) -> dict:
    state = {
        "search_id": "search_publication_test_01",
        "context_version": "nutev_article1_agent_context_v1",
        "question": "What is the current evidence structure?",
        "runtime": {
            "workbench": {"database_sha256": database_sha},
            "article1_routes": {"manifest_sha256": "b" * 64},
            "review_profiles": {"profile_version": "review_profile_v2"},
            "agent_article_summaries": 12,
        },
    }
    path = output_root / "agent_context" / "article1" / "SEARCH_STATE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    return state


def _decision() -> dict:
    return {
        "decision_id": "doi:10.1/a::pmid:123456",
        "domain": "food_literacy",
        "domain_label": "Food / nutrition literacy",
        "anchor": {
            "document_id": "doi:10.1/a",
            "title": "Study A",
            "bundle_id": "result:a",
            "source_sentence_sha256": "d" * 64,
            "result_text": "Outcome improved in the intervention group.",
            "outcomes": ["food literacy"],
            "effect_measures": [],
            "confidence_intervals": [],
            "p_values": [],
            "routes": ["C-STRUCT"],
        },
        "candidate": {
            "document_id": "pmid:123456",
            "title": "Study B",
            "bundle_id": "result:b",
            "source_sentence_sha256": "e" * 64,
            "result_text": "Outcome also improved in the comparator study.",
            "outcomes": ["food literacy"],
            "effect_measures": [],
            "confidence_intervals": [],
            "p_values": [],
            "routes": ["B-NORM"],
        },
        "comparability": {
            "population": "SIMILAR",
            "construct_intervention": "SIMILAR",
            "outcome": "SIMILAR",
            "timeframe": "UNCLEAR",
        },
        "relation": "CONVERGENT",
        "rationale": "The reviewer judged the outcome direction comparable across both source-linked results.",
        "reviewer": "Reviewer One",
        "reviewed_at": "2026-09-01T12:00:00+00:00",
        "human_entered": True,
        "canonical": False,
    }


def _brief(output_root: Path) -> dict:
    search = json.loads(
        (output_root / "agent_context" / "article1" / "SEARCH_STATE.json").read_text(
            encoding="utf-8"
        )
    )
    fingerprint = _digest(context_fingerprint_source(search))
    content = {
        "export_type": BRIEF_TYPE,
        "canonical": False,
        "integrity_verified": True,
        "current_context_match": True,
        "source_review_type": REVIEW_TYPE,
        "source_review_content_sha256": "c" * 64,
        "source_context_fingerprint": fingerprint,
        "search_id": search["search_id"],
        "context_version": search["context_version"],
        "question": search["question"],
        "reviewer": "Reviewer One",
        "relationship_counts": {"CONVERGENT": 1},
        "domain_counts": {"food_literacy": 1},
        "comparability_counts": {"population": {"SIMILAR": 1}},
        "reviewed_decisions": [_decision()],
        "guardrails": {
            "source_review_is_noncanonical": True,
            "integrity_verification_is_not_scientific_validation": True,
            "integrity_verification_does_not_prove_authorship_or_authenticity": True,
            "relationship_counts_are_not_evidence_strength": True,
            "convergent_is_not_certainty": True,
            "divergent_is_not_proven_contradiction": True,
            "brief_is_not_meta_analysis": True,
            "brief_is_not_prisma": True,
            "accepted_evidence_claims_created": False,
            "risk_of_bias_assessed": False,
            "certainty_assessed": False,
            "formal_search_state_changed": False,
        },
    }
    return {
        **content,
        "content_sha256": _digest(content),
        "generated_at": "2026-09-01T12:05:00+00:00",
        "artifact_semantics": "Presentation-ready human review brief.",
    }


def _release(output_root: Path) -> dict:
    staged = stage_brief(
        {"actor": "Registry Operator", "artifact": _brief(output_root)},
        output_root=output_root,
    )
    approved = decide_entry(
        {
            "artifact_id": staged["artifact_id"],
            "action": "APPROVE",
            "governor": "Governance Reviewer",
            "rationale": "Approved for governed dissemination after manual provenance and context review.",
        },
        output_root=output_root,
    )
    return prepare_governed_release(
        {
            "artifact_id": approved["artifact_id"],
            "prepared_by": "Release Operator",
            "purpose": "Prepare a governed package for manuscript drafting and scientific presentation.",
        },
        output_root=output_root,
    )


def test_manifest_builds_source_linked_citations_and_candidate_statements(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    release = _release(tmp_path)
    manifest = build_publication_manifest(
        release["record"]["package_id"],
        publication_owner="Publication Owner",
        intended_use="Prepare a manuscript results section with explicit source traceability.",
        output_root=tmp_path,
    )

    assert manifest["manifest_type"] == MANIFEST_TYPE
    assert manifest["canonical"] is False
    assert len(manifest["citation_bundle"]) == 2
    assert len(manifest["statement_candidates"]) == 1
    statement = manifest["statement_candidates"][0]
    assert statement["statement_type"] == STATEMENT_TYPE
    assert statement["publication_status"] == "CANDIDATE_ONLY"
    assert statement["accepted_evidence_claim"] is False
    assert statement["machine_inferred_scientific_claim"] is False
    assert statement["citation_ids"] == ["CIT-0001-A", "CIT-0001-B"]
    assert "classified by the reviewer as CONVERGENT" in statement["statement_text"]
    assert manifest["citation_bundle"][0]["identifiers"] == {"doi": "10.1/a"}
    assert manifest["citation_bundle"][1]["identifiers"] == {"pmid": "123456"}
    assert manifest["guardrails"]["accepted_evidence_claims_created"] is False
    assert manifest["guardrails"]["certainty_assessed"] is False
    assert manifest["guardrails"]["meta_analysis_performed"] is False
    assert manifest["guardrails"]["prisma_event_emitted"] is False


def test_manifest_is_persisted_idempotently_and_ledger_is_metadata_only(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    release = _release(tmp_path)
    payload = {
        "package_id": release["record"]["package_id"],
        "publication_owner": "Publication Owner",
        "intended_use": "Prepare a manuscript results section with explicit source traceability.",
    }
    first = prepare_publication_manifest(payload, output_root=tmp_path)
    second = prepare_publication_manifest(payload, output_root=tmp_path)

    assert first["record"]["manifest_id"] == second["record"]["manifest_id"]
    assert first["manifest"]["content_sha256"] == second["manifest"]["content_sha256"]
    assert first["record"]["canonical_manifest_record"] is True
    assert first["record"]["publication_manifest_canonical"] is False
    assert first["record"]["accepted_evidence_claims_created"] is False

    status = publication_status(output_root=tmp_path)
    assert status["count"] == 1
    record = status["records"][0]
    assert "citation_bundle" not in record
    assert "statement_candidates" not in record
    assert "reviewed_decisions" not in record


def test_manifest_fails_closed_when_context_changes_after_release(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    release = _release(tmp_path)
    _write_search_state(tmp_path, database_sha="f" * 64)

    with pytest.raises(SynthesisGovernanceError, match="Context fingerprint|contexto científico atual"):
        build_publication_manifest(
            release["record"]["package_id"],
            publication_owner="Publication Owner",
            intended_use="Prepare a manuscript only if the governed release is still current.",
            output_root=tmp_path,
        )


def test_manifest_rejects_tampered_release_package(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    release = _release(tmp_path)
    package_id = release["record"]["package_id"]
    package_path = tmp_path / "scientific" / "synthesis_releases" / "packages" / f"{package_id}.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["question"] = "Tampered question"
    package_path.write_text(json.dumps(package), encoding="utf-8")

    with pytest.raises(SynthesisGovernanceError, match="content SHA-256"):
        build_publication_manifest(
            package_id,
            publication_owner="Publication Owner",
            intended_use="Prepare a manuscript only from an untampered governed release package.",
            output_root=tmp_path,
        )


def test_manifest_requires_complete_source_linked_snapshots(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    brief = _brief(tmp_path)
    brief["reviewed_decisions"][0]["anchor"]["bundle_id"] = ""
    content = {
        key: brief[key]
        for key in brief
        if key not in {"content_sha256", "generated_at", "artifact_semantics"}
    }
    brief["content_sha256"] = _digest(content)
    with pytest.raises(SynthesisGovernanceError, match="result-bundle id"):
        stage_brief({"actor": "Registry Operator", "artifact": brief}, output_root=tmp_path)


def test_manifest_requires_publication_owner_and_specific_use(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    release = _release(tmp_path)
    package_id = release["record"]["package_id"]
    with pytest.raises(SynthesisGovernanceError, match="Identifique"):
        build_publication_manifest(
            package_id,
            publication_owner="",
            intended_use="x" * 30,
            output_root=tmp_path,
        )
    with pytest.raises(SynthesisGovernanceError, match="pelo menos 20"):
        build_publication_manifest(
            package_id,
            publication_owner="Publication Owner",
            intended_use="short",
            output_root=tmp_path,
        )
