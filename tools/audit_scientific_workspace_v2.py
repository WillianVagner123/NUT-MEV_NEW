#!/usr/bin/env python3
"""Adversarial, read-only contract audit for the NutEV Scientific Workspace v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
MASTER = ROOT / "config" / "nutev" / "article1_search_master_v1.json"
QUERY_DRAFT = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(_text(path))


def run_audit() -> dict[str, Any]:
    dashboard = _text(WEB / "dashboard.js")
    ask = _text(WEB / "ask.js")
    strategy = _text(WEB / "strategy.js")
    presentation = _text(WEB / "presentation.js")
    snapshot = _text(WEB / "scientific-snapshot.js")
    quality = _text(WEB / "quality.js")
    intelligence = _text(WEB / "intelligence.js")
    intelligence_html = _text(WEB / "intelligence.html")
    master = _json(MASTER)
    draft = _json(QUERY_DRAFT)

    read_only_scripts = {
        "dashboard.js": dashboard,
        "ask.js": ask,
        "strategy.js": strategy,
        "presentation.js": presentation,
        "quality.js": quality,
        "intelligence.js": intelligence,
    }

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    formal = master.get("formal_search") or {}
    check(
        "PRESS parser is equality-only",
        ".includes('PASS')" not in dashboard
        and '.includes("PASS")' not in dashboard
        and "pressPassed(formal)" in dashboard,
        "Negated values such as NOT_YET_RECORDED_AS_PASS must never satisfy the gate.",
    )
    check(
        "Canonical formal gate remains fail-closed",
        formal.get("press_status") != "PASS"
        and formal.get("gf10_authorized") is False
        and formal.get("query_freeze_complete") is False
        and formal.get("formal_provider_search_executed") is False,
        f"formal_search={formal}",
    )
    check(
        "C4 social-context route remains PRESS-only",
        (
            draft.get("routes", {})
            .get("C-STRUCT", {})
            .get("subroutes", {})
            .get("C4-SOCIAL-CONTEXT", {})
            .get("status")
            == "PRESS_ONLY_CANDIDATE_NOT_APPROVED"
        ),
        "C4 must not be visually or operationally promoted before validation.",
    )
    check(
        "Read-only analytical surfaces contain no POST action",
        all(
            "method:'POST'" not in source.replace(" ", "")
            and 'method:"POST"' not in source.replace(" ", "")
            for source in read_only_scripts.values()
        ),
        "Dashboard, Ask, Strategy, Presentation, Quality and Intelligence are read-only surfaces.",
    )
    check(
        "Ask NutEV has no direct external LLM endpoint",
        "api.openai.com" not in ask and "api.anthropic.com" not in ask,
        "Ask NutEV is grounded retrieval/context composition in this phase.",
    )
    check(
        "Snapshot excludes operational ranking fields",
        all(
            term not in snapshot
            for term in (
                "reference_rank",
                "reference_score",
                "machine_relevance_score",
                "machine_relevance_band",
            )
        ),
        "Presentation snapshot must stay rank-blind.",
    )
    check(
        "Snapshot explicitly refuses PRISMA semantics",
        "snapshot_is_not_prisma:true" in snapshot
        and "snapshot_does_not_change_scientific_state:true" in snapshot,
        "A snapshot records state; it does not approve or transform it.",
    )
    check(
        "Quality Observatory declares system-quality semantics",
        "System health" in _text(WEB / "quality.html")
        or "SYSTEM QUALITY" in _text(WEB / "quality.html"),
        "The observatory must not be presented as evidence-quality assessment.",
    )
    check(
        "Scientific Intelligence remains rank-blind",
        all(
            term not in intelligence
            for term in (
                "reference_rank",
                "reference_score",
                "machine_relevance_score",
                "machine_relevance_band",
            )
        ),
        "Synthesis support must not silently reintroduce Bank or machine ranking semantics.",
    )
    check(
        "Scientific Intelligence does not automate convergence or evidence gaps",
        "convergence_divergence_requires_human_review:true" in intelligence
        and "recurrence_is_not_consensus:true" in intelligence
        and "sparse_mapping_is_not_evidence_gap:true" in intelligence
        and "NOT AUTOMATED CONCLUSION" in intelligence_html,
        "Recurring labels and sparse mapping are navigation signals, not scientific conclusions.",
    )
    check(
        "Scientific Intelligence uses bounded lazy article detail",
        "FINDING_BATCH_LIMIT=24" in intelligence
        and "DETAIL_CONCURRENCY=4" in intelligence
        and "/api/articles/${encodeURIComponent(documentId)}" in intelligence,
        "Finding inspection must stay lazy instead of shipping the whole Workbench detail corpus.",
    )
    combined_frontend = "\n".join(read_only_scripts.values())
    check(
        "No production corpus totals are hardcoded in analytical JS",
        "33067" not in combined_frontend and "33839" not in combined_frontend,
        "Production totals must come from runtime data.",
    )
    check(
        "Formal gates are not exposed as frontend mutations",
        all(
            token not in combined_frontend
            for token in ("authorizeGF10", "emitPrisma", "freezeQuery", "approvePress")
        ),
        "Only canonical scientific workflows may change these states.",
    )

    errors = [item for item in checks if not item["passed"]]
    return {
        "mode": "NUTEV_SCIENTIFIC_WORKSPACE_V2_DEATH_TEST",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "read_only": True,
        "guardrail": (
            "This audit checks software/UI scientific semantics and system contracts; "
            "it does not assess evidence quality, risk of bias, certainty, eligibility, or PRISMA results."
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
