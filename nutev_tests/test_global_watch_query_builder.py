from nutev.global_watch.watch_query_builder import build_watch_queries
from nutev.global_watch.watch_scoring import score_watch_item


def test_build_watch_queries_generates_queries():
    rows = build_watch_queries(["guidelines_consensus"], 7, "quick")
    assert rows and "query_id" in rows[0]


def test_food_literacy_queries_include_nutrition_literacy_in_quick_mode():
    rows = build_watch_queries(["food_literacy_culinary_commensality"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "nutrition literacy" in rendered
    assert "nutrition security" in rendered


def test_food_literacy_queries_include_teaching_kitchen_terms_in_quick_mode():
    rows = build_watch_queries(["food_literacy_culinary_commensality"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "teaching kitchen" in rendered
    assert "culinary nutrition" in rendered


def test_quick_queries_include_scoped_social_prescribing_nutrition_terms():
    rows = build_watch_queries(["implementation_behavior"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "nutrition social prescribing" in rendered
    assert "social prescribing nutrition security" in rendered
    assert "link worker nutrition referral" in rendered
    assert "community resource referral food" in rendered


def test_social_prescribing_nutrition_terms_score_above_generic_referral_language():
    scoped = score_watch_item(
        {
            "title": "Nutrition social prescribing link worker referral for food insecurity",
            "source_provider": "pubmed",
        }
    )
    generic = score_watch_item(
        {
            "title": "Social prescribing link worker referral for loneliness",
            "source_provider": "pubmed",
        }
    )

    assert scoped > generic
    assert scoped - generic >= 45


def test_framework_instrument_queries_include_food_competence_and_commensality_scales():
    rows = build_watch_queries(["frameworks_instruments"], 7, "exhaustive")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "food literacy questionnaire" in rendered
    assert "nutrition literacy instrument" in rendered
    assert "food competence scale" in rendered
    assert "commensality scale" in rendered


def test_obesity_cardiometabolic_queries_include_new_liver_and_lipid_context_terms():
    rows = build_watch_queries(["obesity_cardiometabolic"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "steatotic liver disease" in rendered
    assert "metabolic dysfunction-associated steatotic liver disease" in rendered
    assert "dyslipidaemia" in rendered
    assert "insulin resistance" in rendered
    assert "adiposity-based chronic disease" in rendered
    assert "adiposity based chronic disease" in rendered


def test_obesity_cardiometabolic_queries_include_extended_liver_synonyms():
    rows = build_watch_queries(["obesity_cardiometabolic"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "metabolic dysfunction associated steatotic liver disease" in rendered
    assert "metabolic dysfunction-associated fatty liver disease" in rendered
    assert "nonalcoholic fatty liver disease" in rendered
    assert "non-alcoholic steatohepatitis" in rendered


def test_diet_pattern_queries_include_evidence_synthesis_terms_in_quick_mode():
    rows = build_watch_queries(["diet_patterns"], 7, "quick")
    rendered = " ".join(str(row["query"]) for row in rows).lower()
    assert "network meta-analysis" in rendered
    assert "rapid review" in rendered
    assert "living systematic review" in rendered


def test_guidelines_thesis_mode_surfaces_broader_guidance_families_early():
    rows = build_watch_queries(["guidelines_consensus"], 7, "thesis")
    rendered = [str(row["query"]).lower() for row in rows]

    assert len(rendered) == 6
    assert '("guideline")' in rendered[0]
    assert '("clinical practice guideline")' in rendered[1]
    assert '("consensus statement")' in rendered[2]
    assert '("scientific statement")' in rendered[3]
    assert '("position paper")' in rendered[4]
    assert '("guidance statement")' in rendered[5]


def test_guidelines_exhaustive_mode_includes_clinical_practice_update_terms():
    rows = build_watch_queries(["guidelines_consensus"], 7, "exhaustive")
    rendered = " ".join(str(row["query"]) for row in rows).lower()

    assert "clinical practice update" in rendered
    assert "clinical practice recommendation" in rendered
    assert "clinical practice recommendations" in rendered
