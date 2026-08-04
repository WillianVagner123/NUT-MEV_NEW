from __future__ import annotations

import nutev.search.crossref as crossref
import nutev.search.openalex as openalex


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_crossref_forwards_frozen_filter(monkeypatch):
    calls: list[dict] = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(dict(params or {}))
        return _Response({"message": {"items": []}})

    monkeypatch.delenv("NUTEV_CROSSREF_MAX_RESULTS", raising=False)
    monkeypatch.setattr(crossref.requests, "get", fake_get)

    crossref.search_crossref(
        "food literacy",
        rows=10,
        filter_value="from-pub-date:2015-01-01,until-pub-date:2026-12-31",
    )
    assert calls[0]["query"] == "food literacy"
    assert calls[0]["filter"] == (
        "from-pub-date:2015-01-01,until-pub-date:2026-12-31"
    )
    assert "offset" not in calls[0]


def test_openalex_forwards_frozen_filter(monkeypatch):
    calls: list[dict] = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(dict(params or {}))
        return _Response({"results": [], "meta": {"next_cursor": None}})

    monkeypatch.delenv("NUTEV_OPENALEX_MAX_RESULTS", raising=False)
    monkeypatch.setattr(openalex.requests, "get", fake_get)

    openalex.search_openalex(
        "food competence",
        per_page=10,
        filter_value="from_publication_date:2015-01-01,language:eng",
    )
    assert calls[0]["search"] == "food competence"
    assert calls[0]["filter"] == (
        "from_publication_date:2015-01-01,language:eng"
    )
    assert "cursor" not in calls[0]
