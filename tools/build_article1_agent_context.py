#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.science.article1_agent_context import build_article1_agent_context


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the verified, rank-blind Article 1 AI/agent context bundle."
    )
    parser.add_argument("--search-id", default=None)
    parser.add_argument("--output-root", type=Path, default=Path("project_output_reference"))
    args = parser.parse_args()

    result = build_article1_agent_context(
        args.search_id,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
