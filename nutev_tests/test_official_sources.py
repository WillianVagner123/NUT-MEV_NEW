from __future__ import annotations

from nutev.search.official_sources import manifest_sources


def test_manifest_sources_accepts_legacy_aliases_but_emits_semantic_labels() -> None:
    manifest = {
        "workstreams": {
            "artigo3_framework": [
                {
                    "name": "Brazilian Dietary Guidelines",
                    "url": "https://www.example.org/guidelines/",
                }
            ],
            "a3": [
                {
                    "name": "Brazilian Dietary Guidelines duplicate",
                    "url": "https://example.org/guidelines",
                },
                {
                    "name": "Food literacy framework",
                    "url": "https://example.org/food-literacy",
                },
            ],
        }
    }

    rows = manifest_sources(manifest, "a3")

    assert [row["url"] for row in rows] == [
        "https://www.example.org/guidelines/",
        "https://example.org/food-literacy",
    ]
    assert {row["analytical_label"] for row in rows} == {"framework"}
    assert {row["query"] for row in rows} == {"framework"}
    assert {row["provider_query"] for row in rows} == {"framework"}
