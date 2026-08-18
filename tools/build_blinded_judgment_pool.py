from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from nutev.reference_identity import canonical_identity


DEFAULT_POOL_DEPTH = 100
DEFAULT_POOL_SEED = "nutev-judgment-pool-v1"
DEFAULT_PRIMARY_SYSTEMS = ("nutev_full", "lexical_baseline")
VALID_SPLITS = ("development", "validation", "external_test")


class PoolBuildError(RuntimeError):
    """Raised when a blinded judgment pool cannot be built without ambiguity."""


def _clean(value: object) -> str:
    return str(value or "").strip()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise PoolBuildError(f"Metadata JSONL not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PoolBuildError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise PoolBuildError(f"Non-object JSONL at line {line_number}")
            rows.append(value)
    if not rows:
        raise PoolBuildError("Metadata JSONL contains no records")
    return rows


def _metadata_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = canonical_identity(row)
        if not rid:
            raise PoolBuildError(f"Metadata row lacks canonical identity: {row.get('title')!r}")
        if rid in index:
            raise PoolBuildError(f"Duplicate metadata reference_id: {rid}")
        index[rid] = row
    return index


def _parse_systems(value: str) -> tuple[str, ...]:
    systems = tuple(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))
    if not systems:
        raise PoolBuildError("At least one pool system must be selected")
    return systems


def load_rankings(
    path: Path,
    *,
    depth: int,
    systems: tuple[str, ...] | None = None,
    split: str | None = None,
) -> dict[tuple[str, str], list[tuple[int, str]]]:
    if not path.is_file():
        raise PoolBuildError(f"Rankings CSV not found: {path}")
    selected = set(systems) if systems is not None else None
    groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    seen_refs: set[tuple[str, str, str]] = set()
    seen_ranks: set[tuple[str, str, int]] = set()
    all_questions: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        required = {"question_id", "system", "rank", "reference_id"}
        missing = required - fields
        if missing:
            raise PoolBuildError(
                f"Rankings CSV missing columns: {', '.join(sorted(missing))}"
            )
        if split is not None and "split" not in fields:
            raise PoolBuildError("Split-specific pool requires a split column in rankings")
        for line_number, row in enumerate(reader, start=2):
            question_id = _clean(row.get("question_id"))
            system = _clean(row.get("system"))
            rid = _clean(row.get("reference_id"))
            row_split = _clean(row.get("split")).casefold() if "split" in fields else ""
            try:
                rank = int(_clean(row.get("rank")))
            except ValueError as exc:
                raise PoolBuildError(f"Invalid rank at line {line_number}") from exc
            if not question_id or not system or not rid or rank < 1:
                raise PoolBuildError(f"Invalid ranking identity at line {line_number}")
            if split is not None and row_split != split:
                continue
            all_questions.add(question_id)
            if selected is not None and system not in selected:
                continue
            ref_key = (question_id, system, rid)
            rank_key = (question_id, system, rank)
            if ref_key in seen_refs or rank_key in seen_ranks:
                raise PoolBuildError(
                    f"Duplicate ranking entry at {question_id}/{system}/{rank}/{rid}"
                )
            seen_refs.add(ref_key)
            seen_ranks.add(rank_key)
            if rank <= depth:
                groups.setdefault((question_id, system), []).append((rank, rid))
    if not groups:
        scope = f" for split {split}" if split else ""
        raise PoolBuildError(
            f"Rankings contain no records inside requested pool depth{scope}"
        )
    for items in groups.values():
        items.sort(key=lambda item: (item[0], item[1]))
    if systems is not None:
        for question_id in sorted(all_questions):
            for system in systems:
                if (question_id, system) not in groups:
                    raise PoolBuildError(
                        f"Requested pool system missing for question: {question_id}/{system}"
                    )
    return groups


def _blind_key(seed: str, question_id: str, rid: str) -> str:
    return sha256(f"{seed}|{question_id}|{rid}".encode("utf-8")).hexdigest()


def build_pool(
    ranking_groups: dict[tuple[str, str], list[tuple[int, str]]],
    metadata: dict[str, dict[str, Any]],
    *,
    seed: str = DEFAULT_POOL_SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    membership: dict[tuple[str, str], dict[str, int]] = {}
    for (question_id, system), items in ranking_groups.items():
        for rank, rid in items:
            if rid not in metadata:
                raise PoolBuildError(
                    f"Ranking reference_id has no frozen metadata row: {question_id}/{system}/{rid}"
                )
            membership.setdefault((question_id, rid), {})[system] = rank

    blinded: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    by_question: dict[str, list[tuple[str, dict[str, int]]]] = {}
    for (question_id, rid), systems in membership.items():
        by_question.setdefault(question_id, []).append((rid, systems))

    for question_id in sorted(by_question):
        items = sorted(
            by_question[question_id],
            key=lambda item: _blind_key(seed, question_id, item[0]),
        )
        for blinded_order, (rid, systems) in enumerate(items, start=1):
            row = metadata[rid]
            pool_item_id = "pool_" + sha256(
                f"{question_id}|{rid}".encode("utf-8")
            ).hexdigest()[:16]
            blinded.append(
                {
                    "question_id": question_id,
                    "pool_item_id": pool_item_id,
                    "blinded_order": blinded_order,
                    "reference_id": rid,
                    "title": _clean(row.get("title")),
                    "abstract": _clean(
                        row.get("abstract") or row.get("summary") or row.get("snippet")
                    ),
                    "journal": _clean(row.get("journal")),
                    "year": _clean(row.get("reference_year") or row.get("year")),
                    "doi": _clean(row.get("doi") or row.get("doi_normalized")),
                    "pmid": _clean(row.get("pmid") or row.get("pmid_normalized")),
                    "pmcid": _clean(row.get("pmcid")),
                    "url": _clean(row.get("url") or row.get("url_normalized")),
                }
            )
            audit.append(
                {
                    "question_id": question_id,
                    "pool_item_id": pool_item_id,
                    "reference_id": rid,
                    "system_membership": json.dumps(systems, sort_keys=True),
                    "systems_count": len(systems),
                }
            )
    return blinded, audit


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a blinded judgment pool from label-blind benchmark rankings."
    )
    parser.add_argument("--rankings", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--blinded-output", required=True, type=Path)
    parser.add_argument("--audit-output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--depth", type=int, default=DEFAULT_POOL_DEPTH)
    parser.add_argument("--seed", default=DEFAULT_POOL_SEED)
    parser.add_argument(
        "--systems",
        default=",".join(DEFAULT_PRIMARY_SYSTEMS),
        help="Comma-separated systems to contribute to the judgment pool. Default is the preregistered primary pair.",
    )
    parser.add_argument(
        "--split",
        choices=VALID_SPLITS,
        help="Optional split to build as a physically separate pool, supporting sealed external-test custody.",
    )
    args = parser.parse_args()

    try:
        if args.depth < 1:
            raise PoolBuildError("Pool depth must be >= 1")
        systems = _parse_systems(args.systems)
        metadata_rows = _read_jsonl(args.metadata)
        metadata = _metadata_index(metadata_rows)
        groups = load_rankings(
            args.rankings,
            depth=args.depth,
            systems=systems,
            split=args.split,
        )
        blinded, audit = build_pool(groups, metadata, seed=args.seed)
        _write_csv(
            args.blinded_output,
            blinded,
            [
                "question_id",
                "pool_item_id",
                "blinded_order",
                "reference_id",
                "title",
                "abstract",
                "journal",
                "year",
                "doi",
                "pmid",
                "pmcid",
                "url",
            ],
        )
        _write_csv(
            args.audit_output,
            audit,
            [
                "question_id",
                "pool_item_id",
                "reference_id",
                "system_membership",
                "systems_count",
            ],
        )
        manifest = {
            "pool_type": (
                "PRIMARY_COMMON_POOL_TOP_K_UNION"
                if systems == DEFAULT_PRIMARY_SYSTEMS
                else "CUSTOM_COMMON_POOL_TOP_K_UNION"
            ),
            "split": args.split or "__ALL__",
            "selected_systems": list(systems),
            "depth_per_system": args.depth,
            "blind_order_seed": args.seed,
            "label_blind": True,
            "blinded_output_contains_system_or_rank": False,
            "rankings_sha256": sha256(args.rankings.read_bytes()).hexdigest(),
            "metadata_sha256": sha256(args.metadata.read_bytes()).hexdigest(),
            "blinded_output_sha256": sha256(args.blinded_output.read_bytes()).hexdigest(),
            "audit_output_sha256": sha256(args.audit_output.read_bytes()).hexdigest(),
            "pool_rows": len(blinded),
            "audit_rows": len(audit),
            "scientific_boundary": (
                "The audit output contains system membership and must not be shown to assessors "
                "before initial relevance judgments are locked. The default primary pool contains "
                "only the preregistered candidate and lexical baseline. Split-specific pools allow "
                "external-test evidence to remain under separate custody until the validation gate."
            ),
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except PoolBuildError as exc:
        print(f"Pool build failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
