from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from nutev.science.deepening_lock import (
    DeepeningWorkerLockError,
    acquire_deepening_worker_lock,
)


def test_deepening_lock_rejects_concurrent_worker_and_releases(tmp_path: Path) -> None:
    kwargs = {
        "output_root": tmp_path,
        "search_id": "search-1",
        "tier": "A",
        "pipeline_version": "test-v1",
    }

    with acquire_deepening_worker_lock(**kwargs) as lock_path:
        assert lock_path.is_file()
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        assert owner["search_id"] == "search-1"
        assert owner["tier"] == "A"
        assert owner["pipeline_version"] == "test-v1"
        with pytest.raises(DeepeningWorkerLockError, match="already running"):
            with acquire_deepening_worker_lock(**kwargs):
                pass

    assert not lock_path.exists()


def test_deepening_lock_recovers_orphaned_pid(tmp_path: Path) -> None:
    lock_path = (
        tmp_path
        / "scientific"
        / "deepening"
        / "search-2"
        / "tier-A"
        / ".worker.lock"
    )
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        json.dumps(
            {
                "pid": 2_000_000_000,
                "hostname": socket.gethostname(),
                "token": "orphan",
            }
        ),
        encoding="utf-8",
    )

    with acquire_deepening_worker_lock(
        output_root=tmp_path,
        search_id="search-2",
        tier="A",
        pipeline_version="test-v2",
    ) as acquired:
        assert acquired == lock_path
        owner = json.loads(acquired.read_text(encoding="utf-8"))
        assert owner["token"] != "orphan"

    assert not lock_path.exists()
