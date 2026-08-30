"""Cross-platform single-worker lock for selective deepening runs."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
from typing import Iterator
from uuid import uuid4


class DeepeningWorkerLockError(RuntimeError):
    """Raised when another deepening worker already owns the tier lock."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _lock_is_active(metadata: dict[str, object]) -> bool:
    lock_host = str(metadata.get("hostname") or "").strip()
    current_host = socket.gethostname()
    try:
        pid = int(metadata.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    return bool(lock_host and lock_host == current_host and _pid_alive(pid))


@contextmanager
def acquire_deepening_worker_lock(
    *,
    output_root: Path,
    search_id: str,
    tier: str,
    pipeline_version: str,
) -> Iterator[Path]:
    """Acquire one atomic worker lock for a search/tier and release it in ``finally``.

    A lock from a different container hostname, or from a PID that no longer exists,
    is treated as orphaned and recovered once. This protects shared batch artifacts
    from concurrent writers while remaining restart-safe after container replacement.
    """

    tier_name = str(tier or "").strip().upper()
    lock_dir = (
        Path(output_root).resolve()
        / "scientific"
        / "deepening"
        / str(search_id)
        / f"tier-{tier_name}"
    )
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".worker.lock"
    token = uuid4().hex
    metadata = {
        "schema_version": 1,
        "lock_type": "NUTEV_DEEPENING_SINGLE_WORKER",
        "search_id": str(search_id),
        "tier": tier_name,
        "pipeline_version": str(pipeline_version),
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "acquired_at": _now(),
        "token": token,
    }

    acquired = False
    for attempt in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            existing = _read_lock(lock_path)
            if attempt == 0 and not _lock_is_active(existing):
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            raise DeepeningWorkerLockError(
                "deepening worker already running for this search/tier; "
                f"lock={lock_path}; owner={json.dumps(existing, ensure_ascii=False, sort_keys=True)}"
            ) from exc
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(metadata, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            acquired = True
            break

    if not acquired:
        raise DeepeningWorkerLockError(f"could not acquire deepening worker lock: {lock_path}")

    try:
        yield lock_path
    finally:
        existing = _read_lock(lock_path)
        if str(existing.get("token") or "") == token:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
