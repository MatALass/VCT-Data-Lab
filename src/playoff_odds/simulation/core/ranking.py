from __future__ import annotations
from collections import defaultdict
from typing import Any, Callable

def stage_map_diff(state: dict[str, Any], team: str) -> int:
    t = state['teams'][team]
    return t['maps_won'] - t['maps_lost']

def stage_round_diff(state: dict[str, Any], team: str) -> int:
    t = state['teams'][team]
    return t['rounds_won'] - t['rounds_lost']

def h2h_values(state: dict[str, Any], teams: list[str]) -> dict[str, dict[str, int]]:
    vals = {team: {'match': 0, 'map_diff': 0, 'round_diff': 0} for team in teams}
    for team in teams:
        for opp in teams:
            if team == opp:
                continue
            rec = state['h2h'][team][opp]
            vals[team]['match'] += rec['matches']
            vals[team]['map_diff'] += rec['maps_for'] - rec['maps_against']
            vals[team]['round_diff'] += rec['rounds_for'] - rec['rounds_against']
    return vals

def split_into_equal_buckets(items: list[str], metric_fn: Callable[[str], int]) -> list[list[str]]:
    if not items:
        return []
    scored = [(item, metric_fn(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    buckets: list[list[str]] = []
    current_bucket = [scored[0][0]]
    current_value = scored[0][1]
    for item, value in scored[1:]:
        if value == current_value:
            current_bucket.append(item)
        else:
            buckets.append(current_bucket)
            current_bucket = [item]
            current_value = value
    buckets.append(current_bucket)
    return buckets

def resolve_tie_official(state: dict[str, Any], tied_teams: list[str], rng=None) -> list[str]:
    if len(tied_teams) <= 1:
        return tied_teams
    if len(tied_teams) == 2:
        a, b = tied_teams
        match_score = state['h2h'][a][b]['matches']
        if match_score > 0:
            return [a, b]
        if match_score < 0:
            return [b, a]
        order = tied_teams[:]
        if rng is None:
            order.sort()
            return order
        rng.shuffle(order)
        return order
    h2h = h2h_values(state, tied_teams)
    criteria = [lambda t: h2h[t]['match'], lambda t: h2h[t]['map_diff'], lambda t: h2h[t]['round_diff'], lambda t: stage_map_diff(state, t), lambda t: stage_round_diff(state, t)]
    teams = tied_teams[:]
    for metric_fn in criteria:
        buckets = split_into_equal_buckets(teams, metric_fn)
        if len(buckets) == 1 and len(buckets[0]) == len(teams):
            continue
        resolved: list[str] = []
        for bucket in buckets:
            resolved.extend(bucket if len(bucket) == 1 else resolve_tie_official(state, bucket, rng))
        return resolved
    fallback = teams[:]
    if rng is None:
        fallback.sort()
        return fallback
    rng.shuffle(fallback)
    return fallback

def rank_group_official(state: dict[str, Any], group_name: str, rng=None) -> list[dict[str, Any]]:
    teams = [t['team'] for t in state['teams'].values() if t['group'] == group_name]
    win_buckets: dict[int, list[str]] = defaultdict(list)
    for team in teams:
        win_buckets[state['teams'][team]['wins']].append(team)
    ordered: list[str] = []
    for wins in sorted(win_buckets.keys(), reverse=True):
        ordered.extend(resolve_tie_official(state, win_buckets[wins], rng))
    return [state['teams'][team] for team in ordered]

def final_standings_payload(rankings: dict[str, list[dict[str, Any]]], group_name: str) -> list[dict[str, Any]]:
    payload = []
    for rank, team_state in enumerate(rankings[group_name], start=1):
        payload.append({'rank': rank, 'team': team_state['team'], 'wins': team_state['wins'], 'losses': team_state['losses'], 'mapDiff': team_state['maps_won'] - team_state['maps_lost'], 'roundDiff': team_state['rounds_won'] - team_state['rounds_lost']})
    return payload
