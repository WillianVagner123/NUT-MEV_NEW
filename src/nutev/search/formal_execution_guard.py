"""Execution-edge authorization for FORMAL/PRISMA search strategies."""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from nutev.config_provenance import build_config_provenance
from nutev.search.scientific_gates import (
    formal_execution_authorization,
    load_freeze_record,
    load_gate_records,
)
from nutev.settings import default_config_root


def default_gate_path(project_root: Path) -> Path:
    return Path(project_root) / "00_config" / "scientific_gates.json"


def default_freeze_path(project_root: Path) -> Path:
    return Path(project_root) / "00_config" / "search_freeze.json"


def _git_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repo_root),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def require_formal_execution_authorization(
    project_root: Path,
    strategy_version: dict[str, Any],
    *,
    gate_path: Path | None = None,
    freeze_path: Path | None = None,
    current_git_sha: str | None = None,
    current_config_digest: str | None = None,
    config_root: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Raise unless a FORMAL/PRISMA strategy is bound to authorized freeze evidence."""
    search_type = str(strategy_version.get("search_type") or "").strip().upper()
    prisma_eligible = bool(strategy_version.get("prisma_eligible"))
    if search_type != "FORMAL" and not prisma_eligible:
        return {
            "required": False,
            "authorized": False,
            "formal_execution_authorized": False,
            "prisma_eligible": False,
            "blockers": [],
        }

    root = Path(project_root)
    gates_file = Path(gate_path) if gate_path else default_gate_path(root)
    freeze_file = Path(freeze_path) if freeze_path else default_freeze_path(root)
    missing = []
    if not gates_file.is_file():
        missing.append(f"gate_record_missing:{gates_file}")
    if not freeze_file.is_file():
        missing.append(f"freeze_record_missing:{freeze_file}")
    if missing:
        raise RuntimeError("FORMAL execution blocked: " + "; ".join(missing))

    gates = load_gate_records(gates_file)
    freeze = load_freeze_record(freeze_file)
    version_id = str(strategy_version.get("version_id") or "").strip()
    if version_id not in freeze.strategy_versions:
        raise RuntimeError(
            "FORMAL execution blocked: strategy version is not bound to the freeze record"
        )

    resolved_repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    resolved_sha = current_git_sha or _git_sha(resolved_repo_root)
    resolved_config_root = Path(config_root) if config_root else default_config_root()
    resolved_digest = current_config_digest or str(
        build_config_provenance(resolved_config_root)["config_digest"]
    )
    result = formal_execution_authorization(
        gates=gates,
        freeze=freeze,
        current_git_sha=resolved_sha,
        current_config_digest=resolved_digest,
    )
    if not bool(result["authorized"]):
        blockers = "; ".join(str(item) for item in result["blockers"])
        raise RuntimeError(f"FORMAL execution blocked: {blockers}")
    return {"required": True, **result}


__all__ = [
    "default_freeze_path",
    "default_gate_path",
    "require_formal_execution_authorization",
]
