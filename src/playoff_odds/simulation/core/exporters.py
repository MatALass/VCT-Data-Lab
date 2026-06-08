from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any
import pandas as pd
from .analysis import add_expected_rank, build_auto_insights, top_paths

def export_frontend_json(config: dict[str, Any], summary_df: pd.DataFrame, position_df: pd.DataFrame, best_scenario: dict[str, Any], worst_scenario: dict[str, Any], qualify_paths: dict[str, Counter], eliminate_paths: dict[str, Counter], exact_bounds: dict[str, Any], match_impacts: dict[str, Any], key_matches: list[dict[str, Any]], remaining_matches: list[list[Any]], output_json: str | Path) -> None:
    merged = summary_df.merge(position_df, on=["team", "group"], how="inner")
    merged["expected_rank"] = add_expected_rank(merged)
    position_cols = sorted([c for c in merged.columns if c.startswith("P")], key=lambda x: int(x[1:]))
    groups_payload = []
    total_runs = int(config["n_simulations"])
    for group_name, group_df in merged.groupby("group", sort=True):
        group_df = group_df.sort_values(["qualify_prob", "expected_rank"], ascending=[False, True])
        teams = []
        for row in group_df.to_dict(orient="records"):
            team = row["team"]
            teams.append({
                "team": team,
                "qualifyProb": float(row["qualify_prob"]),
                "bestRankSeen": int(row["best_rank_seen"]),
                "worstRankSeen": int(row["worst_rank_seen"]),
                "expectedRank": float(row["expected_rank"]),
                "positions": {col: float(row[col]) for col in position_cols},
                "scenarioExtremes": {"bestCase": best_scenario.get(team), "worstCase": worst_scenario.get(team)},
                "topQualificationPaths": top_paths(qualify_paths.get(team, Counter()), remaining_matches, total_runs),
                "topEliminationPaths": top_paths(eliminate_paths.get(team, Counter()), remaining_matches, total_runs),
                "exactWinnerOnlyBounds": exact_bounds.get(team),
            })
        groups_payload.append({"name": group_name, "teams": teams})
    payload = {
        "schemaVersion": "3.0.0",
        "league": config["league"],
        "season": config["season"],
        "qualificationSlots": int(config["qualification_slots"]),
        "groups": groups_payload,
        "remainingMatches": [{"group": g, "teamA": a, "teamB": b} for g, a, b in remaining_matches],
        "playedMatches": config.get("played_matches", []),
        "matchImpacts": match_impacts,
        "keyMatches": key_matches,
        "insights": build_auto_insights(groups_payload, key_matches, config.get("model_type", "standings")),
        "notes": {
            "method": "Monte Carlo playoff qualification simulation",
            "officialTieBreakers": [
                "head-to-head match score",
                "head-to-head map differential",
                "head-to-head round differential",
                "stage map differential",
                "stage round differential",
            ],
            "sampleSize": int(config["n_simulations"]),
            "conditionalSampleSize": int(config.get("conditional_simulations", max(1000, config["n_simulations"] // 10))),
            "scenarioExtremes": "Best / worst scenarios are observed within the simulation sample, not exact exhaustive optima.",
            "exactWinnerOnlyBounds": "Exact over match-winner combinations only, using a deterministic 2-0 proxy scoreline for tie-break-sensitive metrics.",
            "modelType": config.get("model_type", "standings"),
            "analysisFeatures": ["matchImpacts", "keyMatches", "autoInsights", "topQualificationPaths", "winnerOnlyBounds", "whatIfCLI", "consoleMatchUpdate"],
            "whatIfMode": "The what-if CLI generates a deterministic snapshot. Unforced matches default to the listed teamA winner so the output stays transparent and reproducible.",
            "playedMatchesPersistence": "Console match updates persist to config.played_matches, update standings totals, remove the fixture from remaining_matches, and then regenerate the frontend dataset.",
        },
    }
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved frontend dataset to: {output_path}")
