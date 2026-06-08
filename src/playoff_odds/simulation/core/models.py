from __future__ import annotations
import math
from typing import Any

def logistic(x: float, scale: float) -> float:
    return 1.0 / (1.0 + math.exp(-x / scale))

def compute_standings_score(team_state: dict[str, Any], weights: dict[str, float]) -> float:
    map_diff = team_state['maps_won'] - team_state['maps_lost']
    round_diff = team_state['rounds_won'] - team_state['rounds_lost']
    return weights['wins'] * team_state['wins'] + weights['map_diff'] * map_diff + weights['round_diff'] * round_diff

def win_probability(state: dict[str, Any], team_a: str, team_b: str, config: dict[str, Any]) -> float:
    if config.get('model_type', 'standings') == 'elo':
        elo_cfg = config.get('elo', {'scale': 400})
        ra = state['teams'][team_a]['rating']
        rb = state['teams'][team_b]['rating']
        return 1.0 / (1.0 + 10 ** ((rb - ra) / float(elo_cfg.get('scale', 400))))
    weights = config['rating_weights']
    sa = compute_standings_score(state['teams'][team_a], weights)
    sb = compute_standings_score(state['teams'][team_b], weights)
    return logistic(sa - sb, config['logistic_scale'])

def update_elo(state: dict[str, Any], winner: str, loser: str, config: dict[str, Any]) -> None:
    if config.get('model_type', 'standings') != 'elo':
        return
    elo_cfg = config.get('elo', {'k': 24, 'scale': 400})
    k = float(elo_cfg.get('k', 24))
    rw = state['teams'][winner]['rating']
    rl = state['teams'][loser]['rating']
    ew = 1.0 / (1.0 + 10 ** ((rl - rw) / float(elo_cfg.get('scale', 400))))
    el = 1.0 - ew
    state['teams'][winner]['rating'] = rw + k * (1.0 - ew)
    state['teams'][loser]['rating'] = rl + k * (0.0 - el)
