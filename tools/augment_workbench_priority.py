#!/usr/bin/env python3
"""Attach the saved Bank NutEV priority ranking to an existing Workbench."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nutev.science.search_bank import latest_search_id
from nutev.science.workbench_priority import augment_workbench_priority


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Attach reference rank, score and operational A/B/C/D tier to an already-built "
            "Article Workbench without rerunning CORE/semantic/excerpts."
        )
    )
    parser.add_argument("--search-id", default=None)
    parser.add_argument("--output-root", default="project_output_reference")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    search_id = args.search_id or latest_search_id(output_root.resolve())
    result = augment_workbench_priority(search_id, output_root=output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
