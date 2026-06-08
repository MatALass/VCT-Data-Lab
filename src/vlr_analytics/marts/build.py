from itertools import combinations

import pandas as pd

from vlr_analytics.config import (
    AGENT_MAP_STATS,
    AGENT_SYNERGY,
    META_TRENDS,
    PROCESSED_MATRIX,
    PROCESSED_SUMMARY,
    TEAM_AGENT_STATS,
    TEAM_COMPOSITIONS,
    TEAM_MAP_STATS,
    TEAM_SIGNATURES,
)
from vlr_analytics.thresholds import MIN_SYNERGY_PAIR_PICKS, MIN_SYNERGY_TEAMS_COUNT
from vlr_analytics.utils import read_csv_required, require_columns, write_csv


def _composition_key_columns() -> list[str]:
    return ["event", "map", "match_id", "team"]


def _pick_rates(matrix: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    key_cols = list(dict.fromkeys(group_cols + _composition_key_columns()))
    comps = matrix[key_cols].drop_duplicates()
    totals = comps.groupby(group_cols).size().rename("total_compositions").reset_index()
    counts = (
        matrix[list(dict.fromkeys(group_cols + _composition_key_columns() + ["agent"]))]
        .drop_duplicates()
        .groupby(group_cols + ["agent"])
        .size()
        .rename("agent_picks")
        .reset_index()
    )
    out = counts.merge(totals, on=group_cols, how="left")
    out["pick_rate_from_comps"] = (out["agent_picks"] / out["total_compositions"]).round(4)
    return out


def build_agent_map_stats(summary: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    base = summary.copy()
    all_maps = base.copy()
    all_maps["map"] = "All Maps"
    weighted = pd.concat([base, all_maps], ignore_index=True)

    def weighted_avg(g: pd.DataFrame, col: str) -> float:
        weights = g["maps_played"].fillna(0)
        if weights.sum() == 0:
            return 0.0
        return float((g[col].fillna(0) * weights).sum() / weights.sum())

    agg = (
        weighted.groupby(["map", "agent"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "maps_played": g["maps_played"].sum(),
                    "events_count": g["event"].nunique(),
                    "pick_rate": weighted_avg(g, "pick_rate"),
                    "atk_side_rate": weighted_avg(g, "atk_win_rate"),
                    "def_side_rate": weighted_avg(g, "def_win_rate"),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    comp_rates = pd.concat([
        _pick_rates(matrix, ["map"]),
        _pick_rates(matrix.assign(map="All Maps"), ["map"]),
    ], ignore_index=True)
    out = agg.merge(comp_rates, on=["map", "agent"], how="left")
    out["side_delta"] = (out["atk_side_rate"] - out["def_side_rate"]).round(4)
    out["sample_confidence"] = (out["maps_played"] / out.groupby("map")["maps_played"].transform("max")).fillna(0).round(4)
    out["observed"] = True
    out["agent_presence_score"] = (
        100
        * (
            0.60 * out["pick_rate"].fillna(0)
            + 0.20 * out["pick_rate_from_comps"].fillna(0)
            + 0.20 * out["sample_confidence"].fillna(0)
        )
    ).round(2)
    return out.sort_values(["map", "agent_presence_score", "agent"], ascending=[True, False, True])


def build_team_compositions(matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in matrix.groupby(["event", "map", "match_id", "team", "opponent"], dropna=False):
        agents = sorted(g["agent"].dropna().unique())
        rows.append(
            {
                "event": keys[0],
                "map": keys[1],
                "match_id": keys[2],
                "team": keys[3],
                "opponent": keys[4],
                "agents": ",".join(agents),
                "agents_count": len(agents),
                "observed": True,
            }
        )
    return pd.DataFrame(rows).sort_values(["event", "map", "team"])


def build_team_agent_stats(matrix: pd.DataFrame) -> pd.DataFrame:
    comps = matrix[["event", "match_id", "team", "map"]].drop_duplicates()
    totals = comps.groupby("team").size().rename("team_total_compositions").reset_index()
    counts = matrix.drop_duplicates(["event", "match_id", "team", "map", "agent"]).groupby(["team", "agent"]).size().rename("agent_picks").reset_index()
    out = counts.merge(totals, on="team", how="left")
    out["team_agent_pick_rate"] = (out["agent_picks"] / out["team_total_compositions"]).round(4)
    out["observed"] = True
    out["signature_level"] = pd.cut(
        out["team_agent_pick_rate"],
        bins=[-0.01, 0.20, 0.40, 0.65, 1.0],
        labels=["rare", "rotation", "core", "signature"],
    )
    return out.sort_values(["team", "team_agent_pick_rate", "agent"], ascending=[True, False, True])


def build_team_map_stats(matrix: pd.DataFrame) -> pd.DataFrame:
    comp = build_team_compositions(matrix)
    out = comp.groupby(["team", "map"], as_index=False).agg(
        compositions=("match_id", "nunique"),
        opponents=("opponent", "nunique"),
        unique_comps=("agents", "nunique"),
    )
    out["comp_diversity"] = (out["unique_comps"] / out["compositions"]).round(4)
    out["map_volume_share"] = (out["compositions"] / out.groupby("team")["compositions"].transform("sum")).round(4)
    out["observed"] = True
    return out.sort_values(["team", "compositions", "map"], ascending=[True, False, True])


def build_agent_synergy(matrix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (event, map_name, match_id, team), g in matrix.groupby(["event", "map", "match_id", "team"], dropna=False):
        agents = sorted(g["agent"].dropna().unique())
        for a, b in combinations(agents, 2):
            rows.append({"event": event, "map": map_name, "match_id": match_id, "team": team, "agent_a": a, "agent_b": b})
    pairs = pd.DataFrame(rows)
    if pairs.empty:
        return pd.DataFrame(columns=["map", "agent_a", "agent_b", "pair_picks", "teams_count", "events_count", "total_compositions", "pair_pick_rate", "agent_a_rate", "agent_b_rate", "synergy_lift", "observed"])

    out = pairs.groupby(["map", "agent_a", "agent_b"], as_index=False).agg(
        pair_picks=("match_id", "nunique"),
        teams_count=("team", "nunique"),
        events_count=("event", "nunique"),
    )
    totals = matrix[["map", "event", "match_id", "team"]].drop_duplicates().groupby("map").size().rename("total_compositions").reset_index()
    out = out.merge(totals, on="map", how="left")
    out["pair_pick_rate"] = out["pair_picks"] / out["total_compositions"]

    agent_rates = _pick_rates(matrix, ["map"])[["map", "agent", "pick_rate_from_comps"]]
    out = out.merge(agent_rates.rename(columns={"agent": "agent_a", "pick_rate_from_comps": "agent_a_rate"}), on=["map", "agent_a"], how="left")
    out = out.merge(agent_rates.rename(columns={"agent": "agent_b", "pick_rate_from_comps": "agent_b_rate"}), on=["map", "agent_b"], how="left")
    expected = out["agent_a_rate"].fillna(0) * out["agent_b_rate"].fillna(0)
    out["synergy_lift"] = (out["pair_pick_rate"] / expected.replace(0, pd.NA)).fillna(0).round(3)
    out["pair_pick_rate"] = out["pair_pick_rate"].round(4)
    out = out[
        (out["pair_picks"] >= MIN_SYNERGY_PAIR_PICKS)
        & (out["teams_count"] >= MIN_SYNERGY_TEAMS_COUNT)
    ].copy()
    out["observed"] = True
    return out.sort_values(["map", "synergy_lift", "pair_picks"], ascending=[True, False, False])


def build_meta_trends(summary: pd.DataFrame) -> pd.DataFrame:
    base = summary[summary["map"] != "All Maps"].copy()
    out = base.groupby(["event", "map"], as_index=False).agg(
        maps_played=("maps_played", "max"),
        avg_pick_rate=("pick_rate", "mean"),
        pick_rate_std=("pick_rate", "std"),
        top_pick_rate=("pick_rate", "max"),
        agents_count=("agent", "nunique"),
    )
    out["meta_concentration"] = out["pick_rate_std"].fillna(0).round(4)
    out["dominance_gap"] = (out["top_pick_rate"] - out["avg_pick_rate"]).round(4)
    return out.sort_values(["event", "map"])


def build_team_signatures(team_agent: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for team, g in team_agent.groupby("team"):
        top = g.sort_values("team_agent_pick_rate", ascending=False).head(5)
        rows.append(
            {
                "team": team,
                "signature_agents": ",".join(top["agent"].astype(str)),
                "signature_strength": round(float(top["team_agent_pick_rate"].mean()), 4),
                "primary_agent": top.iloc[0]["agent"] if len(top) else None,
            }
        )
    return pd.DataFrame(rows).sort_values("signature_strength", ascending=False)


def build_all_marts() -> dict[str, pd.DataFrame]:
    summary = read_csv_required(PROCESSED_SUMMARY)
    matrix = read_csv_required(PROCESSED_MATRIX)
    require_columns(summary, {"event", "map", "maps_played", "atk_win_rate", "def_win_rate", "agent", "pick_rate"}, "processed summary")
    require_columns(matrix, {"event", "map", "match_id", "team", "opponent", "agent"}, "processed matrix")

    team_agent = build_team_agent_stats(matrix)
    outputs = {
        "agent_map_stats": build_agent_map_stats(summary, matrix),
        "team_compositions": build_team_compositions(matrix),
        "team_agent_stats": team_agent,
        "team_map_stats": build_team_map_stats(matrix),
        "agent_synergy": build_agent_synergy(matrix),
        "meta_trends": build_meta_trends(summary),
        "team_signatures": build_team_signatures(team_agent),
    }
    for name, df in outputs.items():
        write_csv(df, globals()[name.upper()])
    return outputs
