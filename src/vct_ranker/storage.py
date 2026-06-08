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
RANKINGS_PATH = ROLE_RANKER_DIR / "tournament_rankings.json"
PLAYERS_PATH = PROCESSED_DIR / "vlr_players_processed.csv"

PLAYER_COLUMNS = [
    "player",
    "team",
    "agents",
    "inferred_role",
    "role_confidence",
    "raw_role",
    "team_role",
    "flex_score",
    "distinct_roles",
    "role_scores",
    "official_role_scores",
    "agent_shares",
    "role_explanation",
    "vct_region",
    "event_name",
    "rating",
    "acs",
    "kd",
    "kast",
    "adr",
    "kpr",
    "apr",
    "fkpr",
    "fdpr",
    "hs_pct",
    "rounds",
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


def _looks_like_tournament_state(data: dict[str, Any]) -> bool:
    return any(isinstance(value, dict) for value in data.values())


def load_rankings(path: Path = RANKINGS_PATH) -> dict[str, Any]:
    """Load tournament rankings without mixing them with legacy Elo ratings.

    The first merged project used data/processed/user_rankings.json for both the Elo
    ranker and the tournament ranker. That made one app read the other app's JSON
    shape. The tournament app now uses data/role_ranker/tournament_rankings.json.

    For backward compatibility, we still import the legacy file only when it looks
    like tournament state, i.e. {player_key: {wins, losses, duels}}.
    """
    ensure_dirs()
    data = _read_json_dict(path)
    if data:
        return data

    legacy_data = _read_json_dict(LEGACY_RANKINGS_PATH)
    if _looks_like_tournament_state(legacy_data):
        return legacy_data
    return {}


def save_rankings(rankings: dict[str, Any], path: Path = RANKINGS_PATH) -> None:
    ensure_dirs()
    with path.open("w", encoding="utf-8") as f:
        json.dump(rankings, f, indent=2, ensure_ascii=False)


# Backward-compatible aliases for older code/imports.
def load_ratings(path: Path = RANKINGS_PATH) -> dict[str, Any]:
    return load_rankings(path)


def save_ratings(ratings: dict[str, Any], path: Path = RANKINGS_PATH) -> None:
    save_rankings(ratings, path)
