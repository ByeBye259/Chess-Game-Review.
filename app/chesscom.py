from __future__ import annotations

import json
from urllib.request import Request, urlopen

CHESSCOM_BASE = "https://api.chess.com/pub"


def _get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "ChessReviewSystem/1.0"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_latest_game(username: str) -> dict | None:
    archives_data = _get_json(f"{CHESSCOM_BASE}/player/{username}/games/archives")
    archives = archives_data.get("archives", [])
    if not archives:
        return None
    latest_archive = archives[-1]
    archive_data = _get_json(latest_archive)
    games = archive_data.get("games", [])
    if not games:
        return None
    return games[-1]


def fetch_pgn_from_game_url(game_url: str) -> str:
    pgn_url = game_url.rstrip("/") + "/pgn"
    req = Request(pgn_url, headers={"User-Agent": "ChessReviewSystem/1.0"})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")
