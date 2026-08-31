from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_regional_profile_is_prefreeze_and_not_prisma() -> None:
    payload = json.loads((WEB / "regional-route-profiles.json").read_text(encoding="utf-8"))
    profile = payload["profiles"][0]
    assert profile["gate_id"] == "GF-01"
    assert profile["mode"] == "PREFREEZE_ROUTE_VALIDATION"
    assert profile["formal_search"] is False
    assert profile["prisma_eligible"] is False
    assert {route["route_id"] for route in profile["routes"]} == {
        "B-NORM-LILACS",
        "B-SUPP-SCIELO",
    }
    assert all(route["query"] for route in profile["routes"])


def test_regional_page_exposes_official_routes_and_guardrails() -> None:
    html = (WEB / "regional-routes.html").read_text(encoding="utf-8")
    script = (WEB / "regional-routes.js").read_text(encoding="utf-8")
    assert "Rotas regionais" in html
    assert "Abrir busca oficial" in script
    assert "SHA-256" in script
    assert "unavailable_not_recoded_as_zero" in script
    assert "formal_search: false" in script
    assert "prisma_eligible: false" in script
    assert "freeze_authorized: false" in script
    assert "gf01_candidate_complete" in script


def test_full_export_requires_record_count_match_when_parseable() -> None:
    script = (WEB / "regional-routes.js").read_text(encoding="utf-8")
    assert "scope === 'FULL_EXPORT'" in script
    assert "parsedTotal !== resultCount" in script
    assert "Exportação marcada como completa" in script


def test_press_page_links_to_regional_validation() -> None:
    html = (WEB / "press-review.html").read_text(encoding="utf-8")
    assert 'href="/regional-routes.html"' in html
    assert "Regional routes" in html
