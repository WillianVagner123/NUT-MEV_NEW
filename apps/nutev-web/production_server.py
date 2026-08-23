from __future__ import annotations

import argparse
from hmac import compare_digest
from http import HTTPStatus
from http.server import ThreadingHTTPServer
import os

from server import NutEVHandler

PROXY_COORDINATOR_HEADER = "X-NutEV-Coordinator-Secret"
PROXY_COORDINATOR_ENV = "NUTEV_PROXY_COORDINATOR_SECRET"


class ProductionNutEVHandler(NutEVHandler):
    """NutEV handler for a trusted reverse proxy in private production.

    Local/desktop operation keeps using ``server.py`` and its loopback-only
    coordinator guardrail. Production may additionally authorize coordinator
    routes when a reverse proxy injects the exact shared secret. The backend
    port must never be published directly to the internet in this mode.
    """

    server_version = "NutEVWeb/1.0-production"

    def _trusted_proxy_coordinator(self) -> bool:
        expected = os.environ.get(PROXY_COORDINATOR_ENV, "").strip()
        presented = self.headers.get(PROXY_COORDINATOR_HEADER, "").strip()
        return bool(expected and presented) and compare_digest(presented, expected)

    def _require_loopback(self) -> bool:
        if self._is_loopback() or self._trusted_proxy_coordinator():
            return True
        self._json(
            {
                "error": "coordinator_access_required",
                "message": (
                    "A coordenação científica exige navegador local ou reverse proxy "
                    "autenticado pelo segredo interno do NutEV."
                ),
            },
            HTTPStatus.FORBIDDEN,
        )
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve NutEV behind an authenticated production reverse proxy."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if not os.environ.get(PROXY_COORDINATOR_ENV, "").strip():
        raise SystemExit(
            f"{PROXY_COORDINATOR_ENV} is required for production_server.py"
        )

    server = ThreadingHTTPServer((args.host, args.port), ProductionNutEVHandler)
    print(f"NutEV production backend em http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
