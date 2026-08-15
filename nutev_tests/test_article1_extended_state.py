from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path

from nutev.search.article1_scientific_status import derive_article1_scientific_status
from nutev.search.licensed_provider_evidence import (
    LicensedProviderExecution,
    default_licensed_evidence_path,
    save_licensed_execution,
)
from nutev.search.scientific_gates import (
    FreezeRecord,
    GateRecord,
    save_freeze_record,
    save_gate_records,
)


def _licensed(provider: str, export: Path) -> LicensedProviderExecution:
    return LicensedProviderExecution(
        provider=provider,
        strategy_version="post-press-v1",
        search_type="PILOT",
        executed_at="2026-08-15T19:00:00-03:00",
        executed_by="Researcher",
        exact_expression=f"{provider} expression",
        interface="licensed interface",
        status="SUCCEEDED",
        total_found=5,
        records_retrieved=5,
        export_path=str(export),
        export_sha256=sha256(export.read_bytes()).hexdigest(),
    )


def test_status_can_advance_from_press_to_formal_execution_without_inference(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project = tmp_path / "project"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "gf02_pubmed_candidates.json").write_text(
        json.dumps(
            {
                "current_candidate": "v0.5",
                "candidate_status": "PROVISIONAL_PILOT_PENDING_NOISE_REVIEW",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "formal_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )

    run_dir = project / "07_logs" / "gf02" / "pubmed" / "run1"
    run_dir.mkdir(parents=True)
    sample = run_dir / "sample.csv"
    with sample.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["classification", "reviewer"])
        writer.writeheader()
        writer.writerow({"classification": "relevant", "reviewer": "R1"})
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "candidate_version": "v0.5",
                "status": "SUCCEEDED",
                "search_type": "PILOT",
                "prisma_eligible": False,
                "rescue_only_sample": str(sample),
            }
        ),
        encoding="utf-8",
    )
    gf02_gate = project / "07_logs" / "gf02" / "gate_status.json"
    gf02_gate.parent.mkdir(parents=True, exist_ok=True)
    gf02_gate.write_text(json.dumps({"human_decision": "READY_FOR_PRESS"}), encoding="utf-8")
    press = project / "07_logs" / "scientific_gates" / "press.json"
    press.parent.mkdir(parents=True, exist_ok=True)
    press.write_text(json.dumps({"review_status": "APPROVED"}), encoding="utf-8")

    for provider in ("scopus", "web_of_science"):
        export = tmp_path / f"{provider}.csv"
        export.write_text("id,title\n1,A\n", encoding="utf-8")
        save_licensed_execution(
            default_licensed_evidence_path(project, provider),
            _licensed(provider, export),
        )

    freeze_id = "freeze-a1"
    gates = [
        GateRecord(
            gate_id=f"GF-{number:02d}",
            requirement=f"gate {number}",
            evidence=("real-evidence",),
            status="COMPLETED",
            owner="Researcher",
            completion_date="2026-08-15",
        )
        for number in range(2, 10)
    ]
    gates.append(
        GateRecord(
            gate_id="GF-10",
            requirement="freeze",
            evidence=(freeze_id,),
            status="AUTHORIZED",
            owner="Researcher",
            completion_date="2026-08-15",
        )
    )
    gate_path = project / "00_config" / "scientific_gates.json"
    save_gate_records(gate_path, gates, registry_version="test")
    save_freeze_record(
        project / "00_config" / "search_freeze.json",
        FreezeRecord(
            freeze_id=freeze_id,
            date="2026-08-15",
            software_version="0.3.0.dev1",
            git_commit_sha="a" * 40,
            strategy_versions=("formal-v1",),
            source_registry_version="source-v1",
            repository_registry_version="repo-v1",
            sentinel_suite_version="sentinel-v1",
            press_evidence_id="press-v1",
            filters=(("date", "frozen"),),
            final_search_date_rule="through freeze date",
            config_digest="b" * 64,
            reviewers=("R1", "R2"),
        ),
    )

    status = derive_article1_scientific_status(repo, project)
    assert status["scopus_wos"]["licensed_pilot_complete"] is True
    assert status["freeze"]["authorized"] is True
    assert status["article1_current_phase"] == "FORMAL_EXECUTION"
    assert status["human_approval_inferred"] is False
