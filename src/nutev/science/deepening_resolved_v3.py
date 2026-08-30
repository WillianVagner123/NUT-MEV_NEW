"""Resolver-v3 wrapper for selective bank deepening.

Version 3 keeps the validated resolver-v2 pipeline intact and changes only the
candidate handed to enrichment: public candidates are lightweight-probed in
order and the first reachable candidate is selected. The wrapper is versioned so
older v2 checkpoints are reprocessed once and then resume normally.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Mapping

from nutev.reference_identity import canonical_identity
from nutev.science.full_text_probe import select_reachable_candidate
from nutev.science.full_text_resolver import resolve_full_text_candidates
import nutev.science.deepening_resolved as v2


DEEPENING_PIPELINE_VERSION = "oa_resolver_v3_fallback_probe"
_PATCH_LOCK = Lock()


def _resolved_asset_row_v3(
    row: Mapping[str, Any],
    *,
    allow_network: bool,
) -> dict[str, Any] | None:
    document_id = canonical_identity(dict(row))
    if not document_id:
        raise v2.BankDeepeningError("selected bank row has no canonical document identity")

    candidates = resolve_full_text_candidates(
        row,
        include_network_resolvers=allow_network,
    )
    if not candidates:
        return None

    selected, probe_attempts = select_reachable_candidate(
        candidates,
        allow_network=allow_network,
    )
    if selected is None:
        return None

    payload: dict[str, Any] = {
        "document_id": document_id,
        "url": selected["url"],
        "scope": selected.get("scope") or "partial",
        "resolver_route": selected.get("resolver_route"),
        "resolver_source": selected.get("resolver_source"),
        "resolver_candidate_count": len(candidates),
        "resolver_candidates": candidates,
        "resolver_probe_attempts": probe_attempts,
        "resolver_probe_attempt_count": len(probe_attempts),
        "resolver_probe_selected": bool(selected.get("probe_selected")),
        "resolver_probe_selected_attempt": selected.get("probe_selected_attempt"),
        "resolver_probe_variant": selected.get("probe_variant"),
    }
    if selected.get("media_type"):
        payload["media_type"] = selected["media_type"]
    if selected.get("license"):
        payload["license"] = selected["license"]
    if selected.get("version"):
        payload["version"] = selected["version"]
    return payload


def run_selective_bank_deepening_resolved_v3(
    search_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run resolver-v2 stages with a versioned probe/fallback selection policy."""

    # The validated v2 orchestration resolves these globals at runtime. Patching is
    # limited to this single-process critical section so we do not duplicate the
    # scientific pipeline or fork its provenance semantics.
    with _PATCH_LOCK:
        previous_version = v2.DEEPENING_PIPELINE_VERSION
        previous_asset_builder = v2._resolved_asset_row
        try:
            v2.DEEPENING_PIPELINE_VERSION = DEEPENING_PIPELINE_VERSION
            v2._resolved_asset_row = _resolved_asset_row_v3
            result = v2.run_selective_bank_deepening_resolved(search_id, **kwargs)
        finally:
            v2.DEEPENING_PIPELINE_VERSION = previous_version
            v2._resolved_asset_row = previous_asset_builder

    result = dict(result)
    result["pipeline_version"] = DEEPENING_PIPELINE_VERSION
    result["retrieval_policy"] = "public_candidate_probe_then_sequential_fallback"
    return result
