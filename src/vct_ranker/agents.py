from __future__ import annotations

# Official Valorant roles: Duelist, Controller, Initiator, Sentinel.
# The app adds "Flex" as a competitive-role label inferred from mixed agent pools.
AGENT_TO_ROLE: dict[str, str] = {
    # Duelists
    "jett": "Duelist",
    "raze": "Duelist",
    "neon": "Duelist",
    "yoru": "Duelist",
    "phoenix": "Duelist",
    "reyna": "Duelist",
    "iso": "Duelist",
    "waylay": "Duelist",
    # Controllers / smokers
    "omen": "Controller",
    "viper": "Controller",
    "astra": "Controller",
    "brimstone": "Controller",
    "harbor": "Controller",
    "clove": "Controller",
    # Initiators
    "sova": "Initiator",
    "fade": "Initiator",
    "breach": "Initiator",
    "skye": "Initiator",
    "kayo": "Initiator",
    "kay/o": "Initiator",
    "gekko": "Initiator",
    "tejo": "Initiator",
    # Sentinels
    "cypher": "Sentinel",
    "killjoy": "Sentinel",
    "sage": "Sentinel",
    "chamber": "Sentinel",
    "deadlock": "Sentinel",
    "vyse": "Sentinel",
}

ROLE_ORDER = ["Duelist", "Controller", "Initiator", "Sentinel", "Flex"]


def normalize_agent_name(agent: str) -> str:
    return (
        str(agent)
        .strip()
        .lower()
        .replace("/agents/", "")
        .replace(".png", "")
        .replace(" ", "")
    )


def get_agent_role(agent: str) -> str | None:
    return AGENT_TO_ROLE.get(normalize_agent_name(agent))
