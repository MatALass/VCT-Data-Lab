"""Unit tests for modeling layer v2.

Tests cover:
- Required output columns
- Label exhaustiveness
- Score ranges
- Low-sample thresholds
- No forbidden metric names (win_rate, strength, probability)
- Insight structure
"""

from __future__ import annotations

import pandas as pd
import pytest

from vlr_analytics.modeling.build import (
    build_agent_meta_presence,
    build_agent_pair_patterns,
    build_composition_patterns,
    build_insights,
    build_team_map_identity,
    build_team_tactical_profiles,
)
from vlr_analytics.thresholds import (
    MIN_META_MAPS_PLAYED,
    MIN_TACTICAL_PROFILE_COMPOSITIONS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AGENTS = ["neon", "viper", "sova", "killjoy", "sage"]
MAPS = ["BIND", "HAVEN", "LOTUS"]


def _make_agent_map() -> pd.DataFrame:
    rows = []
    for m in MAPS:
        for a in AGENTS:
            rows.append({
                "map": m, "agent": a, "maps_played": 10.0,
                "pick_rate": 0.6 if a == "neon" else 0.3,
                "pick_rate_from_comps": 0.5 if a == "neon" else 0.25,
                "sample_confidence": 1.0,
                "side_delta": 0.01,
            })
    # All Maps row
    for a in AGENTS:
        rows.append({
            "map": "All Maps", "agent": a, "maps_played": 30.0,
            "pick_rate": 0.6 if a == "neon" else 0.3,
            "pick_rate_from_comps": 0.5 if a == "neon" else 0.25,
            "sample_confidence": 1.0,
            "side_delta": 0.01,
        })
    return pd.DataFrame(rows)


def _make_team_comps() -> pd.DataFrame:
    rows = []
    for i in range(6):
        rows.append({
            "event": "evt1", "map": "BIND", "match_id": f"m{i}",
            "team": "TeamA", "opponent": "TeamB",
            "agents": "neon,viper,sova,killjoy,sage",
            "agents_count": 5, "observed": True,
        })
    rows.append({
        "event": "evt1", "map": "HAVEN", "match_id": "m7",
        "team": "TeamA", "opponent": "TeamB",
        "agents": "neon,viper,sova,killjoy,brimstone",
        "agents_count": 5, "observed": True,
    })
    rows.append({
        "event": "evt1", "map": "BIND", "match_id": "m8",
        "team": "TeamB", "opponent": "TeamA",
        "agents": "neon,viper,sage,killjoy,fade",
        "agents_count": 5, "observed": True,
    })
    return pd.DataFrame(rows)


def _make_team_map_stats() -> pd.DataFrame:
    return pd.DataFrame([
        {"team": "TeamA", "map": "BIND", "compositions": 6, "opponents": 1,
         "unique_comps": 1, "comp_diversity": 0.17, "map_volume_share": 0.86, "observed": True},
        {"team": "TeamA", "map": "HAVEN", "compositions": 1, "opponents": 1,
         "unique_comps": 1, "comp_diversity": 1.0, "map_volume_share": 0.14, "observed": True},
        {"team": "TeamB", "map": "BIND", "compositions": 1, "opponents": 1,
         "unique_comps": 1, "comp_diversity": 1.0, "map_volume_share": 1.0, "observed": True},
    ])


def _make_team_agent_stats() -> pd.DataFrame:
    rows = []
    for a in AGENTS:
        rows.append({
            "team": "TeamA", "agent": a, "agent_picks": 6,
            "team_total_compositions": 7, "team_agent_pick_rate": 6 / 7,
            "observed": True, "signature_level": "signature",
        })
    rows.append({
        "team": "TeamA", "agent": "brimstone", "agent_picks": 1,
        "team_total_compositions": 7, "team_agent_pick_rate": 1 / 7,
        "observed": True, "signature_level": "rare",
    })
    for a in ["neon", "viper", "sage", "killjoy", "fade"]:
        rows.append({
            "team": "TeamB", "agent": a, "agent_picks": 1,
            "team_total_compositions": 1, "team_agent_pick_rate": 1.0,
            "observed": True, "signature_level": "signature",
        })
    return pd.DataFrame(rows)


def _make_synergy() -> pd.DataFrame:
    return pd.DataFrame([
        {"map": "BIND", "agent_a": "neon", "agent_b": "viper",
         "pair_picks": 10, "teams_count": 4, "events_count": 2,
         "total_compositions": 20, "pair_pick_rate": 0.5,
         "agent_a_rate": 0.8, "agent_b_rate": 0.8,
         "synergy_lift": 0.78, "observed": True},
        {"map": "HAVEN", "agent_a": "sage", "agent_b": "sova",
         "pair_picks": 3, "teams_count": 2, "events_count": 1,
         "total_compositions": 5, "pair_pick_rate": 0.6,
         "agent_a_rate": 0.2, "agent_b_rate": 0.2,
         "synergy_lift": 15.0, "observed": True},
    ])


# ---------------------------------------------------------------------------
# agent_meta_presence
# ---------------------------------------------------------------------------

class TestAgentMetaPresence:
    REQUIRED_COLS = {
        "map", "agent", "maps_played", "pick_rate", "pick_rate_from_comps",
        "sample_reliability_score", "global_pick_rate", "local_pick_delta",
        "cross_map_stability_score", "map_dependence_score",
        "meta_presence_score", "agent_meta_label",
    }
    VALID_LABELS = {
        "global_meta_core", "stable_pick", "map_specialist",
        "situational_pick", "low_sample_signal",
    }

    def test_required_columns(self):
        df = build_agent_meta_presence(_make_agent_map())
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_labels_are_valid(self):
        df = build_agent_meta_presence(_make_agent_map())
        assert set(df["agent_meta_label"].unique()).issubset(self.VALID_LABELS)

    def test_scores_between_0_and_1(self):
        df = build_agent_meta_presence(_make_agent_map())
        for col in ["meta_presence_score", "sample_reliability_score", "cross_map_stability_score"]:
            assert df[col].between(0, 1).all(), f"{col} out of [0,1]"

    def test_local_only_no_all_maps(self):
        df = build_agent_meta_presence(_make_agent_map())
        assert "All Maps" not in df["map"].values

    def test_low_sample_threshold(self):
        agent_map = _make_agent_map()
        agent_map.loc[agent_map["map"] != "All Maps", "maps_played"] = MIN_META_MAPS_PLAYED - 1
        df = build_agent_meta_presence(agent_map)
        assert (df["agent_meta_label"] == "low_sample_signal").all()

    def test_no_forbidden_column_names(self):
        df = build_agent_meta_presence(_make_agent_map())
        forbidden = {"win_rate", "strength", "probability", "tier"}
        cols = {c.lower() for c in df.columns}
        overlap = forbidden & cols
        assert not overlap, f"Forbidden column names found: {overlap}"


# ---------------------------------------------------------------------------
# team_tactical_profiles
# ---------------------------------------------------------------------------

class TestTeamTacticalProfiles:
    REQUIRED_COLS = {
        "team", "total_compositions", "maps_covered", "agent_pool_size",
        "unique_compositions", "composition_reuse_rate", "composition_stability_score",
        "map_pool_visibility_score", "agent_core_score", "map_identity_score",
        "sample_reliability_score", "tactical_profile_score", "tactical_profile_label",
    }
    VALID_LABELS = {
        "stable_core", "flexible_pool", "map_identity_team",
        "experimental_profile", "low_sample_profile",
    }

    def test_required_columns(self):
        df = build_team_tactical_profiles(_make_team_map_stats(), _make_team_agent_stats(), _make_team_comps())
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_labels_are_valid(self):
        df = build_team_tactical_profiles(_make_team_map_stats(), _make_team_agent_stats(), _make_team_comps())
        assert set(df["tactical_profile_label"].unique()).issubset(self.VALID_LABELS)

    def test_scores_between_0_and_1(self):
        df = build_team_tactical_profiles(_make_team_map_stats(), _make_team_agent_stats(), _make_team_comps())
        for col in ["tactical_profile_score", "composition_stability_score",
                    "map_pool_visibility_score", "agent_core_score", "sample_reliability_score"]:
            assert df[col].between(0, 1).all(), f"{col} out of [0,1]"

    def test_no_forbidden_column_names(self):
        df = build_team_tactical_profiles(_make_team_map_stats(), _make_team_agent_stats(), _make_team_comps())
        forbidden = {"win_rate", "strength", "probability", "force"}
        cols = {c.lower() for c in df.columns}
        assert not (forbidden & cols), f"Forbidden: {forbidden & cols}"

    def test_low_sample_label(self):
        small_comps = _make_team_comps().head(1)
        small_maps = _make_team_map_stats()[_make_team_map_stats()["team"] == "TeamB"]
        small_agents = _make_team_agent_stats()[_make_team_agent_stats()["team"] == "TeamB"]
        df = build_team_tactical_profiles(small_maps, small_agents, small_comps)
        assert (df["tactical_profile_label"] == "low_sample_profile").all()


# ---------------------------------------------------------------------------
# team_map_identity
# ---------------------------------------------------------------------------

class TestTeamMapIdentity:
    REQUIRED_COLS = {
        "team", "map", "compositions", "map_volume_share",
        "unique_comps", "comp_diversity", "map_identity_score",
        "identity_label", "sample_reliability_score",
    }
    VALID_LABELS = {"signature_map", "strong_map_identity", "secondary_map", "low_signal"}

    def test_required_columns(self):
        df = build_team_map_identity(_make_team_map_stats())
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_labels_are_valid(self):
        df = build_team_map_identity(_make_team_map_stats())
        assert set(df["identity_label"].unique()).issubset(self.VALID_LABELS)

    def test_map_identity_score_in_range(self):
        df = build_team_map_identity(_make_team_map_stats())
        assert df["map_identity_score"].between(0, 1).all()


# ---------------------------------------------------------------------------
# composition_patterns
# ---------------------------------------------------------------------------

class TestCompositionPatterns:
    REQUIRED_COLS = {
        "team", "map", "agents", "times_used", "teams_using_same_comp",
        "maps_seen", "composition_frequency", "composition_uniqueness_score",
        "composition_stability_label", "sample_reliability_score",
    }
    VALID_LABELS = {
        "standard_meta_comp", "team_signature_comp", "map_specific_comp",
        "rare_comp", "low_sample_comp",
    }

    def test_required_columns(self):
        df = build_composition_patterns(_make_team_comps())
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_labels_are_valid(self):
        df = build_composition_patterns(_make_team_comps())
        assert set(df["composition_stability_label"].unique()).issubset(self.VALID_LABELS)

    def test_frequency_between_0_and_1(self):
        df = build_composition_patterns(_make_team_comps())
        assert df["composition_frequency"].between(0, 1).all()


# ---------------------------------------------------------------------------
# agent_pair_patterns
# ---------------------------------------------------------------------------

class TestAgentPairPatterns:
    REQUIRED_COLS = {
        "map", "agent_a", "agent_b", "pair_picks", "teams_count",
        "pair_pick_rate", "agent_a_rate", "agent_b_rate",
        "synergy_lift", "sample_reliability_score", "pair_pattern_label",
    }
    VALID_LABELS = {"common_core_pair", "map_pair", "high_lift_low_sample", "weak_signal"}

    def test_required_columns(self):
        df = build_agent_pair_patterns(_make_synergy(), _make_agent_map())
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_labels_are_valid(self):
        df = build_agent_pair_patterns(_make_synergy(), _make_agent_map())
        assert set(df["pair_pattern_label"].unique()).issubset(self.VALID_LABELS)

    def test_empty_synergy_returns_empty_with_schema(self):
        df = build_agent_pair_patterns(pd.DataFrame(), _make_agent_map())
        assert df.empty
        assert self.REQUIRED_COLS.issubset(set(df.columns))

    def test_high_lift_low_sample_flagged(self):
        df = build_agent_pair_patterns(_make_synergy(), _make_agent_map())
        row = df[df["synergy_lift"] >= 10]
        assert not row.empty
        assert (row["pair_pattern_label"] == "high_lift_low_sample").all()


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

class TestInsights:
    def _build_all(self):
        agent_map = _make_agent_map()
        team_map = _make_team_map_stats()
        team_agent = _make_team_agent_stats()
        team_comps = _make_team_comps()
        synergy = _make_synergy()
        presence = build_agent_meta_presence(agent_map)
        profiles = build_team_tactical_profiles(team_map, team_agent, team_comps)
        identity = build_team_map_identity(team_map)
        patterns = build_composition_patterns(team_comps)
        pairs = build_agent_pair_patterns(synergy, agent_map)
        return build_insights(presence, profiles, identity, patterns, pairs)

    def test_top_level_keys(self):
        ins = self._build_all()
        assert {"data_quality", "top_insights", "methodology_notes"} == set(ins.keys())

    def test_data_quality_keys(self):
        ins = self._build_all()
        dq = ins["data_quality"]
        required = {"total_compositions_observed", "teams_profiled", "agents_with_meta_presence_data"}
        assert required.issubset(set(dq.keys()))

    def test_each_insight_has_required_fields(self):
        ins = self._build_all()
        required = {"type", "title", "entity", "metric", "value", "confidence", "evidence"}
        for insight in ins["top_insights"]:
            assert required.issubset(set(insight.keys())), f"Missing fields in: {insight}"

    def test_confidence_values_are_valid(self):
        ins = self._build_all()
        valid = {"high", "medium", "low"}
        for insight in ins["top_insights"]:
            assert insight["confidence"] in valid, f"Bad confidence: {insight['confidence']}"

    def test_methodology_notes_is_list_of_strings(self):
        ins = self._build_all()
        assert isinstance(ins["methodology_notes"], list)
        for note in ins["methodology_notes"]:
            assert isinstance(note, str)

    def test_no_win_rate_or_strength_in_insight_titles(self):
        ins = self._build_all()
        forbidden = ["win_rate", "win rate", "strength", "probability"]
        for insight in ins["top_insights"]:
            title_lower = insight["title"].lower()
            for f in forbidden:
                assert f not in title_lower, f"Forbidden term '{f}' found in insight title: {insight['title']}"
