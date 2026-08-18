from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "run_latin_sources.py"
    spec = importlib.util.spec_from_file_location("nutev_run_latin_sources", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lilacs_uses_official_bvs_native_interface() -> None:
    tool = _module()
    url = tool.lilacs_search_url("nutrition guideline")
    assert url.startswith("https://pesquisa.bvsalud.org/portal/")
    assert "LILACS" in url
    assert "nutrition+guideline" in url


def test_scielo_uses_official_native_search_interface() -> None:
    tool = _module()
    url = tool.scielo_search_url("nutrition guideline")
    assert url.startswith("https://search.scielo.org/")
    assert "subject%3A%28nutrition+guideline%29" in url


def test_native_candidates_are_explicitly_nonformal() -> None:
    tool = _module()
    row = tool._candidate(
        "lilacs_bvs_native",
        tool.lilacs_search_url("nutrition guideline"),
        "https://pesquisa.bvsalud.org/portal/resource/pt/biblio-1234567",
        "Clinical nutrition guideline for adult health care",
        "nutrition guideline",
    )
    assert row is not None
    assert row["collection_type"] == "REAL_DISCOVERY_NONFORMAL"
    assert row["formal_execution_authorized"] is False
    assert row["prisma_eligible"] is False
    assert row["scientific_gate_effect"] == "NONE"


def test_native_route_does_not_accept_unrelated_domains() -> None:
    tool = _module()
    row = tool._candidate(
        "scielo_native",
        tool.scielo_search_url("nutrition guideline"),
        "https://example.com/article/1",
        "Nutrition guideline from an unrelated search result",
        "nutrition guideline",
    )
    assert row is None
