from app.review import parse_pgn, review_pgn

SIMPLE_PGN = """
[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.02.01"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Qh5 Nf6 5. Qxf7# 1-0
"""


def test_parse_pgn_extracts_headers_and_moves():
    headers, moves = parse_pgn(SIMPLE_PGN)
    assert headers["White"] == "alice"
    assert headers["Black"] == "bob"
    assert moves[0] == "e4"
    assert moves[-1] == "Qxf7#"


def test_review_returns_expected_shape():
    review = review_pgn(SIMPLE_PGN)
    assert review["summary"]["total_moves"] == 9
    assert len(review["moves"]) == 9
    assert 0 <= review["white_accuracy"] <= 100
    assert 0 <= review["black_accuracy"] <= 100
    assert {"best", "good", "inaccuracy", "mistake", "blunder"}.issuperset(
        {m["category"] for m in review["moves"]}
    )
