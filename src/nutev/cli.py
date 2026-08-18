from __future__ import annotations

import argparse

from nutev.__version__ import __version__

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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "providers":
        for provider in PROVIDERS:
            print(provider)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
