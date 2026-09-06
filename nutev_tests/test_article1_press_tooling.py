from __future__ import annotations

import json
from pathlib import Path

from nutev.science.article1_press import (
    FORMAL_PROVIDERS,
    ROUTE_ORDER,
    build_delta_tests,
    build_press_package,
    compile_route_query,
    route_specs,
)


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"


def load_draft() -> dict:
    return json.loads(DRAFT.read_text(encoding="utf-8"))


def test_current_draft_compiles_all_current_routes_for_all_formal_providers() -> None:
    specs = route_specs(load_draft())
    assert tuple(specs) == ROUTE_ORDER
    for provider in FORMAL_PROVIDERS:
        for route_id in ROUTE_ORDER:
            query = compile_route_query(provider, specs[route_id])
            assert query
            assert "None" not in query


def test_delta_tests_match_the_five_preregistered_press_comparisons() -> None:
    specs = route_specs(load_draft())
    tests = build_delta_tests("pubmed", specs)
    assert [item["id"] for item in tests] == ["D01", "D02", "D03", "D04", "D05"]
    assert "food based" not in tests[0]["baseline_query"]
    assert "food based" in tests[0]["variant_query"]
    assert "healthy eating" not in tests[1]["baseline_query"]
    assert "healthy eating" in tests[1]["variant_query"]
    assert "meal plan*" not in tests[2]["baseline_query"]
    assert "meal plan*" in tests[2]["variant_query"]
    assert tests[3]["route"] == "C3-IMPLEMENTATION"
    assert tests[4]["route"] == "C4-SOCIAL-CONTEXT"
    assert " NOT " in tests[4]["incremental_query"]
    assert all(item["human_interpretation_required"] is True for item in tests)


def test_press_package_is_fail_closed_and_never_native_validates_itself() -> None:
    package = build_press_package(load_draft())
    assert package["status"] == "PREFREEZE_CANDIDATE_ONLY"
    assert package["formal_execution_authorized"] is False
    assert len(package["package_sha256"]) == 64
    assert package["guardrails"]["candidate_is_not_native_validation"] is True
    assert package["guardrails"]["candidate_is_not_press_pass"] is True
    assert package["guardrails"]["candidate_is_not_query_freeze"] is True
    assert package["guardrails"]["candidate_is_not_formal_search"] is True
    assert package["guardrails"]["candidate_is_not_prisma_event"] is True
    for provider in FORMAL_PROVIDERS:
        record = package["provider_packages"][provider]
        assert record["status"] == "CANDIDATE_NOT_NATIVE_VALIDATED"
        assert set(record["routes"]) == set(ROUTE_ORDER)
        assert len(record["delta_tests"]) == 5
    assert package["provider_packages"]["scopus"]["simulation_forbidden"] is True
    assert package["provider_packages"]["web_of_science"]["simulation_forbidden"] is True


def test_provider_dialects_remain_explicitly_distinct() -> None:
    specs = route_specs(load_draft())
    pubmed = compile_route_query("pubmed", specs["B-NORM"])
    bvs = compile_route_query("lilacs_bvs", specs["B-NORM"])
    scielo = compile_route_query("scielo", specs["B-NORM"])
    scopus = compile_route_query("scopus", specs["B-NORM"])
    wos = compile_route_query("web_of_science", specs["B-NORM"])
    assert "[Title/Abstract]" in pubmed
    assert "tw:" in bvs
    assert "TITLE-ABS-KEY(" in scopus
    assert "TS=(" in wos
    assert "TITLE-ABS-KEY(" not in scielo
    assert "[Title/Abstract]" not in scielo
