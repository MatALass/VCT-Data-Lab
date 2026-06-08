from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import pandas as pd
import requests
from bs4 import BeautifulSoup

from vct_ranker_elo.agents import normalize_agent_name
from vct_ranker_elo.roles import infer_player_role
from vct_ranker_elo.vct import VctEvent

VLR_BASE_URL = "https://www.vlr.gg"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VCTRoleRanker/0.1; +https://example.local)",
    "Accept-Language": "en-US,en;q=0.9",
}

STAT_COLUMNS = [
    "rating",
    "acs",
    "kd",
    "kast",
    "adr",
    "kpr",
    "apr",
    "fkpr",
    "fdpr",
    "hs_pct",
]


@dataclass(frozen=True)
class VlrStatsQuery:
    event_id: int | None = None
    direct_url: str | None = None
    region: str | None = None
    timespan: str = "all"
    min_rounds: int = 0
    maps: str = "all"
    agents: str = "all"

    def to_url(self) -> str:
        if self.direct_url:
            params: dict[str, str | int] = {
                "timespan": self.timespan,
                "min_rounds": self.min_rounds,
                "maps": self.maps,
                "agents": self.agents,
            }
            return f"{self.direct_url}?{urlencode(params)}"

        params: dict[str, str | int] = {
            "event_id": self.event_id or "all",
            "region": self.region or "all",
            "timespan": self.timespan,
            "min_rounds": self.min_rounds,
            "maps": self.maps,
            "agents": self.agents,
        }
        return f"{VLR_BASE_URL}/stats/?{urlencode(params)}"


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_float(value: str | None) -> float | None:
    text = clean_text(value).replace("%", "")
    if not text or text in {"-", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    text = clean_text(value).replace(",", "")
    if not text or text in {"-", "nan"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _extract_agents(row) -> list[str]:
    agents: list[str] = []
    for img in row.select("img[src*='/agents/']"):
        src = img.get("src", "")
        agent = normalize_agent_name(src.split("/")[-1])
        if agent and agent not in agents:
            agents.append(agent)
    return agents


def _extract_player_and_team(row) -> tuple[str, str | None]:
    player_cell = row.select_one("td.mod-player") or row.select_one("td:nth-of-type(1)")
    text = clean_text(player_cell.get_text(" ", strip=True) if player_cell else "")

    if not text:
        return "Unknown", None

    chunks = text.split()
    player = chunks[0]
    team = chunks[1] if len(chunks) > 1 else None
    return player, team


def scrape_vlr_player_stats(query: VlrStatsQuery, *, polite_delay: float = 0.7) -> pd.DataFrame:
    """Scrape VLR's public HTML stats table.

    This intentionally avoids private APIs. VLR markup can change, so parsing is defensive:
    missing metrics become null instead of crashing the whole app.
    """
    url = query.to_url()
    time.sleep(polite_delay)
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    rows = soup.select("table.wf-table tr")
    records: list[dict] = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        player, team = _extract_player_and_team(row)
        agents = _extract_agents(row)
        role, confidence = infer_player_role(agents)
        cell_texts = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]

        # VLR stats table generally starts with player, agents, rounds, rating, ACS, K:D, ...
        numeric = cell_texts[2:]
        values = {column: None for column in STAT_COLUMNS}
        rounds = parse_int(numeric[0]) if len(numeric) >= 1 else None

        for column, raw_value in zip(STAT_COLUMNS, numeric[1:], strict=False):
            values[column] = parse_float(raw_value)

        records.append(
            {
                "player": player,
                "team": team,
                "agents": ",".join(agents),
                "inferred_role": role,
                "role_confidence": confidence,
                "rounds": rounds,
                "source_url": url,
                "event_id": query.event_id,
                **values,
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    return df.drop_duplicates(subset=["player", "team"]).sort_values(
        ["inferred_role", "rating", "acs", "player"],
        ascending=[True, False, False, True],
    )



def scrape_vct_events(events: list[VctEvent], *, min_rounds: int = 0, timespan: str = "all") -> pd.DataFrame:
    """Scrape only configured VCT events and add region/event metadata.

    This is stricter than using VLR's global stats page: every returned player comes
    from one of the configured VCT regional league events.
    """
    frames: list[pd.DataFrame] = []

    for event in events:
        query = VlrStatsQuery(event_id=event.event_id, direct_url=event.stats_url, min_rounds=min_rounds, timespan=timespan)
        frame = scrape_vlr_player_stats(query)
        if frame.empty:
            continue

        frame["vct_region"] = event.region
        frame["event_name"] = event.name
        frame["event_stage"] = event.stage
        frame["event_id"] = event.event_id
        frames.append(frame)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(subset=["vct_region", "event_id", "player", "team"]).sort_values(
        ["vct_region", "inferred_role", "rating", "acs", "player"],
        ascending=[True, True, False, False, True],
    )

def scrape_multiple_events(event_ids: list[int], *, min_rounds: int = 100) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for event_id in event_ids:
        query = VlrStatsQuery(event_id=event_id, min_rounds=min_rounds)
        frame = scrape_vlr_player_stats(query)
        if not frame.empty:
            frame["event_id"] = event_id
            frames.append(frame)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["event_id", "player", "team"])
