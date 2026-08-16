from __future__ import annotations

import importlib.util
from pathlib import Path


def _tool_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "run_everything_now.py"
    spec = importlib.util.spec_from_file_location("nutev_run_everything_now", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_queries_keep_pubmed_exact_but_make_non_pubmed_translation_plain() -> None:
    tool = _tool_module()
    queries = tool._queries()

    assert queries["candidate"] == "v0.5"
    assert "[tiab]" in queries["pubmed"]
    assert "[pt]" in queries["pubmed"]
    assert "[tiab]" not in queries["generic"]
    assert "[Mesh]" not in queries["generic"]
    assert "guideline" in queries["generic"].lower()
    assert "nutrition" in queries["generic"].lower()
    assert "*" not in queries["web"]


def test_cross_source_dedupe_prefers_strong_identifiers() -> None:
    tool = _tool_module()
    rows = [
        {"title": "A", "doi": "10.1000/XYZ", "url": "https://example.org/a"},
        {"title": "Different title", "doi": "https://doi.org/10.1000/xyz"},
        {"title": "B", "pmid": "12345"},
        {"title": "B duplicate", "pmid": "12345"},
        {"title": "C", "url": "https://example.org/c"},
        {"title": "C other", "url": "https://example.org/c"},
    ]

    out = tool._dedupe(rows)

    assert len(out) == 3


def test_pubmed_partition_query_is_deterministic() -> None:
    tool = _tool_module()
    from datetime import date

    value = tool._date_query("diet AND guideline", date(2020, 1, 1), date(2020, 12, 31))

    assert value == '(diet AND guideline) AND ("2020/01/01"[dp] : "2020/12/31"[dp])'


def test_collection_type_is_explicitly_nonformal() -> None:
    tool = _tool_module()

    assert tool.COLLECTION_TYPE == "REAL_DISCOVERY_NONFORMAL"
