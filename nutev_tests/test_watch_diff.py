from nutev.global_watch.watch_diff import mark_new_items, update_seen_items


def test_mark_new_items():
    rows = mark_new_items([{"document_id":"doc1"}], {})
    assert rows[0]["is_new"] is True


def test_update_seen_items_preserves_audit_fields():
    rows = [
        {
            "document_id": "doc1",
            "title": "Dietary adherence guideline",
            "matched_categories": "implementation_behavior|guidelines_consensus",
            "matched_providers": "pubmed|openalex",
            "workstream_affinity": ["policy_systems", "implementation"],
            "evidence_type": "guideline",
            "relevance_score": 50,
            "watch_score": 91.5,
            "download_status": "metadata_only",
        }
    ]

    seen = update_seen_items(rows, {})

    assert seen["doc1"]["matched_categories"] == "implementation_behavior|guidelines_consensus"
    assert seen["doc1"]["matched_providers"] == "pubmed|openalex"
    assert seen["doc1"]["workstream_affinity"] == ["policy_systems", "implementation"]
    assert seen["doc1"]["evidence_type"] == "guideline"
    assert seen["doc1"]["watch_score"] == 91.5
