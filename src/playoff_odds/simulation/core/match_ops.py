from __future__ import annotations
from typing import Any
import numpy as np
from .constants import REALISTIC_WINNING_MAP_SCORES, REALISTIC_WINNING_MAP_WEIGHTS
from .models import update_elo, win_probability

def sample_winning_map_score(round_model: str) -> tuple[int, int]:
    if round_model == "extreme":
        return (13, 0)
    idx = np.random.choice(len(REALISTIC_WINNING_MAP_SCORES), p=REALISTIC_WINNING_MAP_WEIGHTS)
    return REALISTIC_WINNING_MAP_SCORES[idx]

def default_round_totals_for_score(winner_maps: int, loser_maps: int, round_model: str) -> tuple[int, int]:
    if round_model == "extreme":
        if (winner_maps, loser_maps) == (2, 0):
            return 26, 0
        if (winner_maps, loser_maps) == (2, 1):
            return 39, 13
    if (winner_maps, loser_maps) == (2, 0):
        return 26, 16
    if (winner_maps, loser_maps) == (2, 1):
        return 37, 29
    raise ValueError(f"Unsupported scoreline for default round totals: {winner_maps}-{loser_maps}")

def sample_match_score(p_winner: float, p_clean_win_base: float) -> tuple[int, int]:
    confidence = abs(p_winner - 0.5) * 2.0
    p_clean = min(0.85, max(0.35, p_clean_win_base + 0.20 * (confidence - 0.5)))
    return (2, 0) if np.random.rand() < p_clean else (2, 1)

def record_h2h(state: dict[str, Any], team_a: str, team_b: str, a_maps: int, b_maps: int, a_rounds: int, b_rounds: int) -> None:
    if a_maps > b_maps:
        state["h2h"][team_a][team_b]["matches"] += 1
        state["h2h"][team_b][team_a]["matches"] -= 1
    else:
        state["h2h"][team_a][team_b]["matches"] -= 1
        state["h2h"][team_b][team_a]["matches"] += 1
    state["h2h"][team_a][team_b]["maps_for"] += a_maps
    state["h2h"][team_a][team_b]["maps_against"] += b_maps
    state["h2h"][team_b][team_a]["maps_for"] += b_maps
    state["h2h"][team_b][team_a]["maps_against"] += a_maps
    state["h2h"][team_a][team_b]["rounds_for"] += a_rounds
    state["h2h"][team_a][team_b]["rounds_against"] += b_rounds
    state["h2h"][team_b][team_a]["rounds_for"] += b_rounds
    state["h2h"][team_b][team_a]["rounds_against"] += a_rounds

def apply_match_result(state: dict[str, Any], winner: str, loser: str, winner_maps: int, loser_maps: int, round_model: str, team_a: str, team_b: str) -> dict[str, int]:
    state["teams"][winner]["wins"] += 1
    state["teams"][loser]["losses"] += 1
    state["teams"][winner]["maps_won"] += winner_maps
    state["teams"][winner]["maps_lost"] += loser_maps
    state["teams"][loser]["maps_won"] += loser_maps
    state["teams"][loser]["maps_lost"] += winner_maps
    a_rounds_total = 0
    b_rounds_total = 0
    for _ in range(winner_maps):
        w, l = sample_winning_map_score(round_model)
        if winner == team_a:
            a_rounds_total += w
            b_rounds_total += l
        else:
            b_rounds_total += w
            a_rounds_total += l
        state["teams"][winner]["rounds_won"] += w
        state["teams"][winner]["rounds_lost"] += l
        state["teams"][loser]["rounds_won"] += l
        state["teams"][loser]["rounds_lost"] += w
    for _ in range(loser_maps):
        l, w = sample_winning_map_score(round_model)
        if winner == team_a:
            a_rounds_total += w
            b_rounds_total += l
        else:
            b_rounds_total += w
            a_rounds_total += l
        state["teams"][winner]["rounds_won"] += w
        state["teams"][winner]["rounds_lost"] += l
        state["teams"][loser]["rounds_won"] += l
        state["teams"][loser]["rounds_lost"] += w
    a_maps = winner_maps if winner == team_a else loser_maps
    b_maps = loser_maps if winner == team_a else winner_maps
    record_h2h(state, team_a, team_b, a_maps, b_maps, a_rounds_total, b_rounds_total)
    return {"a_rounds_total": a_rounds_total, "b_rounds_total": b_rounds_total}

def apply_match_result_with_config(state: dict[str, Any], winner: str, loser: str, winner_maps: int, loser_maps: int, round_model: str, team_a: str, team_b: str, config: dict[str, Any]) -> dict[str, int]:
    result = apply_match_result(state, winner, loser, winner_maps, loser_maps, round_model, team_a, team_b)
    update_elo(state, winner, loser, config)
    return result

def simulate_single_match(state: dict[str, Any], team_a: str, team_b: str, config: dict[str, Any]) -> dict[str, str]:
    p_a = win_probability(state, team_a, team_b, config)
    a_wins = np.random.rand() < p_a
    if a_wins:
        winner, loser, winner_p = team_a, team_b, p_a
    else:
        winner, loser, winner_p = team_b, team_a, 1.0 - p_a
    winner_maps, loser_maps = sample_match_score(winner_p, config["p_clean_win_base"])
    apply_match_result_with_config(state, winner, loser, winner_maps, loser_maps, config["round_model"], team_a, team_b, config)
    return {"group": state["teams"][winner]["group"], "match": f"{team_a} vs {team_b}", "result": f"{winner} {winner_maps}-{loser_maps}", "winner": winner}

def force_match_result(state: dict[str, Any], team_a: str, team_b: str, forced_winner: str, config: dict[str, Any]) -> dict[str, str]:
    winner = forced_winner
    loser = team_b if forced_winner == team_a else team_a
    p_winner = win_probability(state, winner, loser, config) if winner == team_a else 1.0 - win_probability(state, team_a, team_b, config)
    winner_maps, loser_maps = sample_match_score(p_winner, config["p_clean_win_base"])
    apply_match_result_with_config(state, winner, loser, winner_maps, loser_maps, config["round_model"], team_a, team_b, config)
    return {"group": state["teams"][winner]["group"], "match": f"{team_a} vs {team_b}", "result": f"{winner} {winner_maps}-{loser_maps}", "winner": winner}
