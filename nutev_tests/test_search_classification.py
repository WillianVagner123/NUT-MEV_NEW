from nutev.search.classification import classify_search_record


def test_search_classification_uses_provider_article_type_as_high_confidence_signal() -> None:
    result = classify_search_record(
        {
            "article_type": "Randomized Controlled Trial",
            "title": "Creatine supplementation and cognition in older adults",
            "abstract": "A placebo-controlled intervention.",
        },
        query="creatine cognition older adults",
    )
    assert result["document_class"] == "primary_randomized"
    assert result["confidence"] == "high"
    assert result["classification_basis"] == "provider_article_type"
    assert {"creatine", "cognition", "older", "adults"}.issubset(
        set(result["query_match"]["title_hits"])
    )


def test_search_classification_detects_synthesis_from_title_without_upgrading_quality() -> None:
    result = classify_search_record(
        {
            "title": "Mediterranean diet and cardiovascular mortality: a systematic review and meta-analysis",
            "taxonomy_primary": "domain.dietary_patterns.mediterranean",
            "matched_terms": ["mediterranean diet", "dietary pattern"],
        },
        query="mediterranean diet cardiovascular mortality",
    )
    assert result["document_class"] == "evidence_synthesis"
    assert result["confidence"] == "medium"
    assert result["taxonomy_primary"] == "domain.dietary_patterns.mediterranean"
    assert "risk of bias" in result["guardrail"]
    assert "certainty" in result["guardrail"]


def test_search_classification_stays_unclassified_when_signal_is_insufficient() -> None:
    result = classify_search_record(
        {"title": "Nutrition and health in adults", "abstract": "General background."},
        query="nutrition adults",
    )
    assert result["document_class"] == "unclassified"
    assert result["confidence"] == "low"
    assert result["classification_basis"] == "insufficient_signal"


def test_query_overlap_uses_token_boundaries_instead_of_substrings() -> None:
    result = classify_search_record(
        {
            "title": "Women and dietary strategy in nutrition care",
            "abstract": "A population-level overview for nutrition practice.",
        },
        query="men rat nutrition",
    )
    assert "nutrition" in result["query_match"]["title_hits"]
    assert "men" not in result["query_match"]["title_hits"]
    assert "rat" not in result["query_match"]["title_hits"]
    assert "men" not in result["query_match"]["abstract_hits"]
    assert "rat" not in result["query_match"]["abstract_hits"]
