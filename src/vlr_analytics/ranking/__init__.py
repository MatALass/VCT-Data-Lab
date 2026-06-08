"""Role ranking integrations for vlr-analytics-pro.

The canonical tournament ranker lives in the ``vct_ranker`` package.
The legacy Elo ranker is preserved in ``vct_ranker_elo`` for backward compatibility.
"""

from vct_ranker.ranking import (  # re-export canonical tournament ranking helpers
    DEFAULT_MAX_LOSSES,
    build_ranking,
    make_player_key,
    normalize_ranking_state,
    player_stats,
    record_duel_result,
)

__all__ = [
    "DEFAULT_MAX_LOSSES",
    "build_ranking",
    "make_player_key",
    "normalize_ranking_state",
    "player_stats",
    "record_duel_result",
]
