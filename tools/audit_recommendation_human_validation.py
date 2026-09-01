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
        description="Adversarial audit for RecommendationCandidate HumanValidation semantics."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("recommendation_human_validation.py")
    coordinator = read("governed_synthesis_release.py")
    html = read("recommendation-human-validation.html")
    script = read("recommendation-human-validation.js")
    candidate_service = read("recommendation_candidate_drafting.py")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'VALIDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_HUMAN_VALIDATION"' in service
        and 'VALIDATION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_HUMAN_VALIDATION"' in service,
        "HumanValidation must use explicit stage/decide operations.",
    )
    require(
        'VALIDATION_STAGE_OPERATION = "STAGE_RECOMMENDATION_HUMAN_VALIDATION"' in coordinator
        and 'VALIDATION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_HUMAN_VALIDATION"' in coordinator,
        "Local-only coordinator must route HumanValidation operations.",
    )
    require(
        'PENDING = "PENDING"' in service
        and 'ACCEPT = "ACCEPT"' in service
        and 'REJECT = "REJECT"' in service
        and 'REVISE = "REVISE"' in service,
        "HumanValidation must preserve explicit PENDING/ACCEPT/REJECT/REVISE states.",
    )
    require(
        'MODEL_DECISIONS = {ACCEPT: "accept", REJECT: "reject", REVISE: "revise"}' in service,
        "HumanValidation must map explicitly to the scientific model decision vocabulary.",
    )

    for token in (
        '"automatic_validation_decision_performed": False',
        '"automatic_revision_applied": False',
        '"recommendation_candidate_changed": False',
        '"readiness_changed": False',
        '"readiness_evaluated": False',
        '"validated_recommendation_created": False',
        '"clinical_recommendation_created": False',
        '"guideline_recommendation_created": False',
        '"certainty_assessed": False',
        '"grade_assessed": False',
        '"formal_risk_of_bias_assessed": False',
        '"canonical_scientific_synthesis_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"identity_cryptographically_authenticated": False',
    ):
        require(token in service, f"Missing HumanValidation guardrail: {token}")

    require(
        "_load_finalized_candidate" in service
        and "_set_snapshot" in service
        and "_revalidate_case" in service,
        "HumanValidation must revalidate candidate, EvidenceSets and upstream source context.",
    )
    require(
        "decisions conflitantes não podem sobrescrevê-la" in service,
        "Canonical HumanValidation decisions must fail closed on conflicting overwrite attempts.",
    )
    require(
        "REVISE exige revision instructions" in service
        and '"automatic_revision_applied": False' in service,
        "REVISE must require human instructions and never auto-edit the candidate.",
    )
    require(
        '"readiness": READINESS_NOT_EVALUATED' in candidate_service
        and '"recommendation_validated": False' in candidate_service,
        "Upstream RecommendationCandidate must keep readiness not_evaluated and remain unpromoted.",
    )

    require(
        "NO AUTO-ACCEPT" in html
        and "ACCEPT ≠ CLINICAL RECOMMENDATION" in html
        and "PENDING → ACCEPT / REJECT / REVISE" in html,
        "UI must state HumanValidation decision boundaries prominently.",
    )
    require(
        '<option value="">Selecione explicitamente…</option>' in script,
        "HumanValidation UI must not preselect a decision.",
    )
    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "HumanValidation UI must not call an external LLM.",
    )
    require(
        not any(token in lowered for token in ("auto_accept", "auto_reject", "auto_revise")),
        "HumanValidation UI must not expose automatic decision paths.",
    )

    stage_match = re.search(r"async function stage\(card\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect HumanValidation staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("DECIDE_OPERATION" not in stage_body, "Staging must not auto-decide HumanValidation.")
        require("decide(" not in stage_body, "Staging must not invoke HumanValidation decision.")

    decide_match = re.search(r"async function decide\(card\)\{(?P<body>.*?)\n\}", script, re.S)
    require(decide_match is not None, "Could not inspect HumanValidation decision function.")
    if decide_match is not None:
        decide_body = decide_match.group("body")
        require(
            "['ACCEPT','REJECT','REVISE'].includes(decision)" in decide_body,
            "Decision function must require explicit allowed decision.",
        )
        require(
            all(
                token in decide_body
                for token in (
                    "decision_human_entered_confirmed:true",
                    "decision_is_not_certainty_confirmed:true",
                    "decision_is_not_clinical_recommendation_confirmed:true",
                    "upstream_candidate_immutable_confirmed:true",
                )
            ),
            "Decision function must send all human/scientific boundary confirmations.",
        )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
