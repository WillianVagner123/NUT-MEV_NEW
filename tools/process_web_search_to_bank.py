#!/usr/bin/env python3
"""Process a persisted NutEV web search into the low-token scientific bank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nutev.science.search_bank import latest_search_id, run_search_bank_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a persisted NutEV web-search run into Scientific Export -> "
            "abstract-only enrichment -> CORE -> semantic -> excerpts -> Workbench. "
            "No network full-text retrieval and no external LLM calls are performed."
        )
    )
    parser.add_argument(
        "--search-id",
        default=None,
        help="Persisted web search ID. Default: most recent completed run.",
    )
    parser.add_argument(
        "--output-root",
        default="project_output_reference",
        help="NutEV persistent output root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    search_id = args.search_id or latest_search_id(output_root.resolve())

    def progress(event: dict[str, object]) -> None:
        print(json.dumps({"progress": event}, ensure_ascii=False), flush=True)

    result = run_search_bank_pipeline(
        search_id,
        output_root=output_root,
        on_progress=progress,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
