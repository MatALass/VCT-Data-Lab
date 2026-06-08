from __future__ import annotations
import itertools, time
from collections import Counter, defaultdict
from typing import Any
import numpy as np
import pandas as pd
from .match_ops import apply_match_result_with_config, force_match_result, simulate_single_match
from .ranking import final_standings_payload, rank_group_official
from .state import clone_state

def simulate_season_once(initial_state: dict[str, Any], remaining_matches: list[list[Any]], config: dict[str, Any], rng=None):
    state = clone_state(initial_state)
    match_results = []
    for _, team_a, team_b in remaining_matches:
        match_results.append(simulate_single_match(state, team_a, team_b, config))
    group_names = sorted({row[0] for row in remaining_matches})
    rankings = {group: rank_group_official(state, group, rng) for group in group_names}
    return state, rankings, match_results

def monte_carlo(initial_state: dict[str, Any], remaining_matches: list[list[Any]], config: dict[str, Any], show_progress: bool = False, progress_step: int = 1000):
    n = int(config['n_simulations']); slots = int(config['qualification_slots']); teams = sorted(initial_state['teams'].keys())
    groups = {team: initial_state['teams'][team]['group'] for team in teams}; rng = np.random.default_rng(config.get('seed_internal', 42))
    position_counter = defaultdict(Counter); best_rank = {team: float('inf') for team in teams}; worst_rank = {team: float('-inf') for team in teams}
    best_scenario = {team: None for team in teams}; worst_scenario = {team: None for team in teams}; qualify_path_counter = defaultdict(Counter); eliminate_path_counter = defaultdict(Counter)
    start_time = time.perf_counter()
    if show_progress: print(f'Starting Monte Carlo with {n:,} simulations (progress every {progress_step:,})', flush=True)
    max_group_size = max(sum(1 for t in initial_state['teams'].values() if t['group'] == g) for g in {t['group'] for t in initial_state['teams'].values()})
    for i in range(1, n + 1):
        _, rankings, match_results = simulate_season_once(initial_state, remaining_matches, config, rng); winner_signature = tuple(item['winner'] for item in match_results)
        for group_name, ranked_teams in rankings.items():
            for pos, team_state in enumerate(ranked_teams, start=1):
                team = team_state['team']; position_counter[team][pos] += 1
                (qualify_path_counter if pos <= slots else eliminate_path_counter)[team][winner_signature] += 1
                if pos < best_rank[team]:
                    best_rank[team] = pos
                    best_scenario[team] = {'kind': 'bestCase', 'finalRank': pos, 'finalRecord': {'wins': team_state['wins'], 'losses': team_state['losses'], 'mapDiff': team_state['maps_won'] - team_state['maps_lost'], 'roundDiff': team_state['rounds_won'] - team_state['rounds_lost']}, 'matchResults': match_results, 'finalStandings': final_standings_payload(rankings, group_name), 'note': 'Best observed scenario within the Monte Carlo sample. This is not guaranteed to be the exact global optimum.'}
                if pos > worst_rank[team]:
                    worst_rank[team] = pos
                    worst_scenario[team] = {'kind': 'worstCase', 'finalRank': pos, 'finalRecord': {'wins': team_state['wins'], 'losses': team_state['losses'], 'mapDiff': team_state['maps_won'] - team_state['maps_lost'], 'roundDiff': team_state['rounds_won'] - team_state['rounds_lost']}, 'matchResults': match_results, 'finalStandings': final_standings_payload(rankings, group_name), 'note': 'Worst observed scenario within the Monte Carlo sample. This is not guaranteed to be the exact global minimum.'}
        if show_progress and (i % progress_step == 0 or i == n):
            elapsed = time.perf_counter() - start_time; avg_time = elapsed / i; eta = avg_time * (n - i); pct = 100 * i / n
            print(f'[{pct:6.2f}%] {i:,}/{n:,} | elapsed={elapsed:8.2f}s | eta={eta:8.2f}s', flush=True)
    summary_rows = []; position_rows = []
    for team in teams:
        qualify_prob = sum(position_counter[team][pos] / n for pos in range(1, slots + 1))
        summary_rows.append({'team': team, 'group': groups[team], 'qualify_count': int(round(qualify_prob * n)), 'qualify_prob': qualify_prob, 'best_rank_seen': int(best_rank[team]), 'worst_rank_seen': int(worst_rank[team])})
        row = {'team': team, 'group': groups[team]}; total_prob = 0.0
        for pos in range(1, max_group_size + 1):
            prob = position_counter[team][pos] / n; row[f'P{pos}'] = prob; total_prob += prob
        if abs(total_prob - 1.0) > 1e-9: raise ValueError(f'Invalid position probability sum for {team}: {total_prob}')
        position_rows.append(row)
    return pd.DataFrame(summary_rows), pd.DataFrame(position_rows), best_scenario, worst_scenario, qualify_path_counter, eliminate_path_counter

def add_expected_rank(position_df: pd.DataFrame) -> pd.Series:
    position_cols = sorted([c for c in position_df.columns if c.startswith('P')], key=lambda x: int(x[1:]))
    exp_rank = np.zeros(len(position_df), dtype=float)
    for col in position_cols: exp_rank += int(col[1:]) * position_df[col].to_numpy(dtype=float)
    return pd.Series(exp_rank, index=position_df.index)

def conditional_probability(initial_state: dict[str, Any], remaining_matches: list[list[Any]], config: dict[str, Any], forced_match_index: int, forced_winner: str, team_name: str) -> float:
    slots = int(config['qualification_slots']); n = int(config.get('conditional_simulations', max(1000, config['n_simulations'] // 10))); qualifies = 0
    rng = np.random.default_rng(config.get('seed_internal', 42) + forced_match_index)
    for _ in range(n):
        state = clone_state(initial_state)
        for idx, (_, team_a, team_b) in enumerate(remaining_matches):
            force_match_result(state, team_a, team_b, forced_winner, config) if idx == forced_match_index else simulate_single_match(state, team_a, team_b, config)
        rankings = {group: rank_group_official(state, group, rng) for group in sorted({row[0] for row in remaining_matches})}
        for _, ranked_teams in rankings.items():
            for pos, team_state in enumerate(ranked_teams, start=1):
                if team_state['team'] == team_name and pos <= slots: qualifies += 1
    return qualifies / n

def compute_match_impacts(initial_state: dict[str, Any], remaining_matches: list[list[Any]], config: dict[str, Any], baseline_summary: pd.DataFrame) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    baseline = {row['team']: float(row['qualify_prob']) for row in baseline_summary.to_dict(orient='records')}; per_group = defaultdict(list); key_matches = []
    for idx, (group, team_a, team_b) in enumerate(remaining_matches):
        impacted = []; max_delta = 0.0; candidate_teams = [t for t, s in initial_state['teams'].items() if s['group'] == group]
        for team in candidate_teams:
            p_if_a = conditional_probability(initial_state, remaining_matches, config, idx, team_a, team); p_if_b = conditional_probability(initial_state, remaining_matches, config, idx, team_b, team)
            impacted.append({'team': team, 'ifTeamAWins': p_if_a - baseline[team], 'ifTeamBWins': p_if_b - baseline[team]}); max_delta = max(max_delta, abs(p_if_a - p_if_b))
        impacted.sort(key=lambda x: max(abs(x['ifTeamAWins']), abs(x['ifTeamBWins'])), reverse=True)
        per_group[group].append({'match': f'{team_a} vs {team_b}', 'importance': max_delta, 'teamImpacts': impacted[:5]})
        key_matches.append({'group': group, 'match': f'{team_a} vs {team_b}', 'importance': max_delta, 'headline': 'High leverage match for the qualification race'})
    for group in per_group: per_group[group] = sorted(per_group[group], key=lambda x: x['importance'], reverse=True)
    return per_group, sorted(key_matches, key=lambda x: x['importance'], reverse=True)[:5]

def top_paths(counter: Counter, remaining_matches: list[list[Any]], total_runs: int, top_n: int = 3) -> list[dict[str, Any]]:
    paths = []
    for signature, count in counter.most_common(top_n):
        match_results = []
        for winner, (_, team_a, team_b) in zip(signature, remaining_matches):
            loser = team_b if winner == team_a else team_a; match_results.append({'match': f'{team_a} vs {team_b}', 'winner': winner, 'loser': loser})
        paths.append({'share': count / total_runs, 'matches': match_results})
    return paths

def exact_winner_only_bounds(initial_state: dict[str, Any], remaining_matches: list[list[Any]], config: dict[str, Any]) -> dict[str, dict[str, int]]:
    teams = sorted(initial_state['teams'].keys()); bounds = {team: {'best': float('inf'), 'worst': float('-inf')} for team in teams}
    for outcome_bits in itertools.product([0, 1], repeat=len(remaining_matches)):
        state = clone_state(initial_state)
        for bit, (_, team_a, team_b) in zip(outcome_bits, remaining_matches):
            winner = team_a if bit == 0 else team_b; loser = team_b if winner == team_a else team_a
            apply_match_result_with_config(state, winner, loser, 2, 0, 'extreme', team_a, team_b, config)
        rankings = {group: rank_group_official(state, group) for group in sorted({row[0] for row in remaining_matches})}
        for _, ranked_teams in rankings.items():
            for pos, team_state in enumerate(ranked_teams, start=1):
                team = team_state['team']; bounds[team]['best'] = min(bounds[team]['best'], pos); bounds[team]['worst'] = max(bounds[team]['worst'], pos)
    return bounds

def build_auto_insights(payload_groups: list[dict[str, Any]], key_matches: list[dict[str, Any]], model_type: str) -> list[str]:
    insights = []
    if key_matches: insights.append(f"{key_matches[0]['match']} is currently the highest-leverage match on the board.")
    for group in payload_groups:
        bubble = [t for t in group['teams'] if 0.25 <= t['qualifyProb'] <= 0.75]
        if bubble: insights.append(f"{group['name']} is contested because {', '.join(t['team'] for t in bubble[:3])} all remain exposed to the cutoff.")
    strongest = sorted([team for group in payload_groups for team in group['teams']], key=lambda x: x['qualifyProb'], reverse=True)[:2]
    if strongest: insights.append(f"{strongest[0]['team']} is the strongest lock in the current simulation snapshot.")
    insights.append(f"The current simulation model is '{model_type}', and tie-breaks follow VCT EMEA head-to-head criteria before falling back to stage map and round differential.")
    return insights[:5]
