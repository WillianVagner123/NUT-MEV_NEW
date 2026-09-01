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
        description="Adversarial audit for Recommendation Adoption governance semantics."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    service = read("recommendation_adoption.py")
    coordinator = read("governed_synthesis_release.py")
    html = read("recommendation-adoption.html")
    script = read("recommendation-adoption.js")
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        'ADOPTION_STAGE_OPERATION = "STAGE_RECOMMENDATION_ADOPTION"' in service
        and 'ADOPTION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION"' in service,
        "Recommendation Adoption must use explicit stage/decide operations.",
    )
    require(
        'ADOPTION_STAGE_OPERATION = "STAGE_RECOMMENDATION_ADOPTION"' in coordinator
        and 'ADOPTION_DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION"' in coordinator,
        "Local-only coordinator must route Recommendation Adoption operations.",
    )
    require(
        'ADOPT_FOR_DEFINED_SCOPE = "ADOPT_FOR_DEFINED_SCOPE"' in service
        and 'RETURN_FOR_REVISION = "RETURN_FOR_REVISION"' in service,
        "Adoption decisions must use the explicit bounded governance vocabulary.",
    )
    require(
        "_load_finalized_development" in service
        and "_development_snapshot" in service
        and "_revalidate_case" in service,
        "Recommendation Adoption must revalidate the finalized development and upstream context.",
    )

    for token in (
        '"automatic_adoption_decision_performed": False',
        '"automatic_revision_applied": False',
        '"recommendation_strength_evaluated": False',
        '"certainty_assessed": False',
        '"grade_assessed": False',
        '"formal_etd_framework_applied": False',
        '"grade_etd_applied": False',
        '"formal_risk_of_bias_assessed": False',
        '"validated_recommendation_created": False',
        '"clinical_recommendation_created": False',
        '"guideline_recommendation_created": False',
        '"universal_recommendation_created": False',
        '"canonical_scientific_synthesis_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
        '"source_recommendation_development_changed": False',
    ):
        require(token in service, f"Missing Recommendation Adoption guardrail: {token}")

    require(
        '"recommendation_strength": STRENGTH_NOT_EVALUATED' in service,
        "Adoption must preserve recommendation strength as not_evaluated.",
    )
    require(
        "SCOPE-LIMITED ONLY" in html
        and "NO AUTO-STRENGTH" in html
        and "ADOPT_FOR_DEFINED_SCOPE" in html,
        "UI must prominently state scope-limited adoption and no automatic strength.",
    )
    require(
        'option value="">Selecione uma decisão humana' in script,
        "Adoption decision selector must start empty.",
    )

    lowered = script.casefold()
    require(
        not any(token in lowered for token in ("openai", "anthropic", "claude", "gemini", "chatgpt")),
        "Recommendation Adoption UI must not call an external LLM.",
    )
    require(
        not any(token in lowered for token in ("auto_adopt", "auto_strength", "auto_grade", "auto_certainty")),
        "Recommendation Adoption UI must not expose automatic adoption/strength/certainty paths.",
    )

    stage_match = re.search(
        r'root\.querySelectorAll\("\.stage-adoption"\).*?await post\(\{(?P<body>.*?)\}\);',
        script,
        re.S,
    )
    require(stage_match is not None, "Could not inspect Recommendation Adoption staging path.")
    if stage_match is not None:
        stage_body = stage_match.group("body")
        require("STAGE_OPERATION" in stage_body, "Staging must call only the stage operation.")
        require("DECIDE_OPERATION" not in stage_body, "Staging must not auto-decide adoption.")
        require("decision:" not in stage_body, "Staging must not include a hidden adoption decision.")

    require(
        "eventual ADOPT vale apenas para o adoption scope declarado" in service
        and "não infere recommendation strength, certainty ou GRADE" in service
        and "não cria clinical/guideline recommendation automaticamente" in service,
        "Decision must require explicit scope/no-strength/no-guideline confirmations.",
    )
    require(
        "decisão conflitante não pode sobrescrevê-la" in service,
        "Canonical adoption decision must not be silently overwritten.",
    )

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
