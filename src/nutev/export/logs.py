from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _unsupported_provider_count(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return sum(len(items) for items in value.values() if isinstance(items, list))


def assess_scientific_readiness(summary: dict) -> dict[str, Any]:
    """Derive manuscript-use readiness without conflating it with execution.

    A computational run can finish while still being unsuitable for a definitive
    Article 1 methods freeze.  This function therefore exposes a separate state:

    ``blocked``
        At least one computational/scientific prerequisite demonstrably failed.

    ``computationally_ready_for_human_review``
        No blocking computational condition was detected, but the pipeline does
        not claim that human screening/adjudication or manuscript approval is
        complete.

    ``manuscript_ready``
        Reserved for runs that explicitly carry ``human_review_complete=True``
        and ``manuscript_gates_complete=True``.  The software never infers those
        human/scientific approvals by itself.
    """

    execution_status = str(summary.get("run_status") or summary.get("status") or "unknown")
    blockers: list[str] = []

    if execution_status != "completed":
        blockers.append(f"execution_status={execution_status}")
    if _positive_int(summary.get("providers_failed")):
        blockers.append("provider_failures_present")
    if _unsupported_provider_count(summary.get("providers_unsupported_by_workstream")):
        blockers.append("declared_providers_not_executed")

    coverage = summary.get("coverage_loss")
    if isinstance(coverage, dict) and _positive_int(coverage.get("unrecoverable")):
        blockers.append("unrecoverable_coverage_loss")

    for key, value in summary.items():
        if key.endswith("_error") and value:
            blockers.append(key)

    if blockers:
        readiness = "blocked"
    elif summary.get("human_review_complete") is True and summary.get("manuscript_gates_complete") is True:
        readiness = "manuscript_ready"
    else:
        readiness = "computationally_ready_for_human_review"

    return {
        "execution_status": execution_status,
        "scientific_readiness": readiness,
        "scientific_readiness_blockers": sorted(set(blockers)),
        "human_review_complete": bool(summary.get("human_review_complete", False)),
        "manuscript_gates_complete": bool(summary.get("manuscript_gates_complete", False)),
    }


def write_run_summary(path: Path, summary: dict) -> None:
    summary.update(assess_scientific_readiness(summary))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
