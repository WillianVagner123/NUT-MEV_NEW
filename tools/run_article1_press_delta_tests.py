from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from nutev.science.article1_press import build_delta_tests, load_json, route_specs
from nutev.search.pubmed import PubMedClient


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "config" / "nutev" / "article1_query_draft_v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "project_output_reference" / "scientific" / "press" / "article1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    for row in rows[:limit]:
        sample.append(
            {
                "pmid": row.get("pmid") or None,
                "doi": row.get("doi") or None,
                "title": row.get("title") or None,
                "year": row.get("year") or None,
                "journal": row.get("journal") or None,
                "url": row.get("url") or None,
            }
        )
    return sample


def _run_query(
    client: PubMedClient,
    *,
    query: str | None,
    workstream: str,
    sample_size: int,
    checkpoint_dir: Path,
    resume: bool,
) -> dict[str, Any] | None:
    if query is None:
        return None
    result = client.search(
        query,
        limit=sample_size,
        context={
            "workstream": workstream,
            "checkpoint_dir": checkpoint_dir,
            "resume": resume,
        },
    )
    return {
        "provider": result.provider,
        "status": result.status,
        "error": result.error,
        "total_found": result.total_found,
        "total_returned": result.total_returned,
        "checkpoint_path": result.checkpoint_path,
        "sample": _sample_rows(result.rows or [], sample_size),
    }


def _technical_status(records: list[dict[str, Any]]) -> str:
    statuses = {
        str(run.get("status") or "")
        for record in records
        for run in (record.get("baseline"), record.get("variant"), record.get("incremental"))
        if isinstance(run, dict)
    }
    if statuses and statuses <= {"completed", "empty"}:
        return "TECHNICAL_DELTA_RUN_COMPLETE_HUMAN_REVIEW_PENDING"
    if statuses & {"failed", "partial", "skipped"}:
        return "TECHNICAL_DELTA_RUN_INCOMPLETE"
    return "TECHNICAL_DELTA_RUN_EMPTY"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Execute the five preregistered Article 1 PRESS delta-test queries against PubMed as a technical run. "
            "Results never approve PRESS, authorize GF-10, freeze queries, create eligibility decisions, or emit PRISMA."
        )
    )
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--provider", choices=("pubmed",), default="pubmed")
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--checkpoint-dir", type=Path, default=ROOT / "07_logs" / "checkpoints")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required for network execution. Without this flag only the exact planned queries are emitted.",
    )
    args = parser.parse_args()

    if args.sample_size < 1 or args.sample_size > 200:
        raise SystemExit("--sample-size must be between 1 and 200")

    draft = load_json(args.draft)
    specs = route_specs(draft)
    tests = build_delta_tests(args.provider, specs)
    run_id = "article1_press_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not args.execute:
        payload = {
            "schema_version": 1,
            "run_type": "NUTEV_ARTICLE1_PRESS_DELTA_PLAN",
            "run_id": run_id,
            "provider": args.provider,
            "status": "PLAN_ONLY_NOT_EXECUTED",
            "draft_version": draft.get("draft_version"),
            "delta_tests": tests,
            "guardrails": {
                "press_status_changed": False,
                "gf10_authorized": False,
                "query_freeze_performed": False,
                "formal_search_performed": False,
                "prisma_event_emitted": False,
                "human_interpretation_required": True,
            },
        }
    else:
        client = PubMedClient()
        records: list[dict[str, Any]] = []
        for item in tests:
            test_id = item["id"]
            records.append(
                {
                    "id": test_id,
                    "route": item["route"],
                    "comparison": item["comparison"],
                    "queries": {
                        "baseline": item.get("baseline_query"),
                        "variant": item.get("variant_query"),
                        "incremental": item.get("incremental_query"),
                    },
                    "baseline": _run_query(
                        client,
                        query=item.get("baseline_query"),
                        workstream=f"article1_press_{test_id}_baseline",
                        sample_size=args.sample_size,
                        checkpoint_dir=args.checkpoint_dir,
                        resume=args.resume,
                    ),
                    "variant": _run_query(
                        client,
                        query=item.get("variant_query"),
                        workstream=f"article1_press_{test_id}_variant",
                        sample_size=args.sample_size,
                        checkpoint_dir=args.checkpoint_dir,
                        resume=args.resume,
                    ),
                    "incremental": _run_query(
                        client,
                        query=item.get("incremental_query"),
                        workstream=f"article1_press_{test_id}_incremental",
                        sample_size=args.sample_size,
                        checkpoint_dir=args.checkpoint_dir,
                        resume=args.resume,
                    ),
                    "manual_precision": None,
                    "human_interpretation": None,
                    "human_interpretation_required": True,
                }
            )
        payload = {
            "schema_version": 1,
            "run_type": "NUTEV_ARTICLE1_PRESS_DELTA_TECHNICAL_RUN",
            "run_id": run_id,
            "created_at": _now(),
            "provider": args.provider,
            "draft_version": draft.get("draft_version"),
            "status": _technical_status(records),
            "sample_size": args.sample_size,
            "delta_tests": records,
            "guardrails": {
                "technical_run_is_not_press_pass": True,
                "press_status_changed": False,
                "gf10_authorized": False,
                "query_freeze_performed": False,
                "formal_search_performed": False,
                "prisma_event_emitted": False,
                "eligibility_decisions_created": False,
                "human_interpretation_required": True,
            },
        }

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["run_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    output = args.output
    if args.execute and output is None:
        output = DEFAULT_OUTPUT_ROOT / run_id / "DELTA_TEST_RUN.json"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(str(output))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
