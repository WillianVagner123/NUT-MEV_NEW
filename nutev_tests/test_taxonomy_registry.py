from __future__ import annotations

import json
from pathlib import Path

import pytest

from nutev.taxonomy import TaxonomyError, load_canonical_taxonomy


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def test_compatibility_mode_excludes_workstreams_and_document_types(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _write_json(
        config / "keyword_taxonomy.json",
        {
            "global": {
                "diet_patterns": {"core": ["dietary pattern"]},
                "document_types": {"guidelines": ["guideline"]},
            },
            "workstreams": {
                "busca1": {
                    "focus_terms": ["legacy focus"],
                    "web_query_hints": ["legacy query"],
                }
            },
        },
    )

    groups, metadata = load_canonical_taxonomy(config)

    assert metadata["registry_mode"] == "compatibility"
    assert groups == {"global.diet_patterns.core": ["dietary pattern"]}
    assert not any(group.startswith("workstreams.") for group in groups)
    assert not any(group.startswith("global.document_types.") for group in groups)


def test_registry_merges_multiple_raw_paths_into_one_canonical_group(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _write_json(
        config / "keyword_taxonomy.json",
        {
            "global": {
                "implementation_behavior": {
                    "personalized_adherence": ["precision nutrition", "shared decision making"],
                    "personalized_nutrition_adherence": [
                        "precision nutrition",
                        "tailored dietary advice",
                    ],
                }
            }
        },
    )
    _write_json(
        config / "taxonomy_registry.json",
        {
            "schema_version": 1,
            "taxonomy_version": "test-v1",
            "allowed_roots": ["global", "clinical", "outcomes"],
            "excluded_paths": ["global.document_types"],
            "primary_dimension_order": ["domain", "context", "condition", "outcome"],
            "groups": {
                "context.care_delivery.personalized_nutrition": {
                    "source_paths": [
                        "global.implementation_behavior.personalized_adherence",
                        "global.implementation_behavior.personalized_nutrition_adherence",
                    ]
                }
            },
        },
    )

    groups, metadata = load_canonical_taxonomy(config)

    assert metadata["registry_mode"] == "canonical"
    assert metadata["raw_groups_mapped"] == 2
    assert groups["context.care_delivery.personalized_nutrition"] == [
        "shared decision making",
        "tailored dietary advice",
        "precision nutrition",
    ]


def test_registry_fails_closed_for_unmapped_semantic_path(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _write_json(
        config / "keyword_taxonomy.json",
        {"global": {"new_domain": {"unexpected": ["new term"]}}},
    )
    _write_json(
        config / "taxonomy_registry.json",
        {
            "schema_version": 1,
            "taxonomy_version": "test-v1",
            "allowed_roots": ["global", "clinical", "outcomes"],
            "excluded_paths": ["global.document_types"],
            "groups": {
                "domain.example": {
                    "source_paths": ["global.expected.core"]
                }
            },
        },
    )

    with pytest.raises(TaxonomyError, match="Unmapped semantic taxonomy paths"):
        load_canonical_taxonomy(config)


def test_repository_taxonomy_is_fully_registered_and_neutral() -> None:
    config = Path(__file__).resolve().parents[1] / "config"

    groups, metadata = load_canonical_taxonomy(config)

    assert metadata["registry_mode"] == "canonical"
    assert metadata["taxonomy_version"] == "2026-08-v2"
    assert metadata["raw_groups_mapped"] > 0
    assert metadata["raw_groups_excluded"] > 0
    assert groups
    assert all(
        group.split(".", 1)[0] in {"domain", "context", "condition", "outcome"}
        for group in groups
    )
    assert not any("workstreams" in group for group in groups)
    assert not any("busca" in group for group in groups)
    assert not any("artigo" in group for group in groups)
    assert not any("document_types" in group for group in groups)
