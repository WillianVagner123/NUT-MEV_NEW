from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutev.__version__ import __version__
from nutev.science import (
    DocumentEnrichmentError,
    NutEVCoreError,
    RelationalMappingError,
    ScientificExportError,
    SemanticDeconstructionError,
    ScreeningImportError,
    run_core_bank_export,
    run_document_enrichment,
    run_relational_mapping,
    run_scientific_export,
    run_semantic_deconstruction,
    run_screening_import,
)

PROVIDERS = (
    "PubMed", "Europe PMC", "OpenAlex", "Crossref", "DOAJ",
    "Semantic Scholar", "LILACS/BVS", "SciELO", "Official web sources",
    "Google PSE (optional)", "Brave (optional)", "SerpAPI (optional)",
)


def _path_argument(parser: argparse.ArgumentParser, name: str, default: str, help_text: str | None = None) -> None:
    parser.add_argument(name, default=default, help=help_text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nutev",
        description="NutEV Reference Engine: multi-source reference discovery and ranking.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("providers", help="List supported reference providers.")

    p = sub.add_parser("science-export", help="Export audited ranking rows into traceable scientific-domain objects.")
    _path_argument(p, "--ranking-jsonl", "project_output_reference/reference_ranking/reference_ranking.jsonl")
    _path_argument(p, "--audit-manifest", "project_output_reference/reference_ranking/AUDIT_MANIFEST.json")
    _path_argument(p, "--output-dir", "project_output_reference/scientific")

    p = sub.add_parser("science-enrich", help="Retrieve/extract/OCR documents and build reviewer-safe dossiers before screening.")
    _path_argument(p, "--documents-jsonl", "project_output_reference/scientific/document_candidates.jsonl")
    _path_argument(p, "--science-manifest", "project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json")
    p.add_argument("--assets-jsonl", default=None, help="Optional JSONL mapping document_id to local path or full-text URL.")
    p.add_argument("--allow-network", action="store_true", help="Allow HTTP(S) retrieval when no local full-text asset is supplied.")
    _path_argument(p, "--output-dir", "project_output_reference/scientific/enrichment")

    p = sub.add_parser("science-core", help="Materialize the reusable NutEV CORE article record and local evidence bank.")
    _path_argument(p, "--documents-jsonl", "project_output_reference/scientific/document_candidates.jsonl")
    _path_argument(p, "--evidence-records-jsonl", "project_output_reference/scientific/evidence_records.jsonl")
    _path_argument(p, "--science-manifest", "project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json")
    _path_argument(p, "--artifacts-jsonl", "project_output_reference/scientific/enrichment/full_text_artifacts.jsonl")
    _path_argument(p, "--enrichments-jsonl", "project_output_reference/scientific/enrichment/document_enrichments.jsonl")
    _path_argument(p, "--dossiers-jsonl", "project_output_reference/scientific/enrichment/reviewer_dossiers.jsonl")
    _path_argument(p, "--enrichment-manifest", "project_output_reference/scientific/enrichment/ENRICHMENT_MANIFEST.json")
    p.add_argument("--mev-profile", default=None, help="Optional versioned JSON scoring profile; NutEV does not invent MEV weights.")
    _path_argument(p, "--output-dir", "project_output_reference/scientific/core")

    p = sub.add_parser("science-semantic", help="Deconstruct CORE articles into traceable semantic candidates.")
    _path_argument(p, "--core-records-jsonl", "project_output_reference/scientific/core/nutev_core_records.jsonl")
    _path_argument(p, "--core-manifest", "project_output_reference/scientific/core/CORE_MANIFEST.json")
    _path_argument(p, "--enrichments-jsonl", "project_output_reference/scientific/enrichment/document_enrichments.jsonl")
    _path_argument(p, "--enrichment-manifest", "project_output_reference/scientific/enrichment/ENRICHMENT_MANIFEST.json")
    _path_argument(p, "--output-dir", "project_output_reference/scientific/semantic")

    p = sub.add_parser("science-relations", help="Link semantic candidates into conservative scientific relations.")
    _path_argument(p, "--semantic-records-jsonl", "project_output_reference/scientific/semantic/nutev_core_records_semantic.jsonl")
    _path_argument(p, "--semantic-facts-jsonl", "project_output_reference/scientific/semantic/semantic_fact_candidates.jsonl")
    _path_argument(p, "--semantic-manifest", "project_output_reference/scientific/semantic/SEMANTIC_MANIFEST.json")
    _path_argument(p, "--output-dir", "project_output_reference/scientific/relations")

    p = sub.add_parser("science-screening", help="Import final resolved screening decisions and derive explicit PRISMA events.")
    _path_argument(p, "--documents-jsonl", "project_output_reference/scientific/document_candidates.jsonl")
    _path_argument(p, "--science-manifest", "project_output_reference/scientific/SCIENTIFIC_EXPORT_MANIFEST.json")
    _path_argument(p, "--dossiers-jsonl", "project_output_reference/scientific/enrichment/reviewer_dossiers.jsonl")
    _path_argument(p, "--enrichment-manifest", "project_output_reference/scientific/enrichment/ENRICHMENT_MANIFEST.json")
    p.add_argument("--allow-unenriched", action="store_true", help="Compatibility escape hatch for screening without verified enrichment.")
    _path_argument(p, "--decisions-jsonl", "project_output_reference/scientific/screening_decisions_input.jsonl")
    _path_argument(p, "--output-dir", "project_output_reference/scientific/screening")
    return parser


def _print(result: dict) -> int:
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "providers":
        for provider in PROVIDERS:
            print(provider)
        return 0
    if args.command == "science-export":
        try:
            return _print(run_scientific_export(Path(args.ranking_jsonl), Path(args.audit_manifest), Path(args.output_dir)))
        except ScientificExportError as exc:
            print(f"Scientific export failure: {exc}")
            return 2
    if args.command == "science-enrich":
        try:
            return _print(run_document_enrichment(
                Path(args.documents_jsonl), Path(args.science_manifest), Path(args.output_dir),
                assets_jsonl=Path(args.assets_jsonl) if args.assets_jsonl else None,
                allow_network=bool(args.allow_network),
            ))
        except DocumentEnrichmentError as exc:
            print(f"Scientific enrichment failure: {exc}")
            return 2
    if args.command == "science-core":
        try:
            return _print(run_core_bank_export(
                Path(args.documents_jsonl), Path(args.evidence_records_jsonl), Path(args.science_manifest),
                Path(args.artifacts_jsonl), Path(args.enrichments_jsonl), Path(args.dossiers_jsonl),
                Path(args.enrichment_manifest), Path(args.output_dir),
                mev_profile=Path(args.mev_profile) if args.mev_profile else None,
            ))
        except NutEVCoreError as exc:
            print(f"NutEV CORE failure: {exc}")
            return 2
    if args.command == "science-semantic":
        try:
            return _print(run_semantic_deconstruction(
                Path(args.core_records_jsonl), Path(args.core_manifest), Path(args.enrichments_jsonl),
                Path(args.enrichment_manifest), Path(args.output_dir),
            ))
        except SemanticDeconstructionError as exc:
            print(f"NutEV semantic deconstruction failure: {exc}")
            return 2
    if args.command == "science-relations":
        try:
            return _print(run_relational_mapping(
                Path(args.semantic_records_jsonl), Path(args.semantic_facts_jsonl),
                Path(args.semantic_manifest), Path(args.output_dir),
            ))
        except RelationalMappingError as exc:
            print(f"NutEV relational mapping failure: {exc}")
            return 2
    if args.command == "science-screening":
        require_enrichment = not bool(args.allow_unenriched)
        try:
            return _print(run_screening_import(
                Path(args.documents_jsonl), Path(args.science_manifest), Path(args.decisions_jsonl),
                Path(args.output_dir),
                dossiers_jsonl=Path(args.dossiers_jsonl) if require_enrichment else None,
                enrichment_manifest=Path(args.enrichment_manifest) if require_enrichment else None,
                require_enrichment=require_enrichment,
            ))
        except ScreeningImportError as exc:
            print(f"Scientific screening import failure: {exc}")
            return 2
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
