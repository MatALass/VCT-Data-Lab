from __future__ import annotations

import json
from pathlib import Path

from vct_ranker.storage import load_rankings, save_rankings
from vct_ranker_elo.storage import load_ratings, save_ratings


def test_elo_storage_ignores_tournament_json_shape(tmp_path: Path) -> None:
    path = tmp_path / "elo_ratings.json"
    path.write_text(
        json.dumps(
            {
                "alpha__AAA": {"wins": 1, "losses": 0, "duels": 1},
                "bravo__BBB": 1032.5,
                "charlie__CCC": "bad-value",
            }
        ),
        encoding="utf-8",
    )

    assert load_ratings(path) == {"bravo__BBB": 1032.5}


def test_elo_storage_writes_only_numeric_ratings(tmp_path: Path) -> None:
    path = tmp_path / "elo_ratings.json"
    save_ratings({"alpha__AAA": 1016.0, "bravo__BBB": {"wins": 1}}, path)

    assert json.loads(path.read_text(encoding="utf-8")) == {"alpha__AAA": 1016.0}


def test_tournament_storage_roundtrip_uses_nested_records(tmp_path: Path) -> None:
    path = tmp_path / "tournament_rankings.json"
    rankings = {"alpha__AAA": {"wins": 2, "losses": 1, "duels": 3}}
    save_rankings(rankings, path)

    assert load_rankings(path) == rankings
