from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
ROLE_RANKER_DIR = DATA_DIR / "role_ranker"
LEGACY_RANKINGS_PATH = PROCESSED_DIR / "user_rankings.json"
RANKINGS_PATH = ROLE_RANKER_DIR / "elo_ratings.json"
PLAYERS_PATH = PROCESSED_DIR / "vlr_players_processed.csv"

PLAYER_COLUMNS = [
    "player",
    "team",
    "role",
    "agent",
    "map",
    "match_id",
    "pick_count",
]


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ROLE_RANKER_DIR.mkdir(parents=True, exist_ok=True)


def load_players(path: Path = PLAYERS_PATH) -> pd.DataFrame:
    ensure_dirs()
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=PLAYER_COLUMNS)
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame(columns=PLAYER_COLUMNS)


def save_players(df: pd.DataFrame, path: Path = PLAYERS_PATH) -> None:
    ensure_dirs()
    df.to_csv(path, index=False)


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _coerce_elo_ratings(raw: dict[str, Any]) -> dict[str, float]:
    """Keep only values that can safely represent Elo ratings.

    Tournament state uses dictionaries such as {wins, losses, duels}. Those records
    must be ignored by the legacy Elo app instead of crashing with float(dict).
    """
    ratings: dict[str, float] = {}
    for player_key, value in raw.items():
        if isinstance(value, dict):
            # Explicitly do not infer Elo from tournament wins/losses.
            if "rating" in value:
                try:
                    ratings[str(player_key)] = float(value["rating"])
                except (TypeError, ValueError):
                    continue
            continue
        try:
            ratings[str(player_key)] = float(value)
        except (TypeError, ValueError):
            continue
    return ratings


def load_ratings(path: Path = RANKINGS_PATH) -> dict[str, float]:
    ensure_dirs()
    ratings = _coerce_elo_ratings(_read_json_dict(path))
    if ratings:
        return ratings
    return _coerce_elo_ratings(_read_json_dict(LEGACY_RANKINGS_PATH))


def save_ratings(ratings: dict[str, float], path: Path = RANKINGS_PATH) -> None:
    ensure_dirs()
    clean_ratings = _coerce_elo_ratings(ratings)
    with path.open("w", encoding="utf-8") as f:
        json.dump(clean_ratings, f, indent=2, ensure_ascii=False)
