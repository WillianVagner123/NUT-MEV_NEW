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
    parser = argparse.ArgumentParser(
        description="Adversarial audit for human EvidenceSet construction boundaries."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("evidence_set_construction.py")
    release = read("governed_synthesis_release.py")
    html = read("evidence-sets.html")
    script = read("evidence-sets.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'EVIDENCE_SET_STAGE_OPERATION = "STAGE_EVIDENCE_SET"' in service
        and 'EVIDENCE_SET_FINALIZE_OPERATION = "FINALIZE_EVIDENCE_SET"' in service,
        "EvidenceSet must use explicit stage/finalize operations.",
    )
    require(
        'EVIDENCE_SET_STAGE_OPERATION = "STAGE_EVIDENCE_SET"' in release
        and 'EVIDENCE_SET_FINALIZE_OPERATION = "FINALIZE_EVIDENCE_SET"' in release,
        "Local-only coordinator must route EvidenceSet operations.",
    )
    require(
        "_load_accepted_claim" in service
        and "_evaluation_for_claim" in service
        and "_revalidate_draft" in service,
        "EvidenceSet must revalidate accepted claims, finalized appraisals and current context.",
    )
    for token in (
        '"automatic_claim_grouping_performed": False',
        '"automatic_relation_inference_performed": False',
        '"claim_evaluation_scores_aggregated": False',
        '"consensus_inferred": False',
        '"contradiction_inferred": False',
        '"certainty_assessed": False',
        '"overall_certainty_grade_created": False',
        '"formal_risk_of_bias_assessed": False',
        '"canonical_scientific_synthesis_created": False',
        '"clinical_recommendation_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"overlapping_evidence_sets_allowed": True',
        '"single_claim_set_is_not_synthesis": True',
    ):
        require(token in service, f"Missing EvidenceSet guardrail: {token}")
    require(
        "membership_human_curated_confirmed" in service
        and "grouping_is_not_consensus_confirmed" in service
        and "scientific_boundary_confirmed" in service,
        "Finalization must require explicit human membership and boundary confirmations.",
    )
    require(
        "HUMAN CURATION" in html
        and "MEMBERSHIP ≠ CONSENSUS" in html
        and "NO SYNTHESIS YET" in html
        and "OVERLAP ALLOWED" in html,
        "UI must state membership, overlap and non-synthesis boundaries.",
    )
    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "EvidenceSet construction must not call an external LLM to choose membership.",
    )
    require(
        ".checked=true" not in script.replace(" ", "").lower()
        and "checked=true" not in script.replace(" ", "").lower(),
        "EvidenceSet UI must not preselect claims automatically.",
    )
    stage_match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect EvidenceSet staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("FINALIZE_OPERATION" not in stage_body, "Staging must not auto-finalize EvidenceSet.")
        require("finalizeSet(" not in stage_body, "Staging must not call EvidenceSet finalization.")
    for forbidden_field in (
        '"overall_score":',
        '"quality_score":',
        '"certainty_grade":',
        '"pooled_effect":',
    ):
        require(
            forbidden_field not in service.casefold(),
            f"EvidenceSet service must not create scientific aggregate field {forbidden_field}",
        )
    require(
        '"evidence_set_ids": set_ids' in release
        and '"evidence_set_membership_count": len(set_ids)' in release,
        "Membership should be exposed by metadata join rather than upstream artifact mutation.",
    )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
