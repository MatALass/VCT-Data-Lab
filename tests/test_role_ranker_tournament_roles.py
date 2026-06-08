from vct_ranker.roles import infer_player_role


def test_infer_duelist_role():
    role, confidence = infer_player_role(["jett", "raze", "neon"])
    assert role == "Duelist"
    assert confidence == 1.0


def test_infer_flex_when_mixed_pool():
    role, confidence = infer_player_role(["jett", "sova", "omen"])
    assert role == "Flex"
    assert confidence == 0.333
