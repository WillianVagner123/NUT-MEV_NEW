#!/usr/bin/env python3
"""Adversarial read-only audit for governed publication preparation semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def _text(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def run_audit() -> dict[str, Any]:
    service = _text("governed_publication_manifest.py")
    release_service = _text("governed_synthesis_release.py")
    script = _text("synthesis-publication.js")
    html = _text("synthesis-publication.html")
    server = _text("server.py")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "Publication preparation remains behind local-only coordinator",
        'path == "/api/synthesis/releases/prepare"' in server
        and "_require_loopback" in server
        and 'PUBLICATION_OPERATION = "PREPARE_PUBLICATION_MANIFEST"' in release_service,
        "Publication preparation must not introduce a remotely writable scientific surface.",
    )
    check(
        "Governed release is revalidated before publication preparation",
        "build_governed_release(" in service
        and "Release package não corresponde mais ao contexto científico atual" in service,
        "A stale governed release must fail closed instead of being grandfathered into publication.",
    )
    check(
        "Publication statements remain candidate-only",
        '"publication_status": "CANDIDATE_ONLY"' in service
        and '"accepted_evidence_claim": False' in service
        and '"machine_inferred_scientific_claim": False' in service
        and '"requires_human_author_editing": True' in service,
        "Recorded human judgements may be described, but must not become accepted EvidenceClaims automatically.",
    )
    check(
        "Citation bundle remains source-linked",
        all(
            token in service
            for token in (
                '"citation_id"',
                '"decision_id"',
                '"document_id"',
                '"bundle_id"',
                '"source_sentence_sha256"',
                '"result_text"',
            )
        ),
        "Every publication statement must be traceable to source-linked human-review snapshots.",
    )
    check(
        "Publication manifest does not create scientific canon or grading",
        '"canonical_scientific_synthesis_created": False' in service
        and '"accepted_evidence_claims_created": False' in service
        and '"risk_of_bias_assessed": False' in service
        and '"certainty_assessed": False' in service
        and '"meta_analysis_performed": False' in service
        and '"prisma_event_emitted": False' in service
        and '"clinical_recommendation_created": False' in service,
        "Publication preparation must not silently create claims, RoB, certainty, meta-analysis, PRISMA or recommendations.",
    )
    check(
        "Human relation labels are not rewritten as scientific truth",
        "classified by the reviewer as" in service
        and "evidence certainty, causal proof, clinical recommendation, or scientific consensus" in service,
        "Generated wording must describe the reviewer judgement itself rather than infer substantive scientific truth.",
    )
    check(
        "Publication preparation requires explicit user action",
        "preparePublication').addEventListener('click',prepare)" in script
        and "prepare();" not in script.split("async function load()", 1)[1],
        "Loading the page must never create a publication manifest automatically.",
    )
    check(
        "Publication UI rejects claim promotion",
        "accepted_evidence_claim!==false" in script
        and "publication_status!=='CANDIDATE_ONLY'" in script
        and "Statement candidate ≠ accepted EvidenceClaim" in script,
        "The browser must fail closed if the server ever returns promoted statements.",
    )
    check(
        "Publication ledger is metadata-only",
        '"records": records' in service.split("def publication_status", 1)[1]
        and '"citation_bundle"' not in service.split("def publication_status", 1)[1]
        and '"statement_candidates"' not in service.split("def publication_status", 1)[1],
        "Listing manifests must not ship full citation bundles or statement bodies to the browser.",
    )
    check(
        "Publication layer stays offline from external LLMs and ranking",
        all(token not in script for token in ("api.openai.com", "api.anthropic.com", "reference_rank", "machine_relevance_score"))
        and '"external_llm_generated_scientific_claims": False' in service,
        "Publication preparation must remain deterministic and provenance-driven in this phase.",
    )
    check(
        "Visible scientific boundary refuses canonization",
        "Publication Statement Candidate != accepted EvidenceClaim" in html
        and "manifest != meta-analysis" in html
        and "manifest != PRISMA" in html
        and "no canonical scientific synthesis is created" in html,
        "The UI must state the publication boundary in plain language.",
    )

    errors = [item for item in checks if not item["passed"]]
    return {
        "mode": "NUTEV_GOVERNED_PUBLICATION_MANIFEST_DEATH_TEST",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "read_only": True,
        "guardrail": (
            "This audit protects publication-preparation semantics and traceability. It does not "
            "assess evidence quality, risk of bias, certainty, eligibility, causality, clinical "
            "recommendations, meta-analysis, or PRISMA conclusions."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
