from __future__ import annotations

import csv
import json
from pathlib import Path

from nutev.pipelines.article1_preflight import run_article1_preflight
from nutev.review.gf02_press_decision import record_gf02_press_decision
from nutev.search.gf02_gate_materialization import materialize_gf02_prepress_gate


def _sample(path: Path, *, rows: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_id", "classification", "reviewer", "note"],
        )
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                {
                    "sample_id": f"S{index + 1}",
                    "classification": "RELEVANT" if index == 0 else "IRRELEVANT",
                    "reviewer": "Human Reviewer",
                    "note": "reviewed",
                }
            )


def _manifest(project: Path, sample_path: Path, *, recover_second: bool = True) -> Path:
    run_dir = project / "07_logs" / "gf02" / "pubmed" / "gf02_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run_manifest.json"
    payload = {
        "schema_version": 5,
        "run_id": "gf02_test",
        "candidate_version": "v0.5",
        "status": "SUCCEEDED",
        "search_type": "PILOT",
        "prisma_eligible": False,
        "formal_execution_authorized": False,
        "final_line": "#7",
        "rescue_only_sample": str(sample_path),
        "priority_sentinel_mechanism": {
            "NORM-035": {"#7": True},
            "NORM-063": {"#7": recover_second},
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_missing_gate_is_materialized_from_completed_real_evidence(tmp_path: Path) -> None:
    repo = Path.cwd()
    project = tmp_path / "project"
    sample_path = project / "07_logs" / "gf02" / "pubmed" / "gf02_test" / "rescue_only_sample_v0_5.csv"
    _sample(sample_path)
    _manifest(project, sample_path)

    gate = materialize_gf02_prepress_gate(repo, project)
    gate_path = project / "07_logs" / "gf02" / "gate_status.json"

    assert gate_path.is_file()
    assert gate["gate"] == "GF-02"
    assert gate["evidence_complete"] is True
    assert gate["human_decision"] is None
    assert gate["sample_review_complete"] is True
    assert gate["sample_classification_counts"] == {"IRRELEVANT": 1, "RELEVANT": 1}
    assert gate["pubmed_sentinel_evidence"]["recovered_sentinel_ids"] == ["NORM-035", "NORM-063"]
    assert gate["press_approval_inferred"] is False
    assert gate["formal_execution_authorized"] is False
    assert gate["prisma_eligible"] is False

    saved = record_gf02_press_decision(
        gate_path,
        decision="READY_FOR_PRESS",
        decided_by="Human Reviewer",
        rationale="The reviewed PILOT evidence is sufficient to submit to PRESS.",
        decided_at="2026-08-16T00:20:00+00:00",
    )
    assert saved["human_decision"] == "READY_FOR_PRESS"


def test_materialized_gate_blocks_ready_when_priority_sentinel_is_missing(tmp_path: Path) -> None:
    repo = Path.cwd()
    project = tmp_path / "project"
    sample_path = project / "07_logs" / "gf02" / "pubmed" / "gf02_test" / "rescue_only_sample_v0_5.csv"
    _sample(sample_path)
    _manifest(project, sample_path, recover_second=False)

    gate = materialize_gf02_prepress_gate(repo, project)

    assert gate["evidence_complete"] is False
    assert "NORM-063:missing_without_explanation" in gate["blockers"]
    assert gate["human_decision"] is None


def test_changed_evidence_basis_clears_current_decision_but_keeps_history(tmp_path: Path) -> None:
    repo = Path.cwd()
    project = tmp_path / "project"
    sample_path = project / "07_logs" / "gf02" / "pubmed" / "gf02_test" / "rescue_only_sample_v0_5.csv"
    _sample(sample_path)
    _manifest(project, sample_path)
    materialize_gf02_prepress_gate(repo, project)
    gate_path = project / "07_logs" / "gf02" / "gate_status.json"
    record_gf02_press_decision(
        gate_path,
        decision="READY_FOR_PRESS",
        decided_by="Human Reviewer",
        rationale="First evidence basis was acceptable.",
        decided_at="2026-08-16T00:21:00+00:00",
    )

    rows = list(csv.DictReader(sample_path.open(encoding="utf-8-sig", newline="")))
    rows[0]["note"] = "evidence changed"
    with sample_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    refreshed = materialize_gf02_prepress_gate(repo, project)
    assert refreshed["evidence_basis_changed"] is True
    assert refreshed["human_decision"] is None
    assert len(refreshed["human_decision_history"]) == 1


def test_runtime_preflight_passes_canonical_repo_and_writes_audit(tmp_path: Path) -> None:
    result = run_article1_preflight(Path.cwd(), tmp_path / "project")

    assert result["passed"] is True
    assert result["status"] == "PASSED"
    assert result["ci_replacement"] is False
    assert all(item["ok"] for item in result["checks"])
    assert Path(result["audit_path"]).is_file()
