from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd

from vct_ranker.ranking import DEFAULT_MAX_LOSSES, player_stats


@dataclass(frozen=True)
class DuelRules:
    role_confidence_min: float = 0.70
    min_rounds: int = 0
    min_vlr_rating: float = 1.00
    avoid_same_team: bool = True
    max_losses: int = DEFAULT_MAX_LOSSES
    prefer_close_records: bool = True


def eligible_players(players: pd.DataFrame, role: str, region: str, rules: DuelRules) -> pd.DataFrame:
    df = players.copy()
    df = df[df["inferred_role"] == role]

    if region != "All" and "vct_region" in df.columns:
        df = df[df["vct_region"] == region]

    if "role_confidence" in df.columns:
        df = df[pd.to_numeric(df["role_confidence"], errors="coerce") >= rules.role_confidence_min]
    if "rounds" in df.columns:
        df = df[pd.to_numeric(df["rounds"], errors="coerce") >= rules.min_rounds]
    if "rating" in df.columns:
        df = df[pd.to_numeric(df["rating"], errors="coerce") >= rules.min_vlr_rating]

    return df.copy()


def active_players(
    players: pd.DataFrame,
    ranking_state: dict[str, dict[str, int]],
    rules: DuelRules,
) -> pd.DataFrame:
    if players.empty:
        return players.copy()
    df = players.copy()
    df["user_losses"] = df["player_key"].map(
        lambda key: int(player_stats(ranking_state, str(key), max_losses=rules.max_losses)["user_losses"])
    )
    return df[df["user_losses"] < rules.max_losses].copy()


def pick_same_role_duel(
    players: pd.DataFrame,
    ranking_state: dict[str, dict[str, int]],
    rules: DuelRules,
) -> tuple[pd.Series, pd.Series] | None:
    df = active_players(players, ranking_state, rules)
    if len(df) < 2:
        return None

    df["user_duels"] = df["player_key"].map(
        lambda key: int(player_stats(ranking_state, str(key), max_losses=rules.max_losses)["user_duels"])
    )
    df["user_losses"] = df["player_key"].map(
        lambda key: int(player_stats(ranking_state, str(key), max_losses=rules.max_losses)["user_losses"])
    )
    df["user_wins"] = df["player_key"].map(
        lambda key: int(player_stats(ranking_state, str(key), max_losses=rules.max_losses)["user_wins"])
    )

    # Prioritize players with fewer subjective comparisons so the tournament converges evenly.
    min_duels = int(df["user_duels"].min())
    first_pool = df[df["user_duels"] <= min_duels + 1]
    p1 = first_pool.sample(1, random_state=random.randint(0, 1_000_000)).iloc[0]

    candidates = df[df["player_key"] != p1["player_key"]].copy()

    if rules.avoid_same_team and "team" in candidates.columns:
        not_same_team = candidates[candidates["team"] != p1.get("team")]
        if len(not_same_team) >= 1:
            candidates = not_same_team

    if rules.prefer_close_records:
        same_losses = candidates[candidates["user_losses"] == p1["user_losses"]]
        if len(same_losses) >= 1:
            candidates = same_losses
        close_duels = candidates[(candidates["user_duels"] - p1["user_duels"]).abs() <= 2]
        if len(close_duels) >= 1:
            candidates = close_duels

    p2 = candidates.sample(1, random_state=random.randint(0, 1_000_000)).iloc[0]
    return p1, p2
