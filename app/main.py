from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.chesscom import fetch_latest_game, fetch_pgn_from_game_url
from app.review import review_pgn

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404, "Not Found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if self.path.startswith("/api/"):
            self.send_error(404, "Not Found")
            return
        self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/review":
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            self._send_json(400, {"detail": "Invalid JSON body"})
            return

        pgn_text = payload.get("pgn")
        game_url = payload.get("game_url")
        username = payload.get("username")

        try:
            if game_url:
                pgn_text = fetch_pgn_from_game_url(game_url)
            elif username:
                latest_game = fetch_latest_game(username)
                if not latest_game:
                    self._send_json(404, {"detail": "No games found for username"})
                    return
                pgn_text = latest_game.get("pgn")

            if not pgn_text:
                self._send_json(400, {"detail": "Provide one of: pgn, game_url, or username"})
                return

            review = review_pgn(pgn_text)
            self._send_json(200, review)
        except Exception as exc:
            self._send_json(400, {"detail": f"Review failed: {exc}"})


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Serving Chess.com review system on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
