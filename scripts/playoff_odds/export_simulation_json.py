"""
Convert Monte Carlo CSV outputs into the JSON schema expected by the frontend.

Expected inputs:
- summary CSV with columns:
  team, group, qualify_count, qualify_prob, best_rank_seen, worst_rank_seen
- positions CSV with columns:
  team, group, P1, P2, ...

Example:
python scripts/export_simulation_json.py \
  --summary data/vct_qualification_probabilities.csv \
  --positions data/vct_position_probabilities.csv \
  --league "VCT EMEA" \
  --season "2026" \
  --slots 4 \
  --sample-size 10000 \
  --output data/vct-emea-2026.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--positions", required=True)
    parser.add_argument("--league", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--slots", required=True, type=int)
    parser.add_argument("--sample-size", type=int, default=0)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def detect_position_cols(df: pd.DataFrame) -> list[str]:
    cols = [col for col in df.columns if col.startswith("P")]
    return sorted(cols, key=lambda c: int(c[1:]))


def main() -> None:
    args = parse_args()

    summary = pd.read_csv(args.summary)
    positions = pd.read_csv(args.positions)

    position_cols = detect_position_cols(positions)
    merged = summary.merge(positions, on=["team", "group"], how="inner")

    groups_payload = []
    for group_name, group_df in merged.groupby("group", sort=True):
        teams = []
        for row in group_df.sort_values("qualify_prob", ascending=False).to_dict(orient="records"):
            teams.append(
                {
                    "team": row["team"],
                    "qualifyProb": float(row["qualify_prob"]),
                    "bestRankSeen": int(row["best_rank_seen"]),
                    "worstRankSeen": int(row["worst_rank_seen"]),
                    "positions": {col: float(row[col]) for col in position_cols},
                }
            )
        groups_payload.append({"name": group_name, "teams": teams})

    payload = {
        "league": args.league,
        "season": args.season,
        "qualificationSlots": args.slots,
        "groups": groups_payload,
        "notes": {
            "method": "Monte Carlo playoff qualification simulation",
            "sampleSize": args.sample_size,
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved frontend dataset to: {output_path}")


if __name__ == "__main__":
    main()
