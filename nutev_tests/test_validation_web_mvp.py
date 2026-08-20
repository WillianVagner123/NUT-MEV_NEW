from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_validation_web_assets_are_present_and_version_pinned() -> None:
    index = (APP_ROOT / "index.html").read_text(encoding="utf-8")
    launcher = (APP_ROOT / "launcher.js").read_text(encoding="utf-8")
    app = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    local = (APP_ROOT / "local-mode.js").read_text(encoding="utf-8")
    assert './styles.css' in index
    assert './launcher.js' in index
    assert "import('./local-mode.js')" in launcher
    assert "import('./app.js')" in launcher
    assert '@supabase/supabase-js@2.112.3' in app
    assert 'papaparse@5.6.0' in app
    assert 'papaparse@5.6.0' in local


def test_mvp_is_validation_only_and_rejects_blinding_leaks() -> None:
    app = (APP_ROOT / "app.js").read_text(encoding="utf-8")
    local = (APP_ROOT / "local-mode.js").read_text(encoding="utf-8")
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
        assert field in local


def test_local_mode_is_single_assessor_hash_checked_and_persistent() -> None:
    local = (APP_ROOT / "local-mode.js").read_text(encoding="utf-8")
    assert "indexedDB.open" in local
    assert "EXPECTED_QUESTIONS_SHA" in local
    assert "output.sha256 !== packetSha" in local
    assert "assessorIds.size !== 1" in local
    assert "row._draft" in local
    assert "ASSESSOR_${safeName(state.session.assessorId)}_completed.csv" in local


def test_safe_demo_is_synthetic_and_contains_no_real_validation_ids() -> None:
    demo_root = APP_ROOT / "demo"
    questions = (demo_root / "QUESTIONS_DEMO.csv").read_text(encoding="utf-8")
    packet = (demo_root / "ASSESSOR_demo.csv").read_text(encoding="utf-8")
    manifest = (demo_root / "DEMO_MANIFEST.json").read_text(encoding="utf-8")
    for content in (questions, packet, manifest):
        assert "SYNTHETIC_DEMO_NOT_BENCHMARK_EVIDENCE" in content
    assert "Q-V01" not in questions
    assert "Q-V01" not in packet
    assert "assessor_A" not in packet
    assert "assessor_B" not in packet


def test_private_assessor_outputs_are_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        "validation/data/validation_assessor_packets/",
        "NutEV_Validation_assessor_*_PRIVATE.zip",
        "ASSESSOR_assessor_*_completed.csv",
        "NUTEV_assessor_*_backup.json",
        "REVIEW_assessor_*.html",
    ):
        assert pattern in gitignore


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
    local = (APP_ROOT / "local-mode.js").read_text(encoding="utf-8")
    for required in (
        "question_id",
        "reference_id",
        "assessor_id",
        "relevance_grade",
        "blind_to_nutev",
    ):
        assert required in app
        assert required in local
    for required in ("adjudication_status", "adjudicator_id", "adjudication_timestamp"):
        assert required in app
    assert "Export final disponível somente após o round ser locked" in app
