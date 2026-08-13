"""Shared pytest bootstrap for the canonical NutEV suite.

Tests that exercise downstream FORMAL workflows need explicit synthetic gate and
freeze evidence now that the production executor correctly blocks unauthorized
formal searches. This fixture creates test-only evidence; it never weakens the
production guard and is disabled for the strategy-executor tests that verify the
blocking behavior itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from nutev.search import strategy_executor
from nutev_tests.formal_test_support import (
    TEST_CONFIG_DIGEST,
    TEST_GIT_SHA,
    authorize_formal_strategy,
)


@pytest.fixture(autouse=True)
def _synthetic_formal_authorization_for_downstream_tests(monkeypatch, request):
    if Path(str(request.node.fspath)).name == "test_strategy_executor.py":
        return

    original = strategy_executor.require_formal_execution_authorization

    def guarded_with_test_evidence(project_root, strategy_version, **kwargs):
        search_type = str(strategy_version.get("search_type") or "").strip().upper()
        prisma_eligible = bool(strategy_version.get("prisma_eligible"))
        if search_type == "FORMAL" or prisma_eligible:
            authorize_formal_strategy(Path(project_root), str(strategy_version["version_id"]))
            kwargs["current_git_sha"] = TEST_GIT_SHA
            kwargs["current_config_digest"] = TEST_CONFIG_DIGEST
        return original(project_root, strategy_version, **kwargs)

    monkeypatch.setattr(
        strategy_executor,
        "require_formal_execution_authorization",
        guarded_with_test_evidence,
    )
