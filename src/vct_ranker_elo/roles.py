from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from vct_ranker_elo.agents import ROLE_ORDER, get_agent_role, normalize_agent_name

CORE_ROLES = ["Duelist", "Controller", "Initiator", "Sentinel"]
TEAM_ROLES = ["Duelist", "Controller", "Initiator", "Sentinel", "Flex"]
VIPER = "viper"
CHAMBER = "chamber"


@dataclass(frozen=True)
class AgentUsage:
    agent: str
    rounds: float = 1.0


@dataclass(frozen=True)
class RoleInference:
    raw_role: str
    team_role: str
    role_confidence: float
    role_scores: dict[str, float] = field(default_factory=dict)
    official_role_scores: dict[str, float] = field(default_factory=dict)
    agent_shares: dict[str, float] = field(default_factory=dict)
    flex_score: float = 0.0
    distinct_roles: int = 0
    explanation: str = ""


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_agent_usage(agent_pool: Any, *, total_rounds: int | float | None = None) -> list[AgentUsage]:
    """Normalize agent usage into weighted entries.

    Supported inputs:
    - ["jett", "raze"]: equal-weight fallback used by VLR's global stats table.
    - {"jett": 120, "raze": 80}: preferred format when per-agent rounds exist.
    - [{"agent": "jett", "rounds": 120}, ...]
    - "jett,raze": CSV-style stored field.

    The current VLR stats table used by the app exposes the agent pool but not reliable
    per-agent rounds. When no per-agent rounds are available, equal weights are used
    and the explanation makes that limitation explicit.
    """
    if agent_pool is None:
        return []

    if isinstance(agent_pool, str):
        text = agent_pool.strip()
        if not text:
            return []
        # Allow a JSON dict/list if a future scraper stores exact per-agent rounds.
        if text.startswith("{") or text.startswith("["):
            try:
                return parse_agent_usage(json.loads(text), total_rounds=total_rounds)
            except json.JSONDecodeError:
                pass
        items = [part.strip() for part in text.replace(" · ", ",").split(",") if part.strip()]
        return [AgentUsage(normalize_agent_name(agent), 1.0) for agent in items]

    if isinstance(agent_pool, dict):
        usages: list[AgentUsage] = []
        for agent, rounds in agent_pool.items():
            value = _safe_float(rounds, 0.0)
            if value > 0:
                usages.append(AgentUsage(normalize_agent_name(str(agent)), value))
        return usages

    if isinstance(agent_pool, list | tuple | set):
        usages = []
        for item in agent_pool:
            if isinstance(item, dict):
                agent = item.get("agent") or item.get("name") or item.get("agent_name")
                rounds = item.get("rounds") or item.get("rounds_played") or item.get("count") or 1.0
                if agent:
                    value = _safe_float(rounds, 1.0)
                    if value > 0:
                        usages.append(AgentUsage(normalize_agent_name(str(agent)), value))
            elif isinstance(item, tuple) and len(item) >= 2:
                agent, rounds = item[0], item[1]
                value = _safe_float(rounds, 1.0)
                if value > 0:
                    usages.append(AgentUsage(normalize_agent_name(str(agent)), value))
            else:
                usages.append(AgentUsage(normalize_agent_name(str(item)), 1.0))
        return usages

    return []


def _shares_by_agent(usages: list[AgentUsage]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for usage in usages:
        if usage.rounds > 0:
            totals[usage.agent] += usage.rounds
    total = sum(totals.values())
    if total <= 0:
        return {}
    return {agent: value / total for agent, value in totals.items()}


def _official_role_scores(agent_shares: dict[str, float]) -> dict[str, float]:
    scores = {role: 0.0 for role in CORE_ROLES}
    for agent, share in agent_shares.items():
        role = get_agent_role(agent)
        if role in scores:
            scores[role] += share
    return {role: round(score, 6) for role, score in scores.items()}


def _is_duelist_or_chamber_agent(agent: str) -> bool:
    return agent == CHAMBER or get_agent_role(agent) == "Duelist"


def _is_pure_duelist_chamber_pool(agent_shares: dict[str, float]) -> bool:
    agents = set(agent_shares)
    return bool(agents) and all(_is_duelist_or_chamber_agent(agent) for agent in agents)


def _effective_agent_role(agent: str, agent_shares: dict[str, float]) -> str | None:
    """Return the competitive role used by the ranker, not only Riot's class.

    Business rules:
    - Viper is treated as Sentinel-side zone-control, not Controller.
    - Chamber is Duelist only in a pure Duelist/Chamber pool; otherwise Sentinel.
    """
    if agent == VIPER:
        return "Sentinel"
    if agent == CHAMBER:
        return "Duelist" if _is_pure_duelist_chamber_pool(agent_shares) else "Sentinel"
    return get_agent_role(agent)


def _effective_roles_present(agent_shares: dict[str, float]) -> set[str]:
    return {role for agent in agent_shares if (role := _effective_agent_role(agent, agent_shares)) in CORE_ROLES}


def _is_duelist_sentinel_only_pool(agent_shares: dict[str, float]) -> bool:
    roles = _effective_roles_present(agent_shares)
    return roles == {"Duelist", "Sentinel"} and not _is_pure_duelist_chamber_pool(agent_shares)


def _effective_role_scores(agent_shares: dict[str, float], official_scores: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Apply competitive Valorant role interpretation on top of official classes."""
    scores = {role: 0.0 for role in CORE_ROLES}
    notes: list[str] = []

    for agent, share in agent_shares.items():
        role = _effective_agent_role(agent, agent_shares)
        if role in scores:
            scores[role] += share

    if agent_shares.get(VIPER, 0.0) > 0:
        notes.append("Viper treated as Sentinel-side zone-control, not as Controller, for competitive-role inference.")

    if _is_pure_duelist_chamber_pool(agent_shares) and CHAMBER in agent_shares:
        notes.append("Pure Duelist/Chamber pool: Chamber counted as Duelist-adjacent, so the player stays Duelist.")
    elif CHAMBER in agent_shares:
        notes.append("Chamber treated as Sentinel unless the rest of the pool is exclusively Duelist.")

    return {role: round(score, 6) for role, score in scores.items()}, notes

def _flex_score(role_scores: dict[str, float]) -> float:
    values = sorted([score for score in role_scores.values() if score > 0.001], reverse=True)
    if not values:
        return 0.0
    primary = values[0]
    secondary = values[1] if len(values) >= 2 else 0.0
    third = values[2] if len(values) >= 3 else 0.0
    distinct = sum(1 for value in values if value >= 0.10)

    # High flex requires real spread, not a one-map emergency pick.
    score = 0.0
    if distinct >= 3:
        score += 0.45
    if primary < 0.60:
        score += 0.25
    elif primary < 0.70:
        score += 0.15
    if secondary >= 0.20:
        score += 0.20
    if third >= 0.10:
        score += 0.10
    return round(min(1.0, score), 3)


def infer_player_role_details(
    agents: Any,
    *,
    primary_threshold: float = 0.60,
    min_known_agents: int = 1,
    total_rounds: int | float | None = None,
) -> RoleInference:
    usages = parse_agent_usage(agents, total_rounds=total_rounds)
    agent_shares = _shares_by_agent(usages)
    known_agent_shares = {agent: share for agent, share in agent_shares.items() if get_agent_role(agent) is not None}

    if len(known_agent_shares) < min_known_agents:
        return RoleInference(
            raw_role="Flex",
            team_role="Flex",
            role_confidence=0.0,
            role_scores={role: 0.0 for role in CORE_ROLES},
            official_role_scores={role: 0.0 for role in CORE_ROLES},
            agent_shares=agent_shares,
            flex_score=0.0,
            distinct_roles=0,
            explanation="No known Valorant agents found in the player pool.",
        )

    official_scores = _official_role_scores(known_agent_shares)
    effective_scores, notes = _effective_role_scores(known_agent_shares, official_scores)
    sorted_roles = sorted(effective_scores.items(), key=lambda item: item[1], reverse=True)
    primary_role, primary_share = sorted_roles[0]
    significant_roles = [role for role, share in effective_scores.items() if share >= 0.10]
    flex_score = _flex_score(effective_scores)

    is_single_effective_role = len(significant_roles) == 1
    is_pure_duelist_chamber = _is_pure_duelist_chamber_pool(known_agent_shares)
    is_duelist_sentinel_only = _is_duelist_sentinel_only_pool(known_agent_shares)
    duelist_mixed_with_utility = (
        effective_scores.get("Duelist", 0.0) > 0
        and any(effective_scores.get(role, 0.0) > 0 for role in ["Controller", "Initiator", "Sentinel"])
        and not is_pure_duelist_chamber
        and not is_duelist_sentinel_only
    )

    if is_single_effective_role:
        raw_role = primary_role
        confidence = primary_share
        notes.append(f"Only one effective role is present: locked as {primary_role}.")
    elif is_pure_duelist_chamber:
        raw_role = "Duelist"
        confidence = effective_scores.get("Duelist", primary_share)
        notes.append("Only Duelists/Chamber are present: locked as Duelist.")
    elif is_duelist_sentinel_only:
        raw_role = "Sentinel"
        confidence = max(effective_scores.get("Sentinel", 0.0), min(0.67, primary_share))
        notes.append("Duelist + Sentinel-only pool: assigned Sentinel because that utility role is structurally rarer than Duelist.")
    elif duelist_mixed_with_utility:
        raw_role = "Flex"
        confidence = max(flex_score, min(0.67, primary_share))
        notes.append("Mixed Duelist + utility pool: kept as Flex by default instead of true Duelist.")
    elif flex_score >= 0.70 and len(significant_roles) >= 3:
        raw_role = "Flex"
        confidence = flex_score
        notes.append("At least three meaningful roles with no dominant primary role: classified as Flex.")
    elif primary_share >= primary_threshold:
        raw_role = primary_role
        confidence = primary_share
        notes.append(f"Dominant effective role is {primary_role} ({primary_share:.0%}).")
    else:
        raw_role = "Flex"
        confidence = max(flex_score, primary_share)
        notes.append("No role reaches the primary threshold: classified as Flex.")

    if not any(usage.rounds != 1.0 for usage in usages):
        notes.append("Per-agent rounds were unavailable; agent pool was weighted equally.")

    return RoleInference(
        raw_role=raw_role,
        team_role=raw_role,
        role_confidence=round(float(confidence), 3),
        role_scores={role: round(float(effective_scores.get(role, 0.0)), 3) for role in CORE_ROLES},
        official_role_scores={role: round(float(official_scores.get(role, 0.0)), 3) for role in CORE_ROLES},
        agent_shares={agent: round(float(share), 3) for agent, share in known_agent_shares.items()},
        flex_score=flex_score,
        distinct_roles=len(significant_roles),
        explanation=" ".join(notes),
    )


def infer_player_role(
    agents: Any,
    *,
    primary_threshold: float = 0.60,
    min_known_agents: int = 1,
) -> tuple[str, float]:
    """Backward-compatible API returning only role and confidence."""
    details = infer_player_role_details(agents, primary_threshold=primary_threshold, min_known_agents=min_known_agents)
    return details.team_role, details.role_confidence



def _agent_shares_from_row(row: pd.Series) -> dict[str, float]:
    raw = row.get("agent_shares")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    return raw if isinstance(raw, dict) else {}


def _is_duelist_locked_pool(row: pd.Series) -> bool:
    """True when the player should not be reassigned away from Duelist.

    This covers pure Duelist pools and Duelist + Chamber pools, e.g. players like
    Bipo/Filu-style profiles. Team normalization may allow two such Duelists in
    one roster instead of forcing one into a fake missing role.
    """
    agent_shares = _agent_shares_from_row(row)
    if not agent_shares:
        return False
    agents = set(agent_shares)
    non_chamber_agents = agents - {CHAMBER}
    if not non_chamber_agents:
        return False
    return _is_pure_duelist_chamber_pool(agent_shares)


def _unique_core_role_penalty(assigned: dict[int, str], index: int) -> float:
    current = assigned.get(index, "Flex")
    if current not in CORE_ROLES:
        return 0.0
    return 0.20 if list(assigned.values()).count(current) == 1 else 0.0

def _role_score_from_row(row: pd.Series, role: str) -> float:
    if role == "Flex":
        return _safe_float(row.get("flex_score"), 0.0)
    raw = row.get("role_scores")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    if isinstance(raw, dict):
        return _safe_float(raw.get(role), 0.0)
    return 0.0


def _assignment_score(row: pd.Series, role: str) -> float:
    base = _role_score_from_row(row, role)
    raw_role = row.get("raw_role") or row.get("inferred_role")
    if role == raw_role:
        base += 0.08
    if role == "Flex":
        base += _safe_float(row.get("flex_score"), 0.0) * 0.15
    return float(base)


def _normalize_player_team_columns(out: pd.DataFrame) -> pd.DataFrame:
    """Repair player/team parsing artifacts from VLR stats cells.

    Common artifact: player="Asuna 100T", team="100T". The team label was
    included inside the player cell and then displayed twice in Streamlit.
    """
    if not {"player", "team"}.issubset(out.columns):
        return out

    for index, row in out.iterrows():
        player = str(row.get("player") or "").strip()
        team = str(row.get("team") or "").strip()
        if not player:
            continue

        if team and player != team:
            suffix = f" {team}"
            if player.endswith(suffix):
                out.at[index, "player"] = player[: -len(suffix)].strip()
                player = str(out.at[index, "player"]).strip()

        # Legacy lowercase parser bug: lovers rock => player=lovers, team=rock.
        if player and team and player.islower() and team.islower():
            out.at[index, "player"] = f"{player} {team}"
            out.at[index, "team"] = "FA"

    return out


def _is_single_role_locked(row: pd.Series) -> bool:
    role_scores = {}
    raw = row.get("role_scores")
    if isinstance(raw, str):
        try:
            role_scores = json.loads(raw)
        except json.JSONDecodeError:
            role_scores = {}
    elif isinstance(raw, dict):
        role_scores = raw
    significant = [role for role, score in role_scores.items() if _safe_float(score) >= 0.10]
    return len(significant) == 1 or _is_duelist_locked_pool(row)


def _role_is_credibly_supported(row: pd.Series, role: str) -> bool:
    if role == "Flex":
        return _safe_float(row.get("flex_score"), 0.0) >= 0.50
    return _role_score_from_row(row, role) >= 0.15




def _effective_role_count(row: pd.Series) -> int:
    raw = row.get("role_scores")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    if not isinstance(raw, dict):
        return 0
    return sum(1 for score in raw.values() if _safe_float(score) >= 0.10)


def _is_flex_candidate(row: pd.Series) -> bool:
    """A player can be normalized to Flex only when their pool is not locked to one role."""
    if str(row.get("raw_role") or row.get("inferred_role") or "") == "Flex":
        return True
    return not _is_single_role_locked(row) and _effective_role_count(row) >= 2




def _non_current_core_support_score(row: pd.Series, current_role: str) -> float:
    """How much credible off-role evidence a player has outside their current assignment.

    Used to decide which duplicated role should become Flex. Example: if a SEN
    player is currently duplicated Sentinel but has Harbor/Controller evidence,
    that player is a better Flex candidate than a pure Sentinel.
    """
    return sum(
        _role_score_from_row(row, role)
        for role in CORE_ROLES
        if role != current_role and _role_score_from_row(row, role) >= 0.10
    )


def _duplicated_role_flex_score(row: pd.Series, current_role: str) -> float:
    score = _safe_float(row.get("flex_score"), 0.0)
    score += _effective_role_count(row) * 0.10
    score += _non_current_core_support_score(row, current_role) * 0.45
    if str(row.get("raw_role") or "") == "Flex":
        score += 0.25
    if current_role != "Duelist":
        score += 0.10
    return round(float(score), 6)

def _locked_duelist_count(group: pd.DataFrame, assigned: dict[int, str]) -> int:
    return sum(
        1
        for index in group.index
        if assigned.get(index) == "Duelist" and _is_duelist_locked_pool(group.loc[index])
    )


def _stable_team_can_skip_flex(group: pd.DataFrame, assigned: dict[int, str]) -> bool:
    """Flex is optional only for teams with two locked Duelist specialists."""
    return _locked_duelist_count(group, assigned) >= 2


def _has_duplicated_non_duelist_hybrid(group: pd.DataFrame, assigned: dict[int, str]) -> bool:
    """Detect duplicated Sentinel/Controller/Initiator where one player has off-role evidence.

    This intentionally also works when the scraped group has more than 5 rows because
    VLR data can include substitutions or duplicated event rows. Example: SEN can show
    two Sentinel-like players, but johnqt has Harbor/Controller evidence, so he should
    be the Flex rather than leaving the team with no Flex.
    """
    for role in ["Sentinel", "Controller", "Initiator"]:
        indices = [index for index, assigned_role in assigned.items() if assigned_role == role]
        if len(indices) <= 1:
            continue
        for index in indices:
            row = group.loc[index]
            if _is_flex_candidate(row) and _non_current_core_support_score(row, role) >= 0.10:
                return True
    return False


def _should_enforce_flex(group: pd.DataFrame, assigned: dict[int, str]) -> bool:
    """Flex is required for stable 5-player teams and for obvious duplicate-role hybrids.

    Strictly requiring Flex only when len(group) == 5 failed on real VLR exports where
    a team can appear with more rows because of scraped event granularity. The rule is
    now: require Flex for clean 5-player teams, and also when a duplicated non-Duelist
    role has a clear hybrid/off-role candidate.
    """
    if "Flex" in assigned.values() or _stable_team_can_skip_flex(group, assigned):
        return False
    return len(group) == 5 or _has_duplicated_non_duelist_hybrid(group, assigned)


def _enforce_flex_for_stable_team(group: pd.DataFrame, assigned: dict[int, str], suffix: dict[int, str]) -> None:
    """Ensure a team has a Flex unless the double-Duelist exception applies.

    The chosen Flex should normally come from a duplicated non-Duelist role with
    off-role evidence. This fixes cases where a Sentinel + Controller hybrid should
    become Flex because a more natural Sentinel already exists.
    """
    if not _should_enforce_flex(group, assigned):
        return

    duplicate_roles = {role for role in CORE_ROLES if list(assigned.values()).count(role) > 1}
    candidates: list[int] = []

    # Prefer duplicated non-Duelist roles. In a real 5-player team, duplicate Sentinel/
    # Controller/Initiator should usually be resolved into Flex when possible.
    for index, row in group.iterrows():
        current = assigned.get(index, "Flex")
        if current in duplicate_roles and current != "Duelist" and _is_flex_candidate(row):
            candidates.append(index)

    # If the only duplicate is Duelist, move the non-locked mixed Duelist, but never
    # a pure Duelist / Duelist+Chamber specialist.
    if not candidates:
        for index, row in group.iterrows():
            current = assigned.get(index, "Flex")
            if current == "Duelist" and current in duplicate_roles and not _is_duelist_locked_pool(row) and _is_flex_candidate(row):
                candidates.append(index)

    # Conservative fallback: any duplicated core role with a movable player.
    if not candidates:
        for index, row in group.iterrows():
            current = assigned.get(index, "Flex")
            if current in duplicate_roles and _is_flex_candidate(row):
                candidates.append(index)

    if not candidates:
        return

    def flex_candidate_score(index: int) -> float:
        row = group.loc[index]
        current = assigned.get(index, "Flex")
        score = _duplicated_role_flex_score(row, current)
        if current in duplicate_roles:
            score += 0.35
        return score

    chosen = max(candidates, key=flex_candidate_score)
    previous = assigned.get(chosen, "Flex")
    assigned[chosen] = "Flex"
    suffix[chosen] = (
        f"Team context moved this player from duplicated {previous} to Flex: stable 5-player teams "
        "should normally include a Flex unless they intentionally run two locked Duelist specialists."
    )

def _resolve_group_roles(group: pd.DataFrame) -> dict[int, tuple[str, str]]:
    """Return {index: (team_role, explanation_suffix)} for a team/event group.

    Business rules used by the Streamlit ranker:
    - Pure one-role players stay on that role.
    - Pure Duelist and Duelist/Chamber profiles may duplicate Duelist.
    - Each stable team group should still cover the four mandatory Valorant macro roles
      when there is credible evidence: Duelist, Controller/Smoker, Initiator, Sentinel.
    - Flex is normally required for stable 5-player teams; it may be absent only when
      the team has two locked Duelist specialists.
    """
    if group.empty:
        return {}

    assigned: dict[int, str] = {
        index: str(row.get("raw_role") or row.get("inferred_role") or "Flex")
        for index, row in group.iterrows()
    }
    suffix: dict[int, str] = {index: "" for index in group.index}

    # Mandatory macro roles. Flex is not mandatory.
    for missing_role in [role for role in CORE_ROLES if role not in assigned.values()]:
        candidates: list[int] = []
        for index, row in group.iterrows():
            current = assigned.get(index, "Flex")

            if current == missing_role:
                continue

            # Do not invent roles for pure locked players. A team can run two Duelist
            # specialists, but those players should not become fake Smokers/Sentinels.
            if _is_single_role_locked(row) and not _role_is_credibly_supported(row, missing_role):
                continue

            if missing_role == "Duelist":
                has_locked_duelist = any(
                    assigned.get(other_index) == "Duelist" and _is_duelist_locked_pool(group.loc[other_index])
                    for other_index in group.index
                )
                if has_locked_duelist:
                    continue
                if _is_duelist_locked_pool(row) or (current == "Flex" and _role_score_from_row(row, "Duelist") >= 0.50):
                    candidates.append(index)
                continue

            if _role_is_credibly_supported(row, missing_role):
                candidates.append(index)

        # If a 5-player team group still misses a mandatory role, use the least bad
        # flexible candidate, but never a locked one-role specialist. This keeps the
        # four macro roles covered while avoiding obvious nonsense assignments.
        if not candidates and len(group) >= 5:
            for index, row in group.iterrows():
                if _is_single_role_locked(row):
                    continue
                if assigned.get(index) in CORE_ROLES and list(assigned.values()).count(assigned[index]) == 1:
                    continue
                candidates.append(index)

        if not candidates:
            continue

        def candidate_score(index: int) -> float:
            row = group.loc[index]
            score = _assignment_score(row, missing_role)
            score += _safe_float(row.get("flex_score"), 0.0) * 0.12
            score -= _unique_core_role_penalty(assigned, index)
            if assigned.get(index) == "Flex":
                score += 0.15
            return score

        chosen = max(candidates, key=candidate_score)
        previous = assigned.get(chosen, "Flex")
        assigned[chosen] = missing_role
        suffix[chosen] = (
            f"Team context assigned {missing_role} to keep the mandatory macro roles covered "
            f"(Duelist, Controller/Smoker, Initiator, Sentinel); previous role was {previous}."
        )

    _enforce_flex_for_stable_team(group, assigned, suffix)

    # Resolve duplicated roles after mandatory-role coverage. Duelist can duplicate only
    # when both Duelists are locked specialists; duplicated Sentinel/Controller/Initiator
    # in a stable 5-player team should be pushed to Flex when a movable hybrid exists.
    for role in CORE_ROLES:
        role_indices = [index for index, assigned_role in assigned.items() if assigned_role == role]
        if len(role_indices) <= 1:
            continue

        if role == "Duelist":
            if _locked_duelist_count(group, assigned) >= 2:
                continue
            movable = [index for index in role_indices if not _is_duelist_locked_pool(group.loc[index])]
        else:
            movable = [index for index in role_indices if _is_flex_candidate(group.loc[index])]

        if len(group) == 5:
            flex_candidates = movable
        else:
            # For non-clean groups, still resolve duplicated non-Duelist roles when
            # the player has credible off-role evidence. This handles real scraped
            # rosters with substitutions/event-row artifacts without over-forcing
            # arbitrary players into Flex.
            flex_candidates = [
                index for index in movable
                if (
                    _safe_float(group.loc[index].get("flex_score"), 0.0) >= 0.35
                    or (role != "Duelist" and _non_current_core_support_score(group.loc[index], role) >= 0.10)
                )
            ]

        if flex_candidates:
            chosen = max(
                flex_candidates,
                key=lambda index: (
                    _duplicated_role_flex_score(group.loc[index], role),
                    _safe_float(group.loc[index].get("flex_score"), 0.0),
                    _effective_role_count(group.loc[index]),
                    _assignment_score(group.loc[index], "Flex"),
                ),
            )
            previous = assigned.get(chosen, role)
            assigned[chosen] = "Flex"
            suffix[chosen] = (
                f"Team context moved a duplicated {previous} to Flex. Stable 5-player teams should include "
                "Duelist, Controller/Smoker, Initiator, Sentinel and usually Flex; duplicate Duelist is allowed only for locked Duelist specialists."
            )

    return {index: (role, suffix.get(index, "")) for index, role in assigned.items()}

def enrich_player_roles(df: pd.DataFrame) -> pd.DataFrame:
    """Add raw role, team role, confidence and explainability columns."""
    if df.empty:
        return df.copy()

    out = df.copy()

    out = _normalize_player_team_columns(out)

    details_by_index: dict[Any, RoleInference] = {}

    for index, row in out.iterrows():
        agent_rounds = row.get("agent_rounds", None)
        has_agent_rounds = agent_rounds is not None and not (isinstance(agent_rounds, float) and pd.isna(agent_rounds))
        agents = agent_rounds if has_agent_rounds else row.get("agents", [])
        details = infer_player_role_details(agents, total_rounds=row.get("rounds"))
        details_by_index[index] = details
        out.at[index, "raw_role"] = details.raw_role
        out.at[index, "inferred_role"] = details.team_role
        out.at[index, "team_role"] = details.team_role
        out.at[index, "role_confidence"] = details.role_confidence
        out.at[index, "flex_score"] = details.flex_score
        out.at[index, "distinct_roles"] = details.distinct_roles
        out.at[index, "role_scores"] = json.dumps(details.role_scores, sort_keys=True)
        out.at[index, "official_role_scores"] = json.dumps(details.official_role_scores, sort_keys=True)
        out.at[index, "agent_shares"] = json.dumps(details.agent_shares, sort_keys=True)
        out.at[index, "role_explanation"] = details.explanation

    group_cols = [col for col in ["vct_region", "event_id", "event_name", "team"] if col in out.columns]
    if "team" not in group_cols:
        return out

    for _, group in out.groupby(group_cols, dropna=False):
        resolved = _resolve_group_roles(group)
        for index, (team_role, suffix) in resolved.items():
            out.at[index, "team_role"] = team_role
            out.at[index, "inferred_role"] = team_role
            raw_role = str(out.at[index, "raw_role"])
            role_confidence = _role_score_from_row(out.loc[index], team_role) if team_role != "Flex" else _safe_float(out.loc[index].get("flex_score"), 0.0)
            if team_role == raw_role:
                role_confidence = max(role_confidence, _safe_float(out.loc[index].get("role_confidence"), 0.0))
            out.at[index, "role_confidence"] = round(float(role_confidence), 3)
            if suffix:
                out.at[index, "role_explanation"] = f"{out.at[index, 'role_explanation']} {suffix}".strip()

    return out


def composition_label(agents: list[str]) -> str:
    role_counts = Counter(filter(None, (get_agent_role(agent) for agent in agents)))
    parts = [f"{role_counts[role]} {role}" for role in CORE_ROLES if role_counts[role]]
    return " / ".join(parts) if parts else "Unknown"
