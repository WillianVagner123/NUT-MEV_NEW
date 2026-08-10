from pathlib import Path


CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"
CODEQL_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
DEPENDENCY_REVIEW_SHA = "a1d282b36b6f3519aa1f3fc636f609c47dddb294"
GITLEAKS_SHA = "e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e"
UPLOAD_ARTIFACT_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"


def test_workflow_exists():
    assert Path(".github/workflows/nutev-global-watch.yml").exists()


def test_workflow_has_webhook_env():
    txt = Path(".github/workflows/nutev-global-watch.yml").read_text(encoding="utf-8")
    assert "NUTEV_DIGEST_WEBHOOK_URL" in txt


def test_nutev_ci_requirements_exists():
    txt = Path("requirements/nutev-ci.txt").read_text(encoding="utf-8")
    assert "pydantic" in txt
    assert "pytest" in txt


def test_ci_workflow_uses_ci_requirements_manifest():
    # The canonical CI gate (ci.yml) installs deps from the CI manifest and the
    # project with --no-deps, then runs the full nutev_tests suite.
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "requirements/nutev-ci.txt" in ci_workflow
    assert "pip install --no-deps -e ." in ci_workflow
    assert "pytest -q nutev_tests" in ci_workflow


def test_ci_workflow_pins_node24_compatible_actions_to_immutable_shas():
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert f"actions/checkout@{CHECKOUT_SHA}" in ci_workflow
    assert f"actions/setup-python@{SETUP_PYTHON_SHA}" in ci_workflow
    assert "actions/checkout@v" not in ci_workflow
    assert "actions/setup-python@v" not in ci_workflow


def test_security_workflows_pin_reviewed_actions_to_immutable_shas():
    codeql = Path(".github/workflows/codeql.yml").read_text(encoding="utf-8")
    dependency_review = Path(".github/workflows/dependency-review.yml").read_text(
        encoding="utf-8"
    )
    gitleaks = Path(".github/workflows/gitleaks.yml").read_text(encoding="utf-8")

    assert f"github/codeql-action/init@{CODEQL_SHA}" in codeql
    assert f"github/codeql-action/autobuild@{CODEQL_SHA}" in codeql
    assert f"github/codeql-action/analyze@{CODEQL_SHA}" in codeql
    assert f"actions/dependency-review-action@{DEPENDENCY_REVIEW_SHA}" in dependency_review
    assert f"gitleaks/gitleaks-action@{GITLEAKS_SHA}" in gitleaks

    assert "github/codeql-action/init@v" not in codeql
    assert "actions/dependency-review-action@v" not in dependency_review
    assert "gitleaks/gitleaks-action@v" not in gitleaks


def test_global_watch_pins_upload_artifact_to_immutable_sha():
    workflow = Path(".github/workflows/nutev-global-watch.yml").read_text(encoding="utf-8")
    assert f"actions/upload-artifact@{UPLOAD_ARTIFACT_SHA}" in workflow
    assert "actions/upload-artifact@v" not in workflow


def test_dependabot_updates_github_actions_pins():
    dependabot = Path(".github/dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'interval: "weekly"' in dependabot
