from __future__ import annotations
import argparse
from collections import Counter
import pandas as pd
from playoff_odds.simulation.core import build_state, clone_state, exact_winner_only_bounds, export_frontend_json, force_match_result, load_config, rank_group_official

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a deterministic what-if snapshot by forcing one or more match winners.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--force", action="append", default=[], help='Format: "TEAM_A vs TEAM_B=WINNER"')
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()

def parse_forces(force_args: list[str]) -> dict[str, str]:
    forced: dict[str, str] = {}
    for item in force_args:
        if "=" not in item:
            raise ValueError(f"Invalid force expression: {item!r}")
        left, winner = item.split("=", maxsplit=1)
        forced[left.strip()] = winner.strip()
    return forced

def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    config["seed_internal"] = args.seed
    forced = parse_forces(args.force)
    initial_state = build_state(config)
    state = clone_state(initial_state)
    for _, team_a, team_b in config["remaining_matches"]:
        force_match_result(state, team_a, team_b, forced.get(f"{team_a} vs {team_b}", team_a), config)
    rankings = {group: rank_group_official(state, group) for group in sorted({row[0] for row in config["remaining_matches"]})}
    summary_rows = []
    position_rows = []
    max_group_size = max(sum(1 for t in state["teams"].values() if t["group"] == g) for g in {t["group"] for t in state["teams"].values()})
    for group_name, ranked in rankings.items():
        for pos, team_state in enumerate(ranked, start=1):
            summary_rows.append({"team": team_state["team"], "group": group_name, "qualify_count": 1 if pos <= config["qualification_slots"] else 0, "qualify_prob": 1.0 if pos <= config["qualification_slots"] else 0.0, "best_rank_seen": pos, "worst_rank_seen": pos})
            row = {"team": team_state["team"], "group": group_name}
            for p in range(1, max_group_size + 1):
                row[f"P{p}"] = 1.0 if p == pos else 0.0
            position_rows.append(row)
    summary_df = pd.DataFrame(summary_rows)
    position_df = pd.DataFrame(position_rows)
    exact_bounds = exact_winner_only_bounds(initial_state, config["remaining_matches"], config)
    teams = list(summary_df["team"].unique())
    export_frontend_json(
        config=config,
        summary_df=summary_df,
        position_df=position_df,
        best_scenario={},
        worst_scenario={},
        qualify_paths={team: Counter() for team in teams},
        eliminate_paths={team: Counter() for team in teams},
        exact_bounds=exact_bounds,
        match_impacts={},
        key_matches=[],
        remaining_matches=config["remaining_matches"],
        output_json=args.output_json,
    )
    print("Deterministic scenario snapshot written.")

if __name__ == "__main__":
    main()
