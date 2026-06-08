import pandas as pd

from vlr_analytics.processing.transform import build_invalid_compositions_report


def test_invalid_compositions_report_tracks_non_five_agent_compositions(tmp_path):
    matrix = pd.DataFrame(
        [
            {
                "event": "evt",
                "map": "Bind",
                "match_id": "match_1",
                "team": "Team A",
                "opponent": "Team B",
                "agent": "jett",
            },
            {
                "event": "evt",
                "map": "Bind",
                "match_id": "match_1",
                "team": "Team A",
                "opponent": "Team B",
                "agent": "sova",
            },
            {
                "event": "evt",
                "map": "Bind",
                "match_id": "match_1",
                "team": "Team A",
                "opponent": "Team B",
                "agent": "omen",
            },
            {
                "event": "evt",
                "map": "Bind",
                "match_id": "match_1",
                "team": "Team A",
                "opponent": "Team B",
                "agent": "viper",
            },
        ]
    )
    output_path = tmp_path / "invalid_compositions.csv"

    report = build_invalid_compositions_report(matrix, output_path=output_path)

    assert output_path.exists()
    assert len(report) == 1
    row = report.iloc[0].to_dict()
    assert row["team"] == "Team A"
    assert row["agents_count"] == 4
    assert row["expected_agents_count"] == 5
    assert row["reason"] == "missing_agents"


def test_invalid_compositions_report_writes_empty_csv_when_everything_is_valid(tmp_path):
    matrix = pd.DataFrame(
        [
            {
                "event": "evt",
                "map": "Bind",
                "match_id": "match_1",
                "team": "Team A",
                "opponent": "Team B",
                "agent": agent,
            }
            for agent in ["jett", "sova", "omen", "viper", "killjoy"]
        ]
    )
    output_path = tmp_path / "invalid_compositions.csv"

    report = build_invalid_compositions_report(matrix, output_path=output_path)
    persisted = pd.read_csv(output_path)

    assert report.empty
    assert persisted.empty
    assert set(persisted.columns) == {
        "event",
        "map",
        "match_id",
        "team",
        "opponent",
        "agents_count",
        "expected_agents_count",
        "agents",
        "reason",
    }
