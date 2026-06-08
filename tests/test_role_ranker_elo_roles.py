import pandas as pd

from vct_ranker_elo.roles import enrich_player_roles, infer_player_role, infer_player_role_details


def test_infer_duelist_role():
    role, confidence = infer_player_role(["jett", "raze", "neon"])
    assert role == "Duelist"
    assert confidence == 1.0


def test_infer_flex_when_mixed_pool():
    role, confidence = infer_player_role(["jett", "sova", "omen"])
    assert role == "Flex"
    assert confidence == 1.0


def test_viper_does_not_override_sentinel_pool():
    details = infer_player_role_details({"killjoy": 80, "cypher": 60, "viper": 100})
    assert details.raw_role == "Sentinel"
    assert details.role_scores["Sentinel"] > details.role_scores["Controller"]
    assert "Viper treated as Sentinel-side" in details.explanation


def test_weighted_agent_rounds_change_role_logic():
    details = infer_player_role_details({"omen": 180, "cypher": 20, "killjoy": 20})
    assert details.raw_role == "Controller"
    assert details.role_confidence > 0.80


def test_exact_five_team_gets_normalized_roles():
    df = pd.DataFrame(
        [
            {"player": "duelist", "team": "AAA", "event_id": 1, "agents": "jett,raze"},
            {"player": "sentinel", "team": "AAA", "event_id": 1, "agents": "cypher,killjoy"},
            {"player": "controller", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
            {"player": "flex", "team": "AAA", "event_id": 1, "agents": "sova,omen,cypher"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert set(enriched["team_role"]) == {"Duelist", "Controller", "Initiator", "Sentinel", "Flex"}



def test_viper_counts_as_sentinel_even_without_classic_sentinel_agents():
    details = infer_player_role_details({"viper": 120, "omen": 40})
    assert details.role_scores["Sentinel"] > details.role_scores["Controller"]
    assert details.raw_role in {"Sentinel", "Flex"}


def test_duelist_plus_chamber_is_locked_as_duelist():
    details = infer_player_role_details({"jett": 100, "raze": 60, "chamber": 80})
    assert details.raw_role == "Duelist"
    assert details.role_scores["Duelist"] == 1.0
    assert details.role_scores["Sentinel"] == 0.0


def test_team_context_allows_two_pure_duelists_when_no_sentinel_evidence():
    df = pd.DataFrame(
        [
            {"player": "marteen", "team": "M8", "event_id": 1, "agents": "jett,raze"},
            {"player": "bipo", "team": "M8", "event_id": 1, "agents": "neon,phoenix"},
            {"player": "controller", "team": "M8", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "M8", "event_id": 1, "agents": "sova,fade"},
            {"player": "second_init", "team": "M8", "event_id": 1, "agents": "breach,kayo"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"].isin(["marteen", "bipo"]), "team_role"].tolist().count("Duelist") == 2


def test_team_context_assigns_viper_flex_to_missing_sentinel_not_pure_duelist():
    df = pd.DataFrame(
        [
            {"player": "marteen", "team": "M8", "event_id": 1, "agents": "jett,raze"},
            {"player": "bipo", "team": "M8", "event_id": 1, "agents": "neon,phoenix"},
            {"player": "controller", "team": "M8", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "M8", "event_id": 1, "agents": "sova,fade"},
            {"player": "minny", "team": "M8", "event_id": 1, "agents": "viper,sova,breach"},
        ]
    )
    enriched = enrich_player_roles(df)
    minny_role = enriched.loc[enriched["player"] == "minny", "team_role"].iloc[0]
    assert minny_role == "Sentinel"
    assert set(enriched.loc[enriched["player"].isin(["marteen", "bipo"]), "team_role"]) == {"Duelist"}


def test_mixed_duelist_initiator_pool_is_flex_not_true_duelist():
    details = infer_player_role_details(["raze", "kayo", "neon"])
    assert details.raw_role == "Flex"
    assert details.role_scores["Duelist"] > details.role_scores["Initiator"]
    assert "Mixed Duelist + utility pool" in details.explanation


def test_team_context_keeps_mixed_duelist_initiator_as_flex_when_true_duelist_exists():
    df = pd.DataFrame(
        [
            {"player": "pure_duelist", "team": "AAA", "event_id": 1, "agents": "jett,raze,neon"},
            {"player": "seven_like", "team": "AAA", "event_id": 1, "agents": "raze,kayo,neon"},
            {"player": "controller", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "sentinel", "team": "AAA", "event_id": 1, "agents": "cypher,killjoy"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"] == "pure_duelist", "team_role"].iloc[0] == "Duelist"
    assert enriched.loc[enriched["player"] == "seven_like", "team_role"].iloc[0] == "Flex"


def test_duelist_sentinel_player_can_cover_missing_sentinel_role():
    df = pd.DataFrame(
        [
            {"player": "pure_duelist", "team": "AAA", "event_id": 1, "agents": "jett,raze,neon"},
            {"player": "westside_like", "team": "AAA", "event_id": 1, "agents": "jett,raze,cypher"},
            {"player": "controller", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
            {"player": "flex", "team": "AAA", "event_id": 1, "agents": "breach,omen,sova"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"] == "westside_like", "team_role"].iloc[0] == "Sentinel"


def test_legacy_lowercase_team_token_is_repaired_as_multiword_player_name():
    df = pd.DataFrame(
        [
            {"player": "lovers", "team": "rock", "event_id": 1, "agents": "waylay,jett,neon"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[0, "player"] == "lovers rock"
    assert enriched.loc[0, "team"] == "FA"


def test_player_name_with_team_suffix_is_repaired():
    df = pd.DataFrame(
        [
            {"player": "Asuna 100T", "team": "100T", "event_id": 1, "agents": "neon,kayo,sage"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[0, "player"] == "Asuna"
    assert enriched.loc[0, "team"] == "100T"


def test_duelist_plus_sentinel_pool_is_raw_sentinel_not_flex():
    details = infer_player_role_details(["neon", "phoenix", "cypher"])
    assert details.raw_role == "Sentinel"
    assert details.team_role == "Sentinel"
    assert "Duelist + Sentinel-only pool" in details.explanation


def test_chamber_is_sentinel_when_pool_is_not_pure_duelist_chamber():
    details = infer_player_role_details(["neon", "chamber", "sova"])
    assert details.role_scores["Sentinel"] > 0
    assert details.raw_role == "Flex"


def test_team_mandatory_roles_are_covered_when_evidence_exists_and_flex_optional():
    df = pd.DataFrame(
        [
            {"player": "duelist_a", "team": "AAA", "event_id": 1, "agents": "jett,raze"},
            {"player": "duelist_b_sentinel", "team": "AAA", "event_id": 1, "agents": "neon,phoenix,cypher"},
            {"player": "smoker", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
            {"player": "second_initiator", "team": "AAA", "event_id": 1, "agents": "breach,kayo"},
        ]
    )
    enriched = enrich_player_roles(df)
    roles = set(enriched["team_role"])
    assert {"Duelist", "Controller", "Initiator", "Sentinel"}.issubset(roles)
    assert enriched.loc[enriched["player"] == "duelist_b_sentinel", "team_role"].iloc[0] == "Sentinel"


def test_stable_five_team_moves_duplicated_sentinel_hybrid_to_flex_elo():
    df = pd.DataFrame(
        [
            {"player": "duelist", "team": "AAA", "event_id": 1, "agents": "jett,raze,neon"},
            {"player": "flickless_like", "team": "AAA", "event_id": 1, "agents": "neon,phoenix,cypher"},
            {"player": "main_sentinel", "team": "AAA", "event_id": 1, "agents": "cypher,killjoy"},
            {"player": "smoker", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"] == "main_sentinel", "team_role"].iloc[0] == "Sentinel"
    assert enriched.loc[enriched["player"] == "flickless_like", "team_role"].iloc[0] == "Flex"
    assert {"Duelist", "Controller", "Initiator", "Sentinel", "Flex"} == set(enriched["team_role"])


def test_stable_five_team_can_skip_flex_only_with_two_locked_duelists_elo():
    df = pd.DataFrame(
        [
            {"player": "duelist_a", "team": "AAA", "event_id": 1, "agents": "jett,raze"},
            {"player": "duelist_b", "team": "AAA", "event_id": 1, "agents": "neon,phoenix"},
            {"player": "sentinel", "team": "AAA", "event_id": 1, "agents": "cypher,killjoy"},
            {"player": "smoker", "team": "AAA", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "AAA", "event_id": 1, "agents": "sova,fade"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert set(enriched["team_role"]) == {"Duelist", "Controller", "Initiator", "Sentinel"}
    assert enriched["team_role"].tolist().count("Duelist") == 2


def test_sen_like_double_sentinel_controller_hybrid_becomes_flex_elo():
    df = pd.DataFrame(
        [
            {"player": "zekken", "team": "SEN", "event_id": 1, "agents": "jett,raze,neon"},
            {"player": "johnqt", "team": "SEN", "event_id": 1, "agents": "viper,cypher,harbor"},
            {"player": "pure_sentinel", "team": "SEN", "event_id": 1, "agents": "killjoy,cypher"},
            {"player": "smoker", "team": "SEN", "event_id": 1, "agents": "omen,astra"},
            {"player": "initiator", "team": "SEN", "event_id": 1, "agents": "sova,fade"},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"] == "pure_sentinel", "team_role"].iloc[0] == "Sentinel"
    assert enriched.loc[enriched["player"] == "johnqt", "team_role"].iloc[0] == "Flex"
    assert set(enriched["team_role"]) == {"Duelist", "Controller", "Initiator", "Sentinel", "Flex"}


def test_sen_like_double_sentinel_controller_hybrid_becomes_flex_even_with_extra_scraped_row():
    df = pd.DataFrame(
        [
            {"player": "zekken", "team": "SEN", "event_id": 1, "agents": "jett,raze,neon", "rounds": 500},
            {"player": "johnqt", "team": "SEN", "event_id": 1, "agents": "viper,cypher,harbor", "rounds": 500},
            {"player": "pure_sentinel", "team": "SEN", "event_id": 1, "agents": "killjoy,cypher", "rounds": 500},
            {"player": "smoker", "team": "SEN", "event_id": 1, "agents": "omen,astra", "rounds": 500},
            {"player": "initiator", "team": "SEN", "event_id": 1, "agents": "sova,fade", "rounds": 500},
            {"player": "sub_row", "team": "SEN", "event_id": 1, "agents": "neon", "rounds": 20},
        ]
    )
    enriched = enrich_player_roles(df)
    assert enriched.loc[enriched["player"] == "pure_sentinel", "team_role"].iloc[0] == "Sentinel"
    assert enriched.loc[enriched["player"] == "johnqt", "team_role"].iloc[0] == "Flex"
