#!/usr/bin/env python3
"""Adversarial read-only audit for governed synthesis dissemination releases."""

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
    server = _text("server.py")
    service = _text("governed_synthesis_release.py")
    script = _text("synthesis-release.js")
    html = _text("synthesis-release.html")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "Release coordinator is loopback-only",
        'path == "/api/synthesis/releases"' in server
        and 'path == "/api/synthesis/releases/prepare"' in server
        and "_require_loopback" in server,
        "Release status and preparation must not expose coordinator data or mutation to remote clients.",
    )
    check(
        "Release requires approved human governance",
        'entry.get("status") != APPROVED' in service
        and 'decision.get("action") != "APPROVE"' in service
        and 'decision.get("human_entered") is not True' in service
        and 'decision.get("source_revalidated_at_decision") is not True' in service,
        "STAGED/REJECTED entries and non-human or unrevalidated decisions must fail closed.",
    )
    check(
        "Release source is revalidated against current context",
        "validate_brief(brief, output_root=output_root)" in service
        and 'validated["context_fingerprint"] != entry.get("source_context_fingerprint")' in service,
        "An approved source may not be disseminated after its materialized context becomes stale.",
    )
    check(
        "Release package remains noncanonical scientific content",
        'RELEASE_TYPE = "NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1"' in service
        and '"canonical": False' in service
        and '"canonical_scientific_synthesis_created": False' in service
        and "canonical:false" in html,
        "Governed dissemination must never silently promote the Brief into canonical scientific synthesis.",
    )
    check(
        "Release creates no unsupported scientific judgments",
        all(
            token in service
            for token in (
                '"accepted_evidence_claims_created": False',
                '"risk_of_bias_assessed": False',
                '"certainty_assessed": False',
                '"meta_analysis_performed": False',
                '"prisma_event_emitted": False',
                '"formal_search_state_changed": False',
            )
        ),
        "Release preparation may transport reviewed relationships but cannot manufacture claims, RoB, certainty, pooling or PRISMA state.",
    )
    check(
        "Release identity fields are not cryptographic authentication",
        '"identity_cryptographically_authenticated": False' in service
        and "package hash ≠ authenticated authorship" in html,
        "Typed reviewer/governor/preparer metadata and SHA-256 are provenance, not identity authentication.",
    )
    check(
        "Release ledger is metadata-only",
        '"records": records' in service
        and '"reviewed_decisions"' not in service.split("def release_status", 1)[1]
        and '"package":' not in service.split("def release_status", 1)[1],
        "Listing release history must not resend full source-linked decisions or packages.",
    )
    check(
        "Release is explicit user action, never automatic",
        "prepareRelease').addEventListener('click',prepare)" in script
        and "postJson('/api/synthesis/releases/prepare'" in script
        and "prepare();" not in script.split("async function load()", 1)[1],
        "Loading the release workspace cannot prepare or publish a package automatically.",
    )
    check(
        "Release frontend has no external LLM or ranking dependency",
        all(
            token not in script
            for token in (
                "api.openai.com",
                "api.anthropic.com",
                "reference_rank",
                "reference_score",
                "machine_relevance_score",
                "machine_relevance_band",
            )
        ),
        "Dissemination must remain grounded in governed human artifacts, not LLM calls or operational ranking.",
    )

    errors = [item for item in checks if not item["passed"]]
    return {
        "mode": "NUTEV_GOVERNED_SYNTHESIS_RELEASE_DEATH_TEST",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "read_only": True,
        "guardrail": (
            "This audit protects dissemination-package semantics. It does not validate the underlying "
            "science, authenticate identities, assess RoB/certainty, perform meta-analysis, or create PRISMA state."
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
