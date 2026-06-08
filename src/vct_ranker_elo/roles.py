from __future__ import annotations

from collections import Counter

from vct_ranker_elo.agents import get_agent_role, normalize_agent_name


def infer_player_role(
    agents: list[str],
    *,
    primary_threshold: float = 0.60,
    min_known_agents: int = 1,
) -> tuple[str, float]:
    """Infer competitive role from a player's observed VLR agent pool.

    Rules:
    - If no known agent role is found: Flex, 0.0.
    - If the dominant official role >= primary_threshold: that role.
    - Otherwise: Flex, because the player has a mixed pool or map-dependent role.

    This is intentionally conservative. It avoids pretending every VCT player has a fixed role
    when teams run double-duelist, no-sentinel, Viper-controller hybrid, or role swaps.
    """
    known_roles: list[str] = []

    for agent in agents:
        role = get_agent_role(normalize_agent_name(agent))
        if role is not None:
            known_roles.append(role)

    if len(known_roles) < min_known_agents:
        return "Flex", 0.0

    counts = Counter(known_roles)
    role, count = counts.most_common(1)[0]
    confidence = count / len(known_roles)

    if confidence >= primary_threshold:
        return role, round(confidence, 3)

    return "Flex", round(confidence, 3)


def composition_label(agents: list[str]) -> str:
    role_counts = Counter(filter(None, (get_agent_role(agent) for agent in agents)))
    parts = [f"{role_counts[role]} {role}" for role in ["Duelist", "Controller", "Initiator", "Sentinel"] if role_counts[role]]
    return " / ".join(parts) if parts else "Unknown"
