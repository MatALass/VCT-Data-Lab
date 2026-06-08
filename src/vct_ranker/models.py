from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerProfile(BaseModel):
    player: str
    team: str | None = None
    agents: list[str] = Field(default_factory=list)
    inferred_role: str = "Flex"
    role_confidence: float = 0.0
    rounds: int | None = None
    rating: float | None = None
    acs: float | None = None
    kd: float | None = None
    kast: float | None = None
    adr: float | None = None
    kpr: float | None = None
    apr: float | None = None
    fkpr: float | None = None
    fdpr: float | None = None
    hs_pct: float | None = None
    source_url: str | None = None
