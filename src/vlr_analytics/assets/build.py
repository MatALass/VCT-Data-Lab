from __future__ import annotations

import re
from pathlib import Path
from urllib.request import urlopen, Request

import pandas as pd

from vlr_analytics.config import (
    AGENT_ASSET_REGISTRY,
    AGENT_ASSETS,
    PROCESSED_MATRIX,
    PROCESSED_SUMMARY,
    TEAM_ASSET_REGISTRY,
    TEAM_ASSETS,
)
from vlr_analytics.utils import read_csv_required, write_csv


def slugify(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def _download(url: str, path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=25) as response:
            data = response.read()
        if data:
            path.write_bytes(data)
            return True
    except Exception:
        return False
    return False


def build_agent_assets(download: bool = False) -> pd.DataFrame:
    agents = sorted(set(read_csv_required(PROCESSED_SUMMARY)["agent"].dropna().astype(str).str.lower()))
    rows = []
    api_agents = {}
    if download:
        try:
            import json
            with urlopen("https://valorant-api.com/v1/agents?isPlayableCharacter=true", timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            for item in payload.get("data", []):
                api_agents[item["displayName"].lower()] = item
        except Exception:
            api_agents = {}

    for agent in agents:
        slug = slugify(agent)
        file_name = f"{slug}.png"
        local_path = AGENT_ASSETS / file_name
        source_url = None
        downloaded = local_path.exists()
        item = api_agents.get(agent)
        if item:
            source_url = item.get("displayIcon") or item.get("fullPortrait")
            if download and source_url and not local_path.exists():
                downloaded = _download(source_url, local_path)
        rows.append(
            {
                "agent": agent,
                "slug": slug,
                "asset_path": f"/assets/agents/{file_name}" if downloaded else "",
                "source_url": source_url or "",
                "has_local_asset": bool(downloaded),
            }
        )
    out = pd.DataFrame(rows)
    write_csv(out, AGENT_ASSET_REGISTRY)
    return out


def build_team_assets() -> pd.DataFrame:
    matrix = read_csv_required(PROCESSED_MATRIX)
    teams = sorted(set(matrix["team"].dropna().astype(str)) | set(matrix["opponent"].dropna().astype(str)))
    rows = []
    for team in teams:
        slug = slugify(team)
        local_path = TEAM_ASSETS / f"{slug}.png"
        rows.append(
            {
                "team": team,
                "slug": slug,
                "asset_path": f"/assets/teams/{slug}.png" if local_path.exists() else "",
                "logo_url": "",
                "has_local_asset": local_path.exists(),
                "note": "Optional: add a PNG with this slug in data/assets/teams or fill logo_url manually.",
            }
        )
    out = pd.DataFrame(rows)
    write_csv(out, TEAM_ASSET_REGISTRY)
    return out


def build_assets(download_agents: bool = False) -> dict[str, pd.DataFrame]:
    return {"agents": build_agent_assets(download=download_agents), "teams": build_team_assets()}
