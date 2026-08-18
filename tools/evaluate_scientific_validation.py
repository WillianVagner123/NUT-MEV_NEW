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
DEFAULT_REQUIRED_JUDGED_DEPTH = 100
VALID_SPLITS = ("development", "validation", "external_test")


class ValidationDataError(RuntimeError):
    """Raised when benchmark data is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class RankingItem:
    question_id: str
    system: str
    rank: int
    reference_id: str
    split: str = ""


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


def load_rankings(
    path: Path,
    *,
    split: str | None = None,
) -> dict[tuple[str, str], list[RankingItem]]:
    if not path.is_file():
        raise ValidationDataError(f"Rankings file not found: {path}")
    groups: dict[tuple[str, str], list[RankingItem]] = defaultdict(list)
    seen_refs: set[tuple[str, str, str]] = set()
    seen_ranks: set[tuple[str, str, int]] = set()
    question_splits: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        required = {"question_id", "system", "rank", "reference_id"}
        missing = required - fields
        if missing:
            raise ValidationDataError(
                f"Rankings CSV missing columns: {', '.join(sorted(missing))}"
            )
        has_split = "split" in fields
        if split is not None and not has_split:
            raise ValidationDataError(
                "Split-specific evaluation requires a split column in rankings"
            )
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            system = _clean(row.get("system"))
            reference_id = _clean(row.get("reference_id"))
            row_split = _clean(row.get("split")).casefold() if has_split else ""
            rank_raw = _clean(row.get("rank"))
            if not question_id or not system or not reference_id:
                raise ValidationDataError(
                    f"Blank question_id/system/reference_id at line {line_number}"
                )
            if row_split:
                previous_split = question_splits.get(question_id)
                if previous_split and previous_split != row_split:
                    raise ValidationDataError(
                        f"Question appears in multiple splits: {question_id} -> "
                        f"{previous_split}, {row_split}"
                    )
                question_splits[question_id] = row_split
            if split is not None and row_split != split:
                continue
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
                RankingItem(question_id, system, rank, reference_id, row_split)
            )
    if not groups:
        scope = f" for split {split}" if split else ""
        raise ValidationDataError(f"Rankings CSV contains no records{scope}")
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


def _judged_prefix(items: list[RankingItem], gold_for_question: dict[str, int]) -> int:
    prefix = 0
    expected_rank = 1
    for item in items:
        if item.rank != expected_rank:
            break
        if item.reference_id not in gold_for_question:
            break
        prefix += 1
        expected_rank += 1
    return prefix


def _require_judged_prefix(
    question_id: str,
    system: str,
    items: list[RankingItem],
    gold_for_question: dict[str, int],
    required_judged_depth: int,
) -> int:
    judged_prefix = _judged_prefix(items, gold_for_question)
    required = min(required_judged_depth, len(items))
    if judged_prefix < required:
        first_unjudged = items[judged_prefix] if judged_prefix < len(items) else None
        detail = (
            f"rank {first_unjudged.rank} reference {first_unjudged.reference_id}"
            if first_unjudged is not None
            else "ranking ended before required depth"
        )
        raise ValidationDataError(
            "Incomplete judgment coverage inside required benchmark depth for "
            f"{question_id}/{system}: judged prefix={judged_prefix}, required={required}; {detail}"
        )
    return judged_prefix


def evaluate_group(
    question_id: str,
    system: str,
    items: list[RankingItem],
    gold_for_question: dict[str, int],
    *,
    required_judged_depth: int = DEFAULT_REQUIRED_JUDGED_DEPTH,
) -> dict[str, object]:
    if required_judged_depth < 1:
        raise ValidationDataError("required_judged_depth must be >= 1")
    total_relevant = sum(_binary_relevant(grade) for grade in gold_for_question.values())
    judged_prefix = _require_judged_prefix(
        question_id,
        system,
        items,
        gold_for_question,
        required_judged_depth,
    )
    judged_items = items[:judged_prefix]
    judged_grades = [gold_for_question[item.reference_id] for item in judged_items]
    all_retrieved_are_judged = judged_prefix == len(items)
    split = items[0].split if items else ""

    first_relevant_index = next(
        (
            index
            for index, grade in enumerate(judged_grades, start=1)
            if _binary_relevant(grade)
        ),
        None,
    )
    if first_relevant_index is not None:
        reciprocal_rank: object = round(1.0 / first_relevant_index, 6)
    elif all_retrieved_are_judged:
        reciprocal_rank = 0.0
    else:
        reciprocal_rank = ""

    full_average_precision: object = (
        round(_average_precision(judged_grades, total_relevant), 6)
        if all_retrieved_are_judged
        else ""
    )

    row: dict[str, object] = {
        "question_id": question_id,
        "split": split,
        "system": system,
        "retrieved_total": len(items),
        "gold_total": len(gold_for_question),
        "gold_relevant": total_relevant,
        "judged_prefix_length": judged_prefix,
        "retrieved_all_judged": all_retrieved_are_judged,
        "reciprocal_rank": reciprocal_rank,
        "average_precision": full_average_precision,
        "average_precision_at_100": round(
            _average_precision(judged_grades[:100], total_relevant), 6
        ),
    }
    for k in KS:
        effective_k = min(k, len(items))
        judged_at_k = min(judged_prefix, effective_k)
        row[f"judged_at_{k}"] = judged_at_k
        row[f"judgment_coverage_at_{k}"] = (
            round(judged_at_k / effective_k, 6) if effective_k else 1.0
        )
        safe_grades = judged_grades[:effective_k]
        row[f"precision_at_{k}"] = round(_precision_at(safe_grades, k), 6)
        row[f"recall_at_{k}"] = round(
            _recall_at(safe_grades, total_relevant, k), 6
        )
        row[f"ndcg_at_{k}"] = round(
            _ndcg_at(safe_grades, gold_for_question.values(), k), 6
        )
    for target in RECALL_TARGETS:
        label = int(target * 100)
        records = _records_to_recall(judged_grades, total_relevant, target)
        row[f"records_to_{label}_recall"] = records if records is not None else ""
        row[f"fraction_to_{label}_recall"] = (
            round(records / len(items), 6) if records is not None and items else ""
        )
    return row


def evaluate(
    gold: dict[str, dict[str, int]],
    rankings: dict[tuple[str, str], list[RankingItem]],
    *,
    required_judged_depth: int = DEFAULT_REQUIRED_JUDGED_DEPTH,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    systems: set[str] = set()
    for (question_id, system), items in sorted(rankings.items()):
        if question_id not in gold:
            raise ValidationDataError(
                f"Ranking contains question without gold standard: {question_id}"
            )
        systems.add(system)
        rows.append(
            evaluate_group(
                question_id,
                system,
                items,
                gold[question_id],
                required_judged_depth=required_judged_depth,
            )
        )

    for system in sorted(systems):
        members = [row for row in rows if row["system"] == system]
        if not members:
            continue
        member_splits = {str(row.get("split") or "") for row in members}
        aggregate_split = next(iter(member_splits)) if len(member_splits) == 1 else "__ALL__"
        aggregate: dict[str, object] = {
            "question_id": "__MACRO__",
            "split": aggregate_split,
            "system": system,
            "retrieved_total": sum(int(row["retrieved_total"]) for row in members),
            "gold_total": sum(int(row["gold_total"]) for row in members),
            "gold_relevant": sum(int(row["gold_relevant"]) for row in members),
            "judged_prefix_length": sum(
                int(row["judged_prefix_length"]) for row in members
            ),
            "retrieved_all_judged": all(
                bool(row["retrieved_all_judged"]) for row in members
            ),
        }
        metric_keys = [
            key
            for key in members[0]
            if key
            not in {
                "question_id",
                "split",
                "system",
                "retrieved_total",
                "gold_total",
                "gold_relevant",
                "judged_prefix_length",
                "retrieved_all_judged",
            }
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
    parser.add_argument(
        "--split",
        choices=VALID_SPLITS,
        help=(
            "Evaluate only one benchmark split. Use this to keep external-test labels/results "
            "physically sealed until the validation continuation decision is locked."
        ),
    )
    parser.add_argument(
        "--require-judged-through",
        type=int,
        default=DEFAULT_REQUIRED_JUDGED_DEPTH,
        help=(
            "Fail if any retrieved record is unjudged inside this rank depth. "
            "Default 100 matches the pre-registered common-pool depth."
        ),
    )
    args = parser.parse_args()
    try:
        gold = load_gold(args.gold_standard)
        rankings = load_rankings(args.rankings, split=args.split)
        rows = evaluate(
            gold,
            rankings,
            required_judged_depth=args.require_judged_through,
        )
        write_results(args.output, rows)
    except ValidationDataError as exc:
        print(f"Validation data error: {exc}")
        return 2
    print(f"Wrote {len(rows)} benchmark rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
