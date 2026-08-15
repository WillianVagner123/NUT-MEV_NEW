"""Persistent one-button controller for the canonical Article 1 workflow.

The controller is intentionally gate-aware. It runs every currently automatic
step, persists state after each transition, and stops at human/external gates
without inferring scientific approval. Re-running the same command/button
continues from the persisted state instead of creating a new workflow.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from nutev.search.article1_scientific_status import derive_article1_scientific_status
from nutev.search.gf02_pubmed_pilot import run_gf02_pubmed_pilot

LOCAL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
ENGINE_SCHEMA_VERSION = 1
ProgressFn = Callable[[str], None]


def _now_iso() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def _state_path(project_root: Path) -> Path:
    return Path(project_root) / "07_logs" / "engine" / "article1_engine_state.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(project_root: Path, state: dict[str, Any]) -> None:
    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def load_article1_engine_state(project_root: Path) -> dict[str, Any]:
    """Return the persisted controller state, or an empty dict when absent."""
    return _load_json(_state_path(project_root))


def _candidate_version(scientific: dict[str, Any]) -> str:
    return str((scientific.get("gf02") or {}).get("candidate_version") or "UNKNOWN")


def _new_state(scientific: dict[str, Any]) -> dict[str, Any]:
    token = uuid4().hex[:10]
    candidate = _candidate_version(scientific)
    safe_candidate = candidate.replace(".", "_").replace("-", "_")
    return {
        "schema_version": ENGINE_SCHEMA_VERSION,
        "engine_run_id": f"article1_{datetime.now(LOCAL_TIMEZONE).strftime('%Y%m%dT%H%M%S%z')}_{token}",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "candidate_version": candidate,
        "status": "READY",
        "current_phase": str(scientific.get("article1_current_phase") or "GF02_PUBMED_PILOT"),
        "last_message": "Pronto para iniciar.",
        "waiting_on": None,
        "completed_stages": {},
        "gf02_run_id": f"gf02_pubmed_{safe_candidate}_resume_{token}",
        "last_error": None,
    }


def ensure_article1_engine_state(repo_root: Path, project_root: Path) -> dict[str, Any]:
    scientific = derive_article1_scientific_status(Path(repo_root), Path(project_root))
    state = load_article1_engine_state(project_root)
    if not state or str(state.get("candidate_version") or "") != _candidate_version(scientific):
        state = _new_state(scientific)
        _write_state(project_root, state)
    return state


def _emit(
    project_root: Path,
    state: dict[str, Any],
    progress_fn: ProgressFn | None,
    message: str,
) -> None:
    state["last_message"] = message
    _write_state(project_root, state)
    if progress_fn is not None:
        progress_fn(message)


def _pause(
    project_root: Path,
    state: dict[str, Any],
    *,
    status: str,
    phase: str,
    message: str,
) -> dict[str, Any]:
    state["status"] = status
    state["current_phase"] = phase
    state["waiting_on"] = phase
    state["last_message"] = message
    state["last_error"] = None
    _write_state(project_root, state)
    return state


def run_or_resume_article1_engine(
    repo_root: Path,
    *,
    project_root: Path,
    progress_fn: ProgressFn | None = None,
) -> dict[str, Any]:
    """Run all currently automatic Article 1 work and resume from checkpoints.

    The controller never crosses human or external scientific gates by itself.
    It persists a stable GF-02 run id so an interrupted PubMed PILOT can resume
    inside the same audit directory.
    """
    repo = Path(repo_root)
    project = Path(project_root)
    state = ensure_article1_engine_state(repo, project)
    state["status"] = "RUNNING"
    state["waiting_on"] = None
    state["last_error"] = None
    _write_state(project, state)

    try:
        while True:
            scientific = derive_article1_scientific_status(repo, project)
            phase = str(scientific.get("article1_current_phase") or "")
            state["current_phase"] = phase
            _write_state(project, state)

            if phase == "GF02_PUBMED_PILOT":
                _emit(project, state, progress_fn, "Executando GF-02 PubMed a partir do último checkpoint...")

                def relay(message: str) -> None:
                    _emit(project, state, progress_fn, message)

                manifest = run_gf02_pubmed_pilot(
                    repo,
                    project_root=project,
                    run_id=str(state["gf02_run_id"]),
                    resume=True,
                    progress_fn=relay,
                )
                if manifest.get("status") != "SUCCEEDED":
                    raise RuntimeError(
                        "GF-02 terminou com bloqueios de auditoria: "
                        + "; ".join(str(item) for item in (manifest.get("errors") or []))
                    )
                state["completed_stages"]["GF02_PUBMED_PILOT"] = {
                    "completed_at": _now_iso(),
                    "run_id": manifest.get("run_id"),
                    "manifest": str(
                        project
                        / "07_logs"
                        / "gf02"
                        / "pubmed"
                        / str(manifest.get("run_id"))
                        / "run_manifest.json"
                    ),
                }
                _write_state(project, state)
                continue

            if phase == "GF02_NOISE_REVIEW":
                return _pause(
                    project,
                    state,
                    status="WAITING_HUMAN",
                    phase=phase,
                    message=(
                        "Execução automática concluída até aqui. Aguardando classificação humana "
                        "da amostra rescue-only; depois use o mesmo botão CONTINUAR."
                    ),
                )

            if phase == "GF02_HUMAN_DECISION":
                return _pause(
                    project,
                    state,
                    status="WAITING_HUMAN",
                    phase=phase,
                    message=(
                        "Aguardando decisão humana READY_FOR_PRESS ou NOT_READY_FOR_PRESS. "
                        "Depois da decisão, use o mesmo botão CONTINUAR."
                    ),
                )

            if phase == "GF03_PRESS":
                return _pause(
                    project,
                    state,
                    status="WAITING_EXTERNAL",
                    phase=phase,
                    message=(
                        "Aguardando PRESS. O Engine não inventa parecer nem aprovação. "
                        "Quando o registro de PRESS existir, use CONTINUAR."
                    ),
                )

            if phase == "POST_PRESS_PROVIDER_VALIDATION":
                return _pause(
                    project,
                    state,
                    status="WAITING_EXTERNAL",
                    phase=phase,
                    message=(
                        "Fase pós-PRESS detectada. Scopus/WoS licenciado ainda exige integração/execução "
                        "externa; o ponto de retomada ficou salvo."
                    ),
                )

            state["status"] = "COMPLETE"
            state["waiting_on"] = None
            state["last_message"] = "Todas as etapas atualmente automatizadas foram concluídas."
            _write_state(project, state)
            return state

    except Exception as exc:
        state["status"] = "FAILED"
        state["last_error"] = str(exc)
        state["last_message"] = (
            "Execução interrompida. O checkpoint foi preservado; use CONTINUAR para tentar novamente."
        )
        _write_state(project, state)
        raise


def engine_button_label(repo_root: Path, project_root: Path) -> str:
    scientific = derive_article1_scientific_status(Path(repo_root), Path(project_root))
    state = load_article1_engine_state(project_root)
    phase = str(scientific.get("article1_current_phase") or "")
    if not state and phase == "GF02_PUBMED_PILOT":
        return "▶ RODAR TUDO"
    return "▶ CONTINUAR"


__all__ = [
    "engine_button_label",
    "ensure_article1_engine_state",
    "load_article1_engine_state",
    "run_or_resume_article1_engine",
]
