from __future__ import annotations

from typing import Any

from nutev.science.full_text_probe import select_reachable_candidate


class _FakeResponse:
    def __init__(self, status_code: int, *, content_type: str = "", location: str = "") -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        if content_type:
            self.headers["content-type"] = content_type
        if location:
            self.headers["location"] = location
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _requester(responses: dict[str, _FakeResponse]):
    def get(url: str, **_: Any) -> _FakeResponse:
        if url not in responses:
            raise AssertionError(f"unexpected probe URL: {url}")
        return responses[url]

    return get


def test_probe_falls_back_from_failed_xml_to_public_pdf() -> None:
    xml = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML"
    pdf = "https://europepmc.org/articles/PMC123?pdf=render"
    candidates = [
        {
            "url": xml,
            "scope": "full_text",
            "resolver_route": "europe_pmc_fulltext_xml",
            "resolver_source": "europe_pmc",
            "media_type": "application/xml",
        },
        {
            "url": pdf,
            "scope": "full_text",
            "resolver_route": "europe_pmc_open_full_text_link",
            "resolver_source": "europe_pmc",
            "media_type": "application/pdf",
        },
    ]
    selected, attempts = select_reachable_candidate(
        candidates,
        allow_network=True,
        requester=_requester(
            {
                xml: _FakeResponse(404, content_type="application/xml"),
                pdf: _FakeResponse(200, content_type="application/pdf"),
            }
        ),
    )

    assert selected is not None
    assert selected["url"] == pdf
    assert selected["resolver_route"] == "europe_pmc_open_full_text_link"
    assert selected["probe_selected"] is True
    assert selected["probe_selected_attempt"] == 2
    assert [attempt["http_status"] for attempt in attempts] == [404, 200]
    assert attempts[0]["reachable"] is False
    assert attempts[1]["reachable"] is True


def test_probe_upgrades_http_candidate_to_https_after_failure() -> None:
    http_url = "http://www.scielo.br/pdf/csp/v35n12/article.pdf"
    https_url = "https://www.scielo.br/pdf/csp/v35n12/article.pdf"
    candidate = {
        "url": http_url,
        "scope": "partial",
        "resolver_route": "recorded_url",
        "resolver_source": "recorded_metadata",
    }

    selected, attempts = select_reachable_candidate(
        [candidate],
        allow_network=True,
        requester=_requester(
            {
                http_url: _FakeResponse(403, content_type="text/html"),
                https_url: _FakeResponse(200, content_type="application/pdf"),
            }
        ),
    )

    assert selected is not None
    assert selected["url"] == https_url
    assert selected["probe_variant"] == "https_upgrade"
    assert selected["probe_selected_attempt"] == 2
    assert attempts[1]["probe_variant"] == "https_upgrade"


def test_probe_rejects_content_type_mismatch_then_uses_next_candidate() -> None:
    fake_pdf = "https://example.org/article.pdf"
    html = "https://example.org/article"
    candidates = [
        {
            "url": fake_pdf,
            "scope": "full_text",
            "resolver_route": "recorded_pdf_url",
            "media_type": "application/pdf",
        },
        {
            "url": html,
            "scope": "full_text",
            "resolver_route": "recorded_full_text_url",
            "media_type": "text/html",
        },
    ]
    selected, attempts = select_reachable_candidate(
        candidates,
        allow_network=True,
        requester=_requester(
            {
                fake_pdf: _FakeResponse(200, content_type="text/html"),
                html: _FakeResponse(200, content_type="text/html"),
            }
        ),
    )

    assert selected is not None
    assert selected["url"] == html
    assert attempts[0]["reason"] == "content_type_mismatch"
    assert attempts[1]["reachable"] is True


def test_probe_offline_preserves_first_candidate_without_network_attempts() -> None:
    candidates = [
        {"url": "https://example.org/a", "resolver_route": "a", "scope": "full_text"},
        {"url": "https://example.org/b", "resolver_route": "b", "scope": "full_text"},
    ]
    selected, attempts = select_reachable_candidate(candidates, allow_network=False)
    assert selected == candidates[0]
    assert attempts == []
