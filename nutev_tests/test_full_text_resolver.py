from __future__ import annotations

from typing import Any

from nutev.science.full_text_resolver import (
    EUROPE_PMC_SEARCH,
    OPENALEX_WORKS,
    resolve_full_text_candidates,
)


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_europe_pmc_open_full_text_is_prioritized_and_provenanced() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def requester(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url == EUROPE_PMC_SEARCH:
            return FakeResponse(
                {
                    "resultList": {
                        "result": [
                            {
                                "pmid": "12345",
                                "doi": "10.1000/example",
                                "pmcid": "PMC777",
                                "isOpenAccess": "Y",
                                "fullTextUrlList": {
                                    "fullTextUrl": [
                                        {
                                            "availability": "Open access",
                                            "availabilityCode": "OA",
                                            "documentStyle": "pdf",
                                            "url": "https://example.org/article.pdf",
                                        },
                                        {
                                            "availability": "Open access",
                                            "availabilityCode": "OA",
                                            "documentStyle": "html",
                                            "url": "https://example.org/article",
                                        },
                                    ]
                                },
                            }
                        ]
                    }
                }
            )
        if url == OPENALEX_WORKS:
            return FakeResponse({"results": []})
        raise AssertionError(f"unexpected URL: {url}")

    candidates = resolve_full_text_candidates(
        {"doi": "10.1000/example", "pmid": "12345"},
        requester=requester,
    )

    assert candidates[0]["resolver_route"] == "europe_pmc_fulltext_xml"
    assert candidates[0]["scope"] == "full_text"
    assert candidates[0]["media_type"] == "application/xml"
    assert candidates[0]["url"].endswith("/PMC777/fullTextXML")
    assert any(
        item["url"] == "https://example.org/article.pdf"
        and item["media_type"] == "application/pdf"
        for item in candidates
    )
    assert candidates[-2]["resolver_route"] == "doi_landing_fallback"
    assert candidates[-1]["resolver_route"] == "pubmed_landing_fallback"
    assert calls[0][1]["params"]["resultType"] == "core"


def test_openalex_oa_pdf_is_used_when_europe_pmc_has_no_match() -> None:
    def requester(url: str, **kwargs: Any) -> FakeResponse:
        del kwargs
        if url == EUROPE_PMC_SEARCH:
            return FakeResponse({"resultList": {"result": []}})
        if url == OPENALEX_WORKS:
            return FakeResponse(
                {
                    "results": [
                        {
                            "best_oa_location": {
                                "is_oa": True,
                                "pdf_url": "https://repository.example/article.pdf",
                                "landing_page_url": "https://repository.example/article",
                                "license": "cc-by",
                                "version": "publishedVersion",
                                "source": {"type": "repository"},
                            },
                            "locations": [],
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected URL: {url}")

    candidates = resolve_full_text_candidates(
        {"doi": "10.2000/open"},
        requester=requester,
    )

    assert candidates[0]["url"] == "https://repository.example/article.pdf"
    assert candidates[0]["resolver_source"] == "openalex"
    assert candidates[0]["scope"] == "full_text"
    assert candidates[0]["media_type"] == "application/pdf"
    assert candidates[0]["license"] == "cc-by"
    assert candidates[-1]["resolver_route"] == "doi_landing_fallback"


def test_recorded_pdf_stays_first_without_network_resolution() -> None:
    def requester(*args: Any, **kwargs: Any) -> FakeResponse:
        raise AssertionError(f"network requester must not be called: {args} {kwargs}")

    candidates = resolve_full_text_candidates(
        {
            "doi": "10.3000/recorded",
            "pdf_url": "https://publisher.example/open.pdf",
            "url": "https://publisher.example/article",
        },
        requester=requester,
        include_network_resolvers=False,
    )

    assert candidates[0]["resolver_route"] == "recorded_pdf_url"
    assert candidates[0]["scope"] == "full_text"
    assert candidates[0]["media_type"] == "application/pdf"
    assert candidates[-1]["resolver_route"] == "doi_landing_fallback"


def test_non_oa_openalex_location_is_not_promoted_to_full_text() -> None:
    def requester(url: str, **kwargs: Any) -> FakeResponse:
        del kwargs
        if url == EUROPE_PMC_SEARCH:
            return FakeResponse({"resultList": {"result": []}})
        if url == OPENALEX_WORKS:
            return FakeResponse(
                {
                    "results": [
                        {
                            "best_oa_location": {
                                "is_oa": False,
                                "pdf_url": "https://paywall.example/article.pdf",
                                "landing_page_url": "https://paywall.example/article",
                                "source": {"type": "journal"},
                            },
                            "locations": [],
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected URL: {url}")

    candidates = resolve_full_text_candidates(
        {"doi": "10.4000/closed"},
        requester=requester,
    )

    assert not any("paywall.example" in item["url"] for item in candidates)
    assert [item["resolver_route"] for item in candidates] == [
        "doi_landing_fallback"
    ]
