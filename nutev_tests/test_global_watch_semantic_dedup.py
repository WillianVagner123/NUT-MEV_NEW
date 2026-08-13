from __future__ import annotations

from nutev.global_watch.watch_pipeline import _dedup_watch_rows, normalize_watch_hit


def test_dedup_canonicalizes_legacy_affinity_aliases() -> None:
    rows = [
        {
            "document_id": "doc_same",
            "title": "Lifestyle nutrition guidance",
            "source_provider": "crossref",
            "category": "guidelines_consensus",
            "workstream_affinity": ["busca1"],
            "download_status": "metadata_only",
            "relevance_score": 50,
        },
        {
            "document_id": "doc_same",
            "title": "Lifestyle nutrition guidance",
            "abstract": "Implementation fidelity and food literacy support for obesity care.",
            "source_provider": "pubmed",
            "category": "implementation_behavior",
            "workstream_affinity": ["busca2b", "a3"],
            "download_status": "metadata_only",
            "relevance_score": 50,
        },
    ]

    merged = _dedup_watch_rows(rows)

    assert len(merged) == 1
    assert merged[0]["workstream_affinity"] == [
        "policy_systems",
        "implementation",
        "framework",
    ]


def test_dedup_keeps_stronger_download_status_with_semantic_affinity() -> None:
    rows = [
        {
            "document_id": "doc_capture",
            "title": "Nutrition trial",
            "url": "https://example.org/landing",
            "source_provider": "openalex",
            "category": "implementation_behavior",
            "workstream_affinity": ["busca2b"],
            "download_status": "metadata_only",
            "relevance_score": 50,
            "is_recent_publication": False,
        },
        {
            "document_id": "doc_capture",
            "title": "Nutrition trial",
            "url": "https://example.org/fulltext.pdf",
            "source_provider": "crossref",
            "category": "implementation_behavior",
            "workstream_affinity": ["implementation"],
            "download_status": "pdf",
            "relevance_score": 50,
            "is_recent_publication": True,
        },
    ]

    merged = _dedup_watch_rows(rows)

    assert merged[0]["download_status"] == "pdf"
    assert merged[0]["url"] == "https://example.org/fulltext.pdf"
    assert merged[0]["is_recent_publication"] is True
    assert merged[0]["workstream_affinity"] == ["implementation"]


def test_normalize_watch_hit_emits_only_semantic_affinity_labels() -> None:
    item = normalize_watch_hit(
        {
            "title": "Nutrition update for obesity care",
            "abstract": "Implementation fidelity and food literacy support.",
            "summary": "Teaching kitchens and dietary adherence.",
            "url": "https://example.org/article",
            "year": 2025,
        },
        "pubmed",
        "implementation_behavior",
        "nutrition update",
    )

    assert "policy_systems" in item["workstream_affinity"]
    assert "clinical_outcomes" in item["workstream_affinity"]
    assert "implementation" in item["workstream_affinity"]
    assert "framework" in item["workstream_affinity"]
    assert not {"busca1", "busca2a", "busca2b", "a3"}.intersection(
        item["workstream_affinity"]
    )
