from __future__ import annotations

from pathlib import Path

import pytest
import requests

from nutev.search import regional_status
from nutev.search.regional_status import LilacsBVSStatusClient, SciELOStatusClient


class _Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_regional_clients_skip_when_network_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NUTEV_DISABLE_NETWORK", "1")
    for client in (LilacsBVSStatusClient(), SciELOStatusClient()):
        result = client.search("nutrition", limit=5)
        assert result.status == "skipped"
        assert result.total_found is None
        assert result.error == "network_disabled"


def test_lilacs_access_denied_is_failed_not_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(
        regional_status.requests,
        "get",
        lambda *args, **kwargs: _Response(403, "forbidden"),
    )
    result = LilacsBVSStatusClient().search("nutrition", limit=5)
    assert result.status == "failed"
    assert result.total_found is None
    assert "HTTP 403" in str(result.error)
    assert result.meta["availability"] == "unavailable_for_automated_request"


def test_regional_explicit_no_results_marker_is_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(
        regional_status.requests,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            "<html><body><p>Nenhum resultado encontrado</p></body></html>",
        ),
    )
    result = LilacsBVSStatusClient().search("impossible query", limit=5)
    assert result.status == "empty"
    assert result.total_found == 0
    assert result.error is None
    assert result.meta["explicit_zero_marker"] is True


def test_regional_ambiguous_html_without_candidates_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    monkeypatch.setattr(
        regional_status.requests,
        "get",
        lambda *args, **kwargs: _Response(
            200,
            "<html><body><a href='/about'>About this portal</a></body></html>",
        ),
    )
    result = SciELOStatusClient().search("nutrition", limit=5)
    assert result.status == "failed"
    assert result.total_found is None
    assert result.error == "native_html_no_candidates_unverified_zero"
    assert result.meta["explicit_zero_marker"] is False


def test_lilacs_candidate_is_traceable_and_raw_html_is_hashed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    html = (
        "<html><body>"
        "<a href='/portal/resource/pt/biblio-12345'>"
        "Nutrition counseling competencies in clinical practice"
        "</a>"
        "</body></html>"
    )
    monkeypatch.setattr(
        regional_status.requests,
        "get",
        lambda *args, **kwargs: _Response(200, html),
    )
    result = LilacsBVSStatusClient().search(
        "nutrition counseling",
        limit=5,
        context={"checkpoint_dir": tmp_path},
    )
    assert result.status == "completed"
    assert result.total_returned == 1
    assert result.total_found is None
    assert result.rows[0]["source_provider"] == "lilacs_bvs_native"
    assert "bvsalud.org" in result.rows[0]["url"]
    raw_path = Path(str(result.meta["raw_html_path"]))
    assert raw_path.is_file()
    assert len(str(result.meta["raw_html_sha256"])) == 64


def test_scielo_candidate_is_traceable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTEV_DISABLE_NETWORK", raising=False)
    html = (
        "<html><body>"
        "<a href='https://www.scielo.br/j/rn/a/abcdef/article'>"
        "Food literacy and nutrition practice in primary care"
        "</a>"
        "</body></html>"
    )
    monkeypatch.setattr(
        regional_status.requests,
        "get",
        lambda *args, **kwargs: _Response(200, html),
    )
    result = SciELOStatusClient().search("food literacy", limit=5)
    assert result.status == "completed"
    assert result.total_returned == 1
    assert result.rows[0]["source_provider"] == "scielo_native"
    assert "scielo.br" in result.rows[0]["url"]
