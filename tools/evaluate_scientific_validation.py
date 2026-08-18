from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
from statistics import mean, median
from typing import Iterable


KS = (10, 20, 50, 100)
RECALL_TARGETS = (0.80, 0.90, 0.95)


class ValidationDataError(RuntimeError):
    """Raised when benchmark data is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class RankingItem:
    question_id: str
    system: str
    rank: int
    reference_id: str


def _clean(value: object) -> str:
    return str(value or "").strip()


def load_gold(path: Path) -> dict[str, dict[str, int]]:
    if not path.is_file():
        raise ValidationDataError(f"Gold-standard file not found: {path}")
    gold: dict[str, dict[str, int]] = defaultdict(dict)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"question_id", "reference_id", "relevance_grade"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValidationDataError(
                f"Gold-standard CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            reference_id = _clean(row.get("reference_id"))
            grade_raw = _clean(row.get("relevance_grade"))
            if not question_id or not reference_id:
                raise ValidationDataError(
                    f"Blank question_id/reference_id in gold standard at line {line_number}"
                )
            try:
                grade = int(grade_raw)
            except ValueError as exc:
                raise ValidationDataError(
                    f"Invalid relevance_grade at line {line_number}: {grade_raw!r}"
                ) from exc
            if grade not in {0, 1, 2}:
                raise ValidationDataError(
                    f"relevance_grade must be 0, 1 or 2 at line {line_number}"
                )
            previous = gold[question_id].get(reference_id)
            if previous is not None and previous != grade:
                raise ValidationDataError(
                    f"Conflicting gold labels for {question_id}/{reference_id}"
                )
            gold[question_id][reference_id] = grade
    if not gold:
        raise ValidationDataError("Gold-standard CSV contains no records")
    return dict(gold)


def load_rankings(path: Path) -> dict[tuple[str, str], list[RankingItem]]:
    if not path.is_file():
        raise ValidationDataError(f"Rankings file not found: {path}")
    groups: dict[tuple[str, str], list[RankingItem]] = defaultdict(list)
    seen_refs: set[tuple[str, str, str]] = set()
    seen_ranks: set[tuple[str, str, int]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"question_id", "system", "rank", "reference_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValidationDataError(
                f"Rankings CSV missing columns: {', '.join(sorted(missing))}"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            system = _clean(row.get("system"))
            reference_id = _clean(row.get("reference_id"))
            rank_raw = _clean(row.get("rank"))
            if not question_id or not system or not reference_id:
                raise ValidationDataError(
                    f"Blank question_id/system/reference_id at line {line_number}"
                )
            try:
                rank = int(rank_raw)
            except ValueError as exc:
                raise ValidationDataError(
                    f"Invalid rank at line {line_number}: {rank_raw!r}"
                ) from exc
            if rank < 1:
                raise ValidationDataError(f"Rank must be >= 1 at line {line_number}")
            ref_key = (question_id, system, reference_id)
            rank_key = (question_id, system, rank)
            if ref_key in seen_refs:
                raise ValidationDataError(
                    f"Duplicate reference in ranking: {question_id}/{system}/{reference_id}"
                )
            if rank_key in seen_ranks:
                raise ValidationDataError(
                    f"Duplicate rank in ranking: {question_id}/{system}/{rank}"
                )
            seen_refs.add(ref_key)
            seen_ranks.add(rank_key)
            groups[(question_id, system)].append(
                RankingItem(question_id, system, rank, reference_id)
            )
    if not groups:
        raise ValidationDataError("Rankings CSV contains no records")
    for items in groups.values():
        items.sort(key=lambda item: (item.rank, item.reference_id))
    return dict(groups)


def _binary_relevant(grade: int) -> bool:
    return grade > 0


def _precision_at(grades: list[int], k: int) -> float:
    window = grades[:k]
    if not window:
        return 0.0
    return sum(_binary_relevant(grade) for grade in window) / len(window)


def _recall_at(grades: list[int], total_relevant: int, k: int) -> float:
    if total_relevant <= 0:
        return 0.0
    return sum(_binary_relevant(grade) for grade in grades[:k]) / total_relevant


def _reciprocal_rank(grades: list[int]) -> float:
    for index, grade in enumerate(grades, start=1):
        if _binary_relevant(grade):
            return 1.0 / index
    return 0.0


def _average_precision(grades: list[int], total_relevant: int) -> float:
    if total_relevant <= 0:
        return 0.0
    hits = 0
    total = 0.0
    for index, grade in enumerate(grades, start=1):
        if _binary_relevant(grade):
            hits += 1
            total += hits / index
    return total / total_relevant


def _dcg(grades: Iterable[int]) -> float:
    total = 0.0
    for index, grade in enumerate(grades, start=1):
        gain = (2**grade) - 1
        total += gain / math.log2(index + 1)
    return total


def _ndcg_at(grades: list[int], gold_grades: Iterable[int], k: int) -> float:
    observed = _dcg(grades[:k])
    ideal = _dcg(sorted(gold_grades, reverse=True)[:k])
    return observed / ideal if ideal > 0 else 0.0


def _records_to_recall(grades: list[int], total_relevant: int, target: float) -> int | None:
    if total_relevant <= 0:
        return None
    hits = 0
    for index, grade in enumerate(grades, start=1):
        if _binary_relevant(grade):
            hits += 1
        if hits / total_relevant >= target:
            return index
    return None


def evaluate_group(
    question_id: str,
    system: str,
    items: list[RankingItem],
    gold_for_question: dict[str, int],
) -> dict[str, object]:
    total_relevant = sum(_binary_relevant(grade) for grade in gold_for_question.values())
    grades = [gold_for_question.get(item.reference_id, 0) for item in items]
    row: dict[str, object] = {
        "question_id": question_id,
        "system": system,
        "retrieved_total": len(items),
        "gold_total": len(gold_for_question),
        "gold_relevant": total_relevant,
        "reciprocal_rank": round(_reciprocal_rank(grades), 6),
        "average_precision": round(_average_precision(grades, total_relevant), 6),
    }
    for k in KS:
        row[f"precision_at_{k}"] = round(_precision_at(grades, k), 6)
        row[f"recall_at_{k}"] = round(_recall_at(grades, total_relevant, k), 6)
        row[f"ndcg_at_{k}"] = round(
            _ndcg_at(grades, gold_for_question.values(), k), 6
        )
    for target in RECALL_TARGETS:
        label = int(target * 100)
        records = _records_to_recall(grades, total_relevant, target)
        row[f"records_to_{label}_recall"] = records if records is not None else ""
        row[f"fraction_to_{label}_recall"] = (
            round(records / len(items), 6) if records is not None and items else ""
        )
    return row


def evaluate(
    gold: dict[str, dict[str, int]],
    rankings: dict[tuple[str, str], list[RankingItem]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    systems: set[str] = set()
    for (question_id, system), items in sorted(rankings.items()):
        if question_id not in gold:
            raise ValidationDataError(
                f"Ranking contains question without gold standard: {question_id}"
            )
        systems.add(system)
        rows.append(evaluate_group(question_id, system, items, gold[question_id]))

    for system in sorted(systems):
        members = [row for row in rows if row["system"] == system]
        if not members:
            continue
        aggregate: dict[str, object] = {
            "question_id": "__MACRO__",
            "system": system,
            "retrieved_total": sum(int(row["retrieved_total"]) for row in members),
            "gold_total": sum(int(row["gold_total"]) for row in members),
            "gold_relevant": sum(int(row["gold_relevant"]) for row in members),
        }
        metric_keys = [
            key
            for key in members[0]
            if key not in {"question_id", "system", "retrieved_total", "gold_total", "gold_relevant"}
        ]
        for key in metric_keys:
            values = [
                float(row[key])
                for row in members
                if row.get(key) not in {None, ""}
            ]
            aggregate[key] = round(mean(values), 6) if values else ""
            if key.startswith("records_to_") or key.startswith("fraction_to_"):
                aggregate[f"median_{key}"] = round(median(values), 6) if values else ""
        rows.append(aggregate)
    return rows


def write_results(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValidationDataError("No benchmark results to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate NutEV scientific-validation rankings against an independent gold standard."
    )
    parser.add_argument("--gold-standard", required=True, type=Path)
    parser.add_argument("--rankings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        gold = load_gold(args.gold_standard)
        rankings = load_rankings(args.rankings)
        rows = evaluate(gold, rankings)
        write_results(args.output, rows)
    except ValidationDataError as exc:
        print(f"Validation data error: {exc}")
        return 2
    print(f"Wrote {len(rows)} benchmark rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
