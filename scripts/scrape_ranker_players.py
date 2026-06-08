from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vct_ranker.ranking import make_player_key
from vct_ranker.scraper import VlrStatsQuery, scrape_vlr_player_stats
from vct_ranker.storage import save_players


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape VLR player stats into a local CSV.")
    parser.add_argument("--event-id", type=int, default=None)
    parser.add_argument("--region", type=str, default=None)
    parser.add_argument("--timespan", type=str, default="all")
    parser.add_argument("--min-rounds", type=int, default=0)
    args = parser.parse_args()

    query = VlrStatsQuery(
        event_id=args.event_id,
        region=args.region,
        timespan=args.timespan,
        min_rounds=args.min_rounds,
    )
    df = scrape_vlr_player_stats(query)
    if not df.empty:
        df["team"] = df["team"].fillna("FA")
        df["player_key"] = df.apply(lambda row: make_player_key(row["player"], row["team"]), axis=1)
    save_players(df)
    print(f"Saved {len(df)} players from {query.to_url()}")


if __name__ == "__main__":
    main()
