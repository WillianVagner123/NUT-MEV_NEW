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
        description="Adversarial audit for the human ClaimEvaluation appraisal boundary."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("claim_evaluation_appraisal.py")
    release = read("governed_synthesis_release.py")
    html = read("claim-appraisal.html")
    script = read("claim-appraisal.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'EVALUATION_STAGE_OPERATION = "STAGE_CLAIM_EVALUATION"' in service
        and 'EVALUATION_FINALIZE_OPERATION = "FINALIZE_CLAIM_EVALUATION"' in service,
        "ClaimEvaluation must use explicit stage/finalize operations.",
    )
    require(
        'EVALUATION_STAGE_OPERATION = "STAGE_CLAIM_EVALUATION"' in release
        and 'EVALUATION_FINALIZE_OPERATION = "FINALIZE_CLAIM_EVALUATION"' in release,
        "Local-only coordinator must route explicit ClaimEvaluation operations.",
    )
    for dimension in (
        "design_appropriateness",
        "internal_validity_appraisal",
        "directness",
        "precision",
        "applicability",
        "reporting_completeness",
    ):
        require(f'"{dimension}"' in service, f"Missing appraisal dimension: {dimension}")
    for token in (
        '"numeric_appraisal_score_created": False',
        '"automatic_dimension_aggregation_performed": False',
        '"formal_external_instrument_applied": False',
        '"formal_risk_of_bias_assessed": False',
        '"risk_of_bias_assessed": False',
        '"study_validity_determined": False',
        '"certainty_assessed": False',
        '"overall_certainty_grade_created": False',
        '"evidence_set_created": False',
        '"clinical_recommendation_created": False',
        '"screening_eligibility_changed": False',
        '"accepted_claim_statement_changed": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
    ):
        require(token in service, f"Missing ClaimEvaluation guardrail: {token}")
    require(
        "_load_accepted_claim" in service
        and "_validate_candidate_current" in service
        and "EvidenceRecord correspondente ao EvidenceClaim" in service,
        "Appraisal must revalidate accepted claim, source provenance and EvidenceRecord.",
    )
    require(
        "assessment_basis" in service
        and "FULL_TEXT" in service
        and "ABSTRACT_ONLY" in service
        and "SOURCE_SNAPSHOT_ONLY" in service,
        "Appraisal must declare the material basis used by the assessor.",
    )
    require(
        "nonformal_method_confirmed" in service
        and "scientific_boundary_confirmed" in service
        and "claim_scope_confirmed" in service,
        "Finalization must require all three explicit scientific confirmations.",
    )
    require(
        "NO AUTOMATIC SCORE" in html
        and "ClaimEvaluation != formal Risk of Bias" in html
        and "ClaimEvaluation != GRADE" in html
        and "major concerns != automatic exclusion" in html,
        "UI must state the appraisal boundary clearly.",
    )
    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "ClaimEvaluation must not call an external LLM to create scientific appraisal judgments.",
    )
    stage_match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect appraisal staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("FINALIZE_OPERATION" not in stage_body, "Staging must not auto-finalize appraisal.")
        require("finalizeAppraisal(" not in stage_body, "Staging must not call finalization.")
    require(
        "overall_score" not in service
        and "certainty_grade" not in service
        and "quality_score" not in service,
        "ClaimEvaluation service must not introduce aggregate quality/certainty scores.",
    )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
