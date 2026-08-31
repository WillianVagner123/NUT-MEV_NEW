"""Contracts for the NutEV Scientific Intelligence Workspace v2.

Covers the Evidence Map, dashboard drill-down, Review Control Center and Dossier v2. The
scientific guardrails are asserted here, not merely documented: counts are navigation, routes are
not eligibility, machine profiles are not human decisions and the web tier cannot move the
formal-search gate.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

import article1_context_index as context_index
import human_review_store as review_store
import review_control
from article_workbench_data import load_article_page


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _summary(
    document_id: str,
    *,
    title: str,
    year: int | None,
    provider: str,
    document_class: str,
    domains: list[str],
    routes: list[str],
    full_text_status: str,
) -> dict:
    return {
        "context_version": "nutev_article1_agent_context_v1",
        "document_id": document_id,
        "title": title,
        "year": year,
        "doi": document_id.removeprefix("doi:"),
        "pmid": None,
        "source_provider": provider,
        "document_class": "guidance",
        "full_text_status": full_text_status,
        "reference_stub": f"Author. {title}. Journal. {year}.",
        "routes": routes,
        "review_profile": {
            "primary_document_class": document_class,
            "operational_domains": domains,
            "operational_domain_matches": {domain: [f"{domain}-term"] for domain in domains},
        },
        "evidence_excerpt_count": 1,
        "result_bundle_count": 1,
    }


FIXTURE_SUMMARIES = [
    _summary(
        "doi:10.1000/fbdg",
        title="Food-based dietary guideline for adults",
        year=2021,
        provider="pubmed",
        document_class="food_based_dietary_guideline",
        domains=["food_based_guidance", "social_context"],
        routes=["B-NORM"],
        full_text_status="retrieved",
    ),
    _summary(
        "doi:10.1000/cpg-social",
        title="Clinical practice guideline on social eating context",
        year=2023,
        provider="europepmc",
        document_class="clinical_practice_guideline",
        domains=["social_context", "dietary_counseling"],
        routes=["B-NORM", "C-STRUCT"],
        full_text_status="partial",
    ),
    _summary(
        "doi:10.1000/cpg-monitor",
        title="Clinical practice guideline on monitoring",
        year=2020,
        provider="pubmed",
        document_class="clinical_practice_guideline",
        domains=["social_context", "monitoring_follow_up"],
        routes=["C-STRUCT"],
        full_text_status="not_retrieved",
    ),
    _summary(
        "doi:10.1000/qualitative",
        title="Qualitative study without operational domain",
        year=None,
        provider="openalex",
        document_class="primary_qualitative",
        domains=[],
        routes=[],
        full_text_status="unavailable",
    ),
]


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    """A verified, rank-blind Article 1 context bundle."""
    root = tmp_path / "agent_context" / "article1"
    root.mkdir(parents=True)
    summaries = root / "ARTICLE_SUMMARIES.jsonl"
    summaries.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in FIXTURE_SUMMARIES),
        encoding="utf-8",
    )
    (root / "SEARCH_STATE.json").write_text(
        json.dumps(
            {
                "question": "Article 1 question",
                "master_status": "DISCOVERY_CLOSED_FORMAL_SEARCH_PENDING_PRESS_FREEZE",
                "formal_search": {
                    "press_status": "NOT_YET_RECORDED_AS_PASS",
                    "gf10_authorized": False,
                    "query_freeze_complete": False,
                    "formal_provider_search_executed": False,
                    "prisma_search_event_emitted": False,
                },
                "runtime": {"workbench": {"counts": {"articles": 4}}},
            }
        ),
        encoding="utf-8",
    )
    (root / "CONTEXT_MANIFEST.json").write_text(
        json.dumps(
            {
                "context_type": "NUTEV_ARTICLE1_AGENT_CONTEXT",
                "status": "PASS",
                "search_id": "fixture_search",
                "context_version": "nutev_article1_agent_context_v1",
                "created_at": "2026-08-31T00:00:00+00:00",
                "source": {
                    "workbench_database_sha256": "0" * 64,
                    "route_queue_manifest_sha256": "1" * 64,
                },
                "outputs": {
                    "article_summaries": {"path": str(summaries), "sha256": _sha(summaries)}
                },
            }
        ),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# Verified bundle loading
# ---------------------------------------------------------------------------


def test_bundle_is_hash_verified_before_use(bundle: Path) -> None:
    context = context_index.load_context(bundle)
    assert len(context.records) == len(FIXTURE_SUMMARIES)

    (bundle / "ARTICLE_SUMMARIES.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(context_index.Article1ContextError, match="SHA-256 mismatch"):
        context_index.load_context(bundle)


def test_missing_bundle_is_an_explicit_state_not_an_empty_corpus(tmp_path: Path) -> None:
    with pytest.raises(context_index.Article1ContextUnavailable):
        context_index.load_context(tmp_path / "nowhere")


def test_rank_and_relevance_fields_are_refused(bundle: Path) -> None:
    leaked = dict(FIXTURE_SUMMARIES[0], reference_rank=1, reference_score=9.9)
    (bundle / "ARTICLE_SUMMARIES.jsonl").write_text(
        json.dumps(leaked, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path = bundle / "CONTEXT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["article_summaries"]["sha256"] = _sha(bundle / "ARTICLE_SUMMARIES.jsonl")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(context_index.Article1ContextError, match="rank/relevance"):
        context_index.load_context(bundle)


# ---------------------------------------------------------------------------
# Evidence Map
# ---------------------------------------------------------------------------


def _cell(payload: dict, domain: str, document_class: str) -> dict:
    row = next(item for item in payload["rows"] if item["domain"] == domain)
    return next(cell for cell in row["cells"] if cell["document_class"] == document_class)


def test_evidence_map_counts_match_the_underlying_documents(bundle: Path) -> None:
    context = context_index.load_context(bundle)
    payload = context_index.evidence_map(context=context)

    cell = _cell(payload, "social_context", "clinical_practice_guideline")
    assert cell["documents"] == 2
    assert cell["routes"]["B-NORM"] == 1
    assert cell["routes"]["C-STRUCT"] == 2
    assert cell["routes"]["overlap"] == 1
    assert cell["full_text"]["available"] == 1

    # Row totals are distinct documents in the domain; column totals distinct documents in the
    # class. Cell assignments (a document counted once per domain) are reported separately.
    assert payload["row_totals"]["social_context"] == 3
    assert payload["column_totals"]["clinical_practice_guideline"] == 2
    assert payload["universe"]["filtered_documents"] == 4
    assert payload["universe"]["cell_assignments"] == 7
    assert payload["universe"]["multi_domain_documents"] == 3

    # A document with no detected domain is still counted, in an explicit row.
    assert _cell(payload, context_index.NO_DOMAIN_KEY, "primary_qualitative")["documents"] == 1


def test_evidence_map_cell_returns_exactly_the_documents_behind_the_number(bundle: Path) -> None:
    context = context_index.load_context(bundle)
    payload = context_index.evidence_map_cell(
        context=context, domain="social_context", document_class="clinical_practice_guideline"
    )

    assert payload["total_filtered"] == 2
    assert [doc["document_id"] for doc in payload["documents"]] == [
        "doi:10.1000/cpg-social",
        "doi:10.1000/cpg-monitor",
    ]
    assert _cell(context_index.evidence_map(context=context), "social_context",
                 "clinical_practice_guideline")["documents"] == payload["total_filtered"]


def test_evidence_map_filters_are_applied_server_side(bundle: Path) -> None:
    context = context_index.load_context(bundle)

    b_norm = context_index.evidence_map(context=context, route="B-NORM")
    assert b_norm["universe"]["filtered_documents"] == 2
    assert _cell(b_norm, "social_context", "clinical_practice_guideline")["documents"] == 1

    recent = context_index.evidence_map(context=context, year_from=2021)
    assert recent["universe"]["filtered_documents"] == 2

    unrouted = context_index.evidence_map(context=context, route="unrouted")
    assert unrouted["universe"]["filtered_documents"] == 1


def test_evidence_map_intensity_is_document_count_only(bundle: Path) -> None:
    payload = context_index.evidence_map(context=context_index.load_context(bundle))
    assert payload["intensity_semantics"] == (
        "document count only; never quality, certainty or effect magnitude"
    )
    for field in ("quality", "certainty", "risk_of_bias", "effect", "eligib"):
        assert field not in json.dumps(payload["rows"])


def test_timeline_series_are_bounded_and_year_only(bundle: Path) -> None:
    context = context_index.load_context(bundle)
    payload = context_index.timeline(context=context, series=["all", "B-NORM"])

    assert payload["years"] == [2020, 2021, 2023]
    assert payload["undated_documents"] == 1
    all_series = next(item for item in payload["series"] if item["key"] == "all")
    assert all_series["documents"] == 4
    assert sum(point["documents"] for point in all_series["points"]) == 3

    with pytest.raises(context_index.Article1ContextError):
        context_index.timeline(context=context, series=list(context_index.TIMELINE_SERIES)[:7])


def test_routes_compare_separates_overlap_and_exclusives(bundle: Path) -> None:
    payload = context_index.routes_compare(context=context_index.load_context(bundle))
    counts = payload["counts"]

    assert counts["B-NORM"] == 2
    assert counts["C-STRUCT"] == 2
    assert counts["overlap"] == 1
    assert counts["only_B-NORM"] == 1
    assert counts["only_C-STRUCT"] == 1
    assert counts["unrouted"] == 1
    assert "not inclusion" in payload["guardrail"]


def test_dashboard_overview_is_a_server_side_aggregate(bundle: Path) -> None:
    context = context_index.load_context(bundle)
    payload = context_index.dashboard_overview(context=context)

    assert payload["universe"]["filtered_documents"] == 4
    assert payload["full_text"]["available"] == 2
    assert payload["routes"]["union"] == 3
    assert {item["key"] for item in payload["document_classes"]} == {
        "food_based_dietary_guideline", "clinical_practice_guideline", "primary_qualitative"
    }
    # The aggregate never ships the corpus itself.
    assert "articles" not in payload
    assert payload["formal_search"]["gf10_authorized"] is False


# ---------------------------------------------------------------------------
# Drill-down into the paged corpus
# ---------------------------------------------------------------------------


@pytest.fixture
def workbench(tmp_path: Path) -> Path:
    root = tmp_path / "workbench"
    root.mkdir(parents=True)
    database = root / "evidence_workbench_review.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE article_cards (
              document_id TEXT PRIMARY KEY,
              title TEXT, year INTEGER, doi TEXT, pmid TEXT, source_provider TEXT,
              document_class TEXT, full_text_status TEXT, cache_key TEXT, reference_stub TEXT,
              llm_context_chars INTEGER NOT NULL DEFAULT 0, search_text TEXT, card_json TEXT
            );
            CREATE TABLE evidence_excerpts (
              excerpt_id TEXT PRIMARY KEY, document_id TEXT, priority_score REAL, excerpt_json TEXT
            );
            CREATE TABLE result_bundles (
              result_id TEXT PRIMARY KEY, document_id TEXT, priority_score REAL, result_json TEXT
            );
            """
        )
        for row in FIXTURE_SUMMARIES:
            connection.execute(
                """
                INSERT INTO article_cards (
                  document_id, title, year, doi, pmid, source_provider, document_class,
                  full_text_status, cache_key, reference_stub, llm_context_chars, search_text, card_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["document_id"], row["title"], row["year"], row["doi"], row["pmid"],
                    row["source_provider"], row["document_class"], row["full_text_status"],
                    "cache", row["reference_stub"], 100, str(row["title"]).casefold(),
                    json.dumps({"identity": {"title": row["title"]}}),
                ),
            )
        connection.commit()
    (root / "WORKBENCH_MANIFEST.json").write_text(
        json.dumps(
            {
                "workbench_type": "NUTEV_ARTICLE_WORKBENCH_V1",
                "status": "PASS",
                "counts": {"articles": len(FIXTURE_SUMMARIES)},
                "outputs": {"database": {"path": str(database), "sha256": _sha(database)}},
            }
        ),
        encoding="utf-8",
    )
    return root


def test_drill_down_restricts_the_corpus_page_to_the_selected_documents(
    bundle: Path, workbench: Path
) -> None:
    context = context_index.load_context(bundle)
    cell = context_index.evidence_map_cell(
        context=context, domain="social_context", document_class="clinical_practice_guideline"
    )
    document_ids = [doc["document_id"] for doc in cell["documents"]]

    page = load_article_page(
        root=workbench,
        document_ids=document_ids,
        context_filters={"domain": "social_context", "document_class": "clinical_practice_guideline"},
    )
    assert page["total_filtered"] == cell["total_filtered"]
    assert {row["document_id"] for row in page["articles"]} == set(document_ids)
    assert page["context_restricted"] is True
    assert page["filters"]["context"]["domain"] == "social_context"


def test_an_empty_restriction_is_an_empty_page_not_the_whole_corpus(workbench: Path) -> None:
    page = load_article_page(root=workbench, document_ids=[], context_filters={"domain": "none"})
    assert page["total_filtered"] == 0
    assert page["articles"] == []


def test_corpus_stays_server_paginated_and_capped(workbench: Path) -> None:
    page = load_article_page(root=workbench, limit=999)
    assert page["performance"]["max_page_size"] == 100
    assert page["performance"]["full_corpus_sent_to_browser"] is False
    first = load_article_page(root=workbench, limit=1)
    assert first["page_size"] == 1
    assert first["next_cursor"]


# ---------------------------------------------------------------------------
# Review Control Center
# ---------------------------------------------------------------------------


def test_review_status_and_queue_stay_rank_blind(bundle: Path, tmp_path: Path) -> None:
    context = context_index.load_context(bundle)
    store = tmp_path / "human_review"
    review_store.append_event(
        document_id="doi:10.1000/cpg-social", reviewer_id="ana",
        status="REVIEWED", decision="READ", root=store,
    )
    states = review_store.document_states(root=store)

    status = review_control.review_status(context=context, states=states)
    assert status["totals"]["queue"] == 4
    assert status["totals"]["counts"]["REVIEWED"] == 1
    assert status["totals"]["counts"]["NOT_STARTED"] == 3
    assert status["by_route"]["overlap"]["queue"] == 1
    assert status["by_route"]["unrouted"]["queue"] == 1

    queue = review_control.review_queue(context=context, states=states)
    serialized = json.dumps(queue)
    for forbidden in context_index.FORBIDDEN_FIELDS:
        assert forbidden not in serialized
    assert queue["machine_signals_in_queue"] is False
    assert queue["max_page_size"] == 100


def test_review_queue_can_be_filtered_by_human_status(bundle: Path, tmp_path: Path) -> None:
    context = context_index.load_context(bundle)
    store = tmp_path / "human_review"
    review_store.append_event(
        document_id="doi:10.1000/fbdg", reviewer_id="ana", status="IN_REVIEW", root=store
    )
    states = review_store.document_states(root=store)

    in_review = review_control.review_queue(
        context=context, states=states, review_status_filter="IN_REVIEW"
    )
    assert [doc["document_id"] for doc in in_review["documents"]] == ["doi:10.1000/fbdg"]

    not_started = review_control.review_queue(
        context=context, states=states, review_status_filter="NOT_STARTED"
    )
    assert len(not_started["documents"]) == 3

    with pytest.raises(ValueError):
        review_control.review_queue(context=context, states=states, review_status_filter="INCLUDED")


def test_route_membership_is_not_a_review_decision(bundle: Path, tmp_path: Path) -> None:
    context = context_index.load_context(bundle)
    states = review_store.document_states(root=tmp_path / "human_review")
    queue = review_control.review_queue(context=context, states=states, route="B-NORM")

    # Being on a route never produces a human state on its own.
    assert {doc["review"]["status"] for doc in queue["documents"]} == {"NOT_STARTED"}
    assert "REVIEWED means read, not included" in review_control.GUARDRAIL


def test_full_text_retrieval_is_not_a_review_decision(bundle: Path, tmp_path: Path) -> None:
    context = context_index.load_context(bundle)
    states = review_store.document_states(root=tmp_path / "human_review")
    queue = review_control.review_queue(
        context=context, states=states, full_text_status="retrieved"
    )
    assert [doc["document_id"] for doc in queue["documents"]] == ["doi:10.1000/fbdg"]
    assert queue["documents"][0]["review"]["status"] == "NOT_STARTED"


def test_conflicts_expose_both_reviewer_positions(bundle: Path, tmp_path: Path) -> None:
    context = context_index.load_context(bundle)
    store = tmp_path / "human_review"
    review_store.append_event(
        document_id="doi:10.1000/fbdg", reviewer_id="ana", status="REVIEWED",
        decision="READ", reason_text="Lido na íntegra.", root=store,
    )
    review_store.append_event(
        document_id="doi:10.1000/fbdg", reviewer_id="bruno", status="REVIEWED",
        decision="NEEDS_FULL_TEXT", reason_text="Texto incompleto.", root=store,
    )
    rows = review_control.conflicts(
        context=context, states=review_store.document_states(root=store)
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Food-based dietary guideline for adults"
    assert {item["reviewer_id"] for item in rows[0]["reviewers"]} == {"ana", "bruno"}
    assert {item["reason_text"] for item in rows[0]["reviewers"]} == {
        "Lido na íntegra.", "Texto incompleto."
    }


# ---------------------------------------------------------------------------
# Web-tier contracts
# ---------------------------------------------------------------------------


def test_new_pages_are_reachable_from_navigation() -> None:
    for page in ("index.html", "articles.html", "review.html", "evidence-map.html"):
        html = read(page)
        assert 'href="/evidence-map.html"' in html
        assert 'href="/review.html"' in html


def test_evidence_map_page_is_a_table_with_a_count_only_legend() -> None:
    html = read("evidence-map.html")
    script = read("evidence-map.js")

    assert 'id="evidenceMatrix"' in html
    assert "<table" in html
    assert 'id="cellDrawer"' in html
    assert "map-mobile-list" in html
    assert "/api/evidence-map" in script
    assert "/api/evidence-map/cell" in script
    assert "Contagem de documentos. Não é qualidade nem força da evidência." in script
    assert "linkTo('/articles.html'" in script


def test_dashboard_charts_are_drill_down_navigation() -> None:
    script = read("dashboard.js")

    assert "linkTo('/articles.html'" in script
    assert "linkTo('/evidence-map.html'" in script
    assert "linkTo('/review.html'" in script
    assert "a class=\"bar-row drill\"" in script
    assert "a class=\"timeline-bar drill\"" in script


def test_filters_round_trip_through_the_url() -> None:
    workspace = read("workspace.js")
    for page in ("dashboard.js", "evidence-map.js", "review.js", "articles.js"):
        script = read(page)
        assert "readFilters" in script
        assert "writeFilters" in script
    assert "window.history.replaceState" in workspace
    assert "'route', 'domain', 'document_class', 'source_provider'," in workspace


def test_dossier_v2_separates_machine_signals_from_human_review() -> None:
    script = read("articles.js")

    for tab in ("overview", "methods", "evidence", "domains", "recommendations", "provenance", "review"):
        assert f"['{tab}'," in script or f"'{tab}'," in script
    assert "candidate evidence excerpt" in script
    assert "Machine signals (painel separado)" in script
    assert "Accepted NutEV recommendation" in script
    assert "Not extracted" in script
    assert "/api/review/document/" in script
    # The machine relevance band is never shown in the human review tab.
    review_tab = script.split("function humanReviewTab", 1)[1].split("function detailHtml", 1)[0]
    assert "machine_relevance" not in review_tab
    assert "reference_rank" not in review_tab


def test_review_write_path_is_loopback_only_and_operational() -> None:
    server = read("server.py")
    post_section = server.split("def do_POST", 1)[1]

    assert 'if path == "/api/review/event":' in post_section
    assert post_section.split('if path == "/api/review/event":', 1)[1].lstrip().startswith("#")
    assert "self._require_loopback()" in post_section.split('"/api/review/event"', 1)[1][:600]
    assert "review_store.append_event" in post_section


def test_frontend_cannot_move_the_formal_search_gate() -> None:
    server = read("server.py")
    assert '"frontend_can_change_formal_search_gate": False' in server
    assert '"frontend_can_emit_prisma_event": False' in server

    for page in ("dashboard.js", "evidence-map.js", "review.js", "articles.js", "workspace.js"):
        script = read(page)
        for forbidden in (
            "gf10_authorized: true",
            "gf10_authorized=true",
            "press_status: 'PASS'",
            "query_freeze_complete: true",
            "prisma_search_event_emitted: true",
            "article1_search_master",
        ):
            assert forbidden not in script

    # The only write the workspace performs is a human review event.
    for page in ("dashboard.js", "evidence-map.js", "articles.js"):
        assert "method: 'POST'" not in read(page)
    assert read("review.js").count("method: 'POST'") == 1


def test_press_status_is_not_pass_by_substring() -> None:
    """`NOT_YET_RECORDED_AS_PASS` is the live master value; it must never render as PASS."""
    script = read("dashboard.js")

    assert "pressIsPass" in script
    assert "includes('PASS')" not in script

    master = json.loads((ROOT / "config" / "nutev" / "article1_search_master_v1.json").read_text(encoding="utf-8"))
    recorded = str((master.get("formal_search") or {}).get("press_status") or "")
    assert "PASS" in recorded.upper()
    # The regex used by the dashboard, mirrored here so the contract is asserted, not assumed.
    import re
    pattern = re.compile(r"^(PRESS[ _-]?)?PASS$")
    assert pattern.match(recorded.strip().upper()) is None
    assert pattern.match("PASS") is not None
    assert pattern.match("PRESS_PASS") is not None


def test_presentation_mode_only_toggles_presentation_styling() -> None:
    script = read("dashboard.js")
    block = script.split("#presentationToggle'", 1)[1].split("window.addEventListener", 1)[0]

    assert "presentation-mode" in block
    assert "fetch(" not in block
    assert "POST" not in block


def test_workspace_scripts_have_no_production_count_literals() -> None:
    for page in ("dashboard.js", "evidence-map.js", "review.js", "articles.js", "workspace.js"):
        script = read(page)
        for forbidden in ("33067", "33839", "41139", "662", "504", "316", "85"):
            assert forbidden not in script, f"{page} hardcodes a production count"


def test_empty_and_unavailable_states_are_distinguishable() -> None:
    workspace = read("workspace.js")
    assert "não ausência de literatura" in read("evidence-map.js")
    assert "não ausência de literatura" in read("review.js")
    assert "Gap de provider não significa ausência de literatura." in read("dashboard.js")
    for kind in ("loading", "empty", "partial", "stale", "error"):
        assert f"{kind}:" in workspace
