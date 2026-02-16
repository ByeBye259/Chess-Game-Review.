from __future__ import annotations

import re
from typing import Any

RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}
MOVE_NUM_RE = re.compile(r"^\d+\.{1,3}$")
TAG_RE = re.compile(r"^\[(\w+)\s+\"(.*)\"\]$")


def parse_pgn(pgn_text: str) -> tuple[dict[str, str], list[str]]:
    headers: dict[str, str] = {}
    movetext_lines: list[str] = []

    for raw_line in pgn_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        tag_match = TAG_RE.match(line)
        if tag_match:
            headers[tag_match.group(1)] = tag_match.group(2)
            continue
        movetext_lines.append(line)

    movetext = " ".join(movetext_lines)
    movetext = re.sub(r"\{[^}]*\}", " ", movetext)
    movetext = re.sub(r"\([^)]*\)", " ", movetext)
    movetext = re.sub(r"\$\d+", " ", movetext)
    tokens = [t for t in movetext.split() if t]

    moves: list[str] = []
    for tok in tokens:
        if MOVE_NUM_RE.match(tok) or tok in RESULT_TOKENS:
            continue
        if tok[0].isdigit() and "." in tok:
            parts = tok.split(".")
            cand = parts[-1]
            if cand:
                tok = cand
            else:
                continue
        moves.append(tok)

    if not moves:
        raise ValueError("No moves found in PGN")

    return headers, moves


def _move_impact(san: str) -> float:
    impact = 0.2
    if "x" in san:
        impact += 0.5
    if "+" in san:
        impact += 0.3
    if "#" in san:
        impact += 1.5
    if "=" in san:
        impact += 1.0
    if san in {"O-O", "O-O-O"}:
        impact += 0.2
    if san.endswith("?"):
        impact -= 1.0
    if san.endswith("??"):
        impact -= 2.5
    return impact


def categorize_loss(loss: float) -> str:
    if loss < 0.4:
        return "best"
    if loss < 1.0:
        return "good"
    if loss < 2.0:
        return "inaccuracy"
    if loss < 3.0:
        return "mistake"
    return "blunder"


def review_pgn(pgn_text: str) -> dict[str, Any]:
    headers, moves = parse_pgn(pgn_text)

    eval_score = 0.0
    accuracy_buckets = {
        "white": {"best": 0, "good": 0, "inaccuracy": 0, "mistake": 0, "blunder": 0},
        "black": {"best": 0, "good": 0, "inaccuracy": 0, "mistake": 0, "blunder": 0},
    }
    reviewed_moves = []

    for idx, san in enumerate(moves, start=1):
        side = "white" if idx % 2 == 1 else "black"
        before = eval_score
        delta = _move_impact(san)

        if side == "white":
            after = before + delta
            loss = max(0.0, (before + max(delta, 0.5)) - after)
        else:
            after = before - delta
            loss = max(0.0, (min(before, before - 0.5)) - after)

        if "??" in san:
            loss += 3.5
        elif "?" in san:
            loss += 1.5

        category = categorize_loss(loss)
        accuracy_buckets[side][category] += 1
        eval_score = after

        reviewed_moves.append(
            {
                "ply": idx,
                "san": san,
                "side": side,
                "eval_before": round(before, 2),
                "eval_after": round(after, 2),
                "loss": round(loss, 2),
                "category": category,
            }
        )

    def accuracy(side: str) -> float:
        c = accuracy_buckets[side]
        total = sum(c.values()) or 1
        weighted = c["best"] + 0.9 * c["good"] + 0.65 * c["inaccuracy"] + 0.4 * c["mistake"] + 0.1 * c["blunder"]
        return round(100 * weighted / total, 1)

    return {
        "headers": headers,
        "white_accuracy": accuracy("white"),
        "black_accuracy": accuracy("black"),
        "moves": reviewed_moves,
        "summary": {
            "white": accuracy_buckets["white"],
            "black": accuracy_buckets["black"],
            "total_moves": len(reviewed_moves),
        },
    }
