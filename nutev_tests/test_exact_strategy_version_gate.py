from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "apps" / "nutev-web" / "query_compiler.py"
SPEC = importlib.util.spec_from_file_location("nutev_web_query_compiler_version_gate", MODULE_PATH)
assert SPEC and SPEC.loader
compiler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compiler
SPEC.loader.exec_module(compiler)


def _base_strategy() -> dict[str, object]:
    return {
        "mode": "exact",
        "strategy_id": "C-STRUCT-PUBMED",
        "strategy_version": "v0.5.1",
        "run_class": "PILOT",
        "provider_queries": {"pubmed": "diet*[tiab]"},
    }


def test_exact_review_requires_explicit_strategy_version() -> None:
    strategy = _base_strategy()
    strategy["strategy_version"] = ""
    with pytest.raises(ValueError, match="Versão explícita"):
        compiler.compile_query_plan("question", ["pubmed"], strategy)


def test_exact_review_rejects_unversioned_literal() -> None:
    strategy = _base_strategy()
    strategy["strategy_version"] = "UNVERSIONED"
    with pytest.raises(ValueError, match="UNVERSIONED"):
        compiler.compile_query_plan("question", ["pubmed"], strategy)


def test_exact_review_requires_explicit_strategy_id() -> None:
    strategy = _base_strategy()
    strategy["strategy_id"] = ""
    with pytest.raises(ValueError, match="Strategy ID"):
        compiler.compile_query_plan("question", ["pubmed"], strategy)


def test_versioned_exact_review_still_compiles() -> None:
    plan = compiler.compile_query_plan("question", ["pubmed"], _base_strategy())
    assert plan["mode"] == "exact_review"
    assert plan["strategy_id"] == "C-STRUCT-PUBMED"
    assert plan["strategy_version"] == "v0.5.1"
