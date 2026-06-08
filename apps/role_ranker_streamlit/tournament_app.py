from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vct_ranker.agents import ROLE_ORDER
from vct_ranker.matchmaking import DuelRules, active_players, eligible_players, pick_same_role_duel
from vct_ranker.ranking import DEFAULT_MAX_LOSSES, build_ranking, make_player_key, normalize_ranking_state, record_duel_result
from vct_ranker.scraper import scrape_vct_events
from vct_ranker.storage import load_players, load_rankings, save_players, save_rankings
from vct_ranker.vct import VCT_REGIONS, events_for_region

st.set_page_config(page_title="VCT Role Ranker", page_icon="⚔️", layout="wide")

CUSTOM_CSS = """
<style>
.block-container { padding-top: 2rem; }
[data-testid="stMetricValue"] { color: #F2C66D; }
.vct-card {
    border: 1px solid rgba(217,164,65,.28);
    border-radius: 22px;
    padding: 22px;
    background: radial-gradient(circle at top left, rgba(217,164,65,.14), rgba(20,23,34,.92) 42%);
    min-height: 275px;
}
.vct-title { font-size: 1.5rem; font-weight: 800; color: #F7E6BE; margin-bottom: .2rem; }
.vct-subtitle { color: rgba(245,233,211,.72); font-size: .95rem; margin-bottom: .9rem; }
.vct-agents { color: #F2C66D; font-size: .9rem; margin-top: .8rem; }
.small-muted { color: rgba(245,233,211,.62); font-size: .82rem; }
.rule-box {
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 16px;
    padding: 14px 16px;
    background: rgba(255,255,255,.035);
    color: rgba(245,233,211,.78);
    font-size: .9rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def normalize_players(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["team"] = df["team"].fillna("FA")
    if "vct_region" not in df.columns:
        df["vct_region"] = "Unknown"
    if "event_name" not in df.columns:
        df["event_name"] = "Unknown"
    df["player_key"] = df.apply(lambda row: make_player_key(row["player"], row["team"]), axis=1)
    for column in ["rating", "acs", "kd", "kast", "adr", "kpr", "apr", "fkpr", "fdpr", "hs_pct", "rounds", "role_confidence"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def player_card(player: pd.Series) -> None:
    agents = str(player.get("agents", "")).replace(",", " · ") or "agents inconnus"
    st.markdown(
        f"""
        <div class="vct-card">
            <div class="vct-title">{player['player']}</div>
            <div class="vct-subtitle">
                {player.get('team', 'FA')} · {player.get('vct_region', 'Unknown')} · {player.get('inferred_role', 'Flex')} · confiance {player.get('role_confidence', 0):.0%}
            </div>
            <div><b>VLR Rating:</b> {player.get('rating', 'N/A')} · <b>ACS:</b> {player.get('acs', 'N/A')} · <b>Rounds:</b> {player.get('rounds', 'N/A')}</div>
            <div><b>K:D:</b> {player.get('kd', 'N/A')} · <b>ADR:</b> {player.get('adr', 'N/A')} · <b>KAST:</b> {player.get('kast', 'N/A')}</div>
            <div class="vct-agents">{agents}</div>
            <div class="small-muted">Même rôle, même région sélectionnée, filtré sur volume + confiance rôle.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def cached_scrape_vct(region: str, timespan: str, min_rounds: int) -> pd.DataFrame:
    return scrape_vct_events(events_for_region(region), min_rounds=min_rounds, timespan=timespan)



def _duel_context(role: str, region: str, rules: DuelRules, players: pd.DataFrame) -> tuple:
    player_keys = tuple(sorted(str(key) for key in players.get("player_key", pd.Series(dtype=str)).tolist()))
    return (
        role,
        region,
        float(rules.role_confidence_min),
        int(rules.min_rounds),
        float(rules.min_vlr_rating),
        bool(rules.avoid_same_team),
        int(rules.max_losses),
        bool(rules.prefer_close_records),
        player_keys,
    )


def _get_player_by_key(players: pd.DataFrame, player_key: str) -> pd.Series | None:
    matches = players[players["player_key"].astype(str) == str(player_key)]
    if matches.empty:
        return None
    return matches.iloc[0]


def get_or_create_duel(
    players: pd.DataFrame,
    ranking_state: dict,
    rules: DuelRules,
    role: str,
    region: str,
) -> tuple[pd.Series, pd.Series] | None:
    """Keep the displayed duel stable across Streamlit reruns.

    Without this, clicking a button can trigger a rerun, randomly pick a new duel,
    and then apply the click to the new players instead of the players the user saw.
    """
    context = _duel_context(role, region, rules, players)
    if st.session_state.get("current_tournament_context") != context:
        st.session_state.current_tournament_duel = None
        st.session_state.current_tournament_context = context

    stored = st.session_state.get("current_tournament_duel")
    if stored:
        p1 = _get_player_by_key(players, stored[0])
        p2 = _get_player_by_key(players, stored[1])
        if p1 is not None and p2 is not None:
            return p1, p2

    duel = pick_same_role_duel(players, ranking_state, rules)
    if duel is None:
        st.session_state.current_tournament_duel = None
        return None

    p1, p2 = duel
    st.session_state.current_tournament_duel = (str(p1["player_key"]), str(p2["player_key"]))
    return p1, p2


if "ranking_state" not in st.session_state:
    st.session_state.ranking_state = normalize_ranking_state(load_rankings())
if "history" not in st.session_state:
    st.session_state.history = []

st.title("VCT Role Ranker")
st.caption("Classement subjectif des joueurs VCT uniquement, par région et par rôle, via duels contrôlés.")

with st.sidebar:
    st.header("Périmètre VCT")
    source_mode = st.radio("Données", ["Charger CSV local", "Scraper VCT maintenant"], index=0)
    selected_region = st.selectbox("Région VCT", VCT_REGIONS, index=0)
    role_filter = st.selectbox("Rôle à classer", ROLE_ORDER, index=0)

    st.header("Règles de duel")
    min_rounds = st.slider("Minimum rounds", 0, 1000, 300, step=50)
    confidence_min = st.slider("Confiance rôle minimale", 0.0, 1.0, 0.70, step=0.05)
    min_vlr_rating = st.slider("VLR rating minimum", 0.0, 1.5, 1.00, step=0.05)
    max_losses = st.slider("Élimination après X défaites", 1, 5, DEFAULT_MAX_LOSSES, step=1)
    avoid_same_team = st.checkbox("Éviter les duels entre coéquipiers", value=True)
    prefer_close_records = st.checkbox("Comparer des bilans proches", value=True)
    timespan = st.selectbox("Timespan VLR", ["all", "30d", "60d", "90d"], index=0)

    if source_mode == "Scraper VCT maintenant":
        event_names = ", ".join(event.name for event in events_for_region(selected_region))
        st.caption(f"Events utilisés : {event_names}")
        if st.button("Scraper VCT et sauvegarder", type="primary"):
            with st.spinner("Scraping HTML VLR des events VCT configurés..."):
                scraped = cached_scrape_vct(selected_region, timespan, min_rounds)
                scraped = normalize_players(scraped)
                save_players(scraped)
                st.session_state.players = scraped
            st.success(f"{len(scraped)} lignes joueurs VCT chargées.")

    if st.button("Réinitialiser mon tournoi"):
        st.session_state.ranking_state = {}
        save_rankings(st.session_state.ranking_state)
        st.session_state.history = []
        st.session_state.current_tournament_duel = None
        st.success("Tournoi réinitialisé.")

players = st.session_state.get("players", normalize_players(load_players()))

if players.empty:
    st.info("Aucune donnée joueur chargée. Lance le scraping VCT dans la barre latérale.")
    st.stop()

rules = DuelRules(
    role_confidence_min=confidence_min,
    min_rounds=min_rounds,
    min_vlr_rating=min_vlr_rating,
    avoid_same_team=avoid_same_team,
    max_losses=int(max_losses),
    prefer_close_records=prefer_close_records,
)

visible_players = players.copy()
if selected_region != "All" and "vct_region" in visible_players.columns:
    visible_players = visible_players[visible_players["vct_region"] == selected_region]

role_players = eligible_players(players, role_filter, selected_region, rules)

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Joueurs éligibles", len(role_players))
col_b.metric("Équipes", role_players["team"].nunique() if not role_players.empty else 0)
active_role_players = active_players(role_players, st.session_state.ranking_state, rules)
col_c.metric("Duels faits", len(st.session_state.history))
col_d.metric("Joueurs encore en lice", len(active_role_players))

st.markdown(
    f"""
    <div class="rule-box">
    <b>Règles actives :</b> VCT uniquement · région = {selected_region} · rôle = {role_filter} · confiance rôle ≥ {confidence_min:.0%} · rounds ≥ {min_rounds} · VLR rating ≥ {min_vlr_rating:.2f} · élimination après {max_losses} défaites.
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()

left, right = st.columns([1.15, 1])

with left:
    st.subheader(f"Tournoi subjectif : meilleur {role_filter.lower()} ?")
    duel = get_or_create_duel(role_players, st.session_state.ranking_state, rules, role_filter, selected_region)
    if duel is None:
        st.warning("Pas assez de joueurs éligibles. Baisse le minimum de rounds, la confiance rôle ou le rating minimum.")
    else:
        p1, p2 = duel
        c1, c2 = st.columns(2)
        with c1:
            player_card(p1)
            if st.button(f"Choisir {p1['player']}", width="stretch", key="choose_p1"):
                winner_key = str(p1["player_key"])
                loser_key = str(p2["player_key"])
                st.session_state.ranking_state = record_duel_result(st.session_state.ranking_state, winner_key, loser_key)
                st.session_state.history.append((winner_key, loser_key, role_filter, selected_region))
                save_rankings(st.session_state.ranking_state)
                st.session_state.current_tournament_duel = None
                st.rerun()
        with c2:
            player_card(p2)
            if st.button(f"Choisir {p2['player']}", width="stretch", key="choose_p2"):
                winner_key = str(p2["player_key"])
                loser_key = str(p1["player_key"])
                st.session_state.ranking_state = record_duel_result(st.session_state.ranking_state, winner_key, loser_key)
                st.session_state.history.append((winner_key, loser_key, role_filter, selected_region))
                save_rankings(st.session_state.ranking_state)
                st.session_state.current_tournament_duel = None
                st.rerun()

with right:
    st.subheader("Classement actuel")
    ranking_base = visible_players if selected_region != "All" else players
    ranking = build_ranking(ranking_base, st.session_state.ranking_state, role_filter, max_losses=max_losses)
    if not ranking.empty:
        display_cols = ["rank", "player", "team", "vct_region", "user_wins", "user_losses", "losses_remaining", "user_win_rate", "eliminated", "tournament_score", "rating", "acs", "rounds", "agents", "role_confidence"]
        existing_cols = [col for col in display_cols if col in ranking.columns]
        st.dataframe(
            ranking[existing_cols].rename(
                columns={
                    "rank": "#",
                    "player": "Joueur",
                    "team": "Team",
                    "vct_region": "Région",
                    "user_wins": "Victoires",
                    "user_losses": "Défaites",
                    "losses_remaining": "Vies",
                    "user_win_rate": "Win rate",
                    "eliminated": "Éliminé",
                    "tournament_score": "Score tournoi",
                    "rating": "VLR Rating",
                    "acs": "ACS",
                    "rounds": "Rounds",
                    "agents": "Agents",
                    "role_confidence": "Confiance rôle",
                }
            ),
            width="stretch",
            hide_index=True,
        )

st.divider()
st.subheader("Vue analytique")
if not ranking.empty:
    top_n = ranking.head(20).copy()
    fig = px.bar(top_n, x="tournament_score", y="player", orientation="h", hover_data=["team", "vct_region", "user_wins", "user_losses", "user_win_rate", "rating", "acs", "rounds", "agents"])
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=620, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, width="stretch")

with st.expander("Contrôle qualité des rôles et du périmètre VCT"):
    cols = ["player", "team", "vct_region", "event_name", "agents", "inferred_role", "role_confidence", "rounds", "rating", "acs"]
    existing = [col for col in cols if col in players.columns]
    st.dataframe(
        players[existing].sort_values(["vct_region", "inferred_role", "role_confidence"], ascending=[True, True, False]),
        width="stretch",
        hide_index=True,
    )
    st.markdown(
        "Règle rôle : majorité des agents joués. Si aucun rôle officiel n'atteint 60 %, le joueur devient Flex. "
        "Les duels ne comparent ensuite que des joueurs du même rôle inféré et de la région sélectionnée."
    )
