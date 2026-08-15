#!/usr/bin/env python
"""Run the current GF-02 B-NORM-PUBMED PILOT package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from nutev.search.gf02_pubmed_pilot import run_gf02_pubmed_pilot


def _progress(message: str) -> None:
    print(f"[GF-02] {message}", file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute the current GF-02 PubMed PILOT candidate; never writes FORMAL/PRISMA counts."
    )
    parser.add_argument("--project-root", default="project_output_scientific")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Compatibility ceiling for GF-02. Count-first execution does not download this many rows.",
    )
    parser.add_argument(
        "--noise-sample-size",
        type=int,
        default=20,
        help="Size of the current rescue-only human sample (10-20).",
    )
    parser.add_argument("--noise-seed", type=int, default=20260812)
    args = parser.parse_args()

    manifest = run_gf02_pubmed_pilot(
        Path(args.repo_root).resolve(),
        project_root=Path(args.project_root).resolve(),
        limit=args.limit,
        noise_sample_size=args.noise_sample_size,
        noise_seed=args.noise_seed,
        progress_fn=_progress,
    )
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "status": manifest["status"],
                "search_type": manifest["search_type"],
                "prisma_eligible": manifest["prisma_eligible"],
                "candidate_version": manifest["candidate_version"],
                "execution_plan": manifest.get("execution_plan"),
                "line_counts": manifest["line_counts"],
                "final_total_found": manifest["final_total_found"],
                "final_records_returned": manifest["final_records_returned"],
                "final_rows_capped": manifest["final_rows_capped"],
                "final_ncbi_query_translation": manifest["final_ncbi_query_translation"],
                "priority_sentinel_mechanism": manifest["priority_sentinel_mechanism"],
                "rescue_only_total_found": manifest["rescue_only"]["total_found"],
                "rescue_only_records_returned": manifest["rescue_only"]["records_returned"],
                "rescue_only_sample": manifest["rescue_only_sample"],
                "pubmed_advanced_search_details_required": manifest[
                    "pubmed_advanced_search_details_required"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["status"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
