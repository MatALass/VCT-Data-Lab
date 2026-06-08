from __future__ import annotations
import argparse
import sys
from dataclasses import dataclass
from typing import Any
from playoff_odds.simulation.core import canonical_match_key, default_round_totals_for_score, load_config, save_config
from playoff_odds.simulation.run_simulation import main as run_simulation_main

@dataclass(frozen=True)
class MatchSelection:
    index: int
    group: str
    team_a: str
    team_b: str

    @property
    def label(self) -> str:
        return f"[{self.index}] {self.group}: {self.team_a} vs {self.team_b}"

class MatchUpdateError(ValueError):
    pass

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project console for simulation workflows and persisted match updates.")
    sub = parser.add_subparsers(dest="command", required=True)
    set_match = sub.add_parser("set-match-result", help="Persist the result of a remaining match into the config, then optionally regenerate the dataset JSON.")
    set_match.add_argument("--config", required=True)
    set_match.add_argument("--dataset", required=True)
    set_match.add_argument("--match")
    set_match.add_argument("--winner")
    set_match.add_argument("--score", choices=["2-0", "2-1"])
    set_match.add_argument("--seed", type=int, default=42)
    set_match.add_argument("--show-progress", action="store_true")
    set_match.add_argument("--progress-step", type=int, default=1000)
    set_match.add_argument("--output-dir", default="simulation/output")
    set_match.add_argument("--no-regenerate", action="store_true")

    list_matches = sub.add_parser("list-remaining-matches", help="Print remaining matches from the source config.")
    list_matches.add_argument("--config", required=True)
    return parser.parse_args()

def parse_match_label(match_label: str) -> tuple[str, str]:
    if " vs " not in match_label:
        raise MatchUpdateError(f'Invalid match label: {match_label!r}. Expected format "TEAM_A vs TEAM_B".')
    a, b = match_label.split(" vs ", maxsplit=1)
    return a.strip(), b.strip()

def list_remaining_matches(config: dict[str, Any]) -> list[MatchSelection]:
    return [MatchSelection(index=i + 1, group=g, team_a=a, team_b=b) for i, (g, a, b) in enumerate(config["remaining_matches"])]

def choose_match(config: dict[str, Any], requested_match: str | None) -> MatchSelection:
    matches = list_remaining_matches(config)
    if not matches:
        raise MatchUpdateError("No remaining matches are left in the config.")
    if requested_match:
        requested_key = canonical_match_key(*parse_match_label(requested_match))
        for match in matches:
            if canonical_match_key(match.team_a, match.team_b) == requested_key:
                return match
        raise MatchUpdateError(f"Match {requested_match!r} not found.")
    print("Remaining matches:")
    for match in matches:
        print(f"  {match.label}")
    raw_index = input("Choose a match number: ").strip()
    if not raw_index.isdigit():
        raise MatchUpdateError("The selected match number must be numeric.")
    idx = int(raw_index)
    for match in matches:
        if match.index == idx:
            return match
    raise MatchUpdateError(f"No match found for selection #{idx}.")

def choose_winner(match: MatchSelection, requested_winner: str | None) -> str:
    allowed = {match.team_a, match.team_b}
    winner = requested_winner or input(f"Winner ({match.team_a}/{match.team_b}): ").strip()
    if winner not in allowed:
        raise MatchUpdateError(f"Winner must be one of {sorted(allowed)}.")
    return winner

def choose_score(requested_score: str | None) -> tuple[int, int]:
    score_value = requested_score or input("Score (2-0 or 2-1): ").strip()
    if score_value not in {"2-0", "2-1"}:
        raise MatchUpdateError("Score must be either 2-0 or 2-1.")
    a, b = score_value.split("-")
    return int(a), int(b)

def find_standing_row(config: dict[str, Any], team_name: str) -> list[Any]:
    for row in config["standings"]:
        if row[0] == team_name:
            return row
    raise MatchUpdateError(f"Unknown team in standings: {team_name}")

def persist_match_result(config: dict[str, Any], match: MatchSelection, winner: str, winner_maps: int, loser_maps: int) -> dict[str, Any]:
    loser = match.team_b if winner == match.team_a else match.team_a
    round_winner, round_loser = default_round_totals_for_score(winner_maps, loser_maps, str(config["round_model"]))
    team_a_rounds = round_winner if winner == match.team_a else round_loser
    team_b_rounds = round_loser if winner == match.team_a else round_winner

    winner_row = find_standing_row(config, winner)
    loser_row = find_standing_row(config, loser)
    winner_row[2] += 1
    loser_row[3] += 1
    winner_row[4] += winner_maps
    winner_row[5] += loser_maps
    loser_row[4] += loser_maps
    loser_row[5] += winner_maps
    winner_row[6] += round_winner
    winner_row[7] += round_loser
    loser_row[6] += round_loser
    loser_row[7] += round_winner

    config["remaining_matches"] = [
        row for row in config["remaining_matches"]
        if canonical_match_key(row[1], row[2]) != canonical_match_key(match.team_a, match.team_b)
    ]
    config.setdefault("played_matches", []).append({
        "group": match.group,
        "teamA": match.team_a,
        "teamB": match.team_b,
        "winner": winner,
        "loser": loser,
        "winnerMaps": winner_maps,
        "loserMaps": loser_maps,
        "teamARounds": team_a_rounds,
        "teamBRounds": team_b_rounds,
        "source": "console-set-match-result",
    })
    return {
        "group": match.group,
        "match": f"{match.team_a} vs {match.team_b}",
        "winner": winner,
        "loser": loser,
        "score": f"{winner_maps}-{loser_maps}",
        "teamARounds": team_a_rounds,
        "teamBRounds": team_b_rounds,
    }

def rebuild_dataset(config_path: str, dataset_path: str, output_dir: str, seed: int, show_progress: bool, progress_step: int) -> None:
    previous_argv = sys.argv[:]
    argv = ["playoff_odds.simulation.run_simulation", "--config", config_path, "--output-json", dataset_path, "--output-dir", output_dir, "--seed", str(seed), "--progress-step", str(progress_step)]
    if show_progress:
        argv.append("--show-progress")
    try:
        sys.argv = argv
        run_simulation_main()
    finally:
        sys.argv = previous_argv

def command_set_match_result(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    match = choose_match(config, args.match)
    winner = choose_winner(match, args.winner)
    winner_maps, loser_maps = choose_score(args.score)
    summary = persist_match_result(config, match, winner, winner_maps, loser_maps)
    save_config(config, args.config)
    print(f'Persisted result: {summary["match"]} -> {summary["winner"]} {summary["score"]}')
    print(f'Applied round proxy: {summary["teamARounds"]}-{summary["teamBRounds"]} from teamA/teamB perspective.')
    if not args.no_regenerate:
        rebuild_dataset(args.config, args.dataset, args.output_dir, args.seed, args.show_progress, args.progress_step)
        print(f"Regenerated dataset: {args.dataset}")

def command_list_remaining_matches(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    for match in list_remaining_matches(config):
        print(match.label)

def main() -> None:
    args = parse_args()
    if args.command == "set-match-result":
        command_set_match_result(args)
        return
    if args.command == "list-remaining-matches":
        command_list_remaining_matches(args)
        return
    raise MatchUpdateError(f"Unsupported command: {args.command}")

if __name__ == "__main__":
    main()
