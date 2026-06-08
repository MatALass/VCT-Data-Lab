from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
RANKINGS_PATH = PROCESSED_DIR / "user_rankings.json"
PLAYERS_PATH = PROCESSED_DIR / "vlr_players_processed.csv"


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)



from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

DATA_DIR = Path("data")
PLAYERS_FILE = DATA_DIR / "players.csv"

PLAYER_COLUMNS = [
    "player",
    "team",
    "role",
    "agent",
    "map",
    "match_id",
    "pick_count",
]


def load_players(path: Path = PLAYERS_FILE) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame(columns=PLAYER_COLUMNS)


def save_players(df: pd.DataFrame, path: Path = PLAYERS_FILE) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_ratings(path: Path = RANKINGS_PATH) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return {str(k): float(v) for k, v in raw.items()}


def save_ratings(ratings: dict[str, float], path: Path = RANKINGS_PATH) -> None:
    ensure_dirs()
    with path.open("w", encoding="utf-8") as f:
        json.dump(ratings, f, indent=2, ensure_ascii=False)
