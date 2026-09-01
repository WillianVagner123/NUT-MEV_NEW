#!/usr/bin/env python3
"""Adversarial read-only audit for the NutEV Synthesis Governance Registry."""

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
    service = _text("synthesis_governance.py")
    script = _text("synthesis-governance.js")
    html = _text("synthesis-governance.html")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "Governance writes are loopback-only",
        'path == "/api/synthesis/governance"' in server
        and '"/api/synthesis/governance/stage"' in server
        and '"/api/synthesis/governance/decide"' in server
        and "_require_loopback" in server,
        "Registry status, staging and governance decisions must not be writable/readable as coordinator state from remote clients.",
    )
    check(
        "Governance import stays staged",
        'STAGED = "STAGED"' in service
        and '"status": STAGED' in service
        and "APPROVE" not in script.split("async function stage()", 1)[1].split("async function decide", 1)[0],
        "Importing a Brief must never auto-approve it.",
    )
    check(
        "Governance decision is explicit human input",
        'DECISIONS = {"APPROVE": APPROVED, "REJECT": REJECTED}' in service
        and "if not governor:" in service
        and "len(rationale) < 20" in service
        and '"human_entered": True' in service,
        "Approve/reject requires a named human and rationale.",
    )
    check(
        "Source is revalidated at decision time",
        "validate_brief(artifact, output_root=output_root)" in service
        and '"source_revalidated_at_decision": True' in service,
        "A staged artifact may not be approved after its content or current context becomes stale.",
    )
    check(
        "Governance approval does not create canonical scientific synthesis",
        'APPROVED = "APPROVED_FOR_GOVERNED_USE"' in service
        and '"canonical_scientific_synthesis_created": False' in service
        and "no canonical scientific synthesis is created" in html,
        "Governed-use approval is a registry state, not scientific canonization.",
    )
    check(
        "Registry does not claim cryptographic identity authentication",
        '"reviewer_identity_cryptographically_authenticated": False' in service
        and '"identity_cryptographically_authenticated": False' in service
        and "cryptographic identity authentication" in html,
        "Typed reviewer/governor names are provenance labels, not authenticated identities.",
    )
    check(
        "Governance status is not PRISMA or certainty",
        "governance ≠ scientific validation" in html.casefold()
        and "registry != PRISMA" in html
        and "approval != evidence certainty" in html,
        "Registry decisions must not be exposed as screening, certainty, or PRISMA conclusions.",
    )
    check(
        "Registry listing is metadata-only",
        '"entries": entries' in service
        and '"reviewed_decisions"' not in service.split("def registry_status", 1)[1].split("def stage_brief", 1)[0],
        "GET registry status must not ship stored Brief bodies to the browser.",
    )
    check(
        "Governance frontend only writes governance endpoints",
        "postJson('/api/synthesis/governance/stage'" in script
        and "postJson('/api/synthesis/governance/decide'" in script
        and "api.openai.com" not in script
        and "api.anthropic.com" not in script,
        "Governance UI must not call external LLMs or unrelated scientific mutation endpoints.",
    )
    check(
        "Operational ranking is absent from governance surface",
        all(
            token not in script
            for token in (
                "reference_rank",
                "reference_score",
                "machine_relevance_score",
                "machine_relevance_band",
            )
        ),
        "Governance is about verified human synthesis artifacts, not Bank or machine ranking.",
    )

    errors = [item for item in checks if not item["passed"]]
    return {
        "mode": "NUTEV_SYNTHESIS_GOVERNANCE_DEATH_TEST",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "read_only": True,
        "guardrail": (
            "This audit protects registry/governance semantics. It does not authenticate human identity, "
            "assess evidence quality, risk of bias, certainty, eligibility, meta-analysis, or PRISMA results."
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
