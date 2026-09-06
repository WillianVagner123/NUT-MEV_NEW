from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "config" / "nutev" / "article1_search_master_v1.json"
DRAFT_PATH = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"
PRESS_PATH = ROOT / "config" / "nutev" / "article1_press_review_v1.json"
WEB = ROOT / "apps" / "nutev-web"
FROZEN_RUNTIME_SHA = "6aa7a5fe6009776e611ca3e1506486606b05f4f6"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed audit for NutEV Scientific Closure 1.0 semantics."
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    master = load_json(MASTER_PATH)
    draft = load_json(DRAFT_PATH)
    press = load_json(PRESS_PATH)
    formal = master.get("formal_search") or {}

    # Canonical Article 1 state must remain internally consistent.
    require(
        master.get("status")
        in {
            "DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE",
            "PRESS_COMPLETE_GF10_PENDING",
            "GF10_AUTHORIZED_QUERY_FREEZE_PENDING",
            "QUERY_FROZEN_FORMAL_SEARCH_PENDING",
            "FORMAL_SEARCH_EXECUTED_PRISMA_PENDING",
            "FORMAL_SEARCH_COMPLETE",
        },
        "Article 1 Search Master has an unknown scientific-closure status.",
    )

    press_status = str(formal.get("press_status") or "")
    gf10 = formal.get("gf10_authorized") is True
    frozen = formal.get("query_freeze_complete") is True
    formal_run = formal.get("formal_provider_search_executed") is True
    prisma = formal.get("prisma_search_event_emitted") is True

    require(
        press.get("record_type") == "NUTEV_ARTICLE1_PRESS_REVIEW",
        "Canonical Article 1 PRESS record is missing or has the wrong type.",
    )
    require(
        press.get("human_review_required") is True,
        "PRESS must explicitly require human review.",
    )
    require(
        (press.get("guardrails") or {}).get("no_automatic_press_pass") is True,
        "PRESS record must forbid automatic PASS.",
    )

    if press_status == "PASS":
        require(press.get("status") == "PASS", "Search Master says PRESS PASS without canonical PRESS PASS record.")
        require(bool(press.get("reviewer")), "PRESS PASS requires a recorded human reviewer.")
        require(bool(press.get("reviewed_at")), "PRESS PASS requires a human review timestamp.")
        require(bool(press.get("press_decision")), "PRESS PASS requires an explicit human decision.")
        require(
            all(item.get("status") == "COMPLETE" for item in press.get("review_items", [])),
            "PRESS PASS requires every mandatory review item to be complete.",
        )
        require(
            all(item.get("status") == "COMPLETE" for item in press.get("delta_tests", [])),
            "PRESS PASS requires every mandatory delta test to be complete.",
        )
    else:
        require(
            press.get("status") != "PASS",
            "Canonical PRESS record says PASS while Search Master has not recorded PRESS PASS.",
        )

    c4 = press.get("c4_social_context") or {}
    if press.get("status") == "PASS":
        require(
            c4.get("decision") in {"ADOPT_C4", "REVISE_C4", "REJECT_C4"},
            "PRESS PASS requires an explicit human C4 decision.",
        )
    else:
        require(
            c4.get("decision") in {"PENDING_HUMAN_DECISION", "ADOPT_C4", "REVISE_C4", "REJECT_C4"},
            "C4 has an invalid decision state.",
        )

    provider_validation = press.get("provider_native_validation") or {}
    for provider in ("pubmed", "lilacs_bvs", "scielo", "scopus", "web_of_science"):
        require(provider in provider_validation, f"Missing provider-native validation slot: {provider}.")
    for provider in ("scopus", "web_of_science"):
        record = provider_validation.get(provider) or {}
        require(record.get("simulation_forbidden") is True, f"{provider} must remain explicitly non-simulatable.")

    # Gate ordering is strict and fail-closed.
    if gf10:
        require(press_status == "PASS", "GF-10 cannot be authorized before PRESS PASS.")
        require(
            (press.get("downstream_gate") or {}).get("authorized") is True,
            "Search Master GF-10 authorization lacks matching canonical downstream gate record.",
        )
    if frozen:
        require(gf10, "Query freeze cannot be complete before GF-10 authorization.")
    if formal_run:
        require(frozen, "Formal provider search cannot execute before query freeze.")
    if prisma:
        require(formal_run, "PRISMA search event cannot exist before formal provider search execution.")

    require(
        (draft.get("formal_gate") or {}).get("guardrail"),
        "Query draft must preserve an explicit formal-search guardrail.",
    )
    require(
        (draft.get("guardrails") or {}).get("no_eligibility_decision") is True,
        "Query draft must not encode eligibility decisions.",
    )
    require(
        (draft.get("guardrails") or {}).get("no_prisma_event") is True,
        "Query draft must not emit PRISMA events.",
    )

    # UI must not use substring PASS logic: NOT_YET_RECORDED_AS_PASS contains PASS.
    dashboard = read(WEB / "dashboard.js")
    presentation = read(WEB / "presentation.js")
    require(
        "includes('PASS')" not in dashboard and 'includes("PASS")' not in dashboard,
        "Dashboard must never detect PRESS PASS by substring.",
    )
    require(
        "includes('PASS')" not in presentation and 'includes("PASS")' not in presentation,
        "Presentation view must never detect PRESS PASS by substring.",
    )

    press_profiles = load_json(WEB / "press-review-profiles.json")
    active_profile = (press_profiles.get("profiles") or [{}])[0]
    require(
        active_profile.get("source_search_master") == "config/nutev/article1_search_master_v1.json",
        "Active PRESS UI profile must point to the current Article 1 Search Master.",
    )
    require(
        active_profile.get("downstream_gate_id") == "GF-10",
        "Active PRESS UI profile must identify GF-10 as the downstream authorization gate.",
    )
    require(
        active_profile.get("legacy") is not True,
        "A legacy PRESS profile cannot be the active profile.",
    )

    # ClaimEvaluation remains generic appraisal, not formal RoB/GRADE.
    claim_service = read(WEB / "claim_evaluation_appraisal.py")
    require(
        'APPRAISAL_METHOD = "NUTEV_GENERIC_CLAIM_APPRAISAL_V1"' in claim_service,
        "ClaimEvaluation must remain explicitly generic until formal RoB is implemented.",
    )
    require(
        '"formal_risk_of_bias_assessed": False' in claim_service,
        "ClaimEvaluation must not claim formal Risk of Bias assessment.",
    )

    # Recommendation Adoption is governance only, never a clinical recommendation.
    adoption_service = read(WEB / "recommendation_adoption.py")
    for token in (
        '"recommendation_strength_evaluated": False',
        '"certainty_assessed": False',
        '"grade_assessed": False',
        '"formal_etd_framework_applied": False',
        '"formal_risk_of_bias_assessed": False',
        '"clinical_recommendation_created": False',
        '"guideline_recommendation_created": False',
        '"meta_analysis_performed": False',
        '"prisma_event_emitted": False',
    ):
        require(token in adoption_service, f"Recommendation Adoption guardrail missing: {token}")

    # Scientific validation runtime remains frozen until the independent human benchmark closes.
    freeze_doc = read(ROOT / "validation" / "VALIDATION_FREEZE.md")
    benchmark_tool = read(ROOT / "tools" / "verify_benchmark_freeze_chain.py")
    require(FROZEN_RUNTIME_SHA in freeze_doc, "Validation freeze document no longer names the frozen runtime SHA.")
    require(
        f'FROZEN_RUNTIME_SHA = "{FROZEN_RUNTIME_SHA}"' in benchmark_tool,
        "Benchmark freeze-chain tool no longer pins the frozen runtime SHA.",
    )

    result = {
        "status": "PASS" if not failures else "FAIL",
        "article1": {
            "press_status": press_status,
            "gf10_authorized": gf10,
            "query_freeze_complete": frozen,
            "formal_provider_search_executed": formal_run,
            "prisma_search_event_emitted": prisma,
        },
        "press_record_status": press.get("status"),
        "failures": failures,
    }
    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
