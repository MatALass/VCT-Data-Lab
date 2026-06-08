import re
from pathlib import Path

import pandas as pd


RAW_SUMMARY_PATH = "data/raw/vlr_agents_summary_raw.csv"
RAW_MATRIX_PATH = "data/raw/vlr_agents_matrix_raw.csv"

PROCESSED_SUMMARY_PATH = "data/processed/vlr_agents_summary_processed.csv"
PROCESSED_MATRIX_PATH = "data/processed/vlr_agents_matrix_processed.csv"

EXPECTED_MAPS = {
    "All Maps",
    "Bind",
    "Breeze",
    "Fracture",
    "Haven",
    "Lotus",
    "Pearl",
    "Split",
}

EXPECTED_AGENTS_PER_COMP = 5


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_map_name(raw_map: str) -> str:
    raw_map = clean_text(raw_map)

    if raw_map == "" or raw_map.lower() == "nan":
        return "All Maps"

    parts = raw_map.split(" ", 1)

    if len(parts) == 2 and len(parts[0]) == 1:
        return parts[1]

    return raw_map


def percent_to_float(value: str) -> float | None:
    value = clean_text(value).replace("%", "")

    if value == "" or value.lower() == "nan":
        return None

    return float(value) / 100


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def check_duplicates(df: pd.DataFrame, name: str) -> None:
    duplicated_rows = df.duplicated().sum()
    print(f"{name} duplicated rows: {duplicated_rows}")


def validate_maps(df: pd.DataFrame, name: str) -> None:
    maps = set(df["map"].dropna().unique())
    unexpected = sorted(maps - EXPECTED_MAPS)

    print(f"{name} maps: {sorted(maps)}")

    if unexpected:
        print(f"WARNING - unexpected maps in {name}: {unexpected}")
    else:
        print(f"{name} map validation: OK")


def transform_summary(raw_path: str, output_path: str) -> pd.DataFrame:
    print_section("Transform summary dataset")

    df = pd.read_csv(raw_path)

    required_columns = {
        "event",
        "raw_map",
        "raw_maps_played",
        "raw_atk_win_rate",
        "raw_def_win_rate",
        "agent",
        "raw_pick_rate",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Summary raw file is missing columns: {sorted(missing)}")

    df["map"] = df["raw_map"].apply(normalize_map_name)
    df["maps_played"] = df["raw_maps_played"].astype(int)
    df["atk_win_rate"] = df["raw_atk_win_rate"].apply(percent_to_float)
    df["def_win_rate"] = df["raw_def_win_rate"].apply(percent_to_float)
    df["pick_rate"] = df["raw_pick_rate"].apply(percent_to_float)

    final_df = df[
        [
            "event",
            "map",
            "maps_played",
            "atk_win_rate",
            "def_win_rate",
            "agent",
            "pick_rate",
        ]
    ].copy()

    check_duplicates(final_df, "summary")
    validate_maps(final_df, "summary")

    invalid_probabilities = final_df[
        (final_df["pick_rate"] < 0)
        | (final_df["pick_rate"] > 1)
        | (final_df["atk_win_rate"] < 0)
        | (final_df["atk_win_rate"] > 1)
        | (final_df["def_win_rate"] < 0)
        | (final_df["def_win_rate"] > 1)
    ]

    print(f"summary invalid probabilities: {len(invalid_probabilities)}")
    print(f"summary missing values:\n{final_df.isna().sum()}")

    final_df.to_csv(output_path, index=False)
    print(f"Saved summary processed dataset: {final_df.shape[0]} rows")

    return final_df


def build_match_id(row: pd.Series) -> str:
    teams = sorted([str(row["team"]), str(row["opponent"])])
    event = str(row["event"])
    map_name = str(row["map"])

    safe_value = f"{event}__{map_name}__{teams[0]}__{teams[1]}"
    safe_value = re.sub(r"[^a-zA-Z0-9]+", "_", safe_value).strip("_").lower()

    return safe_value


def transform_matrix(raw_path: str, output_path: str) -> pd.DataFrame:
    print_section("Transform matrix dataset")

    df = pd.read_csv(raw_path)

    required_columns = {
        "event",
        "map",
        "team",
        "opponent",
        "agent",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Matrix raw file is missing columns: {sorted(missing)}")

    for col in ["event", "map", "team", "opponent", "agent"]:
        df[col] = df[col].apply(clean_text)

    df["map"] = df["map"].apply(normalize_map_name)
    df["agent"] = df["agent"].str.lower()

    final_df = df[
        [
            "event",
            "map",
            "team",
            "opponent",
            "agent",
        ]
    ].copy()

    final_df["match_id"] = final_df.apply(build_match_id, axis=1)

    final_df = final_df[
        [
            "event",
            "map",
            "match_id",
            "team",
            "opponent",
            "agent",
        ]
    ]

    check_duplicates(final_df, "matrix")
    validate_maps(final_df, "matrix")

    print(f"matrix missing values:\n{final_df.isna().sum()}")

    bad_team_rows = final_df[
        final_df["team"].str.startswith("vs.", na=False)
        | final_df["opponent"].str.startswith("vs.", na=False)
    ]
    print(f"matrix rows with malformed team/opponent: {len(bad_team_rows)}")

    comp_sizes = (
        final_df.groupby(["event", "map", "team", "opponent"])
        .size()
        .value_counts()
        .sort_index()
    )

    print("\nComposition size distribution:")
    print(comp_sizes)

    invalid_comps = (
        final_df.groupby(["event", "map", "team", "opponent"])
        .size()
        .reset_index(name="agents_count")
    )

    invalid_comps = invalid_comps[
        invalid_comps["agents_count"] != EXPECTED_AGENTS_PER_COMP
    ]

    print(f"\nInvalid compositions != {EXPECTED_AGENTS_PER_COMP} agents: {len(invalid_comps)}")

    if not invalid_comps.empty:
        print(invalid_comps.head(20))

    final_df.to_csv(output_path, index=False)
    print(f"Saved matrix processed dataset: {final_df.shape[0]} rows")

    return final_df


def main() -> None:
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    transform_summary(
        raw_path=RAW_SUMMARY_PATH,
        output_path=PROCESSED_SUMMARY_PATH,
    )

    transform_matrix(
        raw_path=RAW_MATRIX_PATH,
        output_path=PROCESSED_MATRIX_PATH,
    )


if __name__ == "__main__":
    main()