#!/usr/bin/env python3
"""Validate independent human review of Article 1 PRESS delta samples.

Fail-closed by design: this tool never updates PRESS/GF-10/freeze/formal-search state.
It only validates human review packets and emits a derived review summary.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ALLOWED = {"", "Y", "N", "U"}
FINAL_ALLOWED = {"Y", "N"}


def _record_ids_sha256(ids: set[str]) -> str:
    payload = "\n".join(sorted(ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("record_count", 0) <= 0:
        raise ValueError("manifest record_count must be positive")
    return data


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _parse_timestamp(value: str, field: str) -> None:
    if not value:
        raise ValueError(f"{field} is required")
    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601: {value}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must include timezone: {value}")


def _validate_reviewer(rows: list[dict[str, str]], label: str, expected_ids: set[str]) -> dict[str, Any]:
    ids = [r.get("record_id", "").strip() for r in rows]
    if len(ids) != len(expected_ids) or set(ids) != expected_ids or len(set(ids)) != len(ids):
        raise ValueError(f"Reviewer {label}: record set mismatch or duplicates")

    per_delta: dict[str, Counter[str]] = defaultdict(Counter)
    reviewer_ids: set[str] = set()
    for r in rows:
        decision = r.get("decision_Y_N_U", "").strip().upper()
        if decision not in ALLOWED:
            raise ValueError(f"Reviewer {label}: invalid decision {decision!r} for {r.get('record_id')}")
        delta = r.get("delta_id", "").strip()
        per_delta[delta][decision or "BLANK"] += 1
        if decision:
            reason = r.get("reason", "").strip()
            reviewer_id = r.get("reviewer_id", "").strip()
            reviewed_at = r.get("reviewed_at", "").strip()
            if not reason:
                raise ValueError(f"Reviewer {label}: reason required for {r.get('record_id')}")
            if not reviewer_id:
                raise ValueError(f"Reviewer {label}: reviewer_id required for {r.get('record_id')}")
            _parse_timestamp(reviewed_at, f"Reviewer {label} reviewed_at")
            reviewer_ids.add(reviewer_id)
    if len(reviewer_ids) > 1:
        raise ValueError(f"Reviewer {label}: multiple reviewer identities found")

    summary: dict[str, Any] = {}
    for delta, counts in sorted(per_delta.items()):
        y = counts["Y"]
        n = counts["N"]
        u = counts["U"]
        blank = counts["BLANK"]
        precision = None if (u or blank or y + n == 0) else y / (y + n)
        summary[delta] = {"Y": y, "N": n, "U": u, "blank": blank, "precision": precision}
    return {
        "reviewer_id": next(iter(reviewer_ids), None),
        "complete": all(v["blank"] == 0 for v in summary.values()),
        "resolved": all(v["blank"] == 0 and v["U"] == 0 for v in summary.values()),
        "per_delta": summary,
        "decisions": {r["record_id"].strip(): r.get("decision_Y_N_U", "").strip().upper() for r in rows},
    }


def _read_adjudication(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    rows = _read_csv(path)
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        rid = r.get("record_id", "").strip()
        if not rid:
            continue
        if rid in out:
            raise ValueError(f"Adjudication duplicate record_id: {rid}")
        out[rid] = r
    return out


def validate(manifest_path: Path, reviewer_a_path: Path, reviewer_b_path: Path, adjudication_path: Path | None = None) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    rows_a = _read_csv(reviewer_a_path)
    rows_b = _read_csv(reviewer_b_path)
    expected_ids = {r.get("record_id", "").strip() for r in rows_a}
    if "" in expected_ids:
        raise ValueError("Reviewer A contains blank record_id")
    if len(expected_ids) != manifest["record_count"]:
        raise ValueError("Reviewer A record_count does not match manifest")
    expected_hash = manifest.get("record_ids_sha256")
    if expected_hash and _record_ids_sha256(expected_ids) != expected_hash:
        raise ValueError("Reviewer record IDs do not match manifest hash")
    expected_delta_counts = manifest.get("delta_record_counts", {})
    actual_delta_counts = Counter(r.get("delta_id", "").strip() for r in rows_a)
    if expected_delta_counts and dict(actual_delta_counts) != expected_delta_counts:
        raise ValueError("Reviewer A delta counts do not match manifest")

    a = _validate_reviewer(rows_a, "A", expected_ids)
    b = _validate_reviewer(rows_b, "B", expected_ids)

    conflicts: list[str] = []
    for rid in sorted(expected_ids):
        da, db = a["decisions"][rid], b["decisions"][rid]
        if da and db and da != db:
            conflicts.append(rid)

    status = "PENDING_REVIEW"
    final_decisions: dict[str, str] = {}
    errors: list[str] = []
    if a["complete"] and b["complete"]:
        if not a["resolved"] or not b["resolved"]:
            status = "HUMAN_REVIEW_HAS_UNRESOLVED_U"
        elif not a["reviewer_id"] or not b["reviewer_id"]:
            status = "HUMAN_REVIEW_IDENTITY_MISSING"
        elif a["reviewer_id"] == b["reviewer_id"]:
            status = "REVIEWER_INDEPENDENCE_VIOLATION"
            errors.append("Reviewer A and Reviewer B must be different human identities")
        elif conflicts:
            status = "READY_FOR_ADJUDICATION"
        else:
            status = "HUMAN_DELTA_REVIEW_COMPLETE"
            final_decisions = dict(a["decisions"])

    adjudication = _read_adjudication(adjudication_path)
    if status == "READY_FOR_ADJUDICATION" and adjudication_path is not None:
        unresolved: list[str] = []
        final_decisions = {}
        for rid in sorted(expected_ids):
            da, db = a["decisions"][rid], b["decisions"][rid]
            if da == db:
                final_decisions[rid] = da
                continue
            row = adjudication.get(rid)
            if not row:
                unresolved.append(rid)
                continue
            decision = row.get("adjudicated_decision", "").strip().upper()
            if decision not in FINAL_ALLOWED:
                unresolved.append(rid)
                continue
            reason = row.get("adjudication_reason", "").strip()
            adjudicator = row.get("adjudicator", "").strip()
            if not reason:
                raise ValueError(f"Adjudication reason required for {rid}")
            if not adjudicator:
                raise ValueError(f"Adjudication adjudicator required for {rid}")
            _parse_timestamp(row.get("adjudicated_at", "").strip(), "adjudicated_at")
            final_decisions[rid] = decision
        if unresolved:
            status = "ADJUDICATION_INCOMPLETE"
            final_decisions = {}
        else:
            status = "HUMAN_DELTA_REVIEW_COMPLETE"

    final_per_delta: dict[str, Counter[str]] = defaultdict(Counter)
    delta_by_id = {r["record_id"].strip(): r["delta_id"].strip() for r in rows_a}
    if status == "HUMAN_DELTA_REVIEW_COMPLETE":
        for rid, decision in final_decisions.items():
            final_per_delta[delta_by_id[rid]][decision] += 1

    final_summary: dict[str, Any] = {}
    for delta in sorted(manifest.get("delta_record_counts", {})):
        counts = final_per_delta[delta]
        y, n = counts["Y"], counts["N"]
        final_summary[delta] = {
            "Y": y,
            "N": n,
            "precision": (y / (y + n)) if status == "HUMAN_DELTA_REVIEW_COMPLETE" and y + n else None,
        }

    return {
        "schema_version": 1,
        "run_id": manifest.get("run_id"),
        "source_run_sha256": manifest.get("source_run_sha256"),
        "status": status,
        "reviewer_A": {k: v for k, v in a.items() if k != "decisions"},
        "reviewer_B": {k: v for k, v in b.items() if k != "decisions"},
        "conflict_count": len(conflicts),
        "conflict_record_ids": conflicts,
        "final_per_delta": final_summary,
        "errors": errors,
        "guardrails": {
            "human_review_result_is_not_press_pass": True,
            "press_pass_created": False,
            "c4_decision_created": False,
            "gf10_authorized": False,
            "query_freeze_created": False,
            "formal_search_created": False,
            "prisma_event_created": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--reviewer-a", type=Path, required=True)
    ap.add_argument("--reviewer-b", type=Path, required=True)
    ap.add_argument("--adjudication", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--compact", action="store_true")
    args = ap.parse_args()
    result = validate(args.manifest, args.reviewer_a, args.reviewer_b, args.adjudication)
    text = json.dumps(result, ensure_ascii=False, indent=None if args.compact else 2, sort_keys=args.compact)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
