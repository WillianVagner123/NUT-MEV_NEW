from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "apps" / "nutev-web" / "pubmed_search_details.py"
SPEC = importlib.util.spec_from_file_location("nutev_pubmed_search_details", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_parse_preserves_translation_warnings_errors_and_count() -> None:
    parsed = module.parse_pubmed_search_details(
        {
            "esearchresult": {
                "count": "1526",
                "querytranslation": '"Diet"[MeSH Terms] AND framework*[Title/Abstract]',
                "warninglist": {
                    "quotedphrasesnotfound": ["nutrition care framework*"],
                    "outputmessages": ["No items found."],
                },
                "errorlist": {"fieldsnotfound": ["BogusField"]},
            }
        }
    )
    assert parsed["count"] == 1526
    assert '"Diet"[MeSH Terms]' in parsed["query_translation"]
    assert parsed["warnings_present"] is True
    assert parsed["errors_present"] is True
    assert parsed["warninglist"]["quotedphrasesnotfound"] == ["nutrition care framework*"]
    assert parsed["errorlist"]["fieldsnotfound"] == ["BogusField"]


def test_zero_result_query_can_still_have_complete_search_details() -> None:
    parsed = module.parse_pubmed_search_details(
        {"esearchresult": {"count": "0", "querytranslation": ""}}
    )
    assert parsed["count"] == 0
    assert parsed["search_details_complete"] is True
    assert parsed["warnings_present"] is False


def test_invalid_payload_fails_closed() -> None:
    with pytest.raises(ValueError, match="esearchresult"):
        module.parse_pubmed_search_details({"x": 1})
