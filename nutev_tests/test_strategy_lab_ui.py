import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
CANONICAL = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"
MIRROR = WEB / "strategy-data" / "article1_query_draft_v1.json"


def test_strategy_web_mirror_matches_canonical_query_draft() -> None:
    assert json.loads(MIRROR.read_text(encoding="utf-8")) == json.loads(
        CANONICAL.read_text(encoding="utf-8")
    )


def test_strategy_lab_is_read_only_and_fail_closed() -> None:
    html = (WEB / "strategy.html").read_text(encoding="utf-8")
    js = (WEB / "strategy.js").read_text(encoding="utf-8")

    assert "Strategy Lab" in html
    assert "C4 continua candidata PRESS, não aprovada" in html
    assert "/press-review.html" in html
    assert "/review-qa.html" in html
    assert "GF-10" in html
    assert "NOT EXECUTED" in js
    assert "Nenhuma versão APPROVED/FROZEN é inferida" in js
    assert "method:'POST'" not in js.replace(" ", "")
    assert "fetch('/strategy-data/article1_query_draft_v1.json'" in js
    assert "SEARCH_STATE.json" in js


def test_strategy_lab_does_not_promote_frequency_to_search_terms() -> None:
    html = (WEB / "strategy.html").read_text(encoding="utf-8")
    draft = json.loads(MIRROR.read_text(encoding="utf-8"))

    assert "frequency does not imply term inclusion" in html
    assert draft["guardrails"]["frequency_does_not_imply_term_inclusion"] is True
    assert draft["guardrails"]["no_eligibility_decision"] is True
    assert draft["guardrails"]["no_prisma_event"] is True
    assert draft["formal_gate"]["authorized"] is False
