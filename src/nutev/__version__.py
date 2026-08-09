"""Canonical version for the nutev-nutmev distribution.

This is the single source of truth for the package version. `pyproject.toml`
reads `__version__` from this file (see `[tool.pdm] version`), decoupling the
NutEV/NutMEV core from the legacy `local_deep_research` version.
"""

__version__ = "0.2.0"
