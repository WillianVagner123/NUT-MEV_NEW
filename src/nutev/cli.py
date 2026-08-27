from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.__version__ import __version__
from nutev.science import (
    DocumentEnrichmentError,
    ScientificExportError,
    ScreeningImportError,
    run_document_enrichment,
    run_scientific_export,
    run_screening_import,
)

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

    science_enrich = subparsers.add_parser(
        "science-enrich",
        help="Retrieve/extract/OCR documents and build reviewer-safe dossiers before screening.",
    )
    science_enrich.add_argument(
        "--documents-jsonl",
        default="project_output_reference/scientific/document_candidates.jsonl",
    )
    science_enrich.add_argument(
        "--science-manifest",
        default="project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json",
    )
    science_enrich.add_argument(
        "--assets-jsonl",
        default=None,
        help="Optional JSONL mapping document_id to local path or full-text URL.",
    )
    science_enrich.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow HTTP(S) retrieval when no local full-text asset is supplied.",
    )
    science_enrich.add_argument(
        "--output-dir",
        default="project_output_reference/scientific/enrichment",
    )

    science_screening = subparsers.add_parser(
        "science-screening",
        help="Import final resolved screening decisions and derive explicit PRISMA events.",
    )
    science_screening.add_argument(
        "--documents-jsonl",
        default="project_output_reference/scientific/document_candidates.jsonl",
    )
    science_screening.add_argument(
        "--science-manifest",
        default="project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json",
    )
    science_screening.add_argument(
        "--dossiers-jsonl",
        default="project_output_reference/scientific/enrichment/reviewer_dossiers.jsonl",
    )
    science_screening.add_argument(
        "--enrichment-manifest",
        default="project_output_reference/scientific/enrichment/ENRICHMENT_MANIFEST.json",
    )
    science_screening.add_argument(
        "--allow-unenriched",
        action="store_true",
        help="Compatibility escape hatch; allow screening import without verified enrichment dossiers.",
    )
    science_screening.add_argument(
        "--decisions-jsonl",
        default="project_output_reference/scientific/screening_decisions_input.jsonl",
    )
    science_screening.add_argument(
        "--output-dir",
        default="project_output_reference/scientific/screening",
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
    if args.command == "science-enrich":
        try:
            result = run_document_enrichment(
                Path(args.documents_jsonl),
                Path(args.science_manifest),
                Path(args.output_dir),
                assets_jsonl=Path(args.assets_jsonl) if args.assets_jsonl else None,
                allow_network=bool(args.allow_network),
            )
        except DocumentEnrichmentError as exc:
            print(f"Scientific enrichment failure: {exc}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "science-screening":
        require_enrichment = not bool(args.allow_unenriched)
        try:
            result = run_screening_import(
                Path(args.documents_jsonl),
                Path(args.science_manifest),
                Path(args.decisions_jsonl),
                Path(args.output_dir),
                dossiers_jsonl=(Path(args.dossiers_jsonl) if require_enrichment else None),
                enrichment_manifest=(
                    Path(args.enrichment_manifest) if require_enrichment else None
                ),
                require_enrichment=require_enrichment,
            )
        except ScreeningImportError as exc:
            print(f"Scientific screening import failure: {exc}")
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
