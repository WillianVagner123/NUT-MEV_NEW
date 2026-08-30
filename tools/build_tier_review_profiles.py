#!/usr/bin/env python3
"""Build deterministic reviewer-navigation profiles for one NutEV bank tier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nutev.science.review_profiles import build_tier_review_profiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an audited deterministic review profile for a bank tier and attach it "
            "atomically to the Article Workbench. This is reviewer navigation only; it does "
            "not emit eligibility, quality, risk-of-bias, certainty, recommendation, or PRISMA decisions."
        )
    )
    parser.add_argument("--search-id", required=True)
    parser.add_argument("--output-root", default="project_output_reference")
    parser.add_argument("--tier", choices=["A", "B", "C", "D"], default="A")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_tier_review_profiles(
        args.search_id,
        output_root=Path(args.output_root),
        tier=args.tier,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
