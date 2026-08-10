"""Canonical package version for the nutev-nutmev distribution.

This is the single source of truth for the current source-tree package version.
`pyproject.toml` reads `__version__` from this file (see `[tool.pdm] version`).

Published releases/tags are immutable. Release metadata, Git tag,
CITATION.cff, Zenodo metadata and release notes must describe the same exact
release identity before publication.
"""

__version__ = "0.3.0"
