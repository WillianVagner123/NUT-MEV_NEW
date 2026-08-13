"""Pure UI adapter for safe global-search previews.

This layer converts validation exceptions into displayable messages. It does not
change search semantics, strategy state, GF-02 evidence, or provider execution.
"""
from __future__ import annotations

from typing import Any

from nutev.search.strategy_builder import (
    FILTER_SUPPORT,
    build_all,
    parse_strategy,
    unified_from_text,
)

_FILTER_LABELS = {
    "year": "ano",
    "language": "idioma",
    "publication_type": "tipo de publicação",
}


def provider_filter_warnings(spec: dict[str, Any]) -> list[str]:
    """Describe requested filters that each provider cannot render in `specific`."""
    requested = {
        "year": bool(spec.get("year_from") is not None or spec.get("year_to") is not None),
        "language": bool(spec.get("languages")),
        "publication_type": bool(spec.get("publication_types")),
    }
    warnings: list[str] = []
    for provider, support in FILTER_SUPPORT.items():
        unsupported = [
            _FILTER_LABELS[name]
            for name, active in requested.items()
            if active and not bool(support.get(name))
        ]
        if unsupported:
            warnings.append(
                f"{provider}: filtro(s) não aplicados em specific: {', '.join(unsupported)}."
            )
    return warnings


def prepare_search_strategy_preview(
    query_text: object,
    *,
    year_from: object = None,
    year_to: object = None,
    languages: object = "",
    publication_types: object = "",
) -> dict[str, Any]:
    """Return a safe preview payload instead of leaking `ValueError` to the UI."""
    try:
        spec = unified_from_text(
            query_text,
            year_from=year_from,
            year_to=year_to,
            languages=languages,
            publication_types=publication_types,
        )
        if not spec:
            return {"spec": {}, "grid": {}, "warnings": [], "error": ""}
        grid = build_all(parse_strategy(spec))
    except ValueError as exc:
        return {"spec": {}, "grid": {}, "warnings": [], "error": str(exc)}
    return {
        "spec": spec,
        "grid": grid,
        "warnings": provider_filter_warnings(spec),
        "error": "",
    }


__all__ = ["prepare_search_strategy_preview", "provider_filter_warnings"]
