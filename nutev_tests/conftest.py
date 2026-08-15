from __future__ import annotations

from pathlib import Path

import pytest

from nutev.search import gf02_pubmed_current, strategy_executor
from nutev_tests.formal_test_support import TEST_CONFIG_DIGEST, TEST_GIT_SHA, authorize_formal_strategy


@pytest.fixture(autouse=True)
def _synthetic_formal_authorization_for_downstream_tests(monkeypatch, request):
    test_file = Path(str(request.node.fspath)).name
    if test_file == "test_gf02_pubmed_pilot.py":
        # Historical unit fixtures use GUIDELINE_TITLE as a neutral structural
        # placeholder. Keep that compatibility test-only; production validation
        # and the canonical current query remain unchanged.
        monkeypatch.setattr(
            gf02_pubmed_current,
            "_ALLOWED_RESCUE_WORDS",
            gf02_pubmed_current._ALLOWED_RESCUE_WORDS | {"title"},
        )
    if test_file == "test_strategy_executor.py":
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

    monkeypatch.setattr(strategy_executor, "require_formal_execution_authorization", guarded_with_test_evidence)
