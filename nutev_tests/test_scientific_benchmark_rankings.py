from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_scientific_benchmark_rankings.py"
SPEC = importlib.util.spec_from_file_location("build_scientific_benchmark_rankings", MODULE_PATH)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


def _rows() -> list[dict]:
    return [
        {
            "reference_rank": 1,
            "reference_score": 70.0,
            "title": "Nutrition care overview",
            "abstract": "general nutrition",
            "doi": "10.1000/general",
            "reference_year": 2024,
            "score_breakdown": {
                "taxonomy": 30.0,
                "focus_keywords": 20.0,
                "document_type": 5.0,
                "provider": 6.0,
                "identifier": 2.0,
                "recency": 4.0,
                "penalties": 0.0,
            },
        },
        {
            "reference_rank": 2,
            "reference_score": 60.0,
            "title": "Mediterranean diet and diabetes",
            "abstract": "mediterranean diet glycemic control diabetes",
            "doi": "10.1000/med",
            "reference_year": 2020,
            "score_breakdown": {
                "taxonomy": 40.0,
                "focus_keywords": 5.0,
                "document_type": 0.0,
                "provider": 6.0,
                "identifier": 2.0,
                "recency": 2.0,
                "penalties": 0.0,
            },
        },
        {
            "reference_rank": 3,
            "reference_score": 50.0,
            "title": "Older dietary guideline",
            "abstract": "diet guidance",
            "doi": "10.1000/old",
            "reference_year": 2010,
            "score_breakdown": {
                "taxonomy": 10.0,
                "focus_keywords": 10.0,
                "document_type": 12.0,
                "provider": 6.0,
                "identifier": 2.0,
                "recency": 0.0,
                "penalties": 0.0,
            },
        },
    ]


def test_lexical_baseline_uses_question_not_nutev_order() -> None:
    question = benchmark.Question("q1", "Mediterranean diet diabetes", "development")
    ranked = benchmark._rank_rows(
        question,
        _rows(),
        "lexical_baseline",
        seed=benchmark.DEFAULT_RANDOM_SEED,
    )
    assert ranked[0][0] == "doi:10.1000/med"


def test_recency_baseline_is_independent_of_nutev_score() -> None:
    question = benchmark.Question("q1", "nutrition", "development")
    ranked = benchmark._rank_rows(
        question,
        _rows(),
        "recency_baseline",
        seed=benchmark.DEFAULT_RANDOM_SEED,
    )
    assert [rid for rid, _ in ranked] == [
        "doi:10.1000/general",
        "doi:10.1000/med",
        "doi:10.1000/old",
    ]


def test_ablation_removes_only_declared_component() -> None:
    question = benchmark.Question("q1", "nutrition", "development")
    ranked = benchmark._rank_rows(
        question,
        _rows(),
        "nutev_no_taxonomy",
        seed=benchmark.DEFAULT_RANDOM_SEED,
    )
    scores = dict(ranked)
    assert scores["doi:10.1000/general"] == 40.0
    assert scores["doi:10.1000/med"] == 20.0


def test_union_unranked_is_deterministic_and_question_specific() -> None:
    q1 = benchmark.Question("q1", "nutrition", "development")
    q2 = benchmark.Question("q2", "nutrition", "validation")
    first = benchmark._rank_rows(q1, _rows(), "union_unranked", seed="seed")
    second = benchmark._rank_rows(q1, _rows(), "union_unranked", seed="seed")
    other = benchmark._rank_rows(q2, _rows(), "union_unranked", seed="seed")
    assert first == second
    assert {rid for rid, _ in first} == {rid for rid, _ in other}
    assert first != other


def test_duplicate_reference_id_fails_closed() -> None:
    rows = _rows()
    rows.append(
        {
            **rows[0],
            "title": "Same DOI elsewhere",
            "reference_rank": 4,
        }
    )
    with pytest.raises(benchmark.BenchmarkBuildError, match="duplicate canonical reference_id"):
        benchmark.build_rankings(
            [benchmark.Question("q1", "nutrition", "development")],
            rows,
        )


def test_questions_require_predeclared_split(tmp_path: Path) -> None:
    path = tmp_path / "questions.csv"
    path.write_text(
        "question_id,question_text,split\nq1,What matters?,unknown\n",
        encoding="utf-8",
    )
    with pytest.raises(benchmark.BenchmarkBuildError, match="Invalid split"):
        benchmark.load_questions(path)


def test_manifest_declares_label_blind_common_pool_scope(tmp_path: Path) -> None:
    questions = tmp_path / "questions.csv"
    questions.write_text(
        "question_id,question_text,split\nq1,Nutrition care,development\n",
        encoding="utf-8",
    )
    frozen = tmp_path / "ranking.jsonl"
    frozen.write_text(json.dumps(_rows()[0]) + "\n", encoding="utf-8")
    output = tmp_path / "rankings.csv"
    benchmark.write_rankings(
        output,
        benchmark.build_rankings(
            [benchmark.Question("q1", "Nutrition care", "development")],
            [_rows()[0]],
        ),
    )
    manifest = tmp_path / "manifest.json"
    benchmark.write_manifest(
        manifest,
        candidate_sha=benchmark.FROZEN_RUNTIME_SHA,
        questions_path=questions,
        ranking_path=output,
        input_path=frozen,
        seed=benchmark.DEFAULT_RANDOM_SEED,
        question_count=1,
        record_count=1,
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["label_blind_build"] is True
    assert data["gold_standard_consumed"] is False
    assert data["benchmark_type"] == "COMMON_POOL_PRIORITIZATION"


def test_written_rankings_match_evaluator_schema(tmp_path: Path) -> None:
    output = tmp_path / "rankings.csv"
    rows = benchmark.build_rankings(
        [benchmark.Question("q1", "Mediterranean diabetes", "external_test")],
        _rows(),
    )
    benchmark.write_rankings(output, rows)
    with output.open(encoding="utf-8-sig", newline="") as handle:
        parsed = list(csv.DictReader(handle))
    assert {"question_id", "system", "rank", "reference_id"}.issubset(parsed[0])
    assert "external_test" in {row["split"] for row in parsed}
