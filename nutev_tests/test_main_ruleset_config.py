from __future__ import annotations

import json
from pathlib import Path


def _ruleset() -> dict:
    path = Path(__file__).resolve().parents[1] / ".github" / "rulesets" / "main.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_main_ruleset_targets_main_and_blocks_direct_history_rewrites() -> None:
    ruleset = _ruleset()
    assert ruleset["name"] == "Protect main"
    assert ruleset["target"] == "branch"
    assert ruleset["enforcement"] == "active"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    rule_types = {rule["type"] for rule in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= rule_types


def test_main_ruleset_requires_current_canonical_checks() -> None:
    ruleset = _ruleset()
    status_rule = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    params = status_rule["parameters"]
    assert params["strict_required_status_checks_policy"] is True
    contexts = {row["context"] for row in params["required_status_checks"]}
    assert contexts == {
        "tests (python 3.12)",
        "tests (python 3.13)",
        "windows smoke (python 3.12)",
        "typecheck provenance core",
        "lint (ruff)",
        "CodeQL analyze (python)",
        "dependency-review",
        "gitleaks secret scan",
        "forbidden files & large files",
        "build, twine check, clean wheel install",
    }


def test_pull_request_rule_requires_pr_without_forcing_second_human_reviewer() -> None:
    ruleset = _ruleset()
    pr_rule = next(rule for rule in ruleset["rules"] if rule["type"] == "pull_request")
    params = pr_rule["parameters"]
    assert params["required_approving_review_count"] == 0
    assert params["required_review_thread_resolution"] is True
    assert set(params["allowed_merge_methods"]) == {"merge", "squash", "rebase"}
