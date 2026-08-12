#!/usr/bin/env python
"""Run the exact GF-02 PubMed v0.2/v0.3 PILOT candidates with audit artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.search.gf02_pubmed_pilot import run_gf02_pubmed_pilot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute exact GF-02 PubMed PILOT candidates; never writes FORMAL/PRISMA counts."
    )
    parser.add_argument("--project-root", default="project_output_scientific")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--noise-sample-size", type=int, default=20)
    parser.add_argument("--noise-seed", type=int, default=20260812)
    args = parser.parse_args()

    manifest = run_gf02_pubmed_pilot(
        Path(args.repo_root).resolve(),
        project_root=Path(args.project_root).resolve(),
        limit=args.limit,
        noise_sample_size=args.noise_sample_size,
        noise_seed=args.noise_seed,
    )
    print(json.dumps(
        {
            "run_id": manifest["run_id"],
            "status": manifest["status"],
            "prisma_eligible": manifest["prisma_eligible"],
            "v0.2_total": manifest["versions"]["v0.2"]["total_found"],
            "v0.3_total": manifest["versions"]["v0.3"]["total_found"],
            "priority_sentinel_comparison": manifest["priority_sentinel_comparison"],
            "noise_sample": manifest["noise_sample"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if manifest["status"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
