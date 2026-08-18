from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "rank_references.py"
SPEC = importlib.util.spec_from_file_location("rank_references", MODULE_PATH)
assert SPEC and SPEC.loader
rank_references = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rank_references)


def _base_config(config: Path, *, focus: list[str] | None = None, weights: dict[str, float] | None = None) -> None:
    config.mkdir(parents=True, exist_ok=True)
    (config / "keyword_taxonomy.json").write_text(
        json.dumps({"global": {"nutrition": {"core": ["nutrition care", "dietary pattern", "healthy eating"]}}}),
        encoding="utf-8",
    )
    (config / "reference_mode.json").write_text(
        json.dumps({"mode": "REFERENCE_RANKING", "focus_keywords": focus or [], "provider_weights": weights or {}}),
        encoding="utf-8",
    )


def _write_collection(project: Path, rows: list[dict], *, latin: bool = False) -> None:
    run_dir = project / ("latin_run" if latin else "run")
    log_dir = project / "07_logs" / ("latin_native" if latin else "collect_everything")
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    master = run_dir / "master.jsonl"
    master.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    (log_dir / "latest.json").write_text(json.dumps({"master_records_path": str(master)}), encoding="utf-8")


def _read_ranked(project: Path) -> list[dict]:
    path = project / "reference_ranking" / "reference_ranking.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_taxonomy_title_match_outweighs_abstract_only_match() -> None:
    taxonomy = {"global.nutrition.core": ["dietary pattern"]}
    title_row = rank_references.score_record(
        {"title": "Dietary pattern guidance", "abstract": "x", "source_provider": "pubmed"}, taxonomy, [], {}
    )
    abstract_row = rank_references.score_record(
        {"title": "Nutrition paper", "abstract": "Dietary pattern guidance", "source_provider": "pubmed"}, taxonomy, [], {}
    )
    assert title_row["reference_score"] > abstract_row["reference_score"]


def test_focus_document_type_and_provider_weights_raise_priority() -> None:
    baseline = rank_references.score_record(
        {"title": "Nutrition care report", "abstract": "x", "source_provider": "crossref"}, {}, [], {"crossref": 1, "pubmed": 6}
    )
    prioritized = rank_references.score_record(
        {"title": "Clinical practice guideline for lifestyle medicine nutrition care", "abstract": "x", "source_provider": "pubmed", "pmid": "123"},
        {}, ["lifestyle medicine"], {"crossref": 1, "pubmed": 6}
    )
    assert prioritized["reference_score"] > baseline["reference_score"]
    assert "lifestyle medicine" in prioritized["focus_keyword_hits"]
    assert "clinical practice guideline" in prioritized["document_type_hits"]


def test_recency_is_secondary_to_relevance() -> None:
    taxonomy = {"global.nutrition.core": ["dietary pattern"]}
    relevant_old = rank_references.score_record(
        {"title": "Dietary pattern recommendations", "abstract": "x", "year": 2010}, taxonomy, [], {}
    )
    unrelated_new = rank_references.score_record(
        {"title": "Unrelated technical note", "abstract": "x", "year": 2026}, taxonomy, [], {}
    )
    assert relevant_old["reference_score"] > unrelated_new["reference_score"]


def test_deduplication_prefers_richer_record() -> None:
    rows = [
        {"title": "Same", "doi": "10.1000/example", "abstract": "short"},
        {"title": "Same elsewhere", "doi": "10.1000/example", "abstract": "a much richer abstract"},
    ]
    unique = rank_references._dedupe(rows)
    assert len(unique) == 1
    assert unique[0]["abstract"] == "a much richer abstract"


def test_run_is_deterministic_and_exports_same_order(tmp_path: Path) -> None:
    config = tmp_path / "config"
    project = tmp_path / "project"
    _base_config(config, focus=["lifestyle medicine"], weights={"pubmed": 6, "crossref": 1})
    _write_collection(project, [
        {"title": "Clinical practice guideline for nutrition care and lifestyle medicine", "abstract": "Dietary pattern recommendations", "source_provider": "pubmed", "pmid": "123", "year": 2025},
        {"title": "Healthy eating framework", "abstract": "Dietary pattern", "source_provider": "crossref", "doi": "10.1000/example", "year": 2024},
    ])
    first = rank_references.run(project, config, 10)
    first_rows = _read_ranked(project)
    second = rank_references.run(project, config, 10)
    second_rows = _read_ranked(project)
    assert first["mode"] == "REFERENCE_RANKING"
    assert second["records_unique"] == first["records_unique"]
    assert [(r["title"], r["reference_score"], r["reference_rank"]) for r in first_rows] == [
        (r["title"], r["reference_score"], r["reference_rank"]) for r in second_rows
    ]
    with (project / "reference_ranking" / "reference_ranking.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert [row["title"] for row in csv_rows] == [row["title"] for row in second_rows]
    markdown = (project / "reference_ranking" / "TOP_REFERENCIAS.md").read_text(encoding="utf-8")
    assert [markdown.index(row["title"]) for row in second_rows] == sorted(markdown.index(row["title"]) for row in second_rows)
    assert (project / "reference_ranking" / "latest.json").is_file()


def test_public_output_uses_explicit_metadata_allowlist(tmp_path: Path) -> None:
    config = tmp_path / "config"
    project = tmp_path / "project"
    _base_config(config)
    _write_collection(project, [{
        "title": "Nutrition care guideline",
        "abstract": "healthy eating",
        "source_provider": "pubmed",
        "pmid": "123",
        "internal_control": "must-not-leak",
    }])
    rank_references.run(project, config, 10)
    row = _read_ranked(project)[0]
    assert "internal_control" not in row
    assert row["title"] == "Nutrition care guideline"


def test_latin_source_identity_is_preserved(tmp_path: Path) -> None:
    config = tmp_path / "config"
    project = tmp_path / "project"
    _base_config(config)
    _write_collection(project, [{"title": "Nutrition baseline", "abstract": "healthy eating", "source_provider": "pubmed", "pmid": "1"}])
    _write_collection(project, [
        {"title": "LILACS nutrition guidance", "abstract": "healthy eating", "source_provider": "lilacs_bvs_native", "url": "https://example.org/lilacs"},
        {"title": "SciELO dietary pattern", "abstract": "healthy eating", "source_provider": "scielo_native", "url": "https://example.org/scielo"},
    ], latin=True)
    rank_references.run(project, config, 10)
    providers = {row["reference_provider"] for row in _read_ranked(project)}
    assert {"lilacs_bvs_native", "scielo_native"}.issubset(providers)
