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
        description="Adversarial audit for RecommendationCandidate drafting semantics."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("recommendation_candidate_drafting.py")
    coordinator = read("governed_synthesis_release.py")
    html = read("recommendation-candidates.html")
    script = read("recommendation-candidates.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'RECOMMENDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_CANDIDATE"' in service
        and 'RECOMMENDATION_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_CANDIDATE"' in service,
        "RecommendationCandidate must use explicit stage/finalize operations.",
    )
    require(
        'RECOMMENDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_CANDIDATE"' in coordinator
        and 'RECOMMENDATION_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_CANDIDATE"' in coordinator,
        "Local-only coordinator must route RecommendationCandidate operations.",
    )
    require(
        'READINESS_NOT_EVALUATED = "not_evaluated"' in service,
        "RecommendationCandidate readiness must start as not_evaluated.",
    )
    for token in (
        '"automatic_statement_generation_performed": False',
        '"automatic_readiness_inference_performed": False',
        '"readiness_evaluated": False',
        '"recommendation_validated": False',
        '"human_validation_created": False',
        '"evidence_set_agreement_inferred": False',
        '"evidence_set_contradiction_inferred": False',
        '"evidence_set_scores_aggregated": False',
        '"certainty_assessed": False',
        '"overall_certainty_grade_created": False',
        '"formal_risk_of_bias_assessed": False',
        '"clinical_recommendation_created": False',
        '"canonical_scientific_synthesis_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"multiple_evidence_sets_do_not_imply_consensus": True',
    ):
        require(token in service, f"Missing RecommendationCandidate guardrail: {token}")

    require(
        "_load_finalized_evidence_set" in service
        and "_member_snapshot" in service
        and "_revalidate_draft" in service,
        "RecommendationCandidate must revalidate EvidenceSets and upstream source snapshots.",
    )
    require(
        "statement_human_authored_confirmed" in service
        and "human_validation_required_confirmed" in service,
        "RecommendationCandidate must require explicit human authorship and later HumanValidation acknowledgement.",
    )
    require(
        "HUMAN AUTHORSHIP" in html
        and "CANDIDATE ≠ VALIDATED RECOMMENDATION" in html
        and "READINESS = NOT_EVALUATED" in html,
        "UI must state candidate/authorship/readiness boundaries.",
    )
    require(
        "Nenhum conteúdo é pré-preenchido" in html,
        "UI must make the empty human-authored statement contract explicit.",
    )

    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "RecommendationCandidate UI must not call an external LLM.",
    )
    stage_match = re.search(r"async function stage\(\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect RecommendationCandidate staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("FINALIZE_OPERATION" not in stage_body, "Staging must not auto-finalize a candidate.")
        require("finalizeCandidate(" not in stage_body, "Staging must not invoke candidate finalization.")

    require(
        '"readiness": READINESS_NOT_EVALUATED' in service,
        "Finalized RecommendationCandidate must preserve readiness=not_evaluated.",
    )
    require(
        '"recommendation_candidate_created": True' in service
        and '"recommendation_validated": False' in service,
        "Candidate finalization must remain distinct from recommendation validation.",
    )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
