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
        description="Adversarial audit for Recommendation Development semantics."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("recommendation_development.py")
    coordinator = read("governed_synthesis_release.py")
    html = read("recommendation-development.html")
    script = read("recommendation-development.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'DEVELOPMENT_STAGE_OPERATION = "STAGE_RECOMMENDATION_DEVELOPMENT"' in service
        and 'DEVELOPMENT_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_DEVELOPMENT"' in service,
        "Recommendation Development must use explicit stage/finalize operations.",
    )
    require(
        'DEVELOPMENT_STAGE_OPERATION = "STAGE_RECOMMENDATION_DEVELOPMENT"' in coordinator
        and 'DEVELOPMENT_FINALIZE_OPERATION = "FINALIZE_RECOMMENDATION_DEVELOPMENT"' in coordinator,
        "Local-only coordinator must route Recommendation Development operations.",
    )
    require(
        'DEVELOPMENT_METHOD = "NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1"' in service,
        "Recommendation Development must declare the generic NutEV method explicitly.",
    )
    require(
        'if str(validation.get("decision") or "") != "accept"' in service,
        "Recommendation Development must require HumanValidation ACCEPT.",
    )
    require(
        "_load_accepted_human_validation" in service
        and "_candidate_snapshot" in service
        and "_revalidate_draft" in service,
        "Recommendation Development must revalidate HumanValidation, candidate and upstream context.",
    )

    for token in (
        '"automatic_recommendation_generation_performed": False',
        '"candidate_statement_auto_promoted": False',
        '"recommendation_strength_evaluated": False',
        '"formal_etd_framework_applied": False',
        '"grade_etd_applied": False',
        '"certainty_assessed": False',
        '"grade_assessed": False',
        '"formal_risk_of_bias_assessed": False',
        '"formal_benefit_harm_balance_determined": False',
        '"values_preferences_formally_assessed": False',
        '"resource_use_formally_assessed": False',
        '"equity_formally_assessed": False',
        '"acceptability_formally_assessed": False',
        '"feasibility_formally_assessed": False',
        '"validated_recommendation_created": False',
        '"clinical_recommendation_created": False',
        '"guideline_recommendation_created": False',
        '"canonical_scientific_synthesis_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
    ):
        require(token in service, f"Missing Recommendation Development guardrail: {token}")

    require(
        'STRENGTH_NOT_EVALUATED = "not_evaluated"' in service,
        "Recommendation strength must remain not_evaluated in this phase.",
    )
    require(
        "NOT GRADE EtD" in html
        and "NO AUTO-RECOMMENDATION" in html
        and "strength not_evaluated" in html,
        "UI must state generic/non-GRADE/no-auto-strength boundaries prominently.",
    )
    require(
        "nunca copiado" in html and "Nenhum campo é pré-preenchido" in script,
        "Source candidate wording must not be silently promoted into the new recommendation wording.",
    )

    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "Recommendation Development UI must not call an external LLM.",
    )
    require(
        not any(token in lowered for token in ("auto_recommend", "auto_strength", "auto_grade", "auto_etd")),
        "Recommendation Development UI must not expose automatic decision/strength/framework paths.",
    )

    stage_match = re.search(r"async function stage\(card\)\{(?P<body>.*?)\n\}", script, re.S)
    require(stage_match is not None, "Could not inspect Recommendation Development staging function.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("FINALIZE_OPERATION" not in stage_body, "Staging must not auto-finalize development.")
        require("finalizeDevelopment(" not in stage_body, "Staging must not invoke finalization.")
        require("candidate.statement" not in stage_body, "Staging must not copy source candidate wording.")

    require(
        "GRADE Evidence-to-Decision" in service
        and "força da recomendação permanece not_evaluated" in service
        and "não cria clinical/guideline recommendation" in service,
        "Finalization must require explicit non-GRADE, non-strength and non-formal-recommendation confirmations.",
    )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
