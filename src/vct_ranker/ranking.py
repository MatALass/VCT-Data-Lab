from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

DEFAULT_MAX_LOSSES = 3


@dataclass(frozen=True)
class DuelResult:
    winner: str
    loser: str
    role: str
    region: str


def make_player_key(player: str, team: str | None = None) -> str:
    safe_player = str(player).strip()
    safe_team = str(team or "FA").strip()
    return f"{safe_player}__{safe_team}"


def empty_player_record() -> dict[str, int]:
    return {"wins": 0, "losses": 0, "duels": 0}


def normalize_ranking_state(raw_state: dict[str, Any] | None) -> dict[str, dict[str, int]]:
    """Accept both the new tournament format and the old Elo JSON format.

    Old format was {player_key: 1000.0}. New format is
    {player_key: {wins: int, losses: int, duels: int}}.
    """
    if not raw_state:
        return {}

    normalized: dict[str, dict[str, int]] = {}
    for player_key, value in raw_state.items():
        if isinstance(value, dict):
            wins = int(value.get("wins", 0) or 0)
            losses = int(value.get("losses", 0) or 0)
            duels = int(value.get("duels", wins + losses) or 0)
        else:
            # Backward compatibility: old Elo values cannot be converted to preferences safely.
            wins = 0
            losses = 0
            duels = 0
        normalized[str(player_key)] = {"wins": wins, "losses": losses, "duels": duels}
    return normalized


def record_duel_result(
    state: dict[str, dict[str, int]],
    winner_key: str,
    loser_key: str,
) -> dict[str, dict[str, int]]:
    updated = normalize_ranking_state(state)

    winner = updated.get(winner_key, empty_player_record()).copy()
    loser = updated.get(loser_key, empty_player_record()).copy()

    winner["wins"] += 1
    winner["duels"] += 1

    loser["losses"] += 1
    loser["duels"] += 1

    updated[winner_key] = winner
    updated[loser_key] = loser
    return updated


def player_stats(
    state: dict[str, dict[str, int]],
    player_key: str,
    *,
    max_losses: int = DEFAULT_MAX_LOSSES,
) -> dict[str, float | int | bool]:
    record = normalize_ranking_state(state).get(player_key, empty_player_record())
    wins = int(record.get("wins", 0))
    losses = int(record.get("losses", 0))
    duels = int(record.get("duels", wins + losses))
    active = losses < max_losses
    win_rate = wins / duels if duels > 0 else 0.0

    # Score intentionally transparent: first survive, then win rate, then volume.
    tournament_score = (wins * 100.0) - (losses * 130.0) + (win_rate * 50.0)

    return {
        "user_wins": wins,
        "user_losses": losses,
        "user_duels": duels,
        "user_win_rate": win_rate,
        "eliminated": not active,
        "losses_remaining": max(max_losses - losses, 0),
        "tournament_score": tournament_score,
    }


def build_ranking(
    players: pd.DataFrame,
    state: dict[str, dict[str, int]],
    role: str | None = None,
    *,
    max_losses: int = DEFAULT_MAX_LOSSES,
) -> pd.DataFrame:
    df = players.copy()
    if role and role != "All":
        df = df[df["inferred_role"] == role].copy()

    if df.empty:
        return df

    stats = df["player_key"].map(lambda key: player_stats(state, str(key), max_losses=max_losses))
    stats_df = pd.DataFrame(list(stats), index=df.index)
    df = pd.concat([df, stats_df], axis=1)

    sort_columns = ["eliminated", "tournament_score", "user_win_rate", "user_wins", "rating", "acs"]
    existing_sort_columns = [column for column in sort_columns if column in df.columns]
    ascending = [True, False, False, False, False, False][: len(existing_sort_columns)]
    df = df.sort_values(existing_sort_columns, ascending=ascending)
    df["rank"] = range(1, len(df) + 1)
    return df
