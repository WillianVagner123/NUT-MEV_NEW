from __future__ import annotations

from nutev.global_watch.watch_query_builder import build_watch_queries
from nutev.global_watch.watch_scoring import score_watch_item


def test_food_literacy_queries_add_labeling_and_security_context() -> None:
    queries = build_watch_queries(
        ["food_literacy_culinary_commensality"],
        since_days=30,
        mode="quick",
    )

    first_query = str(queries[0]["query"])
    assert '"nutrition security"' in first_query
    assert '"nutrition label"' in first_query
    assert '"label reading"' in first_query
    assert '"front-of-pack"' in first_query
    assert '"front-of-pack labeling"' in first_query
    assert '"front-of-pack labelling"' in first_query
    assert '"choice architecture"' in first_query
    assert '"healthy food retail"' in first_query
    assert '"food procurement policy"' in first_query


def test_labeling_and_security_signals_improve_priority() -> None:
    enriched = score_watch_item(
        {
            "title": "Nutrition security and front-of-pack labeling to improve food literacy in obesity care",
        }
    )
    generic = score_watch_item({"title": "Food literacy in obesity care"})

    assert enriched > generic
