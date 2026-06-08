from pathlib import Path

import pandas as pd


INPUT_PATH = "data/processed/vlr_agents_summary_processed.csv"
OUTPUT_PATH = "data/processed/vlr_agents_summary_aggregated.csv"

PROBABILITY_COLUMNS = ["pick_rate", "atk_win_rate", "def_win_rate"]


def weighted_average(group: pd.DataFrame, value_col: str, weight_col: str) -> float | None:
    valid = group.dropna(subset=[value_col, weight_col])

    if valid.empty:
        return None

    total_weight = valid[weight_col].sum()

    if total_weight == 0:
        return None

    return (valid[value_col] * valid[weight_col]).sum() / total_weight


def aggregate_summary(input_path: str, output_path: str) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    required_columns = {
        "event",
        "map",
        "maps_played",
        "atk_win_rate",
        "def_win_rate",
        "agent",
        "pick_rate",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing columns: {sorted(missing)}")

    aggregated = (
        df.groupby(["map", "agent"], as_index=False)
        .apply(
            lambda group: pd.Series(
                {
                    "maps_played": group["maps_played"].sum(),
                    "pick_rate": weighted_average(group, "pick_rate", "maps_played"),
                    "atk_win_rate": weighted_average(group, "atk_win_rate", "maps_played"),
                    "def_win_rate": weighted_average(group, "def_win_rate", "maps_played"),
                    "events_count": group["event"].nunique(),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )

    aggregated = aggregated[
        [
            "map",
            "maps_played",
            "events_count",
            "atk_win_rate",
            "def_win_rate",
            "agent",
            "pick_rate",
        ]
    ].copy()

    for col in PROBABILITY_COLUMNS:
        aggregated[col] = aggregated[col].round(2)

    aggregated = aggregated.sort_values(
        ["map", "pick_rate", "agent"],
        ascending=[True, False, True],
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    aggregated.to_csv(output_path, index=False)

    print(f"Saved aggregated summary dataset: {aggregated.shape[0]} rows")
    print(f"Output: {output_path}")

    return aggregated


def main() -> None:
    aggregate_summary(INPUT_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()