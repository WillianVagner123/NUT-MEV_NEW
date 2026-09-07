from pathlib import Path

from nutev.search.classification import classify_search_record
from nutev.search.document_classes import (
    CANONICAL_DOCUMENT_CLASS_MEMBERS,
    DOCUMENT_CLASS_ONTOLOGY_VERSION,
    canonical_document_class,
    document_classes_for_canonical,
)


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"


def test_canonical_ontology_groups_scientific_workbench_subtypes_without_erasing_them() -> None:
    assert DOCUMENT_CLASS_ONTOLOGY_VERSION == "nutev-document-class-v1"
    assert canonical_document_class("food_based_dietary_guideline") == "guidance"
    assert canonical_document_class("clinical_practice_guideline") == "guidance"
    assert canonical_document_class("consensus_statement") == "guidance"
    assert canonical_document_class("position_statement") == "guidance"
    assert canonical_document_class("framework_model") == "framework_implementation"
    assert canonical_document_class("competency_curriculum") == "framework_implementation"
    assert canonical_document_class("implementation_evaluation") == "framework_implementation"
    assert document_classes_for_canonical("guidance") == CANONICAL_DOCUMENT_CLASS_MEMBERS["guidance"]
    assert document_classes_for_canonical("framework_implementation") == CANONICAL_DOCUMENT_CLASS_MEMBERS["framework_implementation"]


def test_search_classifier_can_emit_framework_implementation_as_a_canonical_class() -> None:
    result = classify_search_record(
        {
            "title": "A competency framework for nutrition care implementation",
            "abstract": "Development and implementation evaluation of the framework.",
        },
        query="nutrition care competency framework",
    )
    assert result["document_class"] == "framework_implementation"
    assert result["confidence"] == "medium"
    assert result["classification_basis"] == "title_abstract_text_signals"


def test_search_library_and_dossier_share_the_same_web_ontology_module() -> None:
    ontology = (WEB / "document-classes.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    facets = (WEB / "search-facets-ui.js").read_text(encoding="utf-8")
    articles = (WEB / "articles.js").read_text(encoding="utf-8")
    saved = (WEB / "saved-library-ui.js").read_text(encoding="utf-8")

    assert "nutev-document-class-v1" in ontology
    for canonical in CANONICAL_DOCUMENT_CLASS_MEMBERS:
        assert f"{canonical}:" in ontology
    assert "from'./document-classes.js'" in app
    assert "from'./document-classes.js'" in facets
    assert "from'./document-classes.js'" in articles
    assert "from'./document-classes.js'" in saved


def test_biblioteca_filter_uses_only_canonical_classes_and_backend_expands_groups() -> None:
    html = (WEB / "articles.html").read_text(encoding="utf-8")
    backend = (WEB / "article_workbench_data.py").read_text(encoding="utf-8")

    for canonical in CANONICAL_DOCUMENT_CLASS_MEMBERS:
        assert f'value="{canonical}"' in html
    for legacy in (
        "food_based_dietary_guideline",
        "clinical_practice_guideline",
        "consensus_statement",
        "position_statement",
        "framework_model",
        "competency_curriculum",
        "implementation_evaluation",
    ):
        assert f'value="{legacy}"' not in html
    assert "document_classes_for_canonical(document_class)" in backend
    assert "document_class IN (" in backend
    assert 'article["canonical_document_class"] = canonical_document_class' in backend
    assert '"document_subtype": str(effective_document_class)' in backend
