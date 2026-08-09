"""Canonical package version for the nutev-nutmev distribution.

This is the single source of truth for the *current source-tree package* version.
`pyproject.toml` reads `__version__` from this file (see `[tool.pdm] version`).

Published citation/archive metadata can intentionally remain on the latest
immutable public release while `main` carries a PEP 440 development version.
Before the next public release, the release checklist requires package, Git tag,
CITATION.cff, Zenodo metadata and release notes to be reconciled on one exact
release identity.
"""

__version__ = "0.3.0.dev0"
