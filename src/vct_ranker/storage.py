from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
RANKINGS_PATH = PROCESSED_DIR / "user_rankings.json"
PLAYERS_PATH = PROCESSED_DIR / "vlr_players_processed.csv"

PLAYER_COLUMNS = [
    "player",
    "team",
    "agents",
    "inferred_role",
    "role_confidence",
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


def load_rankings(path: Path = RANKINGS_PATH) -> dict[str, Any]:
    ensure_dirs()
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_rankings(rankings: dict[str, Any], path: Path = RANKINGS_PATH) -> None:
    ensure_dirs()
    with path.open("w", encoding="utf-8") as f:
        json.dump(rankings, f, indent=2, ensure_ascii=False)


# Backward-compatible aliases for older code/imports.
def load_ratings(path: Path = RANKINGS_PATH) -> dict[str, Any]:
    return load_rankings(path)


def save_ratings(ratings: dict[str, Any], path: Path = RANKINGS_PATH) -> None:
    save_rankings(ratings, path)
