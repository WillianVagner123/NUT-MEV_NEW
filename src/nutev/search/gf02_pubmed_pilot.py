"""Compatibility facade for the current optimized GF-02 B-NORM-PUBMED PILOT.

The public import path remains stable. Operational execution uses a count-first
plan: required PubMed lines are counted with ESearch ``retmax=0`` and only the
10-20 rescue-only records needed for human review are downloaded. This module
is PILOT-only and never authorizes FORMAL/PRISMA execution.
"""

from nutev.search.gf02_pubmed_optimized import (
    load_candidate_config,
    load_sentinel_registry,
    resolved_line_expressions,
    run_gf02_pubmed_pilot,
)

__all__ = [
    "load_candidate_config",
    "load_sentinel_registry",
    "resolved_line_expressions",
    "run_gf02_pubmed_pilot",
]
