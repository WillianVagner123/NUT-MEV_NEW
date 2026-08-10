from __future__ import annotations

import tomllib
from pathlib import Path


def _pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def test_arxiv_provider_does_not_require_third_party_arxiv_client() -> None:
    search_deps = _pyproject()["project"]["optional-dependencies"]["search"]
    assert not any(dep.lower().startswith("arxiv") for dep in search_deps)

    source = Path("src/nutev/search/arxiv.py").read_text(encoding="utf-8")
    assert "requests.get(" in source
    assert "export.arxiv.org/api/query" in source
    assert "import arxiv" not in source
    assert "from arxiv" not in source


def test_document_extra_requires_current_pypdf_security_line() -> None:
    document_deps = _pyproject()["project"]["optional-dependencies"]["documents"]
    assert "pypdf~=6.14.2" in document_deps

    ci_requirements = Path("requirements/nutev-ci.txt").read_text(encoding="utf-8")
    assert "pypdf>=6.14.2" in ci_requirements
