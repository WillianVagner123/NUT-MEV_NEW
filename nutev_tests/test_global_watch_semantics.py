from __future__ import annotations

from nutev.global_watch.watch_pipeline import infer_workstream_affinity
from nutev.global_watch.watch_query_builder import build_watch_queries
from nutev.global_watch.watch_scoring import score_watch_item


def test_quick_watch_queries_expand_implementation_semantics() -> None:
    queries = build_watch_queries(["implementation_behavior"], since_days=7, mode="quick")
    rendered = " ".join(str(item["query"]) for item in queries).lower()

    assert "barriers and facilitators" in rendered
    assert "registered dietitian" in rendered
    assert "dietitian-led intervention" in rendered
    assert "self-management" in rendered
    assert "shared decision making" in rendered
    assert "weight loss maintenance" in rendered


def test_watch_score_prioritizes_self_management_implementation_signals() -> None:
    baseline = score_watch_item(
        {
            "title": "Lifestyle intervention for obesity",
            "abstract": "",
            "snippet": "",
            "evidence_type": "study",
            "category": "implementation_behavior",
            "relevance_score": 50,
            "source_provider": "pubmed",
            "download_status": "metadata_only",
        }
    )
    enriched = score_watch_item(
        {
            "title": (
                "Dietitian-led lifestyle intervention with self-management support "
                "and shared decision making for obesity"
            ),
            "abstract": "Treatment adherence improved during weight loss maintenance.",
            "snippet": "",
            "evidence_type": "study",
            "category": "implementation_behavior",
            "relevance_score": 50,
            "source_provider": "pubmed",
            "download_status": "metadata_only",
        }
    )

    assert enriched > baseline


def test_infer_workstream_affinity_routes_self_management_titles_to_implementation() -> None:
    affinity = infer_workstream_affinity(
        (
            "Dietitian-led obesity care uses self-management support and shared "
            "decision making to improve weight loss maintenance"
        ),
        "implementation_behavior",
    )

    assert "implementation" in affinity
    assert "busca2b" not in affinity
