from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from typing import Any
from .match_ops import record_h2h

def build_state(config: dict[str, Any]) -> dict[str, Any]:
    state = {
        "teams": {},
        "h2h": defaultdict(
            lambda: defaultdict(
                lambda: {
                    "matches": 0,
                    "maps_for": 0,
                    "maps_against": 0,
                    "rounds_for": 0,
                    "rounds_against": 0,
                }
            )
        ),
    }
    initial_ratings = config.get("initial_ratings", {})
    for team, group, wins, losses, maps_won, maps_lost, rounds_won, rounds_lost in config["standings"]:
        state["teams"][team] = {
            "team": team,
            "group": group,
            "wins": int(wins),
            "losses": int(losses),
            "maps_won": int(maps_won),
            "maps_lost": int(maps_lost),
            "rounds_won": int(rounds_won),
            "rounds_lost": int(rounds_lost),
            "rating": float(initial_ratings.get(team, 1500.0)),
        }
    for match in config.get("played_matches", []):
        team_a = str(match["teamA"])
        team_b = str(match["teamB"])
        winner_is_a = str(match["winner"]) == team_a
        record_h2h(
            state,
            team_a,
            team_b,
            int(match["winnerMaps"]) if winner_is_a else int(match["loserMaps"]),
            int(match["loserMaps"]) if winner_is_a else int(match["winnerMaps"]),
            int(match["teamARounds"]),
            int(match["teamBRounds"]),
        )
    return state

def clone_state(state: dict[str, Any]) -> dict[str, Any]:
    return {"teams": deepcopy(state["teams"]), "h2h": deepcopy(state["h2h"])}
