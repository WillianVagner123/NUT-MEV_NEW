from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.__version__ import __version__
from nutev.science import ScientificExportError, run_scientific_export

PROVIDERS = (
    "PubMed",
    "Europe PMC",
    "OpenAlex",
    "Crossref",
    "DOAJ",
    "Semantic Scholar",
    "LILACS/BVS",
    "SciELO",
    "Official web sources",
    "Google PSE (optional)",
    "Brave (optional)",
    "SerpAPI (optional)",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nutev",
        description="NutEV Reference Engine: multi-source reference discovery and ranking.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("providers", help="List supported reference providers.")

    science_export = subparsers.add_parser(
        "science-export",
        help="Export audited ranking rows into traceable scientific-domain objects.",
    )
    science_export.add_argument(
        "--ranking-jsonl",
        default="project_output_reference/reference_ranking/reference_ranking.jsonl",
    )
    science_export.add_argument(
        "--audit-manifest",
        default="project_output_reference/reference_ranking/AUDIT_MANIFEST.json",
    )
    science_export.add_argument(
        "--output-dir",
        default="project_output_reference/scientific",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "providers":
        for provider in PROVIDERS:
            print(provider)
        return 0
    if args.command == "science-export":
        try:
            result = run_scientific_export(
                Path(args.ranking_jsonl),
                Path(args.audit_manifest),
                Path(args.output_dir),
            )
        except ScientificExportError as exc:
            print(f"Scientific export failure: {exc}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
