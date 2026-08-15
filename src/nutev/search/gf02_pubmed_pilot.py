"""Compatibility facade for the current GF-02 B-NORM-PUBMED PILOT.

The public import path remains stable while the implementation resolves the
current candidate from ``config/gf02_pubmed_candidates.json``. This module is
PILOT-only and never authorizes FORMAL/PRISMA execution.
"""

from nutev.search.gf02_pubmed_current import (
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
