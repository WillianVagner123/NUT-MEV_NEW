from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_validation_web_assets_are_present_and_version_pinned() -> None:
    index = (APP_ROOT / "index.html").read_text(encoding="utf-8")
    app = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    assert './styles.css' in index
    assert './app.js' in index
    assert '@supabase/supabase-js@2.112.3' in app
    assert 'papaparse@5.6.0' in app


def test_mvp_is_validation_only_and_rejects_blinding_leaks() -> None:
    app = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    schema = (APP_ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    assert "check (split = 'validation')" in schema
    assert "external_test" not in schema.casefold()
    for field in (
        "reference_score",
        "reference_rank",
        "taxonomy_primary",
        "taxonomy_secondary",
        "system_origin",
        "nutev_score",
        "nutev_rank",
    ):
        assert field in app


def test_every_exposed_validation_table_has_rls_and_anon_is_revoked() -> None:
    schema = (APP_ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    tables = (
        "validation_profiles",
        "validation_rounds",
        "validation_questions",
        "validation_references",
        "validation_assignments",
        "validation_progress",
        "validation_adjudications",
    )
    for table in tables:
        assert f"alter table public.{table} enable row level security;" in schema
    assert "from anon;" in schema
    assert "private.current_validation_role()" in schema
    assert "private.is_assigned_to_item" in schema


def test_assessment_cannot_close_with_incomplete_or_unblinded_decisions() -> None:
    schema = (APP_ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    assert "a.relevance_grade is null" in schema
    assert "a.decision_timestamp is null" in schema
    assert "a.blind_to_nutev is not true" in schema
    assert "all blind assessments must be complete before adjudication" in schema


def test_exports_match_gold_standard_validator_contract() -> None:
    app = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    for required in (
        "question_id",
        "reference_id",
        "assessor_id",
        "relevance_grade",
        "blind_to_nutev",
        "adjudication_status",
        "adjudicator_id",
        "adjudication_timestamp",
    ):
        assert required in app
    assert "Export final disponível somente após o round ser locked" in app
