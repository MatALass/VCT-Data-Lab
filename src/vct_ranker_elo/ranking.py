from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

DEFAULT_RATING = 1000.0
DEFAULT_K_FACTOR = 32.0


@dataclass(frozen=True)
class DuelResult:
    winner: str
    loser: str
    role: str


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))


def update_elo(
    ratings: dict[str, float],
    winner: str,
    loser: str,
    *,
    k_factor: float = DEFAULT_K_FACTOR,
) -> dict[str, float]:
    winner_rating = ratings.get(winner, DEFAULT_RATING)
    loser_rating = ratings.get(loser, DEFAULT_RATING)

    winner_expected = expected_score(winner_rating, loser_rating)
    loser_expected = expected_score(loser_rating, winner_rating)

    ratings[winner] = winner_rating + k_factor * (1.0 - winner_expected)
    ratings[loser] = loser_rating + k_factor * (0.0 - loser_expected)
    return ratings


def build_ranking(players: pd.DataFrame, ratings: dict[str, float], role: str | None = None) -> pd.DataFrame:
    df = players.copy()
    if role and role != "All":
        df = df[df["inferred_role"] == role].copy()

    if df.empty:
        return df

    df["user_rating"] = df["player_key"].map(lambda key: ratings.get(key, DEFAULT_RATING))
    df["rank"] = df["user_rating"].rank(method="first", ascending=False).astype(int)
    return df.sort_values(["user_rating", "rating", "acs"], ascending=[False, False, False])


def make_player_key(player: str, team: str | None = None) -> str:
    safe_player = str(player).strip()
    safe_team = str(team or "FA").strip()
    return f"{safe_player}__{safe_team}"
