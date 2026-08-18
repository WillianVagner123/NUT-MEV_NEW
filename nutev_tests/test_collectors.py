from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECT_PATH = REPO_ROOT / "tools" / "run_everything_now.py"
LATIN_PATH = REPO_ROOT / "tools" / "run_latin_sources.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = _load("run_everything_now", COLLECT_PATH)
latin = _load("run_latin_sources", LATIN_PATH)


@pytest.mark.parametrize(
    "module_name",
    [
        "nutev.search.pubmed",
        "nutev.search.europepmc",
        "nutev.search.openalex",
        "nutev.search.crossref",
        "nutev.search.doaj",
        "nutev.search.semantic_scholar",
        "nutev.search.google_pse",
        "nutev.search.brave_optional",
        "nutev.search.serpapi_optional",
        "nutev.search.official_sources",
    ],
)
def test_supported_provider_modules_import(module_name: str) -> None:
    assert importlib.import_module(module_name)


def test_collection_normalization_and_deduplication() -> None:
    assert collect._normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert collect._normalize_pmid("PMID: 12345") == "12345"
    rows = [
        {"title": "A", "doi": "10.1000/example", "abstract": "short"},
        {"title": "A richer", "doi": "10.1000/example", "abstract": "a richer abstract"},
    ]
    unique = collect._dedupe(rows)
    assert len(unique) == 1
    assert unique[0]["abstract"] == "a richer abstract"


def test_provider_failure_is_explicit_and_empty(tmp_path: Path) -> None:
    def fail() -> list[dict]:
        raise RuntimeError("provider unavailable")

    rows, meta = collect._run_list_provider(tmp_path, "example", fail)
    assert rows == []
    assert meta["status"] == "failed"
    assert "provider unavailable" in meta["error"]
    records = tmp_path / "providers" / "example.jsonl"
    assert records.is_file()
    assert records.read_text(encoding="utf-8") == ""


def test_latin_candidates_preserve_native_provider_identity() -> None:
    bvs = latin._candidate(
        "lilacs_bvs_native",
        "https://pesquisa.bvsalud.org/portal/",
        "https://pesquisa.bvsalud.org/portal/resource/pt/example",
        "Dietary guidance for healthy eating in primary care",
        "nutrition guideline",
    )
    scielo = latin._candidate(
        "scielo_native",
        "https://search.scielo.org/",
        "https://www.scielo.br/j/example/a/article123/",
        "Dietary pattern recommendations for cardiometabolic health",
        "nutrition guideline",
    )
    assert bvs and bvs["source_provider"] == "lilacs_bvs_native"
    assert scielo and scielo["source_provider"] == "scielo_native"
    assert bvs["collection_type"] == "REFERENCE_COLLECTION"
    assert scielo["collection_type"] == "REFERENCE_COLLECTION"


def test_latin_access_denied_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Response:
        status_code = 403

    monkeypatch.setattr(latin.requests, "get", lambda *args, **kwargs: Response())
    result = latin._run_provider(
        "scielo_native",
        "https://search.scielo.org/?q=nutrition",
        "nutrition",
        tmp_path,
    )
    assert result["status"] == "unavailable"
    assert result["records"] == 0
    assert result["http_status"] == 403
    assert "fabricated" in result["availability_note"]


def test_official_manifest_loads_without_network() -> None:
    from nutev.search.official_sources import all_manifest_sources, load_official_manifest

    manifest = load_official_manifest(REPO_ROOT / "config", include_countries=True)
    rows = all_manifest_sources(manifest)
    assert rows
    assert all(row["source_provider"] == "official_web" for row in rows)
    assert all(row["url"].startswith(("http://", "https://")) for row in rows)


def test_collection_config_has_operational_and_deep_limits() -> None:
    config = json.loads((REPO_ROOT / "config" / "reference_search.json").read_text(encoding="utf-8"))
    expected = {"pubmed", "europepmc", "openalex", "crossref", "doaj", "semantic_scholar"}
    assert set(config["provider_limits"]).issuperset(expected)
    assert set(config["deep_provider_limits"]).issuperset(expected)
    assert all(config["provider_limits"][name] <= config["deep_provider_limits"][name] for name in expected)
