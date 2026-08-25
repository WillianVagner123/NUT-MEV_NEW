from __future__ import annotations

from nutev.search.pubmed import _completed_checkpoint_satisfies_limit


def _checkpoint(*, count: int, rows: int, retstart_done: int, status: str = "completed") -> dict:
    return {
        "status": status,
        "count": count,
        "rows": [{"pmid": str(i)} for i in range(rows)],
        "retstart_done": retstart_done,
    }


def test_bounded_completed_checkpoint_does_not_satisfy_exhaustive_request() -> None:
    checkpoint = _checkpoint(count=1600, rows=25, retstart_done=25)
    assert _completed_checkpoint_satisfies_limit(checkpoint, 25) is True
    assert _completed_checkpoint_satisfies_limit(checkpoint, 1600) is False
    assert _completed_checkpoint_satisfies_limit(checkpoint, 2_147_483_647) is False


def test_full_checkpoint_satisfies_exhaustive_sentinel() -> None:
    checkpoint = _checkpoint(count=1600, rows=1600, retstart_done=1600)
    assert _completed_checkpoint_satisfies_limit(checkpoint, 2_147_483_647) is True


def test_checkpoint_must_cover_retstart_and_rows() -> None:
    assert _completed_checkpoint_satisfies_limit(
        _checkpoint(count=100, rows=100, retstart_done=25),
        100,
    ) is False
    assert _completed_checkpoint_satisfies_limit(
        _checkpoint(count=100, rows=25, retstart_done=100),
        100,
    ) is False
