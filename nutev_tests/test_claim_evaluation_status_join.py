from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
TESTS = ROOT / "nutev_tests"
for path in (WEB, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from claim_evaluation_appraisal import finalize_claim_evaluation, stage_claim_evaluation  # noqa: E402
from evidence_claim_review import _claim_root  # noqa: E402
from evidence_claim_review_gate import decide_claim_candidate  # noqa: E402
from governed_synthesis_release import release_status  # noqa: E402
from test_claim_evaluation_appraisal import _finalize_payload  # noqa: E402
from test_evidence_claim_review import (  # noqa: E402
    _accept_payload,
    _candidate,
    _stage,
    _write_evidence_records,
    _write_search_state,
)


def test_finalized_appraisal_is_joined_without_rewriting_canonical_claim(tmp_path: Path) -> None:
    _write_search_state(tmp_path)
    claim_status = _stage(tmp_path)
    _write_evidence_records(tmp_path)
    source_candidate_id = _candidate(claim_status)["candidate_id"]
    accepted = decide_claim_candidate(_accept_payload(source_candidate_id), output_root=tmp_path)
    claim_id = str(accepted["accepted_claims"][0]["claim_id"])

    claim_path = _claim_root(tmp_path) / "accepted" / f"{claim_id}.json"
    original_claim_bytes = claim_path.read_bytes()
    original_claim = json.loads(original_claim_bytes)
    assert original_claim["guardrails"]["claim_evaluation_created"] is False

    staged = stage_claim_evaluation(
        {"claim_id": claim_id, "staged_by": "Appraisal Coordinator"}, output_root=tmp_path
    )
    evaluation_candidate_id = staged["candidates"][0]["candidate_id"]
    finalized = finalize_claim_evaluation(
        _finalize_payload(evaluation_candidate_id), output_root=tmp_path
    )
    evaluation_id = str(finalized["finalized_evaluations"][0]["evaluation_id"])

    assert claim_path.read_bytes() == original_claim_bytes
    persisted_claim = json.loads(claim_path.read_text(encoding="utf-8"))
    assert persisted_claim["guardrails"]["claim_evaluation_created"] is False
    assert persisted_claim["content_sha256"] == original_claim["content_sha256"]

    status = release_status(output_root=tmp_path)
    joined_claim = next(
        item for item in status["accepted_evidence_claims"] if item["claim_id"] == claim_id
    )
    assert joined_claim["claim_evaluation_created"] is False
    assert joined_claim["claim_evaluation_finalized"] is True
    assert joined_claim["claim_evaluation_id"] == evaluation_id


def test_claim_ui_reads_downstream_join_instead_of_relabeling_original_guardrail() -> None:
    script = (WEB / "evidence-claims.js").read_text(encoding="utf-8")
    release = (WEB / "governed_synthesis_release.py").read_text(encoding="utf-8")

    assert "claim_evaluation_finalized" in script
    assert "claim_evaluation_id" in script
    assert "Downstream ClaimEvaluation" in script
    assert "claim.claim_evaluation_created?'created':'NOT CREATED'" not in script
    assert '"claim_evaluation_finalized": finalized is not None' in release
    assert '"claim_evaluation_id": finalized.get("evaluation_id") if finalized else None' in release
