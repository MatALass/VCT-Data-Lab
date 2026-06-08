from pathlib import Path

import pandas as pd


INPUT_PATH = "data/processed/vlr_agents_matrix_processed.csv"
OUTPUT_PATH = "data/processed/vlr_agents_matrix_aggregated.csv"


def compute_pick_rates(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    compositions = df[group_cols + ["event", "match_id", "team"]].drop_duplicates()

    total_comps = (
        compositions.groupby(group_cols)
        .size()
        .rename("total_compositions")
        .reset_index()
    )

    agent_counts = (
        df[group_cols + ["event", "match_id", "team", "agent"]]
        .drop_duplicates()
        .groupby(group_cols + ["agent"])
        .size()
        .rename("agent_picks")
        .reset_index()
    )

    result = agent_counts.merge(total_comps, on=group_cols, how="left")
    result["pick_rate"] = (
        result["agent_picks"] / result["total_compositions"]
    ).round(2)

    return result


def aggregate_matrix(input_path: str, output_path: str) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    required_columns = {"event", "map", "match_id", "team", "opponent", "agent"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    by_map = compute_pick_rates(df, ["map"])

    all_maps_df = df.copy()
    all_maps_df["map"] = "All Maps"
    all_maps = compute_pick_rates(all_maps_df, ["map"])

    aggregated = pd.concat([all_maps, by_map], ignore_index=True)

    aggregated = aggregated.sort_values(
        ["map", "pick_rate", "agent"],
        ascending=[True, False, True],
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    aggregated.to_csv(output_path, index=False)

    print(f"Saved matrix aggregated dataset: {aggregated.shape[0]} rows")
    print(f"Output: {output_path}")

    return aggregated


def main() -> None:
    aggregate_matrix(INPUT_PATH, OUTPUT_PATH)


if __name__ == "__main__":
    main()