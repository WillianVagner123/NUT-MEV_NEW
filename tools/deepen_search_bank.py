#!/usr/bin/env python3
"""Deepen one NutEV bank tier in resumable full-text batches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nutev.science.deepening_resolved import run_selective_bank_deepening_resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Selectively deepen a persisted NutEV bank tier using public/open-access "
            "full-text resolution, text extraction/OCR, CORE, semantic extraction, "
            "excerpts, and an atomic Workbench overlay. No external LLM calls are performed."
        )
    )
    parser.add_argument("--search-id", required=True, help="Persisted NutEV bank search ID.")
    parser.add_argument("--output-root", default="project_output_reference")
    parser.add_argument("--tier", choices=["A", "B", "C", "D"], default="A")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum selected records for this invocation. 0 means all remaining selection.",
    )
    parser.add_argument("--start-rank", type=int, default=1)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help=(
            "Allow public/open-access resolver calls plus retrieval of selected document URLs. "
            "Without this flag, deepening is offline."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def progress(event: dict[str, object]) -> None:
        print(json.dumps({"progress": event}, ensure_ascii=False), flush=True)

    result = run_selective_bank_deepening_resolved(
        args.search_id,
        output_root=Path(args.output_root),
        tier=args.tier,
        batch_size=args.batch_size,
        limit=args.limit,
        start_rank=args.start_rank,
        allow_network=args.allow_network,
        on_progress=progress,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
