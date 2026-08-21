from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"


def test_reviewer_link_helper_is_loaded_only_on_coordinator_index() -> None:
    index = (VALIDATION_ROOT / "index.html").read_text(encoding="utf-8")
    review = (VALIDATION_ROOT / "review.html").read_text(encoding="utf-8")
    assert "reviewer-link-config.js" in index
    assert "reviewer-link-config.js" not in review


def test_reviewer_link_helper_rewrites_only_private_link_base() -> None:
    script = (VALIDATION_ROOT / "reviewer-link-config.js").read_text(encoding="utf-8")
    assert "tokenFromPrivateLink" in script
    assert "privateReviewLink" in script
    assert "/validation/review.html#token=" in script
    assert "button.dataset.link = next" in script
    assert "new URLSearchParams(parsed.hash" in script
    assert "#token=" in script


def test_reviewer_base_configuration_never_persists_reviewer_tokens() -> None:
    script = (VALIDATION_ROOT / "reviewer-link-config.js").read_text(encoding="utf-8")
    assert "nutev_validation_reviewer_base_v1" in script
    assert "localStorage.setItem(REVIEW_BASE_KEY, base)" in script
    assert "localStorage.setItem(REVIEW_BASE_KEY, token" not in script
    assert "localStorage.setItem" in script
    assert "sessionStorage" not in script


def test_reviewer_base_rejects_unsafe_or_malformed_urls() -> None:
    script = (VALIDATION_ROOT / "reviewer-link-config.js").read_text(encoding="utf-8")
    assert "['http:', 'https:'].includes(parsed.protocol)" in script
    assert "parsed.username || parsed.password" in script
    assert "parsed.search || parsed.hash" in script
    assert "Informe uma URL completa" in script


def test_loopback_coordinator_requires_explicit_reviewer_address() -> None:
    script = (VALIDATION_ROOT / "reviewer-link-config.js").read_text(encoding="utf-8")
    assert "localhost" in script
    assert "127.0.0.1" in script
    assert "0.0.0.0" in script
    assert "Endereço dos avaliadores" in script
    assert "Os links ainda apontariam para localhost/0.0.0.0" in script


def test_reviewer_link_panel_is_idempotent_across_launcher_rerenders() -> None:
    script = (VALIDATION_ROOT / "reviewer-link-config.js").read_text(encoding="utf-8")
    assert "data-review-base-state" in script
    assert "existing?.dataset.reviewBaseState === desiredState" in script
    assert "MutationObserver" in script
    assert "renderingReviewerLinks" in script
