from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from playoff_odds.simulation.core import build_state, compute_match_impacts, exact_winner_only_bounds, export_frontend_json, load_config, monte_carlo

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Monte Carlo playoff simulation and export frontend JSON.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--show-progress", action="store_true")
    parser.add_argument("--progress-step", type=int, default=1000)
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)
    config = load_config(args.config)
    config["seed_internal"] = args.seed
    initial_state = build_state(config)
    summary_df, position_df, best_scenario, worst_scenario, qualify_paths, eliminate_paths = monte_carlo(
        initial_state=initial_state,
        remaining_matches=config["remaining_matches"],
        config=config,
        show_progress=args.show_progress,
        progress_step=args.progress_step,
    )
    match_impacts, key_matches = compute_match_impacts(initial_state, config["remaining_matches"], config, summary_df)
    exact_bounds = exact_winner_only_bounds(initial_state, config["remaining_matches"], config)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(output_dir / "summary.csv", index=False)
        position_df.to_csv(output_dir / "positions.csv", index=False)
        print(f"Saved CSV outputs to: {output_dir}")
    export_frontend_json(
        config=config,
        summary_df=summary_df,
        position_df=position_df,
        best_scenario=best_scenario,
        worst_scenario=worst_scenario,
        qualify_paths=qualify_paths,
        eliminate_paths=eliminate_paths,
        exact_bounds=exact_bounds,
        match_impacts=match_impacts,
        key_matches=key_matches,
        remaining_matches=config["remaining_matches"],
        output_json=args.output_json,
    )

if __name__ == "__main__":
    main()
