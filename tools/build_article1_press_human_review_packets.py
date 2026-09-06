#!/usr/bin/env python3
"""Build deterministic, independent human-review packets for Article 1 PRESS delta samples.

This tool creates review templates only. It never writes scientific gate state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

REVIEW_FIELDS = [
    "packet_position",
    "record_id",
    "delta_id",
    "route",
    "route_purpose",
    "pmid",
    "doi",
    "title",
    "year",
    "journal",
    "url",
    "decision_Y_N_U",
    "reason",
    "reviewer_id",
    "reviewed_at",
]

ADJUDICATION_FIELDS = [
    "record_id",
    "delta_id",
    "route",
    "pmid",
    "title",
    "reviewer_A_decision",
    "reviewer_B_decision",
    "adjudicated_decision",
    "adjudication_reason",
    "adjudicator",
    "adjudicated_at",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized_text_sha256(path: Path) -> str:
    """Hash text artifacts after normalizing CRLF to LF for cross-platform checkout stability."""
    return _sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _record_ids_sha256(records: list[dict[str, Any]]) -> str:
    payload = "\n".join(sorted(str(r["record_id"]) for r in records)).encode("utf-8")
    return _sha256_bytes(payload)


def _load_sample(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    record_type = data.get("record_type")
    if record_type == "NUTEV_ARTICLE1_PRESS_HUMAN_REVIEW_SAMPLE_MANIFEST":
        records: list[dict[str, Any]] = []
        for item in data.get("files", []):
            csv_path = path.parent / str(item["path"])
            actual_sha = _normalized_text_sha256(csv_path)
            if actual_sha != item.get("sha256"):
                raise ValueError(f"sample file hash mismatch: {csv_path.name}")
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            records.extend(rows)
        data = dict(data)
        data["records"] = records
    elif record_type != "NUTEV_ARTICLE1_PRESS_HUMAN_REVIEW_SAMPLE":
        raise ValueError("unexpected sample record_type")

    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("sample records must be a non-empty list")
    ids = [str(r.get("record_id", "")).strip() for r in records]
    if "" in ids or len(ids) != len(set(ids)):
        raise ValueError("sample record_id values must be unique and non-empty")
    for r in records:
        if "decision" in r or "human_decision" in r or "label" in r:
            raise ValueError("sample must not contain human decision labels")
    return data


def _write_reviewer(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for position, r in enumerate(records, 1):
            writer.writerow(
                {
                    "packet_position": position,
                    "record_id": r["record_id"],
                    "delta_id": r["delta_id"],
                    "route": r["route"],
                    "route_purpose": r.get("route_purpose", ""),
                    "pmid": r.get("pmid", ""),
                    "doi": r.get("doi", "") or "",
                    "title": r.get("title", ""),
                    "year": r.get("year", ""),
                    "journal": r.get("journal", ""),
                    "url": r.get("url", "") or "",
                    "decision_Y_N_U": "",
                    "reason": "",
                    "reviewer_id": "",
                    "reviewed_at": "",
                }
            )


def _write_adjudication(path: Path, records: list[dict[str, Any]]) -> None:
    ordered = sorted(records, key=lambda r: (str(r["delta_id"]), int(r.get("sample_index", 0)), str(r["record_id"])))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ADJUDICATION_FIELDS)
        writer.writeheader()
        for r in ordered:
            writer.writerow(
                {
                    "record_id": r["record_id"],
                    "delta_id": r["delta_id"],
                    "route": r["route"],
                    "pmid": r.get("pmid", ""),
                    "title": r.get("title", ""),
                    "reviewer_A_decision": "",
                    "reviewer_B_decision": "",
                    "adjudicated_decision": "",
                    "adjudication_reason": "",
                    "adjudicator": "",
                    "adjudicated_at": "",
                }
            )


def build_packets(sample_path: Path, output_dir: Path) -> dict[str, Any]:
    sample = _load_sample(sample_path)
    records = list(sample["records"])
    run_sha = str(sample.get("source_run_sha256", ""))
    if len(run_sha) < 32:
        raise ValueError("source_run_sha256 missing or invalid")

    seed_a = int(run_sha[:16], 16)
    seed_b = int(run_sha[16:32], 16)
    rows_a = records.copy()
    rows_b = records.copy()
    random.Random(seed_a).shuffle(rows_a)
    random.Random(seed_b).shuffle(rows_b)
    if len(records) > 1 and [r["record_id"] for r in rows_a] == [r["record_id"] for r in rows_b]:
        # Extremely small fixtures can collide by chance even with different seeds.
        # Preserve deterministic independence by rotating reviewer B one position.
        rows_b = rows_b[1:] + rows_b[:1]

    output_dir.mkdir(parents=True, exist_ok=True)
    path_a = output_dir / "REVIEWER_A.csv"
    path_b = output_dir / "REVIEWER_B.csv"
    path_adj = output_dir / "ADJUDICATION_TEMPLATE.csv"
    _write_reviewer(path_a, rows_a)
    _write_reviewer(path_b, rows_b)
    _write_adjudication(path_adj, records)

    delta_counts = Counter(str(r["delta_id"]) for r in records)
    manifest = {
        "schema_version": 1,
        "record_type": "NUTEV_ARTICLE1_PRESS_HUMAN_REVIEW_PACKET_MANIFEST",
        "run_id": sample.get("run_id"),
        "provider": sample.get("provider"),
        "source_run_sha256": run_sha,
        "source_sample_sha256": _sha256_bytes(sample_path.read_bytes()),
        "record_count": len(records),
        "record_ids_sha256": _record_ids_sha256(records),
        "delta_record_counts": dict(sorted(delta_counts.items())),
        "randomization": {
            "reviewer_A_seed": seed_a,
            "reviewer_B_seed": seed_b,
            "same_records_different_order": True,
        },
        "labels": {
            "Y": "relevant to Article 1 question / route purpose",
            "N": "not relevant",
            "U": "uncertain; requires abstract/full-text inspection",
        },
        "files": {},
        "guardrails": {
            "reviewer_decisions_blank": True,
            "model_labels_used_for_official_precision": False,
            "press_pass_created": False,
            "c4_decision_created": False,
            "gf10_authorized": False,
            "query_freeze_created": False,
            "formal_search_created": False,
            "prisma_event_created": False,
        },
    }
    for path in (path_a, path_b, path_adj):
        manifest["files"][path.name] = {
            "sha256": _sha256_bytes(path.read_bytes()),
            "bytes": path.stat().st_size,
        }
    manifest_path = output_dir / "REVIEW_PACKET_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    result = build_packets(args.sample, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2, sort_keys=args.compact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
