import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-hetzner.yml"
DEPLOY_DOC = ROOT / "docs" / "HETZNER_AUTODEPLOY.md"
PRESS_DIR = ROOT / "evidence" / "article1_press" / "article1_press_20260906T202201Z"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_manual_hetzner_deploy_is_main_only_and_does_not_require_autodeploy_flag() -> None:
    workflow = " ".join(read(WORKFLOW).split())

    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "vars.HETZNER_AUTODEPLOY == 'true'" in workflow
    assert "github.event_name == 'workflow_run'" in workflow
    assert (
        "(github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main') || "
        "(vars.HETZNER_AUTODEPLOY == 'true' && github.event_name == 'workflow_run'"
    ) in workflow


def test_hetzner_documentation_matches_workflow_configuration_surface() -> None:
    workflow = read(WORKFLOW)
    doc = read(DEPLOY_DOC)

    assert "environment: HETZNER" in workflow
    assert "environment named `HETZNER`" in doc
    for variable in ("HETZNER_HOST", "HETZNER_USER", "HETZNER_PORT", "HETZNER_APP_DIR"):
        assert f"vars.{variable}" in workflow
        assert variable in doc
    assert "secrets.HETZNER_SSH_KEY" in workflow
    assert "HETZNER_SSH_KEY" in doc
    assert "does not disable an explicit manual deploy from `main`" in doc


def test_press_sample_manifest_persists_exact_incremental_identity_counts_without_labels() -> None:
    manifest = json.loads(read(PRESS_DIR / "SAMPLE_MANIFEST.json"))
    summary = json.loads(read(PRESS_DIR / "TECHNICAL_SUMMARY.json"))

    assert manifest["record_type"] == "NUTEV_ARTICLE1_PRESS_SAMPLE_CUSTODY_MANIFEST"
    assert manifest["run_id"] == summary["run_id"] == "article1_press_20260906T202201Z"
    assert manifest["run_sha256"] == summary["run_sha256"]
    assert manifest["custody_status"] == "PERSISTED_IDENTIFIERS_ONLY"
    assert manifest["human_labels_present"] is False
    assert manifest["full_text_or_abstract_persisted"] is False
    assert manifest["guardrails"]["manifest_is_not_press_pass"] is True
    assert summary["sample_custody_status"] == "PERSISTED_IDENTIFIERS_ONLY"
    assert summary["press_pass_inferred"] is False
    assert summary["human_review_state"] == "PENDING"

    expected_counts = {"D01": 0, "D02": 25, "D03": 25, "D04": 25, "D05": 25}
    deltas = {item["id"]: item for item in manifest["deltas"]}
    assert set(deltas) == set(expected_counts)

    for delta_id, expected_count in expected_counts.items():
        delta = deltas[delta_id]
        records = delta["records"]
        assert delta["persisted_sample_count"] == expected_count
        assert len(records) == expected_count
        assert [record["position"] for record in records] == list(range(1, expected_count + 1))
        for record in records:
            assert set(record) == {"position", "pmid", "doi"}
            assert record["pmid"].isdigit()
            assert record["doi"].startswith("10.")

    assert summary["persisted_incremental_sample_counts"] == expected_counts
    assert deltas["D01"]["incremental_total_found"] == 0


def test_press_human_packet_uses_persistent_manifest_but_keeps_scientific_decision_open() -> None:
    packet = read(PRESS_DIR / "HUMAN_REVIEW_PACKET.md")

    assert "Persistent sample custody: `SAMPLE_MANIFEST.json`" in packet
    assert "The manifest proves sample custody; it does not label any record as relevant or irrelevant." in packet
    assert "ADOPT_C4" in packet
    assert "REVISE_C4" in packet
    assert "REJECT_C4" in packet
    assert "Only after those judgments" in packet
