from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd

from vct_ranker_elo.ranking import DEFAULT_RATING


@dataclass(frozen=True)
class DuelRules:
    role_confidence_min: float = 0.70
    min_rounds: int = 0
    min_vlr_rating: float = 1.00
    max_elo_gap: float = 125.0
    avoid_same_team: bool = True


def eligible_players(players: pd.DataFrame, role: str, region: str, rules: DuelRules) -> pd.DataFrame:
    df = players.copy()
    df = df[df["inferred_role"] == role]

    if region != "All" and "vct_region" in df.columns:
        df = df[df["vct_region"] == region]

    if "role_confidence" in df.columns:
        df = df[df["role_confidence"] >= rules.role_confidence_min]
    if "rounds" in df.columns:
        df = df[pd.to_numeric(df["rounds"], errors="coerce") >= rules.min_rounds]
    if "rating" in df.columns:
        df = df[pd.to_numeric(df["rating"], errors="coerce") >= rules.min_vlr_rating]

    return df.copy()


def pick_same_role_duel(players: pd.DataFrame, ratings: dict[str, float], rules: DuelRules) -> tuple[pd.Series, pd.Series] | None:
    if len(players) < 2:
        return None

    df = players.copy()
    df["user_rating"] = df["player_key"].map(lambda key: ratings.get(key, DEFAULT_RATING))

    p1 = df.sample(1, random_state=random.randint(0, 1_000_000)).iloc[0]
    candidates = df[df["player_key"] != p1["player_key"]].copy()

    if rules.avoid_same_team and "team" in candidates.columns:
        not_same_team = candidates[candidates["team"] != p1.get("team")]
        if len(not_same_team) >= 1:
            candidates = not_same_team

    close = candidates[(candidates["user_rating"] - p1["user_rating"]).abs() <= rules.max_elo_gap]
    if len(close) >= 1:
        candidates = close

    p2 = candidates.sample(1, random_state=random.randint(0, 1_000_000)).iloc[0]
    return p1, p2
