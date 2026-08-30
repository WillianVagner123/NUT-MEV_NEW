from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_articles_ui_exposes_operational_priority_without_scientific_overclaim() -> None:
    html = (WEB / "articles.html").read_text(encoding="utf-8")
    js = (WEB / "articles.js").read_text(encoding="utf-8")

    assert 'id="tierFilter"' in html
    assert 'id="sortFilter"' in html
    assert 'value="relevance"' in html
    assert "Tier A · aprofundar primeiro" in html
    assert "Não equivalem a inclusão científica" in html

    assert "__nutev_tier:" in js
    assert "__nutev_sort:" in js
    assert "reference_rank" in js
    assert "reference_score" in js
    assert "reference_tier" in js
    assert "julgamento científico" in js
