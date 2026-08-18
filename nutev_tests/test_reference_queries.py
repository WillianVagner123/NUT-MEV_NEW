from __future__ import annotations

import json
from pathlib import Path

from nutev.search.reference_queries import load_reference_search, provider_limit, reference_queries


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "reference_search.json"


def test_reference_search_config_is_canonical() -> None:
    data = load_reference_search(CONFIG)
    assert data["mode"] == "REFERENCE_COLLECTION"
    queries = reference_queries(CONFIG)
    assert set(queries) == {"pubmed", "generic", "web"}
    assert all(value.strip() for value in queries.values())
    assert provider_limit(CONFIG, "pubmed", 1) >= 1


def test_reference_mode_and_taxonomies_are_present() -> None:
    mode = json.loads((REPO_ROOT / "config" / "reference_mode.json").read_text(encoding="utf-8"))
    assert mode["mode"] == "REFERENCE_RANKING"
    taxonomy_files = sorted((REPO_ROOT / "config").glob("keyword_taxonomy*.json"))
    assert taxonomy_files
    assert all(path.stat().st_size > 0 for path in taxonomy_files)
