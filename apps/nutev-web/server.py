from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import webbrowser

APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
VALIDATION_ROOT = REPO_ROOT / "apps" / "nutev-validation"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from search_adapter import PROVIDER_LABELS, PROVIDER_ORDER, search_evidence

MAX_BODY_BYTES = 32 * 1024


class NutEVHandler(SimpleHTTPRequestHandler):
    server_version = "NutEVWeb/0.1"

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def _json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, object]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Content-Length inválido") from exc
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Payload inválido ou grande demais")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON inválido") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON precisa ser um objeto")
        return value

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"status": "ok", "service": "nutev-web", "validation_available": VALIDATION_ROOT.is_dir()})
            return
        if path == "/api/providers":
            self._json({"providers": [{"id": p, "label": PROVIDER_LABELS[p]} for p in PROVIDER_ORDER]})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/search":
            self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            result = search_evidence(
                payload.get("query"),
                providers=[str(x) for x in payload.get("providers", [])] if isinstance(payload.get("providers"), list) else None,
                per_provider=int(payload.get("per_provider", 25)),
                max_results=int(payload.get("max_results", 100)),
            )
        except ValueError as exc:
            self._json({"error": "invalid_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:
            self._json(
                {"error": "search_failed", "message": f"{type(exc).__name__}: {exc}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return
        self._json(result)

    def translate_path(self, path: str) -> str:
        clean = urlparse(path).path
        if clean.startswith("/validation"):
            suffix = clean[len("/validation"):].lstrip("/")
            target = VALIDATION_ROOT / (suffix or "index.html")
            if target.is_dir():
                target = target / "index.html"
            return str(target)
        suffix = clean.lstrip("/")
        target = APP_ROOT / (suffix or "index.html")
        if target.is_dir():
            target = target / "index.html"
        return str(target)

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[nutev-web] " + (fmt % args) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the unified NutEV search + validation web interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NutEVHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"NutEV web disponível em {url}")
    print("Ctrl+C para encerrar.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
