from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "apps" / "nutev-web" / "query_compiler.py"
SPEC = importlib.util.spec_from_file_location("nutev_web_query_compiler", MODULE_PATH)
assert SPEC and SPEC.loader
compiler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compiler
SPEC.loader.exec_module(compiler)


def _strategy() -> dict[str, object]:
    return {
        "framework": "PCC",
        "concepts": [
            {"label": "Population", "terms": ["free:adult*", "mesh:Adult"]},
            {"label": "Concept", "terms": ["free:lifestyle medicine", "decs:Medicina do Estilo de Vida"]},
            {"label": "Context", "terms": ["free:nutrition", "mesh:Diet"]},
        ],
    }


def test_structured_review_compiles_provider_specific_queries() -> None:
    plan = compiler.compile_query_plan(
        "What is the scope of nutrition evidence in Lifestyle Medicine?",
        ["pubmed", "europepmc", "lilacs_bvs_native", "openalex"],
        _strategy(),
    )
    assert plan["mode"] == "structured_review"
    assert plan["framework"] == "PCC"
    assert plan["controlled_vocabulary_terms"] == 3
    pubmed = plan["provider_queries"]["pubmed"]
    assert '"Adult"[Mesh]' in pubmed["query"]
    assert 'adult*[Title/Abstract]' in pubmed["query"]
    assert '"Medicina do Estilo de Vida"[Title/Abstract]' in pubmed["query"]
    assert pubmed["dialect"] == "pubmed_mesh_title_abstract"
    europe = plan["provider_queries"]["europepmc"]
    assert 'MESH:"Adult"' in europe["query"]
    assert 'TITLE_ABS:"lifestyle medicine"' in europe["query"]
    bvs = plan["provider_queries"]["lilacs_bvs_native"]
    assert 'mh:"Medicina do Estilo de Vida"' in bvs["query"]
    assert 'tw:"lifestyle medicine"' in bvs["query"]
    openalex = plan["provider_queries"]["openalex"]
    assert "[Mesh]" not in openalex["query"]
    assert "mh:" not in openalex["query"]
    assert '"lifestyle medicine"' in openalex["query"]


def test_exact_review_preserves_provider_syntax_byte_for_byte() -> None:
    exact = '(("Diet"[Mesh] OR diet*[tiab]) AND (guideline[pt] OR guideline*[ti])) NOT comment[pt]'
    plan = compiler.compile_query_plan(
        "What do normative documents recommend for adult dietary care?",
        ["pubmed"],
        {
            "mode": "exact",
            "strategy_id": "B-NORM-PUBMED",
            "strategy_version": "v0.7",
            "run_class": "PILOT",
            "provider_queries": {"pubmed": exact},
        },
    )
    assert plan["mode"] == "exact_review"
    assert plan["strategy_id"] == "B-NORM-PUBMED"
    assert plan["strategy_version"] == "v0.7"
    assert plan["run_class"] == "PILOT"
    assert plan["provider_queries"]["pubmed"]["query"] == exact
    assert plan["provider_queries"]["pubmed"]["dialect"] == "exact_provider_syntax"


def test_exact_review_requires_query_for_every_selected_provider() -> None:
    with pytest.raises(ValueError, match="query para cada base selecionada"):
        compiler.compile_query_plan(
            "question",
            ["pubmed", "openalex"],
            {
                "mode": "exact",
                "strategy_id": "TEST",
                "strategy_version": "v1",
                "run_class": "PILOT",
                "provider_queries": {"pubmed": "diet*[ti]"},
            },
        )


def test_exact_review_rejects_invalid_run_class() -> None:
    with pytest.raises(ValueError, match="run_class"):
        compiler.compile_query_plan(
            "question",
            ["pubmed"],
            {
                "mode": "exact",
                "run_class": "PRISMA_MAGIC",
                "provider_queries": {"pubmed": "diet*[ti]"},
            },
        )


def test_natural_language_mode_does_not_invent_controlled_vocabulary() -> None:
    question = "nutrition and lifestyle medicine"
    plan = compiler.compile_query_plan(question, ["pubmed", "openalex"], None)
    assert plan["mode"] == "natural_language"
    assert plan["controlled_vocabulary_terms"] == 0
    assert plan["provider_queries"]["pubmed"]["query"] == question
    assert any("não inventa MeSH/DeCS" in item for item in plan["warnings"])


def test_duplicate_terms_are_removed_within_concept() -> None:
    strategy = {
        "framework": "PCC",
        "concepts": [
            {"label": "Concept", "terms": ["mesh:Diet", "mesh:diet", "free:diet"]}
        ],
    }
    plan = compiler.compile_query_plan("diet", ["pubmed"], strategy)
    terms = plan["concepts"][0]["terms"]
    assert len(terms) == 2


def test_invalid_framework_fails_closed() -> None:
    with pytest.raises(ValueError, match="PCC, PICO ou PECO"):
        compiler.compile_query_plan(
            "question",
            ["pubmed"],
            {"framework": "SPIDER", "concepts": [{"label": "x", "terms": ["x"]}]},
        )


def test_unknown_term_kind_fails_closed() -> None:
    with pytest.raises(ValueError, match="Tipo de termo não suportado"):
        compiler.compile_query_plan(
            "question",
            ["pubmed"],
            {
                "framework": "PCC",
                "concepts": [{"label": "x", "terms": [{"text": "x", "kind": "fake"}]}],
            },
        )
