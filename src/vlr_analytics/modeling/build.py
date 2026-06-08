"""VLR Analytics — Modeling Layer v2.

This module builds interpretable analytical tables from mart-layer data.
It never claims to measure team strength, win probability, or competitive rank.
All scores are presence / stability / structure scores — not power scores.

Outputs (data/models/):
  agent_meta_presence.csv
  team_tactical_profiles.csv
  team_map_identity.csv
  composition_patterns.csv
  agent_pair_patterns.csv
  composition_archetypes.csv
  insights.json
"""

from __future__ import annotations

import json
import warnings
from typing import Any

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import MultiLabelBinarizer

from vlr_analytics.config import (
    AGENT_MAP_STATS,
    AGENT_SYNERGY,
    AGENT_TIERS,
    COMPOSITION_ARCHETYPES,
    COMPOSITION_CLUSTERS,
    INSIGHTS,
    MAP_SPECIALISTS,
    TEAM_AGENT_STATS,
    TEAM_COMPOSITIONS,
    TEAM_MAP_IDENTITY,
    TEAM_MAP_STATS,
    TEAM_STRENGTHS,
)
from vlr_analytics.config import MODELS_DIR
from vlr_analytics.thresholds import (
    MIN_COMP_PATTERN_USES,
    MIN_MAP_IDENTITY_COMPOSITIONS,
    MIN_META_MAPS_PLAYED,
    MIN_SYNERGY_PAIR_PICKS,
    MIN_TACTICAL_PROFILE_COMPOSITIONS,
)
from vlr_analytics.utils import read_csv_required, write_csv, write_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_divide(num: pd.Series, denom: pd.Series, fill: float = 0.0) -> pd.Series:
    return (num / denom.replace(0, pd.NA)).fillna(fill)


def _reliability_score(volume: pd.Series, max_vol: float) -> pd.Series:
    """0-1 reliability score using sqrt damping so mid-volume gets fair signal."""
    if max_vol == 0:
        return pd.Series(0.0, index=volume.index)
    return ((volume / max_vol).clip(0, 1) ** 0.5).round(4)


def _confidence(reliability: float) -> str:
    if reliability >= 0.60:
        return "high"
    if reliability >= 0.35:
        return "medium"
    return "low"

def build_agent_global_meta(agent_meta_presence: pd.DataFrame) -> pd.DataFrame:
    """Build one global row per agent.

    This table is designed for overview/dashboard usage.
    It prevents duplicated agent rows caused by map-level records.
    """

    local = agent_meta_presence[agent_meta_presence["map"] != "All Maps"].copy()

    if local.empty:
        return pd.DataFrame(
            columns=[
                "agent",
                "maps_observed",
                "total_maps_played",
                "avg_pick_rate",
                "max_pick_rate",
                "avg_meta_presence_score",
                "avg_map_dependence_score",
                "max_map_dependence_score",
                "cross_map_stability_score",
                "sample_reliability_score",
                "primary_map",
                "global_agent_label",
            ]
        )

    primary_maps = (
        local.sort_values(["agent", "pick_rate"], ascending=[True, False])
        .groupby("agent", as_index=False)
        .first()[["agent", "map"]]
        .rename(columns={"map": "primary_map"})
    )

    df = (
        local.groupby("agent", as_index=False)
        .agg(
            maps_observed=("map", "nunique"),
            total_maps_played=("maps_played", "sum"),
            avg_pick_rate=("pick_rate", "mean"),
            max_pick_rate=("pick_rate", "max"),
            avg_meta_presence_score=("meta_presence_score", "mean"),
            avg_map_dependence_score=("map_dependence_score", "mean"),
            max_map_dependence_score=("map_dependence_score", "max"),
            cross_map_stability_score=("cross_map_stability_score", "mean"),
            sample_reliability_score=("sample_reliability_score", "mean"),
        )
        .merge(primary_maps, on="agent", how="left")
    )

    def _label(row: pd.Series) -> str:
        if row["sample_reliability_score"] < 0.30:
            return "low_sample_agent"

        if (
            row["avg_meta_presence_score"] >= 0.55
            and row["cross_map_stability_score"] >= 0.60
        ):
            return "global_core_agent"

        if row["max_map_dependence_score"] >= 0.65:
            return "map_specialist_agent"

        if row["avg_meta_presence_score"] >= 0.35:
            return "situational_agent"

        return "low_presence_agent"

    df["global_agent_label"] = df.apply(_label, axis=1)

    numeric_cols = [
        "avg_pick_rate",
        "max_pick_rate",
        "avg_meta_presence_score",
        "avg_map_dependence_score",
        "max_map_dependence_score",
        "cross_map_stability_score",
        "sample_reliability_score",
    ]

    for col in numeric_cols:
        df[col] = df[col].round(4)

    return df[
        [
            "agent",
            "maps_observed",
            "total_maps_played",
            "avg_pick_rate",
            "max_pick_rate",
            "avg_meta_presence_score",
            "avg_map_dependence_score",
            "max_map_dependence_score",
            "cross_map_stability_score",
            "sample_reliability_score",
            "primary_map",
            "global_agent_label",
        ]
    ].sort_values(
        ["avg_meta_presence_score", "avg_pick_rate"],
        ascending=False,
    )
# ---------------------------------------------------------------------------
# 1. Agent Meta Presence
# ---------------------------------------------------------------------------

def build_agent_meta_presence(agent_map: pd.DataFrame) -> pd.DataFrame:
    """Produce agent_meta_presence.csv.

    Scores measure presence and stability, NOT power or win rate.

    Important:
    - Per-map rows are computed from local map rows.
    - Global/overview rows are produced separately in agent_global_meta.csv.
    """
    global_ref = (
        agent_map[agent_map["map"] == "All Maps"][["agent", "pick_rate", "pick_rate_from_comps"]]
        .rename(columns={"pick_rate": "global_pick_rate", "pick_rate_from_comps": "global_comp_rate"})
    )

    local = agent_map[agent_map["map"] != "All Maps"].copy()
    local = local.merge(global_ref, on="agent", how="left")
    local["local_pick_delta"] = (
        local["pick_rate"].fillna(0) - local["global_pick_rate"].fillna(0)
    ).round(4)

    stability = (
        local.groupby("agent")["pick_rate"]
        .std()
        .fillna(0)
        .rename("pick_rate_std")
        .reset_index()
    )
    local = local.merge(stability, on="agent", how="left")

    max_std = local["pick_rate_std"].max() or 1.0
    local["cross_map_stability_score"] = (1 - local["pick_rate_std"] / max_std).round(4)

    max_delta = local["local_pick_delta"].abs().max() or 1.0
    local["map_dependence_score"] = (
        local["local_pick_delta"] / max_delta
    ).clip(-1, 1).round(4)

    max_maps = local["maps_played"].max() or 1.0
    local["sample_reliability_score"] = _reliability_score(
        local["maps_played"].fillna(0), max_maps
    )

    local["meta_presence_score"] = (
        0.40 * local["pick_rate"].fillna(0)
        + 0.25 * local["pick_rate_from_comps"].fillna(0)
        + 0.20 * local["cross_map_stability_score"]
        + 0.15 * local["sample_reliability_score"]
    ).round(4)

    def _label(row: pd.Series) -> str:
        if row["sample_reliability_score"] < 0.25 or row["maps_played"] < MIN_META_MAPS_PLAYED:
            return "low_sample_signal"

        p = row["meta_presence_score"]
        stab = row["cross_map_stability_score"]
        delta = row["map_dependence_score"]

        if p >= 0.55 and stab >= 0.65:
            return "global_meta_core"
        if p >= 0.40 and stab >= 0.50:
            return "stable_pick"
        if delta >= 0.40:
            return "map_specialist"
        if p >= 0.20:
            return "situational_pick"
        return "low_sample_signal"

    local["agent_meta_label"] = local.apply(_label, axis=1)

    output_cols = [
        "map",
        "agent",
        "maps_played",
        "pick_rate",
        "pick_rate_from_comps",
        "sample_reliability_score",
        "global_pick_rate",
        "local_pick_delta",
        "cross_map_stability_score",
        "map_dependence_score",
        "meta_presence_score",
        "agent_meta_label",
    ]

    local = local[output_cols]

    # Keep this output strictly local-map scoped.
    # Global/overview rows belong to `agent_global_meta.csv`, built from these local rows.
    result = local

    return result.sort_values(
        ["map", "meta_presence_score", "agent"],
        ascending=[True, False, True],
    )


# ---------------------------------------------------------------------------
# 2. Team Tactical Profiles
# ---------------------------------------------------------------------------

def build_team_tactical_profiles(
    team_map: pd.DataFrame,
    team_agent: pd.DataFrame,
    team_comps: pd.DataFrame,
) -> pd.DataFrame:
    """Produce team_tactical_profiles.csv.

    tactical_profile_score = structural legibility, NOT win probability.
    """
    map_agg = team_map.groupby("team", as_index=False).agg(
        maps_covered=("map", "nunique"),
        total_compositions=("compositions", "sum"),
    )

    comp_agg = team_comps.groupby("team", as_index=False).agg(
        unique_compositions=("agents", "nunique"),
        total_comp_rows=("agents", "count"),
    )
    comp_agg["composition_reuse_rate"] = (
        1 - _safe_divide(comp_agg["unique_compositions"], comp_agg["total_comp_rows"])
    ).round(4)

    agent_agg = team_agent.groupby("team", as_index=False).agg(
        agent_pool_size=("agent", "nunique"),
        core_agents_count=(
            "signature_level",
            lambda s: int((s.astype(str).isin(["core", "signature"])).sum()),
        ),
    )

    df = map_agg.merge(comp_agg, on="team", how="outer").merge(agent_agg, on="team", how="outer")
    df["composition_stability_score"] = df["composition_reuse_rate"].fillna(0).round(4)

    max_maps = df["maps_covered"].max() or 1
    df["map_pool_visibility_score"] = (df["maps_covered"].fillna(0) / max_maps).round(4)

    df["agent_core_score"] = _safe_divide(
        df["core_agents_count"].fillna(0),
        df["agent_pool_size"].fillna(1),
    ).round(4)

    map_identity = (
        team_map.groupby("team")["map_volume_share"]
        .max()
        .rename("map_identity_score")
        .reset_index()
    )
    df = df.merge(map_identity, on="team", how="left")
    df["map_identity_score"] = df["map_identity_score"].fillna(0).round(4)

    max_comps = df["total_compositions"].max() or 1
    df["sample_reliability_score"] = _reliability_score(
        df["total_compositions"].fillna(0), max_comps
    )

    df["tactical_profile_score"] = (
        0.25 * df["composition_stability_score"]
        + 0.20 * df["agent_core_score"]
        + 0.20 * df["map_pool_visibility_score"]
        + 0.20 * df["map_identity_score"]
        + 0.15 * df["sample_reliability_score"]
    ).round(4)

    def _label(row: pd.Series) -> str:
        if (
            row["sample_reliability_score"] < 0.30
            or (row["total_compositions"] or 0) < MIN_TACTICAL_PROFILE_COMPOSITIONS
        ):
            return "low_sample_profile"

        stab = row["composition_stability_score"]
        identity = row["map_identity_score"]
        pool = row.get("agent_pool_size", 0) or 0

        if stab >= 0.55 and row["agent_core_score"] >= 0.50:
            return "stable_core"
        if identity >= 0.65:
            return "map_identity_team"
        if pool >= 8 and stab < 0.40:
            return "flexible_pool"
        if stab < 0.30 and pool >= 7:
            return "experimental_profile"
        return "stable_core"

    df["tactical_profile_label"] = df.apply(_label, axis=1)

    return df[
        [
            "team",
            "total_compositions",
            "maps_covered",
            "agent_pool_size",
            "unique_compositions",
            "composition_reuse_rate",
            "composition_stability_score",
            "map_pool_visibility_score",
            "agent_core_score",
            "map_identity_score",
            "sample_reliability_score",
            "tactical_profile_score",
            "tactical_profile_label",
        ]
    ].sort_values("tactical_profile_score", ascending=False)


# ---------------------------------------------------------------------------
# 3. Team Map Identity
# ---------------------------------------------------------------------------

def build_team_map_identity(team_map: pd.DataFrame) -> pd.DataFrame:
    df = team_map.copy()

    volume_weight = df["compositions"].fillna(0) * df["map_volume_share"].fillna(0)
    max_vw = volume_weight.max() or 1
    df["map_identity_score"] = (volume_weight / max_vw).round(4)

    max_comps_per_map = df.groupby("map")["compositions"].transform("max").replace(0, 1)
    df["sample_reliability_score"] = (
        df["compositions"].fillna(0) / max_comps_per_map
    ).round(4)

    def _identity_label(row: pd.Series) -> str:
        if (
            row["compositions"] < MIN_MAP_IDENTITY_COMPOSITIONS
            or row["sample_reliability_score"] < 0.20
        ):
            return "low_signal"

        score = row["map_identity_score"]
        share = row["map_volume_share"]

        if score >= 0.75 or share >= 0.60:
            return "signature_map"
        if score >= 0.45 or share >= 0.35:
            return "strong_map_identity"
        return "secondary_map"

    df["identity_label"] = df.apply(_identity_label, axis=1)

    return df[
        [
            "team",
            "map",
            "compositions",
            "map_volume_share",
            "unique_comps",
            "comp_diversity",
            "map_identity_score",
            "identity_label",
            "sample_reliability_score",
        ]
    ].sort_values(["team", "map_identity_score"], ascending=[True, False])


# ---------------------------------------------------------------------------
# 4. Composition Patterns
# ---------------------------------------------------------------------------

def build_composition_patterns(team_comps: pd.DataFrame) -> pd.DataFrame:
    pattern = (
        team_comps.groupby(["team", "map", "agents"], as_index=False)
        .agg(times_used=("match_id", "nunique"))
    )

    comp_team_count = (
        team_comps.drop_duplicates(["team", "agents"])
        .groupby("agents")["team"]
        .nunique()
        .rename("teams_using_same_comp")
        .reset_index()
    )

    comp_map_count = (
        team_comps.drop_duplicates(["map", "agents"])
        .groupby("agents")["map"]
        .nunique()
        .rename("maps_seen")
        .reset_index()
    )

    team_map_total = (
        team_comps.groupby(["team", "map"])["match_id"]
        .nunique()
        .rename("team_map_total")
        .reset_index()
    )

    pattern = (
        pattern.merge(comp_team_count, on="agents", how="left")
        .merge(comp_map_count, on="agents", how="left")
        .merge(team_map_total, on=["team", "map"], how="left")
    )

    pattern["composition_frequency"] = _safe_divide(
        pattern["times_used"], pattern["team_map_total"]
    ).round(4)

    max_teams = pattern["teams_using_same_comp"].max() or 1
    pattern["composition_uniqueness_score"] = (
        1 - (pattern["teams_using_same_comp"] - 1) / max(max_teams - 1, 1)
    ).clip(0, 1).round(4)

    max_uses = pattern["times_used"].max() or 1
    pattern["sample_reliability_score"] = _reliability_score(pattern["times_used"], max_uses)

    def _comp_label(row: pd.Series) -> str:
        if row["times_used"] < MIN_COMP_PATTERN_USES:
            return "low_sample_comp"

        teams_using = row["teams_using_same_comp"]
        uniqueness = row["composition_uniqueness_score"]
        maps_seen = row["maps_seen"]
        freq = row["composition_frequency"]

        if teams_using >= 4:
            return "standard_meta_comp"
        if uniqueness >= 0.90 and freq >= 0.50:
            return "team_signature_comp"
        if maps_seen == 1 and freq >= 0.30:
            return "map_specific_comp"
        if teams_using <= 2 and freq < 0.30:
            return "rare_comp"
        return "standard_meta_comp"

    pattern["composition_stability_label"] = pattern.apply(_comp_label, axis=1)

    return pattern[
        [
            "team",
            "map",
            "agents",
            "times_used",
            "teams_using_same_comp",
            "maps_seen",
            "composition_frequency",
            "composition_uniqueness_score",
            "composition_stability_label",
            "sample_reliability_score",
        ]
    ].sort_values(["team", "map", "times_used"], ascending=[True, True, False])


# ---------------------------------------------------------------------------
# 5. Agent Pair Patterns
# ---------------------------------------------------------------------------

def build_agent_pair_patterns(agent_synergy: pd.DataFrame, agent_map: pd.DataFrame) -> pd.DataFrame:
    schema = [
        "map",
        "agent_a",
        "agent_b",
        "pair_picks",
        "teams_count",
        "pair_pick_rate",
        "agent_a_rate",
        "agent_b_rate",
        "synergy_lift",
        "sample_reliability_score",
        "pair_pattern_label",
    ]

    if agent_synergy.empty:
        return pd.DataFrame(columns=schema)

    df = agent_synergy.copy()

    max_picks = df["pair_picks"].max() or 1
    df["sample_reliability_score"] = _reliability_score(df["pair_picks"], max_picks)

    def _pair_label(row: pd.Series) -> str:
        reliability = row["sample_reliability_score"]
        picks = row["pair_picks"]
        lift = row["synergy_lift"]
        teams = row["teams_count"]
        a_rate = row.get("agent_a_rate", 0) or 0
        b_rate = row.get("agent_b_rate", 0) or 0

        if reliability < 0.25 or picks < MIN_SYNERGY_PAIR_PICKS:
            return "weak_signal"
        if a_rate >= 0.40 and b_rate >= 0.40 and teams >= 4:
            return "common_core_pair"
        if lift >= 2.0 and picks <= 5:
            return "high_lift_low_sample"
        if teams >= 3 and lift >= 1.3:
            return "map_pair"
        return "weak_signal"

    df["pair_pattern_label"] = df.apply(_pair_label, axis=1)

    return df.reindex(columns=schema).sort_values(
        ["map", "synergy_lift", "pair_picks"],
        ascending=[True, False, False],
    )


# ---------------------------------------------------------------------------
# 6. Composition Clusters
# ---------------------------------------------------------------------------

def build_composition_clusters(compositions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """KMeans on agent vectors. Exploratory only — not a primary model."""
    df = compositions.copy()
    df["agent_list"] = df["agents"].fillna("").map(
        lambda x: [a.strip() for a in str(x).split(",") if a.strip()]
    )

    if len(df) < 3:
        df["cluster"] = 0
        df["cluster_label"] = "not_enough_data"
        df["exploratory_cluster"] = True

        arch = pd.DataFrame(
            [
                {
                    "cluster": 0,
                    "cluster_label": "not_enough_data",
                    "compositions": len(df),
                    "representative_agents": "",
                    "note": "exploratory_only",
                }
            ]
        )
        return df.drop(columns=["agent_list"]), arch

    mlb = MultiLabelBinarizer()
    x = mlb.fit_transform(df["agent_list"])
    n_clusters = min(8, max(2, len(df) // 25))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
        df["cluster"] = model.fit_predict(x)

    encoded = pd.DataFrame(x, columns=mlb.classes_)
    encoded["cluster"] = df["cluster"].values

    labels: dict[int, str] = {}
    arch_rows = []

    for cluster, group in encoded.groupby("cluster"):
        profile = group.drop(columns="cluster").mean().sort_values(ascending=False)
        top_agents = list(profile.head(5).index)

        label = " + ".join(top_agents[:3])
        labels[int(cluster)] = label

        cluster_rows = df[df["cluster"] == cluster]

        arch_rows.append(
            {
                "cluster": int(cluster),
                "cluster_label": label,
                "compositions": int(len(cluster_rows)),
                "teams_count": int(cluster_rows["team"].nunique()),
                "maps_count": int(cluster_rows["map"].nunique()),
                "representative_agents": ",".join(top_agents),
                "most_common_map": (
                    cluster_rows["map"].mode().iat[0]
                    if not cluster_rows["map"].mode().empty
                    else None
                ),
                "note": "exploratory_only",
            }
        )

    df["cluster_label"] = df["cluster"].map(labels)
    df["exploratory_cluster"] = True

    arch = pd.DataFrame(arch_rows).sort_values("compositions", ascending=False)

    return df.drop(columns=["agent_list"]), arch


# ---------------------------------------------------------------------------
# 7. Insights JSON
# ---------------------------------------------------------------------------


def build_insights(
    agent_presence: pd.DataFrame,
    tactical_profiles: pd.DataFrame,
    team_map_identity: pd.DataFrame,
    comp_patterns: pd.DataFrame,
    pair_patterns: pd.DataFrame,
) -> dict[str, Any]:
    top_insights: list[dict[str, Any]] = []

    global_meta = agent_presence[
        agent_presence["agent_meta_label"] == "global_meta_core"
    ].sort_values("meta_presence_score", ascending=False)

    if not global_meta.empty:
        row = global_meta.iloc[0]
        top_insights.append(
            {
                "type": "meta_agent",
                "title": f"{row['agent']} is the most present agent in the observed meta",
                "entity": row["agent"],
                "metric": "meta_presence_score",
                "value": round(float(row["meta_presence_score"]), 4),
                "confidence": _confidence(float(row["sample_reliability_score"])),
                "evidence": {
                    "global_pick_rate": round(float(row["global_pick_rate"]), 4),
                    "cross_map_stability": round(
                        float(row["cross_map_stability_score"]), 4
                    ),
                    "maps_played": int(row["maps_played"]),
                },
                "warning": None,
            }
        )

    specialists = agent_presence[
        agent_presence["agent_meta_label"] == "map_specialist"
    ].sort_values("map_dependence_score", ascending=False)

    if not specialists.empty:
        row = specialists.iloc[0]
        top_insights.append(
            {
                "type": "map_specialist",
                "title": f"{row['agent']} shows strong map dependency on {row['map']}",
                "entity": row["agent"],
                "metric": "map_dependence_score",
                "value": round(float(row["map_dependence_score"]), 4),
                "confidence": _confidence(float(row["sample_reliability_score"])),
                "evidence": {
                    "map": row["map"],
                    "local_pick_rate": round(float(row["pick_rate"]), 4),
                    "global_pick_rate": round(float(row["global_pick_rate"]), 4),
                    "local_pick_delta": round(float(row["local_pick_delta"]), 4),
                },
                "warning": (
                    "Map-dependency is based on pick-rate delta only; "
                    "it does not imply win-rate difference."
                ),
            }
        )

    stable_profiles = tactical_profiles[
        tactical_profiles["tactical_profile_label"] == "stable_core"
    ].sort_values("tactical_profile_score", ascending=False)

    if not stable_profiles.empty:
        row = stable_profiles.iloc[0]
        top_insights.append(
            {
                "type": "team_profile",
                "title": (
                    f"{row['team']} has the most structured tactical profile "
                    "in the observed data"
                ),
                "entity": row["team"],
                "metric": "tactical_profile_score",
                "value": round(float(row["tactical_profile_score"]), 4),
                "confidence": _confidence(float(row["sample_reliability_score"])),
                "evidence": {
                    "composition_stability_score": round(
                        float(row["composition_stability_score"]), 4
                    ),
                    "agent_core_score": round(float(row["agent_core_score"]), 4),
                    "maps_covered": int(row["maps_covered"]),
                    "total_compositions": int(row["total_compositions"]),
                },
                "warning": (
                    "tactical_profile_score measures structural legibility, "
                    "not competitive strength."
                ),
            }
        )

    signature_maps = team_map_identity[
        team_map_identity["identity_label"] == "signature_map"
    ].sort_values("map_identity_score", ascending=False)

    if not signature_maps.empty:
        row = signature_maps.iloc[0]
        top_insights.append(
            {
                "type": "map_identity",
                "title": f"{row['team']} has a signature map identity on {row['map']}",
                "entity": row["team"],
                "metric": "map_identity_score",
                "value": round(float(row["map_identity_score"]), 4),
                "confidence": _confidence(float(row["sample_reliability_score"])),
                "evidence": {
                    "map": row["map"],
                    "map_volume_share": round(float(row["map_volume_share"]), 4),
                    "compositions": int(row["compositions"]),
                    "comp_diversity": round(float(row["comp_diversity"]), 4),
                },
                "warning": None,
            }
        )

    signature_comps = comp_patterns[
        comp_patterns["composition_stability_label"] == "team_signature_comp"
    ].sort_values(["composition_frequency", "times_used"], ascending=False)

    if not signature_comps.empty:
        row = signature_comps.iloc[0]
        top_insights.append(
            {
                "type": "signature_composition",
                "title": f"{row['team']} relies on a signature composition on {row['map']}",
                "entity": row["team"],
                "metric": "composition_frequency",
                "value": round(float(row["composition_frequency"]), 4),
                "confidence": _confidence(float(row["sample_reliability_score"])),
                "evidence": {
                    "agents": row["agents"],
                    "times_used": int(row["times_used"]),
                    "teams_using_same_comp": int(row["teams_using_same_comp"]),
                    "map": row["map"],
                },
                "warning": None,
            }
        )

    if not pair_patterns.empty:
        high_lift_low_sample = pair_patterns[
            pair_patterns["pair_pattern_label"] == "high_lift_low_sample"
        ].sort_values("synergy_lift", ascending=False)

        if not high_lift_low_sample.empty:
            row = high_lift_low_sample.iloc[0]
            top_insights.append(
                {
                    "type": "agent_pair",
                    "title": (
                        f"{row['agent_a']} + {row['agent_b']} shows high co-pick lift "
                        f"on {row['map']} but low sample"
                    ),
                    "entity": f"{row['agent_a']}+{row['agent_b']}",
                    "metric": "synergy_lift",
                    "value": round(float(row["synergy_lift"]), 3),
                    "confidence": "low",
                    "evidence": {
                        "map": row["map"],
                        "pair_picks": int(row["pair_picks"]),
                        "teams_count": int(row["teams_count"]),
                    },
                    "warning": (
                        "High lift with low sample. Treat this as a weak signal "
                        "requiring more data."
                    ),
                }
            )

        common_core_pairs = pair_patterns[
            pair_patterns["pair_pattern_label"] == "common_core_pair"
        ].sort_values(["teams_count", "pair_pick_rate"], ascending=False)

        if not common_core_pairs.empty:
            row = common_core_pairs.iloc[0]
            top_insights.append(
                {
                    "type": "agent_pair",
                    "title": (
                        f"{row['agent_a']} + {row['agent_b']} is a widespread "
                        "core pair across the observed meta"
                    ),
                    "entity": f"{row['agent_a']}+{row['agent_b']}",
                    "metric": "pair_pick_rate",
                    "value": round(float(row["pair_pick_rate"]), 4),
                    "confidence": _confidence(float(row["sample_reliability_score"])),
                    "evidence": {
                        "map": row["map"],
                        "teams_count": int(row["teams_count"]),
                        "synergy_lift": round(float(row["synergy_lift"]), 3),
                    },
                    "warning": None,
                }
            )

    data_quality = {
        "total_compositions_observed": int(len(comp_patterns)),
        "teams_profiled": int(len(tactical_profiles)),
        "agents_with_meta_presence_data": int(len(agent_presence)),
        "signature_maps_found": int(
            (team_map_identity["identity_label"] == "signature_map").sum()
        ),
        "pair_patterns_above_threshold": int(len(pair_patterns)),
        "insights_generated": len(top_insights),
    }

    methodology_notes = [
        "All scores measure presence, stability, or structural legibility — not win probability or competitive rank.",
        "meta_presence_score = 0.40 × pick_rate + 0.25 × composition_rate + 0.20 × cross_map_stability + 0.15 × reliability.",
        "tactical_profile_score = 0.25 × stability + 0.20 × agent_core + 0.20 × map_pool + 0.20 × map_identity + 0.15 × reliability.",
        "map_identity_score = compositions × map_volume_share, normalised per map.",
        "synergy_lift = pair_pick_rate / (agent_a_rate × agent_b_rate). Values above 1 indicate co-picks above an independence baseline.",
        f"Low-sample thresholds: maps_played < {MIN_META_MAPS_PLAYED} means low_sample_signal; total_compositions < {MIN_TACTICAL_PROFILE_COMPOSITIONS} means low_sample_profile.",
        "KMeans composition clusters are exploratory only and should not be interpreted as a tactical truth model.",
        "Data source: observed VLR.gg compositions. No map winners, scorelines, round outcomes, or player-level performance are used.",
    ]

    def _json_safe(obj: Any) -> Any:
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        return obj

    return json.loads(
        json.dumps(
            {
                "data_quality": data_quality,
                "top_insights": top_insights,
                "methodology_notes": methodology_notes,
            },
            default=_json_safe,
        )
    )


# ---------------------------------------------------------------------------
# Backward-compat shims
# ---------------------------------------------------------------------------


def _build_agent_tiers_compat(agent_meta_presence: pd.DataFrame) -> pd.DataFrame:
    df = agent_meta_presence.copy()
    df["tier_score"] = df["meta_presence_score"]
    df["tier"] = df["agent_meta_label"]
    return df


def _build_team_strengths_compat(tactical_profiles: pd.DataFrame) -> pd.DataFrame:
    df = tactical_profiles.copy()
    df["team_profile_score"] = df["tactical_profile_score"]
    return df


def _build_map_specialists_compat(agent_meta_presence: pd.DataFrame) -> pd.DataFrame:
    return agent_meta_presence[
        agent_meta_presence["agent_meta_label"] == "map_specialist"
    ].copy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_all_models() -> dict[str, pd.DataFrame]:
    agent_map = read_csv_required(AGENT_MAP_STATS)
    team_map = read_csv_required(TEAM_MAP_STATS)
    team_agent = read_csv_required(TEAM_AGENT_STATS)
    team_comps = read_csv_required(TEAM_COMPOSITIONS)

    synergy = (
        read_csv_required(AGENT_SYNERGY)
        if AGENT_SYNERGY.exists()
        else pd.DataFrame()
    )

    agent_meta_presence = build_agent_meta_presence(agent_map)
    agent_global_meta = build_agent_global_meta(agent_meta_presence)
    tactical_profiles = build_team_tactical_profiles(
        team_map=team_map,
        team_agent=team_agent,
        team_comps=team_comps,
    )
    team_map_identity = build_team_map_identity(team_map)
    comp_patterns = build_composition_patterns(team_comps)
    pair_patterns = build_agent_pair_patterns(synergy, agent_map)
    comp_clusters, archetypes = build_composition_clusters(team_comps)

    insights = build_insights(
        agent_presence=agent_meta_presence,
        tactical_profiles=tactical_profiles,
        team_map_identity=team_map_identity,
        comp_patterns=comp_patterns,
        pair_patterns=pair_patterns,
    )

    agent_meta_presence_path = MODELS_DIR / "agent_meta_presence.csv"
    agent_global_meta_path = MODELS_DIR / "agent_global_meta.csv"
    team_tactical_profiles_path = MODELS_DIR / "team_tactical_profiles.csv"
    comp_patterns_path = MODELS_DIR / "composition_patterns.csv"
    agent_pair_patterns_path = MODELS_DIR / "agent_pair_patterns.csv"

    write_csv(agent_meta_presence, agent_meta_presence_path)
    write_csv(agent_global_meta, agent_global_meta_path)
    write_csv(tactical_profiles, team_tactical_profiles_path)
    write_csv(team_map_identity, TEAM_MAP_IDENTITY)
    write_csv(comp_patterns, comp_patterns_path)
    write_csv(pair_patterns, agent_pair_patterns_path)
    write_csv(comp_clusters, COMPOSITION_CLUSTERS)
    write_csv(archetypes, COMPOSITION_ARCHETYPES)
    write_json(insights, INSIGHTS)

    agent_tiers_compat = _build_agent_tiers_compat(agent_meta_presence)
    team_strengths_compat = _build_team_strengths_compat(tactical_profiles)
    map_specialists_compat = _build_map_specialists_compat(agent_meta_presence)

    write_csv(agent_tiers_compat, AGENT_TIERS)
    write_csv(team_strengths_compat, TEAM_STRENGTHS)
    write_csv(map_specialists_compat, MAP_SPECIALISTS)

    return {
        "agent_meta_presence": agent_meta_presence,
        "team_tactical_profiles": tactical_profiles,
        "team_map_identity": team_map_identity,
        "composition_patterns": comp_patterns,
        "agent_pair_patterns": pair_patterns,
        "composition_clusters": comp_clusters,
        "composition_archetypes": archetypes,
        "agent_tiers": agent_tiers_compat,
        "team_profile_scores": team_strengths_compat,
        "map_specialists": map_specialists_compat,
        "agent_global_meta": agent_global_meta,
    }