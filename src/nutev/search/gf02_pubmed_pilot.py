"""Compatibility facade for the current GF-02 B-NORM-PUBMED v0.4 PILOT.

The public import path is kept stable while the implementation lives in
``gf02_pubmed_v04``. This module remains PILOT-only and does not authorize
FORMAL/PRISMA execution.
"""

from nutev.search.gf02_pubmed_v04 import (
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
