import json
from pathlib import Path

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from vlr_analytics.config import (
    AGENT_ASSETS,
    AGENT_ASSET_REGISTRY,
    AGENT_GLOBAL_META,
    AGENT_MAP_STATS,
    AGENT_META_PRESENCE,
    AGENT_PAIR_PATTERNS,
    AGENT_SYNERGY,
    AGENT_TIERS,
    COMPOSITION_ARCHETYPES,
    COMPOSITION_CLUSTERS,
    COMPOSITION_PATTERNS,
    INSIGHTS,
    MAP_SPECIALISTS,
    META_TRENDS,
    TEAM_AGENT_STATS,
    TEAM_ASSETS,
    TEAM_ASSET_REGISTRY,
    TEAM_COMPOSITIONS,
    TEAM_MAP_IDENTITY,
    TEAM_MAP_STATS,
    TEAM_SIGNATURES,
    TEAM_STRENGTHS,
    TEAM_TACTICAL_PROFILES,
)

app = FastAPI(title="VLR Analytics API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/assets/agents",
    StaticFiles(directory=str(AGENT_ASSETS), check_dir=False),
    name="agent-assets",
)
app.mount(
    "/assets/teams",
    StaticFiles(directory=str(TEAM_ASSETS), check_dir=False),
    name="team-assets",
)

TABLES = {
    # --- Mart layer ---
    "agent-map-stats": AGENT_MAP_STATS,
    "team-compositions": TEAM_COMPOSITIONS,
    "team-agent-stats": TEAM_AGENT_STATS,
    "team-map-stats": TEAM_MAP_STATS,
    "agent-synergy": AGENT_SYNERGY,
    "meta-trends": META_TRENDS,
    "team-signatures": TEAM_SIGNATURES,

    # --- Model layer v2 ---
    "agent-global-meta": AGENT_GLOBAL_META,
    "agent-meta-presence": AGENT_META_PRESENCE,
    "team-tactical-profiles": TEAM_TACTICAL_PROFILES,
    "team-map-identity": TEAM_MAP_IDENTITY,
    "composition-patterns": COMPOSITION_PATTERNS,
    "agent-pair-patterns": AGENT_PAIR_PATTERNS,
    "composition-clusters": COMPOSITION_CLUSTERS,
    "composition-archetypes": COMPOSITION_ARCHETYPES,

    # --- Backward-compat aliases ---
    "team-profile-scores": TEAM_STRENGTHS,
    "team-strengths": TEAM_STRENGTHS,
    "agent-tiers": AGENT_TIERS,
    "map-specialists": MAP_SPECIALISTS,

    # --- Asset registries ---
    "agent-assets": AGENT_ASSET_REGISTRY,
    "team-assets": TEAM_ASSET_REGISTRY,
}


def read_table(path: Path) -> list[dict]:
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Missing generated file: {path.name}. Run `vlr model` first.",
        )

    return pd.read_csv(path).replace({pd.NA: None}).to_dict(orient="records")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": "vlr-analytics-pro",
        "status": "ok",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
        "available_endpoints": [
            "/tables",
            "/tables/{name}",
            "/insights",
            "/dashboard",
            "/assets/agents/{filename}",
            "/assets/teams/{filename}",
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tables")
def tables() -> dict[str, list[str]]:
    return {"tables": sorted(TABLES)}


@app.get("/tables/{name}")
def table(
    name: str,
    limit: int = 5000,
    observed_only: bool = Query(False),
) -> list[dict]:
    if name not in TABLES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown table: {name}. Available: {sorted(TABLES)}",
        )

    rows = read_table(TABLES[name])

    if observed_only:
        rows = [
            row
            for row in rows
            if row.get("observed", True) in (True, "True", "true", 1, "1")
        ]

    return rows[:limit]


@app.get("/insights")
def insights() -> dict:
    if not INSIGHTS.exists():
        raise HTTPException(
            status_code=404,
            detail="Missing insights.json. Run `vlr model` first.",
        )

    return json.loads(INSIGHTS.read_text(encoding="utf-8"))


@app.get("/dashboard")
def dashboard() -> dict:
    primary_tables = [
        "agent-global-meta",
        "agent-meta-presence",
        "team-tactical-profiles",
        "team-map-identity",
        "composition-patterns",
        "agent-pair-patterns",
        "composition-archetypes",
    ]

    return {
        "insights": insights(),
        "tables": {name: table(name, limit=10000) for name in primary_tables},
        "assets": {
            "agents": read_table(AGENT_ASSET_REGISTRY)
            if AGENT_ASSET_REGISTRY.exists()
            else [],
            "teams": read_table(TEAM_ASSET_REGISTRY)
            if TEAM_ASSET_REGISTRY.exists()
            else [],
        },
    }


def run_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run("vlr_analytics.api.main:app", host=host, port=port, reload=True)