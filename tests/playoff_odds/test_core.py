from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from playoff_odds.simulation.cli import MatchSelection, persist_match_result
from playoff_odds.simulation.core import apply_match_result_with_config, build_state, export_frontend_json, load_config, rank_group_official, validate_config

class SimulationCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        cls.config_path = cls.project_root / "data" / "playoff_odds" / "config.sample.json"
        cls.config = load_config(cls.config_path)

    def test_standings_model_does_not_mutate_elo(self) -> None:
        config = dict(self.config)
        config["model_type"] = "standings"
        state = build_state(config)
        before_winner = state["teams"]["FUT"]["rating"]
        before_loser = state["teams"]["TL"]["rating"]
        apply_match_result_with_config(state, "FUT", "TL", 2, 0, "extreme", "FUT", "TL", config)
        self.assertEqual(before_winner, state["teams"]["FUT"]["rating"])
        self.assertEqual(before_loser, state["teams"]["TL"]["rating"])

    def test_elo_updates_once_with_expected_k(self) -> None:
        config = dict(self.config)
        config["model_type"] = "elo"
        config["elo"] = {"k": 24, "scale": 400}
        state = build_state(config)
        rw = state["teams"]["FUT"]["rating"]
        rl = state["teams"]["TL"]["rating"]
        expected_w = 1.0 / (1.0 + 10 ** ((rl - rw) / 400.0))
        expected_delta = 24 * (1.0 - expected_w)
        apply_match_result_with_config(state, "FUT", "TL", 2, 0, "extreme", "FUT", "TL", config)
        self.assertAlmostEqual(state["teams"]["FUT"]["rating"], rw + expected_delta, places=9)
        self.assertAlmostEqual(state["teams"]["TL"]["rating"], rl - expected_delta, places=9)

    def test_two_way_head_to_head_breaker(self) -> None:
        config = dict(self.config)
        state = build_state(config)
        state["teams"]["GX"]["wins"] = 3
        state["teams"]["BBL"]["wins"] = 3
        state["teams"]["GX"]["losses"] = 1
        state["teams"]["BBL"]["losses"] = 1
        apply_match_result_with_config(state, "GX", "BBL", 2, 0, "extreme", "GX", "BBL", config)
        ranked = rank_group_official(state, "Omega")
        gx_index = next(i for i, row in enumerate(ranked) if row["team"] == "GX")
        bbl_index = next(i for i, row in enumerate(ranked) if row["team"] == "BBL")
        self.assertLess(gx_index, bbl_index)

    def test_export_contains_expected_rank_and_schema_version(self) -> None:
        summary_df = pd.DataFrame([
            {"team": "A", "group": "G", "qualify_count": 1, "qualify_prob": 0.7, "best_rank_seen": 1, "worst_rank_seen": 2},
            {"team": "B", "group": "G", "qualify_count": 1, "qualify_prob": 0.3, "best_rank_seen": 1, "worst_rank_seen": 2},
        ])
        position_df = pd.DataFrame([
            {"team": "A", "group": "G", "P1": 0.7, "P2": 0.3},
            {"team": "B", "group": "G", "P1": 0.3, "P2": 0.7},
        ])
        config = {"league": "Test", "season": "2026", "qualification_slots": 1, "n_simulations": 10, "conditional_simulations": 5, "model_type": "standings", "played_matches": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "dataset.json"
            export_frontend_json(config, summary_df, position_df, {}, {}, {}, {}, {"A": {"best": 1, "worst": 2}, "B": {"best": 1, "worst": 2}}, {}, [], [["G", "A", "B"]], out)
            payload = json.loads(out.read_text(encoding="utf-8"))
            teams = {team["team"]: team for team in payload["groups"][0]["teams"]}
            self.assertEqual(payload["schemaVersion"], "3.0.0")
            self.assertAlmostEqual(teams["A"]["expectedRank"], 1.3, places=9)
            self.assertAlmostEqual(teams["B"]["expectedRank"], 1.7, places=9)

    def test_validate_config_rejects_duplicate_remaining_match(self) -> None:
        config = load_config(self.config_path)
        config["remaining_matches"].append(config["remaining_matches"][0])
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_persist_match_result_updates_config_shape(self) -> None:
        config = load_config(self.config_path)
        match_row = config["remaining_matches"][0]
        selection = MatchSelection(index=1, group=match_row[0], team_a=match_row[1], team_b=match_row[2])
        summary = persist_match_result(config, selection, winner=match_row[1], winner_maps=2, loser_maps=1)
        self.assertEqual(summary["winner"], match_row[1])
        self.assertEqual(len(config["played_matches"]), 1)
        self.assertEqual(len(config["remaining_matches"]), len(self.config["remaining_matches"]) - 1)
        played_match = config["played_matches"][0]
        self.assertEqual(played_match["teamA"], match_row[1])
        self.assertEqual(played_match["teamB"], match_row[2])
        self.assertEqual(played_match["winner"], match_row[1])
        self.assertEqual(played_match["winnerMaps"], 2)

if __name__ == "__main__":
    unittest.main()
