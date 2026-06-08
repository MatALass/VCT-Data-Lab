from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from playoff_odds.simulation.run_simulation import main as run_simulation_main

DATA_DIR = ROOT / "data" / "playoff_odds"
DEFAULT_CONFIG = DATA_DIR / "config.sample.json"
DEFAULT_DATASET = DATA_DIR / "vct-emea-2026.json"
DEFAULT_OUTPUT_DIR = ROOT / "simulation" / "output"

st.set_page_config(page_title="VCT Playoff Odds", page_icon="🎲", layout="wide")

CUSTOM_CSS = """
<style>
.block-container { padding-top: 2rem; }
[data-testid="stMetricValue"] { color: #F2C66D; }
.playoff-note {
    border: 1px solid rgba(217,164,65,.26);
    border-radius: 16px;
    padding: 14px 16px;
    background: rgba(217,164,65,.08);
    color: rgba(245,233,211,.82);
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _dataset_signature(path: Path) -> tuple[str, int, int]:
    if not path.exists():
        return (str(path), 0, 0)
    stat = path.stat()
    return (str(path), int(stat.st_mtime), int(stat.st_size))


@st.cache_data(show_spinner=False)
def load_dataset(signature: tuple[str, int, int]) -> dict[str, Any]:
    path = Path(signature[0])
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def teams_frame(dataset: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group in dataset.get("groups", []):
        group_name = group.get("name", "Unknown")
        for team in group.get("teams", []):
            row = {
                "group": group_name,
                "team": team.get("team"),
                "qualify_prob": float(team.get("qualifyProb", 0.0)),
                "expected_rank": float(team.get("expectedRank", 0.0)),
                "best_rank_seen": team.get("bestRankSeen"),
                "worst_rank_seen": team.get("worstRankSeen"),
            }
            bounds = team.get("exactWinnerOnlyBounds") or {}
            row["exact_best"] = bounds.get("best")
            row["exact_worst"] = bounds.get("worst")
            positions = team.get("positions") or {}
            for key, value in positions.items():
                row[key] = float(value)
            rows.append(row)
    return pd.DataFrame(rows)


def matches_frame(dataset: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    impacts = dataset.get("matchImpacts", {}) or {}
    for group_name, matches in impacts.items():
        for match in matches:
            row = {"group": group_name, **match}
            rows.append(row)
    if not rows:
        for match in dataset.get("remainingMatches", []) or []:
            rows.append({"group": match.get("group"), "match": f"{match.get('teamA')} vs {match.get('teamB')}"})
    return pd.DataFrame(rows)


def run_simulation(config_path: Path, dataset_path: Path, seed: int, show_progress: bool) -> None:
    previous_argv = sys.argv[:]
    sys.argv = [
        "playoff_odds.simulation.run_simulation",
        "--config",
        str(config_path),
        "--output-json",
        str(dataset_path),
        "--output-dir",
        str(DEFAULT_OUTPUT_DIR),
        "--seed",
        str(seed),
    ]
    if show_progress:
        sys.argv.append("--show-progress")
    try:
        run_simulation_main()
    finally:
        sys.argv = previous_argv


st.title("VCT Playoff Odds")
st.caption("Simulation Monte Carlo des qualifications/playoffs intégrée au projet VCT Data Lab.")

with st.sidebar:
    st.header("Dataset")
    dataset_path = Path(st.text_input("JSON dataset", value=str(DEFAULT_DATASET)))
    config_path = Path(st.text_input("Config simulation", value=str(DEFAULT_CONFIG)))
    seed = st.number_input("Seed", min_value=0, value=42, step=1)
    show_progress = st.checkbox("Afficher la progression console", value=False)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Recharger JSON", width="stretch"):
            load_dataset.clear()
            st.rerun()
    with col_b:
        if st.button("Recalculer", type="primary", width="stretch"):
            if not config_path.exists():
                st.error(f"Config introuvable : {config_path}")
            else:
                with st.spinner("Simulation Monte Carlo en cours..."):
                    run_simulation(config_path, dataset_path, int(seed), show_progress)
                    load_dataset.clear()
                st.success("Dataset recalculé.")
                st.rerun()

    st.markdown("---")
    st.caption("Le recalcul lance le moteur Python local. Les changements de filtres ci-dessous ne recalculent pas la simulation.")

dataset = load_dataset(_dataset_signature(dataset_path))
if not dataset:
    st.info("Aucun dataset chargé. Utilise le dataset par défaut ou clique sur Recalculer.")
    st.stop()

teams = teams_frame(dataset)
matches = matches_frame(dataset)

meta_left, meta_mid, meta_right = st.columns(3)
meta_left.metric("League", dataset.get("league", "N/A"))
meta_mid.metric("Season", dataset.get("season", "N/A"))
meta_right.metric("Slots qualification", dataset.get("qualificationSlots", "N/A"))

if not teams.empty:
    selected_group = st.selectbox("Groupe", ["All"] + sorted(teams["group"].dropna().unique().tolist()))
    visible = teams if selected_group == "All" else teams[teams["group"] == selected_group]

    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.subheader("Probabilité de qualification")
        fig = px.bar(
            visible.sort_values("qualify_prob", ascending=True),
            x="qualify_prob",
            y="team",
            color="group" if selected_group == "All" else None,
            orientation="h",
            hover_data=["expected_rank", "best_rank_seen", "worst_rank_seen", "exact_best", "exact_worst"],
        )
        fig.update_xaxes(tickformat=".0%")
        fig.update_layout(height=520, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.subheader("Classement simulation")
        display = visible.copy()
        display["qualify_prob"] = display["qualify_prob"].map(lambda x: f"{x:.1%}")
        cols = ["group", "team", "qualify_prob", "expected_rank", "best_rank_seen", "worst_rank_seen", "exact_best", "exact_worst"]
        st.dataframe(
            display[cols].rename(
                columns={
                    "group": "Groupe",
                    "team": "Équipe",
                    "qualify_prob": "Qualif %",
                    "expected_rank": "Rang attendu",
                    "best_rank_seen": "Meilleur rang MC",
                    "worst_rank_seen": "Pire rang MC",
                    "exact_best": "Meilleur exact",
                    "exact_worst": "Pire exact",
                }
            ),
            width="stretch",
            hide_index=True,
        )

st.divider()
st.subheader("Matchs à fort impact")
if not matches.empty:
    ordered = matches.copy()
    if "importance" in ordered.columns:
        ordered["importance"] = pd.to_numeric(ordered["importance"], errors="coerce")
        ordered = ordered.sort_values("importance", ascending=False)
    st.dataframe(ordered, width="stretch", hide_index=True)
else:
    st.info("Aucun match restant ou impact calculé dans ce dataset.")

st.divider()
st.subheader("Insights")
insights = dataset.get("insights", []) or []
if insights:
    for insight in insights:
        st.markdown(f"- {insight}")
else:
    st.info("Aucun insight généré.")

with st.expander("Notes méthodologiques"):
    notes = dataset.get("notes", {}) or {}
    if notes:
        for key, value in notes.items():
            st.markdown(f"**{key}**: {value}")
    else:
        st.markdown("Aucune note méthodologique disponible.")
