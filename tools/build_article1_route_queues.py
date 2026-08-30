#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.science.article1_routes import build_article1_route_queues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build rank-blind B-NORM and C-STRUCT human reading queues for Article 1."
    )
    parser.add_argument("--search-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("project_output_reference"),
    )
    parser.add_argument("--tier", default="A")
    args = parser.parse_args()

    result = build_article1_route_queues(
        args.search_id,
        output_root=args.output_root,
        tier=args.tier,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
