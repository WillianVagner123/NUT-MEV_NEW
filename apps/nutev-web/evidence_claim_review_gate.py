from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from evidence_claim_review import (
    DEFAULT_OUTPUT_ROOT,
    SynthesisGovernanceError,
    _evidence_record_index,
    _load_candidate,
    _validate_candidate_current,
    decide_claim_candidate as _decide_claim_candidate_after_referential_gate,
)


def decide_claim_candidate(
    payload: Mapping[str, Any], *, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> dict[str, Any]:
    """Apply the referential-integrity gate before an ACCEPT review can be persisted.

    REVISE and REJECT remain valid without a materialized EvidenceRecord because they
    create no canonical EvidenceClaim. ACCEPT must resolve the candidate against the
    current publication context and an actual `evidence_records.jsonl` row before the
    underlying service writes a human validation record.
    """

    decision = str(payload.get("decision") or "").strip().upper()
    if decision != "ACCEPT":
        return _decide_claim_candidate_after_referential_gate(
            payload, output_root=output_root
        )

    candidate_id = str(payload.get("candidate_id") or "").strip()
    candidate, _ = _load_candidate(candidate_id, output_root=output_root)
    _validate_candidate_current(candidate, output_root=output_root)
    evidence_record_id = str(candidate.get("evidence_record_id") or "")
    evidence_record = _evidence_record_index(output_root).get(evidence_record_id)
    snapshot = candidate.get("source_snapshot")
    document_id = (
        str(snapshot.get("document_id") or "").strip()
        if isinstance(snapshot, Mapping)
        else ""
    )
    if not evidence_record or str(evidence_record.get("document_id") or "") != document_id:
        raise SynthesisGovernanceError(
            "EvidenceRecord correspondente não foi localizado; materialize/atualize "
            "evidence_records.jsonl antes de ACCEPT"
        )

    return _decide_claim_candidate_after_referential_gate(
        payload, output_root=output_root
    )
