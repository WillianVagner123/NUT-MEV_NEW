from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adversarial audit for the EvidenceClaim human-promotion boundary.")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("evidence_claim_review.py")
    release = read("governed_synthesis_release.py")
    html = read("evidence-claims.html")
    script = read("evidence-claims.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'CLAIM_STAGE_OPERATION = "STAGE_EVIDENCE_CLAIM_REVIEW"' in service
        and 'CLAIM_DECIDE_OPERATION = "DECIDE_EVIDENCE_CLAIM"' in service,
        "Claim review must use explicit stage/decision operations.",
    )
    require(
        'CLAIM_STAGE_OPERATION = "STAGE_EVIDENCE_CLAIM_REVIEW"' in release
        and 'CLAIM_DECIDE_OPERATION = "DECIDE_EVIDENCE_CLAIM"' in release,
        "Local-only release coordinator must route both explicit claim operations.",
    )
    require(
        '"directly_promotable_to_evidence_claim": False' in service
        and '"pairwise_statement_directly_promotable": False' in service
        and "EvidenceClaim belongs to one EvidenceRecord" in service,
        "Pairwise synthesis statements must never be directly promoted into atomic EvidenceClaims.",
    )
    require(
        'output_root / "scientific" / "evidence_records.jsonl"' in service
        and "EvidenceRecord correspondente não foi localizado" in service,
        "ACCEPT must require a real EvidenceRecord, not only a derived id.",
    )
    require(
        "source_attribution_confirmed" in service
        and "scientific_boundary_confirmed" in service,
        "ACCEPT must require explicit human scientific-boundary confirmations.",
    )
    require(
        '"claim_semantics": "SOURCE_REPORTED_PROPOSITION"' in service,
        "Canonical claim semantics must remain source-reported proposition, not truth/certainty.",
    )
    for token in (
        '"claim_acceptance_is_not_screening_inclusion": True',
        '"screening_eligibility_verified": False',
        '"claim_evaluation_created": False',
        '"risk_of_bias_assessed": False',
        '"certainty_assessed": False',
        '"evidence_set_created": False',
        '"canonical_scientific_synthesis_created": False',
        '"clinical_recommendation_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"pairwise_synthesis_statement_promoted": False',
        '"identity_cryptographically_authenticated": False',
    ):
        require(token in service, f"Missing EvidenceClaim guardrail: {token}")
    require(
        "Human claim statement — starts empty" in script
        and "claim_statement:candidate.result_text" not in script
        and not re.search(r'value=["\']\$\{esc\(candidate\.result_text', script),
        "UI must not prefill/copy the source result text into the canonical claim statement.",
    )
    require(
        "ACCEPT bloqueado: EvidenceRecord não resolvido" in script,
        "UI must visibly block ACCEPT when EvidenceRecord is unresolved.",
    )
    require(
        "EvidenceClaim acceptance != screening inclusion" in html
        and "EvidenceClaim != Risk of Bias" in html
        and "EvidenceClaim != certainty" in html
        and "EvidenceClaim != recommendation" in html,
        "UI must state the scientific boundary around claim acceptance.",
    )
    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "EvidenceClaim review must not call an external LLM to create/accept scientific claims.",
    )
    stage_match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("DECIDE_OPERATION" not in stage_body, "Staging must not auto-decide a claim.")
        require("decision:'ACCEPT'" not in stage_body, "Staging must not auto-accept a claim.")

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
