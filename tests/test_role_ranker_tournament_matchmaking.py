import pandas as pd

from vct_ranker.matchmaking import DuelRules, eligible_players, pick_same_role_duel


def test_eligible_players_filters_same_role_and_region():
    df = pd.DataFrame(
        [
            {"player_key": "a", "inferred_role": "Duelist", "vct_region": "EMEA", "role_confidence": 1.0, "rounds": 500, "rating": 1.1, "team": "A"},
            {"player_key": "b", "inferred_role": "Controller", "vct_region": "EMEA", "role_confidence": 1.0, "rounds": 500, "rating": 1.1, "team": "B"},
            {"player_key": "c", "inferred_role": "Duelist", "vct_region": "Americas", "role_confidence": 1.0, "rounds": 500, "rating": 1.1, "team": "C"},
        ]
    )

    out = eligible_players(df, "Duelist", "EMEA", DuelRules())
    assert list(out["player_key"]) == ["a"]


def test_pick_same_role_duel_returns_two_distinct_players():
    df = pd.DataFrame(
        [
            {"player_key": "a", "team": "A"},
            {"player_key": "b", "team": "B"},
        ]
    )
    duel = pick_same_role_duel(df, {}, DuelRules())
    assert duel is not None
    assert duel[0]["player_key"] != duel[1]["player_key"]
