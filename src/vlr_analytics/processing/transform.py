import re

import pandas as pd

from vlr_analytics.config import (
    EXPECTED_AGENTS_PER_COMP,
    INVALID_COMPOSITIONS_REPORT,
    PROCESSED_MATRIX,
    PROCESSED_SUMMARY,
    RAW_MATRIX,
    RAW_SUMMARY,
)
from vlr_analytics.utils import (
    clean_text,
    normalize_map_name,
    percent_to_float,
    read_csv_required,
    require_columns,
    write_csv,
)

INVALID_COMPOSITION_COLUMNS = [
    "event",
    "map",
    "match_id",
    "team",
    "opponent",
    "agents_count",
    "expected_agents_count",
    "agents",
    "reason",
]


def build_match_id(row: pd.Series) -> str:
    teams = sorted([str(row["team"]), str(row["opponent"])])
    raw = f"{row['event']}__{row['map']}__{teams[0]}__{teams[1]}"
    return re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_").lower()


def transform_summary(input_path=RAW_SUMMARY, output_path=PROCESSED_SUMMARY) -> pd.DataFrame:
    df = read_csv_required(input_path)
    require_columns(
        df,
        {
            "event",
            "raw_map",
            "raw_maps_played",
            "raw_atk_win_rate",
            "raw_def_win_rate",
            "agent",
            "raw_pick_rate",
        },
        "summary raw",
    )
    out = pd.DataFrame(
        {
            "event": df["event"].map(clean_text),
            "map": df["raw_map"].map(normalize_map_name),
            "maps_played": df["raw_maps_played"].astype(int),
            "atk_win_rate": df["raw_atk_win_rate"].map(percent_to_float),
            "def_win_rate": df["raw_def_win_rate"].map(percent_to_float),
            "agent": df["agent"].map(clean_text).str.lower(),
            "pick_rate": df["raw_pick_rate"].map(percent_to_float),
        }
    )
    out = out.drop_duplicates()
    write_csv(out, output_path)
    return out


def build_invalid_compositions_report(
    matrix: pd.DataFrame,
    output_path=INVALID_COMPOSITIONS_REPORT,
) -> pd.DataFrame:
    """Build a data-quality report for incomplete or oversized compositions.

    A valid Valorant composition should contain exactly five unique agents for one
    team on one map. The report is intentionally non-blocking: it keeps the
    pipeline usable while making scraping/data-quality anomalies explicit.
    """
    if matrix.empty:
        report = pd.DataFrame(columns=INVALID_COMPOSITION_COLUMNS)
        write_csv(report, output_path)
        return report

    grouped = (
        matrix.groupby(["event", "map", "match_id", "team"], as_index=False)
        .agg(
            opponent=("opponent", "first"),
            agents_count=("agent", "nunique"),
            agents=("agent", lambda values: ",".join(sorted(set(map(str, values))))),
        )
    )

    report = grouped[grouped["agents_count"] != EXPECTED_AGENTS_PER_COMP].copy()
    if report.empty:
        report = pd.DataFrame(columns=INVALID_COMPOSITION_COLUMNS)
    else:
        report["expected_agents_count"] = EXPECTED_AGENTS_PER_COMP
        report["reason"] = report["agents_count"].map(
            lambda count: "missing_agents"
            if count < EXPECTED_AGENTS_PER_COMP
            else "too_many_agents"
        )
        report = report[INVALID_COMPOSITION_COLUMNS].sort_values(
            ["event", "map", "match_id", "team"]
        )

    write_csv(report, output_path)
    return report


def transform_matrix(input_path=RAW_MATRIX, output_path=PROCESSED_MATRIX) -> pd.DataFrame:
    df = read_csv_required(input_path)
    require_columns(df, {"event", "map", "team", "opponent", "agent"}, "matrix raw")
    for col in ["event", "map", "team", "opponent", "agent"]:
        df[col] = df[col].map(clean_text)
    df["map"] = df["map"].map(normalize_map_name)
    df["agent"] = df["agent"].str.lower()
    out = df[["event", "map", "team", "opponent", "agent"]].drop_duplicates().copy()
    out["match_id"] = out.apply(build_match_id, axis=1)
    out = out[["event", "map", "match_id", "team", "opponent", "agent"]]

    invalid_report = build_invalid_compositions_report(out)
    if not invalid_report.empty:
        print(
            f"WARNING: {len(invalid_report)} compositions have != "
            f"{EXPECTED_AGENTS_PER_COMP} agents. "
            f"See {INVALID_COMPOSITIONS_REPORT}."
        )

    write_csv(out, output_path)
    return out


def process_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    return transform_summary(), transform_matrix()
