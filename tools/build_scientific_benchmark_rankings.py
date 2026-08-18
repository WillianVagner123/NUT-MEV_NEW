from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from nutev.reference_identity import canonical_identity


FROZEN_RUNTIME_SHA = "6aa7a5fe6009776e611ca3e1506486606b05f4f6"
DEFAULT_RANDOM_SEED = "nutev-benchmark-v1"
BM25_K1 = 1.2
BM25_B = 0.75
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


class BenchmarkBuildError(RuntimeError):
    """Raised when benchmark inputs could contaminate or invalidate the comparison."""


@dataclass(frozen=True)
class Question:
    question_id: str
    question_text: str
    split: str


def _clean(value: object) -> str:
    return str(value or "").strip()


def _tokens(value: object) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(_clean(value))]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise BenchmarkBuildError(f"JSONL file not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BenchmarkBuildError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise BenchmarkBuildError(
                    f"Non-object JSONL record at {path}:{line_number}"
                )
            rows.append(value)
    if not rows:
        raise BenchmarkBuildError(f"JSONL file is empty: {path}")
    return rows


def load_questions(path: Path) -> list[Question]:
    if not path.is_file():
        raise BenchmarkBuildError(f"Questions CSV not found: {path}")
    questions: list[Question] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"question_id", "question_text", "split"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise BenchmarkBuildError(
                f"Questions CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            question_text = _clean(row.get("question_text"))
            split = _clean(row.get("split")).casefold()
            if not question_id or not question_text:
                raise BenchmarkBuildError(
                    f"Blank question_id/question_text at line {line_number}"
                )
            if question_id in seen:
                raise BenchmarkBuildError(f"Duplicate question_id: {question_id}")
            if split not in {"development", "validation", "external_test"}:
                raise BenchmarkBuildError(
                    f"Invalid split for {question_id}: {split!r}"
                )
            seen.add(question_id)
            questions.append(Question(question_id, question_text, split))
    if not questions:
        raise BenchmarkBuildError("Questions CSV contains no questions")
    return questions


def reference_id(row: dict[str, Any]) -> str:
    value = canonical_identity(row)
    if not value:
        raise BenchmarkBuildError(
            f"Record has no canonical benchmark identity: {row.get('title')!r}"
        )
    return value


def _document_text(row: dict[str, Any]) -> str:
    values = [
        row.get("title"),
        row.get("abstract"),
        row.get("summary"),
        row.get("snippet"),
        row.get("keywords"),
        row.get("keyword"),
        row.get("subjects"),
    ]
    return " ".join(_clean(value) for value in values if _clean(value))


def _year(row: dict[str, Any]) -> int:
    for key in ("reference_year", "year", "publication_year", "published_year"):
        raw = _clean(row.get(key))
        match = re.search(r"\b(19|20)\d{2}\b", raw)
        if match:
            return int(match.group(0))
    return 0


def _dedupe_by_reference_id(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        rid = reference_id(row)
        if rid in seen:
            raise BenchmarkBuildError(
                f"Frozen ranking contains duplicate canonical reference_id: {rid}"
            )
        seen.add(rid)
        result.append(dict(row))
    return result


def _bm25_scores(question: str, rows: list[dict[str, Any]]) -> dict[str, float]:
    query_terms = list(dict.fromkeys(_tokens(question)))
    docs = {reference_id(row): _tokens(_document_text(row)) for row in rows}
    if not docs:
        return {}
    avg_len = sum(len(tokens) for tokens in docs.values()) / len(docs)
    avg_len = avg_len or 1.0

    document_frequency: dict[str, int] = {}
    for term in query_terms:
        document_frequency[term] = sum(1 for tokens in docs.values() if term in set(tokens))

    scores: dict[str, float] = {}
    n_docs = len(docs)
    for rid, tokens in docs.items():
        frequencies: dict[str, int] = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        score = 0.0
        doc_len = len(tokens)
        for term in query_terms:
            tf = frequencies.get(term, 0)
            if not tf:
                continue
            df = document_frequency.get(term, 0)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            denom = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * doc_len / avg_len)
            score += idf * (tf * (BM25_K1 + 1.0)) / denom
        scores[rid] = score
    return scores


def _hash_order(question_id: str, rid: str, seed: str) -> str:
    return sha256(f"{seed}|{question_id}|{rid}".encode("utf-8")).hexdigest()


def _score_without_component(row: dict[str, Any], component: str) -> float:
    breakdown = row.get("score_breakdown")
    if not isinstance(breakdown, dict):
        raise BenchmarkBuildError(
            "Frozen NutEV ranking lacks score_breakdown required for label-blind ablations"
        )
    base = float(row.get("reference_score") or 0.0)
    return base - float(breakdown.get(component) or 0.0)


def _rank_rows(
    question: Question,
    rows: list[dict[str, Any]],
    system: str,
    *,
    seed: str,
) -> list[tuple[str, float | None]]:
    if system == "nutev_full":
        ordered = sorted(
            rows,
            key=lambda row: (
                int(row.get("reference_rank") or 10**12),
                reference_id(row),
            ),
        )
        return [(reference_id(row), float(row.get("reference_score") or 0.0)) for row in ordered]

    component_map = {
        "nutev_no_taxonomy": "taxonomy",
        "nutev_no_focus": "focus_keywords",
        "nutev_no_provider_weight": "provider",
        "nutev_no_recency": "recency",
        "nutev_no_document_type": "document_type",
        "nutev_no_identifier_bonus": "identifier",
    }
    if system in component_map:
        component = component_map[system]
        scored = [
            (reference_id(row), _score_without_component(row, component), _year(row))
            for row in rows
        ]
        scored.sort(key=lambda item: (-item[1], -item[2], item[0]))
        return [(rid, score) for rid, score, _ in scored]

    if system == "lexical_baseline":
        scores = _bm25_scores(question.question_text, rows)
        ranked = [(reference_id(row), scores.get(reference_id(row), 0.0), _year(row)) for row in rows]
        ranked.sort(key=lambda item: (-item[1], -item[2], item[0]))
        return [(rid, score) for rid, score, _ in ranked]

    if system == "recency_baseline":
        ranked = [(reference_id(row), _year(row)) for row in rows]
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return [(rid, float(year)) for rid, year in ranked]

    if system == "union_unranked":
        ranked = [(reference_id(row), _hash_order(question.question_id, reference_id(row), seed)) for row in rows]
        ranked.sort(key=lambda item: item[1])
        return [(rid, None) for rid, _ in ranked]

    raise BenchmarkBuildError(f"Unknown benchmark system: {system}")


def build_rankings(
    questions: list[Question],
    frozen_rows: list[dict[str, Any]],
    *,
    seed: str = DEFAULT_RANDOM_SEED,
) -> list[dict[str, Any]]:
    rows = _dedupe_by_reference_id(frozen_rows)
    systems = [
        "nutev_full",
        "lexical_baseline",
        "recency_baseline",
        "union_unranked",
        "nutev_no_taxonomy",
        "nutev_no_focus",
        "nutev_no_provider_weight",
        "nutev_no_recency",
        "nutev_no_document_type",
        "nutev_no_identifier_bonus",
    ]
    output: list[dict[str, Any]] = []
    for question in questions:
        for system in systems:
            ranked = _rank_rows(question, rows, system, seed=seed)
            for rank, (rid, score) in enumerate(ranked, start=1):
                output.append(
                    {
                        "question_id": question.question_id,
                        "split": question.split,
                        "system": system,
                        "rank": rank,
                        "reference_id": rid,
                        "system_score": "" if score is None else round(score, 8),
                    }
                )
    return output


def write_rankings(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["question_id", "split", "system", "rank", "reference_id", "system_score"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(
    path: Path,
    *,
    candidate_sha: str,
    questions_path: Path,
    ranking_path: Path,
    input_path: Path,
    seed: str,
    question_count: int,
    record_count: int,
) -> None:
    payload = {
        "benchmark_type": "COMMON_POOL_PRIORITIZATION",
        "candidate_runtime_sha": candidate_sha,
        "frozen_runtime_sha_required": FROZEN_RUNTIME_SHA,
        "label_blind_build": True,
        "gold_standard_consumed": False,
        "bm25": {"k1": BM25_K1, "b": BM25_B},
        "union_unranked_order": "deterministic_sha256_pseudorandom",
        "union_unranked_seed": seed,
        "question_count": question_count,
        "record_count": record_count,
        "questions_path": str(questions_path),
        "frozen_ranking_input": str(input_path),
        "ranking_output": str(ranking_path),
        "input_sha256": sha256(input_path.read_bytes()).hexdigest(),
        "questions_sha256": sha256(questions_path.read_bytes()).hexdigest(),
        "ranking_sha256": sha256(ranking_path.read_bytes()).hexdigest(),
        "scientific_boundary": (
            "This common-pool harness tests prioritization among records already eligible in the "
            "frozen NutEV output. It does not by itself estimate discovery recall outside that pool."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build label-blind common-pool rankings for the NutEV scientific benchmark."
    )
    parser.add_argument("--questions", required=True)
    parser.add_argument("--frozen-ranking", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--seed", default=DEFAULT_RANDOM_SEED)
    args = parser.parse_args()

    try:
        if args.candidate_sha != FROZEN_RUNTIME_SHA:
            raise BenchmarkBuildError(
                "Candidate SHA does not match validation/VALIDATION_FREEZE.md: "
                f"expected {FROZEN_RUNTIME_SHA}, got {args.candidate_sha}"
            )
        questions_path = Path(args.questions)
        frozen_path = Path(args.frozen_ranking)
        output_path = Path(args.output)
        questions = load_questions(questions_path)
        frozen_rows = _read_jsonl(frozen_path)
        rankings = build_rankings(questions, frozen_rows, seed=args.seed)
        write_rankings(output_path, rankings)
        write_manifest(
            Path(args.manifest),
            candidate_sha=args.candidate_sha,
            questions_path=questions_path,
            ranking_path=output_path,
            input_path=frozen_path,
            seed=args.seed,
            question_count=len(questions),
            record_count=len(frozen_rows),
        )
    except BenchmarkBuildError as exc:
        print(f"Benchmark build failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
