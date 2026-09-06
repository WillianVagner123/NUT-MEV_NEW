#!/usr/bin/env python3
"""Extract immutable human-review samples from an Article 1 PRESS delta run.

This tool copies technical PubMed samples only. It never creates human labels or scientific gate state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

FIELDS = [
    "record_id",
    "delta_id",
    "route",
    "route_purpose",
    "sample_index",
    "pmid",
    "doi",
    "title",
    "year",
    "journal",
    "url",
]

ROUTE_PURPOSE = {
    "B-NORM": "normative guidance, guidelines, consensus and statements",
    "C1-CARE-PROCESS": "nutrition care process, models, pathways, prescription and counselling structures",
    "C3-IMPLEMENTATION": "implementation, delivery, adoption and operationalization of nutrition-related models and practices",
    "C4-SOCIAL-CONTEXT": "social context, food environment, social support, commensality and family/shared meals linked to assessment/care/frameworks",
}

EXPECTED_DELTAS = ("D02", "D03", "D04", "D05")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized_sha256(path: Path) -> str:
    return _sha256(path.read_bytes().replace(b"\r\n", b"\n"))


def extract(run_path: Path, output_dir: Path) -> dict[str, Any]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("run_type") != "NUTEV_ARTICLE1_PRESS_DELTA_TECHNICAL_RUN":
        raise ValueError("unexpected run_type")
    if run.get("status") != "TECHNICAL_DELTA_RUN_COMPLETE_HUMAN_REVIEW_PENDING":
        raise ValueError("delta run is not in the expected technical-complete/human-pending state")
    run_sha = str(run.get("run_sha256", ""))
    if len(run_sha) != 64:
        raise ValueError("run_sha256 missing or invalid")

    tests = {str(item.get("id")): item for item in run.get("delta_tests", [])}
    if any(delta not in tests for delta in EXPECTED_DELTAS):
        raise ValueError("required delta tests D02-D05 are missing")

    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    total = 0
    for delta in EXPECTED_DELTAS:
        item = tests[delta]
        route = str(item.get("route", ""))
        incremental = item.get("incremental") or {}
        sample = incremental.get("sample")
        if not isinstance(sample, list) or len(sample) != 25:
            raise ValueError(f"{delta} incremental sample must contain exactly 25 records")
        if int(incremental.get("total_returned", -1)) != 25:
            raise ValueError(f"{delta} total_returned must equal 25")

        out_path = output_dir / f"HUMAN_REVIEW_SAMPLE_{delta}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for idx, record in enumerate(sample, 1):
                pmid = str(record.get("pmid", "")).strip()
                if not pmid:
                    raise ValueError(f"{delta} sample record {idx} has no PMID")
                writer.writerow(
                    {
                        "record_id": f"{delta}-PUBMED-{idx:02d}-{pmid}",
                        "delta_id": delta,
                        "route": route,
                        "route_purpose": ROUTE_PURPOSE.get(route, ""),
                        "sample_index": idx,
                        "pmid": pmid,
                        "doi": record.get("doi") or "",
                        "title": record.get("title") or "",
                        "year": record.get("year") or "",
                        "journal": record.get("journal") or "",
                        "url": record.get("url") or "",
                    }
                )
        files.append(
            {
                "path": out_path.name,
                "delta_id": delta,
                "records": 25,
                "sha256": _normalized_sha256(out_path),
            }
        )
        total += 25

    manifest = {
        "schema_version": 1,
        "record_type": "NUTEV_ARTICLE1_PRESS_HUMAN_REVIEW_SAMPLE_MANIFEST",
        "run_id": run.get("run_id"),
        "provider": run.get("provider"),
        "source_run_sha256": run_sha,
        "technical_status": run.get("status"),
        "record_count": total,
        "files": files,
        "guardrails": {
            "no_human_labels_present": True,
            "not_press_pass": True,
            "not_c4_decision": True,
            "not_gf10": True,
            "not_query_freeze": True,
            "not_formal_search": True,
            "not_prisma": True,
        },
    }
    manifest_path = output_dir / "HUMAN_REVIEW_SAMPLE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--expected-run-sha256")
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()
    result = extract(args.run, args.output_dir)
    if args.expected_run_sha256 and result["source_run_sha256"] != args.expected_run_sha256:
        raise SystemExit("source run SHA-256 does not match expected value")
    print(json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2, sort_keys=args.compact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
