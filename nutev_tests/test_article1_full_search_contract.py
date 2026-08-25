from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_article1_profile_has_canonical_routes_and_guardrails() -> None:
    profile = json.loads((WEB / "article1-search-profile.json").read_text(encoding="utf-8"))
    assert profile["profile_id"] == "article1-full-search-2026-08-25"
    assert profile["formal_gate"]["gf10_authorized"] is False
    assert profile["formal_gate"]["status"] == "PREFREEZE_ONLY"
    groups = profile["canonical_keywords"]
    for key in (
        "nutrition_core",
        "normative_markers",
        "structural_care",
        "food_competence",
        "professional_competence",
        "implementation",
        "dietary_orientation",
    ):
        assert groups[key]
    assert "disease" not in json.dumps(groups).lower()


def test_database_roles_keep_formal_and_discovery_sources_separate() -> None:
    profile = json.loads((WEB / "article1-search-profile.json").read_text(encoding="utf-8"))
    db = {item["id"]: item for item in profile["databases"]}
    assert db["pubmed"]["article1_role"] == "FORMAL_CANDIDATE"
    assert db["lilacs_bvs_native"]["article1_role"] == "FORMAL_CANDIDATE"
    assert db["scielo_native"]["article1_role"] == "FORMAL_SUPPLEMENTARY"
    assert db["scopus"]["execution"] == "MANUAL_LICENSED"
    assert db["wos"]["execution"] == "MANUAL_LICENSED"
    for provider in ("europepmc", "openalex", "crossref", "doaj", "semantic_scholar"):
        assert db[provider]["article1_role"] == "DISCOVERY_ONLY"


def test_manual_queries_use_provider_native_field_syntax() -> None:
    profile = json.loads((WEB / "article1-search-profile.json").read_text(encoding="utf-8"))
    manual = profile["manual_queries"]
    assert manual["scopus"]["B-NORM"].startswith("TITLE-ABS-KEY(")
    assert manual["scopus"]["C-STRUCT"].startswith("TITLE-ABS-KEY(")
    assert manual["wos"]["B-NORM"].startswith("TS=(")
    assert manual["wos"]["C-STRUCT"].startswith("TS=(")


def test_full_search_ui_is_fail_closed_for_formal_execution() -> None:
    html = (WEB / "full-search.html").read_text(encoding="utf-8")
    js = (WEB / "full-search.js").read_text(encoding="utf-8")
    assert "Pesquisa completa" in html
    assert "Rodar todos — PREFLIGHT" in html
    assert "Rodar todos — FORMAL" in html
    assert "gf10_authorized" in js
    assert "PASS_STATIC" in js
    assert "não entram no PRISMA" in js
    assert "MANUAL_LICENSED" in js
    assert "per_provider:formal?0:25" in js
    assert "max_results:formal?0:300" in js


def test_main_navigation_exposes_full_search() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/full-search.html"' in html
    assert "Pesquisa completa" in html
