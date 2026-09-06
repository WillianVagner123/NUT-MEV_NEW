from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "nutev-web"
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

MODULE_PATH = WEB_ROOT / "search_adapter.py"
SPEC = importlib.util.spec_from_file_location("nutev_web_search_adapter_optional_contract", MODULE_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


class _Result:
    def __init__(self, rows: list[dict[str, str]], status: str = "completed") -> None:
        self.rows = rows
        self.status = status
        self.total_found = None
        self.error = ""


def test_global_provider_order_includes_optional_web_sources() -> None:
    assert "google_pse" in adapter.PROVIDER_ORDER
    assert "brave" in adapter.PROVIDER_ORDER
    assert "serpapi" in adapter.PROVIDER_ORDER
    assert "google_pse" in adapter.DIRECT_PROVIDERS
    assert "brave" in adapter.DIRECT_PROVIDERS
    assert "serpapi" in adapter.DIRECT_PROVIDERS
    assert adapter.LATIN_PROVIDERS == ("lilacs_bvs_native", "scielo_native")


def test_optional_web_cap_is_recorded_as_partial_when_saturated() -> None:
    cap = 20
    result = adapter._cap_aware_optional_result(
        "brave",
        requested_limit=2_147_483_647,
        cap=cap,
        call=lambda: _Result([{"title": str(index)} for index in range(cap)]),
    )
    assert result.status == "partial"
    assert result.error == "connector_limit_reached:brave:20"


def test_optional_web_result_below_cap_can_remain_complete() -> None:
    result = adapter._cap_aware_optional_result(
        "brave",
        requested_limit=2_147_483_647,
        cap=20,
        call=lambda: _Result([{"title": "one"}]),
    )
    assert result.status == "completed"
    assert result.error == ""


def test_missing_credentials_status_is_not_rewritten(monkeypatch) -> None:
    result = _Result([], status="skipped")
    result.error = "missing BRAVE_API_KEY"
    monkeypatch.setattr(adapter, "search_brave", lambda query, limit: result)

    returned = adapter._provider_call("brave", "nutrition", 2_147_483_647)()

    assert returned.status == "skipped"
    assert returned.error == "missing BRAVE_API_KEY"
