"""Fast runtime preflight for the one-button Article 1 Engine.

This is not a replacement for CI. It checks the local scientific configuration,
project writeability and critical invariant files before the Engine starts a
network/search step, then persists the result for audit.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.gf02_evidence import validate_sentinel_registry
from nutev.search.gf02_pubmed_pilot import load_candidate_config, load_sentinel_registry

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_article1_preflight(repo_root: Path, project_root: Path) -> dict[str, Any]:
    """Validate critical local invariants before any automatic execution begins."""
    repo = Path(repo_root)
    project = Path(project_root)
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    config_path = repo / "config" / "gf02_pubmed_candidates.json"
    sentinel_path = repo / "config" / "article1_sentinel_registry.json"

    try:
        config = load_candidate_config(config_path)
        record("gf02_config", True, str(config_path))
    except Exception as exc:
        config = {}
        record("gf02_config", False, str(exc))

    if config:
        record(
            "gf02_is_pilot",
            str(config.get("search_type") or "").upper() == "PILOT",
            f"search_type={config.get('search_type')}",
        )
        record(
            "gf02_not_prisma_eligible",
            config.get("prisma_eligible") is False,
            f"prisma_eligible={config.get('prisma_eligible')}",
        )
        record(
            "gf02_formal_not_pre_authorized",
            config.get("formal_execution_authorized") is False,
            f"formal_execution_authorized={config.get('formal_execution_authorized')}",
        )
        record(
            "gf02_candidate_present",
            bool(str(config.get("current_candidate") or "").strip()),
            f"current_candidate={config.get('current_candidate')}",
        )

    try:
        sentinels = load_sentinel_registry(sentinel_path)
        validate_sentinel_registry(sentinels)
        record("sentinel_registry", True, f"{len(sentinels)} sentinel(s) validated")
    except Exception as exc:
        record("sentinel_registry", False, str(exc))

    try:
        audit_dir = project / "07_logs" / "engine"
        audit_dir.mkdir(parents=True, exist_ok=True)
        probe = audit_dir / f".preflight-write-{uuid4().hex}.tmp"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        record("project_writeable", True, str(project))
    except Exception as exc:
        record("project_writeable", False, str(exc))

    passed = all(bool(item["ok"]) for item in checks)
    payload = {
        "schema_version": 1,
        "checked_at": datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds"),
        "status": "PASSED" if passed else "FAILED",
        "passed": passed,
        "checks": checks,
        "ci_replacement": False,
        "note": "Runtime preflight complements repository CI; it does not replace the full automated test suite.",
    }
    audit_path = project / "07_logs" / "engine" / "preflight.json"
    _atomic_json(audit_path, payload)
    payload["audit_path"] = str(audit_path)
    return payload


__all__ = ["run_article1_preflight"]
