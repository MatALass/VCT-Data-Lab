from __future__ import annotations
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_KEYS = {
    "league",
    "season",
    "qualification_slots",
    "n_simulations",
    "rating_weights",
    "logistic_scale",
    "p_clean_win_base",
    "round_model",
    "standings",
    "remaining_matches",
}

def canonical_match_key(team_a: str, team_b: str) -> tuple[str, str]:
    return tuple(sorted((team_a, team_b)))

def normalize_config(config: dict[str, Any]) -> None:
    config.setdefault("played_matches", [])
    config.setdefault("conditional_simulations", max(1000, int(config.get("n_simulations", 10000)) // 10))
    config.setdefault("model_type", "standings")

def validate_config(config: dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - set(config)
    if missing:
        raise ValueError(f"Missing required config keys: {sorted(missing)}")

    standings = config["standings"]
    if not isinstance(standings, list) or not standings:
        raise ValueError("Config must contain a non-empty standings list.")

    teams: set[str] = set()
    groups: dict[str, str] = {}
    for row in standings:
        if not isinstance(row, list) or len(row) != 8:
            raise ValueError(f"Each standings row must have 8 values: {row!r}")
        team, group, wins, losses, maps_won, maps_lost, rounds_won, rounds_lost = row
        if team in teams:
            raise ValueError(f"Duplicate team in standings: {team}")
        teams.add(team)
        groups[team] = group
        if any(int(v) < 0 for v in [wins, losses, maps_won, maps_lost, rounds_won, rounds_lost]):
            raise ValueError(f"Negative standings values are not allowed for team {team}.")

    remaining_seen: set[tuple[str, str]] = set()
    for row in config["remaining_matches"]:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"Each remaining match row must be [group, team_a, team_b]: {row!r}")
        group, team_a, team_b = row
        if team_a not in teams or team_b not in teams:
            raise ValueError(f"Remaining match references unknown team: {row!r}")
        if group != groups[team_a] or group != groups[team_b]:
            raise ValueError(f"Remaining match group mismatch: {row!r}")
        key = canonical_match_key(team_a, team_b)
        if key in remaining_seen:
            raise ValueError(f"Duplicate remaining match detected: {team_a} vs {team_b}")
        remaining_seen.add(key)

    for match in config.get("played_matches", []):
        required = {"group", "teamA", "teamB", "winner", "loser", "winnerMaps", "loserMaps", "teamARounds", "teamBRounds"}
        missing_keys = required - set(match)
        if missing_keys:
            raise ValueError(f"Played match is missing keys {sorted(missing_keys)}: {match!r}")
        team_a = str(match["teamA"])
        team_b = str(match["teamB"])
        winner = str(match["winner"])
        loser = str(match["loser"])
        if winner not in {team_a, team_b} or loser not in {team_a, team_b} or winner == loser:
            raise ValueError(f"Played match has invalid winner/loser values: {match!r}")
        if canonical_match_key(team_a, team_b) in remaining_seen:
            raise ValueError(f"Match cannot be both played and remaining: {team_a} vs {team_b}")

    if int(config["qualification_slots"]) <= 0 or int(config["n_simulations"]) <= 0 or int(config["conditional_simulations"]) <= 0:
        raise ValueError("Simulation counts and qualification_slots must be positive.")

def load_config(path: str | Path) -> dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    normalize_config(config)
    validate_config(config)
    return config

def save_config(config: dict[str, Any], path: str | Path) -> None:
    normalize_config(config)
    validate_config(config)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
