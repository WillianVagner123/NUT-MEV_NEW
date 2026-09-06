from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

import search_adapter


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_home_query_runs_immediately_after_search_page_initializes() -> None:
    app = read("app.js")
    assert "if(params.get('view')==='history'){switchView('history');return}" in app
    assert "if(engineReady&&state.providers.length)await runSearch()" in app


def test_primary_shell_contains_only_generic_search_product_surfaces() -> None:
    script = read("product-ui.js")
    nav = script.split("const NAV_GROUPS=", 1)[1].split("const GLOSSARY=", 1)[0]
    for href in ("/evidence.html", "/evidence-map.html", "/radar.html", "/ask.html"):
        assert href not in nav
    home = read("index.html")
    for href in ('href="/evidence-map.html"', 'href="/radar.html"', 'href="/ask.html"'):
        assert href not in home


def test_article1_exploration_surfaces_are_noindexed_and_use_canonical_shell() -> None:
    for name in ("evidence.html", "evidence-map.html", "radar.html", "ask.html"):
        html = read(name)
        assert '<meta name="robots" content="noindex,nofollow">' in html
        assert 'src="./product-ui.js"' in html
        nav = re.search(r'<nav[^>]*>(.*?)</nav>', html, re.S)
        assert nav and "PRESS" not in nav.group(1) and "Review" not in nav.group(1)


def test_query_relevance_dominates_legacy_nutev_priority(monkeypatch) -> None:
    monkeypatch.setattr(search_adapter, "load_canonical_taxonomy", lambda _path: ({}, {}))
    monkeypatch.setattr(search_adapter, "_read_profile", lambda: {"focus_keywords": [], "provider_weights": {}, "guardrails": {}})
    monkeypatch.setattr(search_adapter, "score_record", lambda row, *_args, **_kwargs: {**row, "reference_score": float(row["legacy_priority"])})
    ranked = search_adapter._score_rows([
        {"title": "Creatine supplementation and cognition in older adults", "abstract": "Creatine improved cognitive task performance in older adults.", "provider_query": "creatine cognition older adults", "legacy_priority": 10},
        {"title": "Lifestyle medicine clinical practice guideline", "abstract": "General lifestyle care guidance.", "provider_query": "creatine cognition older adults", "legacy_priority": 100},
    ], query="creatine cognition older adults")
    assert ranked[0]["title"].startswith("Creatine supplementation")
    assert ranked[0]["query_relevance_score"] > ranked[1]["query_relevance_score"]
    assert ranked[0]["nutev_priority_score"] == 10
    assert ranked[1]["nutev_priority_score"] == 100


def test_classification_explanation_uses_effective_provider_query(monkeypatch) -> None:
    monkeypatch.setattr(search_adapter, "load_canonical_taxonomy", lambda _path: ({}, {}))
    monkeypatch.setattr(search_adapter, "_read_profile", lambda: {"focus_keywords": [], "provider_weights": {}, "guardrails": {}})
    monkeypatch.setattr(search_adapter, "score_record", lambda row, *_args, **_kwargs: {**row, "reference_score": 1.0})
    result = search_adapter._score_rows([
        {"title": "Creatine and cognition", "abstract": "Older adults", "provider_query": "creatine cognition"}
    ], query="human question without those terms")[0]
    match = result["search_classification"]["query_match"]
    assert "creatine" in match["title_hits"]
    assert "human" not in match["terms_considered"]
