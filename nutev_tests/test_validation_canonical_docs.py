from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"
WEB_ROOT = REPO_ROOT / "apps" / "nutev-web"


def test_validation_readme_declares_site_first_flow_as_canonical() -> None:
    text = (VALIDATION_ROOT / "README.md").read_text(encoding="utf-8")
    assert "caminho operacional canônico" in text.lower()
    assert "python apps/nutev-web/server.py" in text
    assert "PREPARAR RODADA" in text
    assert "AVALIAÇÃO CEGA A / B" in text
    assert "GOLD STANDARD + VALIDATOR CANÔNICO" in text
    assert "LOCK DA DECISÃO PRÉ-ESPECIFICADA" in text
    assert "B — DEMOTE" in text


def test_supabase_is_documented_as_legacy_optional_not_current_canonical_path() -> None:
    readme = (VALIDATION_ROOT / "README.md").read_text(encoding="utf-8")
    deployment = (VALIDATION_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "Backend Supabase legado/opcional" in readme
    assert "Legacy/optional hosted Supabase implementation" in deployment
    assert "not the canonical deployment for the current round" in deployment


def test_operational_docs_preserve_external_test_seal_and_scientific_boundary() -> None:
    validation = (VALIDATION_ROOT / "README.md").read_text(encoding="utf-8")
    web = (WEB_ROOT / "README.md").read_text(encoding="utf-8")
    assert "external_test_released = false" in validation
    assert "automatic_external_release = false" in validation
    assert "Prontidão do software não é promoção científica" in validation
    assert "External test" in web or "external_test" in web
