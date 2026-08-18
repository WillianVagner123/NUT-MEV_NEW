from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_PACKET_SEED = "nutev-assessor-packet-v1"
FORBIDDEN_LEAKAGE_COLUMNS = {
    "system",
    "rank",
    "system_score",
    "reference_score",
    "reference_rank",
    "score_breakdown",
    "taxonomy",
    "taxonomy_primary",
    "taxonomy_secondary",
    "system_membership",
    "systems_count",
}
INPUT_REQUIRED = {
    "question_id",
    "pool_item_id",
    "reference_id",
    "title",
}
OUTPUT_COLUMNS = [
    "question_id",
    "pool_item_id",
    "assessor_order",
    "reference_id",
    "title",
    "abstract",
    "journal",
    "year",
    "doi",
    "pmid",
    "pmcid",
    "url",
    "assessor_id",
    "relevance_grade",
    "reason",
    "decision_timestamp",
    "blind_to_nutev",
    "notes",
]


class AssessorPacketError(RuntimeError):
    """Raised when a blinded assessor packet cannot be created safely."""


def _clean(value: object) -> str:
    return str(value or "").strip()


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    if not safe:
        raise AssessorPacketError(f"Invalid assessor_id for file naming: {value!r}")
    return safe


def load_blinded_pool(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise AssessorPacketError(f"Blinded pool file not found: {path}")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = INPUT_REQUIRED - fields
        if missing:
            raise AssessorPacketError(
                f"Blinded pool CSV missing columns: {', '.join(sorted(missing))}"
            )
        leaked = FORBIDDEN_LEAKAGE_COLUMNS & fields
        if leaked:
            raise AssessorPacketError(
                "Blinded pool contains forbidden system/ranking fields: "
                + ", ".join(sorted(leaked))
            )
        for line_number, raw in enumerate(reader, start=2):
            row = {key: _clean(value) for key, value in raw.items() if key is not None}
            question_id = row.get("question_id", "")
            reference_id = row.get("reference_id", "")
            pool_item_id = row.get("pool_item_id", "")
            if not question_id or not reference_id or not pool_item_id:
                raise AssessorPacketError(f"Blank pool identity at line {line_number}")
            key = (question_id, reference_id)
            if key in seen:
                raise AssessorPacketError(
                    f"Duplicate blinded pool identity: {question_id}/{reference_id}"
                )
            seen.add(key)
            rows.append(row)
    if not rows:
        raise AssessorPacketError("Blinded pool contains no rows")
    return rows


def _order_key(seed: str, assessor_id: str, question_id: str, reference_id: str) -> str:
    return sha256(
        f"{seed}|{assessor_id}|{question_id}|{reference_id}".encode("utf-8")
    ).hexdigest()


def build_packet(
    rows: list[dict[str, str]],
    assessor_id: str,
    *,
    seed: str = DEFAULT_PACKET_SEED,
) -> list[dict[str, Any]]:
    assessor_id = _clean(assessor_id)
    if not assessor_id:
        raise AssessorPacketError("assessor_id cannot be blank")
    by_question: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_question.setdefault(row["question_id"], []).append(row)

    output: list[dict[str, Any]] = []
    for question_id in sorted(by_question):
        ordered = sorted(
            by_question[question_id],
            key=lambda row: _order_key(
                seed, assessor_id, question_id, row["reference_id"]
            ),
        )
        for assessor_order, row in enumerate(ordered, start=1):
            output.append(
                {
                    "question_id": question_id,
                    "pool_item_id": row.get("pool_item_id", ""),
                    "assessor_order": assessor_order,
                    "reference_id": row.get("reference_id", ""),
                    "title": row.get("title", ""),
                    "abstract": row.get("abstract", ""),
                    "journal": row.get("journal", ""),
                    "year": row.get("year", ""),
                    "doi": row.get("doi", ""),
                    "pmid": row.get("pmid", ""),
                    "pmcid": row.get("pmcid", ""),
                    "url": row.get("url", ""),
                    "assessor_id": assessor_id,
                    "relevance_grade": "",
                    "reason": "",
                    "decision_timestamp": "",
                    "blind_to_nutev": "true",
                    "notes": "",
                }
            )
    return output


def write_packet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create independently shuffled blinded assessment packets from a NutEV judgment pool."
    )
    parser.add_argument("--pool", required=True, type=Path)
    parser.add_argument("--assessor-id", action="append", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--seed", default=DEFAULT_PACKET_SEED)
    args = parser.parse_args()

    try:
        assessor_ids = tuple(dict.fromkeys(_clean(value) for value in args.assessor_id))
        if any(not value for value in assessor_ids):
            raise AssessorPacketError("assessor_id cannot be blank")
        if len(assessor_ids) < 2:
            raise AssessorPacketError(
                "Benchmark-grade preparation requires at least two assessor IDs"
            )
        pool_rows = load_blinded_pool(args.pool)
        outputs: list[dict[str, Any]] = []
        for assessor_id in assessor_ids:
            packet_rows = build_packet(pool_rows, assessor_id, seed=args.seed)
            filename = f"ASSESSOR_{_safe_filename(assessor_id)}.csv"
            output_path = args.output_dir / filename
            write_packet(output_path, packet_rows)
            outputs.append(
                {
                    "assessor_id": assessor_id,
                    "path": str(output_path),
                    "rows": len(packet_rows),
                    "sha256": sha256(output_path.read_bytes()).hexdigest(),
                }
            )
        manifest = {
            "packet_type": "BLINDED_INDEPENDENT_ASSESSMENT",
            "label_blind": True,
            "minimum_assessors_required": 2,
            "assessor_ids": list(assessor_ids),
            "independent_order_per_assessor": True,
            "packet_seed": args.seed,
            "pool_path": str(args.pool),
            "pool_sha256": sha256(args.pool.read_bytes()).hexdigest(),
            "pool_rows": len(pool_rows),
            "outputs": outputs,
            "forbidden_fields_checked": sorted(FORBIDDEN_LEAKAGE_COLUMNS),
            "scientific_boundary": (
                "Packets contain no system membership, ranking score, NutEV rank or taxonomy fields. "
                "Assessors must not receive the pool audit file or another assessor's decisions before locking initial judgments."
            ),
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except AssessorPacketError as exc:
        print(f"Assessor packet failure: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
