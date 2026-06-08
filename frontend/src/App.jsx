import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API_BASE = "http://localhost:8000";

function asRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.rows)) return payload.rows;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.items)) return payload.items;
  return [];
}

function numberValue(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatValue(value, decimals = 3) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(decimals);
  }
  return String(value);
}

function formatPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function clampPercent(value, min = 4, max = 96) {
  return Math.max(min, Math.min(max, value));
}

function hashNumber(value) {
  const text = String(value ?? "");
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function jitteredMatrixPoint({ id, xScore, yScore, packedRight = false }) {
  const hash = hashNumber(id);
  const baseX = packedRight ? Math.min(88, xScore * 100) : xScore * 100;
  const baseY = yScore * 100;
  const angle = ((hash % 360) * Math.PI) / 180;
  const ring = 0.35 + (((hash >>> 3) % 5) / 5) * 0.75;
  const xRadius = packedRight ? 18 : 4.5;
  const yRadius = packedRight ? 16 : 5.5;

  return {
    x: clampPercent(baseX + Math.cos(angle) * xRadius * ring),
    y: clampPercent(baseY + Math.sin(angle) * yRadius * ring),
  };
}

function topBy(rows, key, limit = 10) {
  return [...(rows ?? [])]
    .sort((a, b) => numberValue(b[key]) - numberValue(a[key]))
    .slice(0, limit);
}

function Badge({ children, variant = "neutral" }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

function ScoreBar({ value }) {
  const n = Math.max(0, Math.min(1, numberValue(value)));
  return (
    <div className="scorebar">
      <div className="scorebar-fill" style={{ width: `${n * 100}%` }} />
    </div>
  );
}

function MetricCard({ label, value, helper }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {helper && <small>{helper}</small>}
    </article>
  );
}

function Section({ title, eyebrow, description, children, id, className = "" }) {
  return (
    <section id={id} className={`section ${className}`.trim()}>
      <div className="section-title">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

function DataTable({ rows, columns, empty = "Aucune donnée disponible." }) {
  if (!rows || rows.length === 0) {
    return <div className="empty-state">{empty}</div>;
  }

  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column.key}>
                  {column.render
                    ? column.render(row[column.key], row)
                    : formatValue(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBanner({ type = "info", message }) {
  return (
    <div className={`status-banner status-banner--${type}`}>
      {message}
    </div>
  );
}

function humanizeLabel(value) {
  const label = String(value ?? "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

  const replacements = {
    "Global Core Agent": "Core meta",
    "Situational Agent": "Situational",
    "Low Presence Agent": "Low presence",
    "Stable Core": "Stable core",
    "Map Specialist": "Map specialist",
    "Standard Meta Comp": "Standard comp",
    "Team Signature Comp": "Team signature",
    "Experimental Comp": "Experimental",
  };

  return replacements[label] ?? label;
}

function reliabilityLevel(value) {
  const n = numberValue(value);
  if (n >= 0.75) return { label: "High reliability", variant: "good" };
  if (n >= 0.45) return { label: "Medium reliability", variant: "warn" };
  return { label: "Low sample", variant: "risk" };
}

function ReliabilityBadge({ value }) {
  const level = reliabilityLevel(value);
  return <Badge variant={level.variant}>{level.label}</Badge>;
}

function ExecutiveCard({ eyebrow, title, value, children, variant = "neutral" }) {
  return (
    <article className={`executive-card executive-card--${variant}`}>
      <span className="executive-card__eyebrow">{eyebrow}</span>
      <h3>{title}</h3>
      {value && <strong>{value}</strong>}
      <div className="executive-card__body">{children}</div>
    </article>
  );
}

function InsightBlock({ title, interpretation, implication, children }) {
  return (
    <article className="insight-block">
      <div className="insight-block__content">
        <h3>{title}</h3>
        {children}
      </div>
      <div className="insight-block__reading">
        <p><strong>Interpretation.</strong> {interpretation}</p>
        <p><strong>Implication.</strong> {implication}</p>
      </div>
    </article>
  );
}


const ANALYTIC_RULES = {
  coreAgentMinPick: 0.4,
  coreAgentMinStability: 0.6,
  mapSpecialistMinMaxPick: 0.45,
  mapSpecialistMaxAvgPick: 0.4,
  mapSpecialistMinDependence: 0.35,
  fringeMaxPick: 0.05,
  strongIdentityMinCompStability: 0.6,
  strongIdentityMinMapIdentity: 0.3,
  flexibleMaxCompStability: 0.35,
  flexibleMinMapPool: 0.65,
  offMetaMinDistance: 0.65,
  offMetaMinUniqueness: 0.55,
  commonMapShellMinFrequency: 0.12,
  commonMapShellMinTeamShare: 0.25,
  offMetaMinCompStability: 0.35,
};

function qualitativePickLabel(value) {
  const n = numberValue(value);
  if (n >= 0.7) return "dominant";
  if (n >= 0.4) return "structuring";
  if (n >= 0.2) return "situational";
  if (n >= 0.05) return "marginal";
  return "near-zero";
}

function metaStateFromMetrics(top5PickMass, relevantAgentsCount) {
  if (top5PickMass >= 0.58 && relevantAgentsCount <= 8) {
    return {
      label: "Highly concentrated",
      tone: "risk",
      takeaway: "A narrow set of agents carries most of the observed pick mass.",
      implication: "Start every tactical read from the core-agent constraints before looking at variants.",
    };
  }
  if (top5PickMass >= 0.44) {
    return {
      label: "Moderately concentrated",
      tone: "warn",
      takeaway: "The meta has a visible core but still leaves room for several viable alternatives.",
      implication: "Separate global anchors from map or team-specific adaptations.",
    };
  }
  return {
    label: "Open agent pool",
    tone: "good",
    takeaway: "No small agent group fully dominates the observed dataset.",
    implication: "Read the meta through role coverage and map context rather than one fixed default shell.",
  };
}

function compositionStateFromShare(topCompShare, top5CompShare) {
  if (top5CompShare >= 0.55 || topCompShare >= 0.18) {
    return {
      label: "Standardized composition space",
      short: "Standardized",
      tone: "risk",
      takeaway: "A small set of compositions covers a large share of observed usage.",
      implication: "Benchmark team choices against the reference shells before treating them as innovation.",
    };
  }
  if (top5CompShare >= 0.35 || topCompShare >= 0.1) {
    return {
      label: "Mixed composition space",
      short: "Mixed",
      tone: "warn",
      takeaway: "There are recognizable reference compositions, but usage remains distributed.",
      implication: "Compare the top shells, then inspect team-specific deviations.",
    };
  }
  return {
    label: "Highly diverse composition space",
    short: "Highly diverse",
    tone: "good",
    takeaway: "Composition usage is fragmented; no dominant standard structure controls the dataset.",
    implication: "Avoid overfitting to one comp. The tactical value is in patterns, not a single default five-agent shell.",
  };
}

function KeyTakeaway({ children }) {
  return (
    <article className="key-takeaway">
      <span>Key takeaway</span>
      <p>{children}</p>
    </article>
  );
}

function RuleNote({ children }) {
  return <p className="rule-note">{children}</p>;
}

function AgentInsightCard({ agent, type = "core" }) {
  const pick = numberValue(agent.avg_pick_rate);
  const stability = numberValue(agent.cross_map_stability_score);
  const maxPick = numberValue(agent.max_pick_rate);
  const mapDependence = numberValue(agent.max_map_dependence_score);
  const isCore = type === "core";
  const agentName = formatValue(agent.agent);
  const primaryMap = formatValue(agent.primary_map);
  const pickLabel = qualitativePickLabel(pick);
  const title = isCore ? "Core meta agent" : "Map-dependent agent";
  const interpretation = isCore
    ? `${agentName} is a ${pickLabel} pick with enough cross-map stability to constrain baseline compositions.`
    : `${agentName} is not a global anchor: its value is concentrated in narrower map contexts, especially ${primaryMap}.`;
  const implication = isCore
    ? "Treat this agent as a first-order drafting constraint when reading the meta."
    : "Analyze it by map before drawing global conclusions; average pick rate can hide its tactical role.";

  return (
    <article className={`entity-card entity-card--${isCore ? "core" : "specialist"}`}>
      <div className="entity-card__header">
        <div>
          <span className="entity-card__kicker">{title}</span>
          <h3>{agentName}</h3>
        </div>
        <ReliabilityBadge value={agent.sample_reliability_score} />
      </div>
      <div className="stat-grid stat-grid--3">
        <div><span>Avg pick</span><strong>{formatPercent(pick)}</strong><em>{pickLabel}</em></div>
        <div><span>{isCore ? "Stability" : "Max pick"}</span><strong>{formatPercent(isCore ? stability : maxPick)}</strong></div>
        <div><span>Primary map</span><strong>{primaryMap}</strong></div>
      </div>
      <ScoreBar value={isCore ? pick : mapDependence} />
      <p className="entity-card__text"><strong>Interpretation.</strong> {interpretation}</p>
      <p className="entity-card__text"><strong>Implication.</strong> {implication}</p>
    </article>
  );
}

function CompositionInsightCard({ composition }) {
  const share = numberValue(composition.global_frequency ?? composition.composition_frequency);
  const usageLabel = share >= 0.1 ? "reference shell" : share >= 0.04 ? "recurring shell" : "thin signal";
  return (
    <article className="entity-card entity-card--composition">
      <div className="entity-card__header">
        <div>
          <span className="entity-card__kicker">{usageLabel}</span>
          <h3>{formatValue(composition.agents)}</h3>
        </div>
        <ReliabilityBadge value={composition.sample_reliability_score} />
      </div>
      <div className="stat-grid stat-grid--3">
        <div><span>Uses</span><strong>{formatValue(composition.total_uses ?? composition.times_used)}</strong></div>
        <div><span>Teams</span><strong>{formatValue(composition.teams_using_same_comp)}</strong></div>
        <div><span>Share</span><strong>{formatPercent(share)}</strong></div>
      </div>
      <p className="entity-card__text"><strong>Interpretation.</strong> This is a {usageLabel}: visible enough to compare against team-specific variants, but not a winrate or strength claim.</p>
      <p className="entity-card__text"><strong>Implication.</strong> Use it as an observed benchmark, then inspect which teams adapt or reject it.</p>
    </article>
  );
}

function TeamInsightCard({ team, mode = "identity" }) {
  const stable = mode === "identity";
  const compStability = numberValue(team.composition_stability_score);
  const mapIdentity = numberValue(team.map_identity_score);
  return (
    <article className={`entity-card entity-card--${stable ? "team-core" : "team-flex"}`}>
      <div className="entity-card__header">
        <div>
          <span className="entity-card__kicker">{stable ? "Strong identity" : "Flexible profile"}</span>
          <h3>{formatValue(team.team)}</h3>
        </div>
        <ReliabilityBadge value={team.sample_reliability_score} />
      </div>
      <div className="stat-grid stat-grid--3">
        <div><span>Comp stability</span><strong>{formatPercent(compStability)}</strong></div>
        <div><span>Map identity</span><strong>{formatPercent(mapIdentity)}</strong></div>
        <div><span>Maps</span><strong>{formatValue(team.maps_covered)}</strong></div>
      </div>
      <p className="entity-card__text"><strong>Interpretation.</strong> {stable ? "This team repeats enough structure to be read as preparation-driven rather than random." : "This team shows broader map visibility and lower composition reuse, so its identity is adaptive."}</p>
      <p className="entity-card__text"><strong>Implication.</strong> {stable ? "Use it as a strong candidate for team-specific scouting and composition comparison." : "Read its choices by map and matchup context instead of forcing one fixed identity."}</p>
    </article>
  );
}

function aggregateCompositions(rows) {
  const grouped = new Map();
  for (const row of rows ?? []) {
    const agents = String(row.agents ?? "").split(",").map((agent) => agent.trim()).filter(Boolean).sort().join(", ");
    if (!agents) continue;
    const current = grouped.get(agents) ?? { ...row, agents, total_uses: 0, teams: new Set(), reliability_sum: 0, reliability_count: 0 };
    const uses = Math.max(1, numberValue(row.times_used));
    current.total_uses += uses;
    if (row.team) current.teams.add(row.team);
    current.teams_using_same_comp = Math.max(numberValue(current.teams_using_same_comp), numberValue(row.teams_using_same_comp), current.teams.size);
    current.reliability_sum += numberValue(row.sample_reliability_score);
    current.reliability_count += 1;
    grouped.set(agents, current);
  }
  const aggregated = Array.from(grouped.values());
  const totalUses = aggregated.reduce((sum, row) => sum + numberValue(row.total_uses), 0);
  return aggregated
    .map((row) => ({
      ...row,
      teams_using_same_comp: row.teams.size || numberValue(row.teams_using_same_comp),
      global_frequency: totalUses > 0 ? numberValue(row.total_uses) / totalUses : 0,
      sample_reliability_score: row.reliability_count > 0 ? row.reliability_sum / row.reliability_count : row.sample_reliability_score,
    }))
    .sort((a, b) => numberValue(b.global_frequency) - numberValue(a.global_frequency));
}

function normalizeAgentsKey(value) {
  return String(value ?? "")
    .split(",")
    .map((agent) => agent.trim())
    .filter(Boolean)
    .sort()
    .join(", ");
}

function buildCompositionReference(rows) {
  const global = new Map();
  const byMap = new Map();
  const mapTotals = new Map();
  const mapTeams = new Map();

  for (const row of rows ?? []) {
    const agentsKey = normalizeAgentsKey(row.agents);
    if (!agentsKey) continue;
    const mapKey = String(row.map ?? row.map_name ?? "Unknown Map").trim() || "Unknown Map";
    const teamName = String(row.team ?? "").trim();
    const uses = Math.max(1, numberValue(row.times_used));

    if (!global.has(agentsKey)) global.set(agentsKey, { uses: 0, teams: new Set(), maps: new Set() });
    const globalEntry = global.get(agentsKey);
    globalEntry.uses += uses;
    if (teamName) globalEntry.teams.add(teamName);
    globalEntry.maps.add(mapKey);

    if (!byMap.has(mapKey)) byMap.set(mapKey, new Map());
    const mapComps = byMap.get(mapKey);
    if (!mapComps.has(agentsKey)) mapComps.set(agentsKey, { uses: 0, teams: new Set() });
    const mapEntry = mapComps.get(agentsKey);
    mapEntry.uses += uses;
    if (teamName) mapEntry.teams.add(teamName);

    mapTotals.set(mapKey, (mapTotals.get(mapKey) ?? 0) + uses);
    if (!mapTeams.has(mapKey)) mapTeams.set(mapKey, new Set());
    if (teamName) mapTeams.get(mapKey).add(teamName);
  }

  return { global, byMap, mapTotals, mapTeams };
}

function compositionNoveltyForRow(row, reference, teamCount) {
  const agentsKey = normalizeAgentsKey(row.agents);
  const mapKey = String(row.map ?? row.map_name ?? "Unknown Map").trim() || "Unknown Map";
  const globalEntry = reference.global.get(agentsKey);
  const mapEntry = reference.byMap.get(mapKey)?.get(agentsKey);
  const mapTotal = Math.max(1, numberValue(reference.mapTotals.get(mapKey)));
  const teamsOnMap = Math.max(1, reference.mapTeams.get(mapKey)?.size ?? teamCount ?? 1);
  const mapFrequency = numberValue(mapEntry?.uses) / mapTotal;
  const mapTeamShare = numberValue(mapEntry?.teams?.size) / teamsOnMap;
  const globalTeamShare = teamCount > 0 ? numberValue(globalEntry?.teams?.size) / teamCount : 0;

  // Map-aware novelty: several compositions can be meta on the same map.
  // A comp is novel only when few teams use it on that map and its map-level frequency is low.
  const mapPopularity = Math.max(
    mapFrequency / ANALYTIC_RULES.commonMapShellMinFrequency,
    mapTeamShare / ANALYTIC_RULES.commonMapShellMinTeamShare,
    globalTeamShare * 0.75,
  );
  const novelty = Math.max(0, Math.min(1, 1 - Math.min(1, mapPopularity)));
  const isCommonMapShell = mapFrequency >= ANALYTIC_RULES.commonMapShellMinFrequency || mapTeamShare >= ANALYTIC_RULES.commonMapShellMinTeamShare;

  return { agentsKey, mapKey, mapFrequency, mapTeamShare, globalTeamShare, novelty, isCommonMapShell };
}

function computeTeamMetaDeviation(team, compositions, aggregatedComps, teamCount) {
  const teamComps = (compositions ?? []).filter((row) => row.team === team.team);
  const reference = buildCompositionReference(compositions);
  const totalUses = teamComps.reduce((sum, row) => sum + Math.max(1, numberValue(row.times_used)), 0);

  if (!team || totalUses <= 0) {
    return {
      distanceToMeta: 0,
      uniquenessScore: 0,
      commonShellReuseShare: 0,
      rareShellShare: 0,
      offMetaStructureScore: 0,
      representativeRareShells: [],
      label: "No composition evidence",
      variant: "risk",
      interpretation: "No composition evidence is available for this team.",
      implication: "Do not classify meta deviation without composition-level rows.",
    };
  }

  let commonShellUses = 0;
  let rareShellUses = 0;
  let weightedNovelty = 0;
  const rareShells = new Map();

  for (const row of teamComps) {
    const uses = Math.max(1, numberValue(row.times_used));
    const novelty = compositionNoveltyForRow(row, reference, teamCount);
    if (novelty.isCommonMapShell) commonShellUses += uses;
    if (novelty.novelty >= ANALYTIC_RULES.offMetaMinUniqueness) rareShellUses += uses;
    weightedNovelty += uses * novelty.novelty;

    if (novelty.novelty >= ANALYTIC_RULES.offMetaMinUniqueness) {
      const key = `${novelty.agentsKey}__${novelty.mapKey}`;
      const current = rareShells.get(key) ?? { agents: novelty.agentsKey, map: novelty.mapKey, uses: 0, novelty: novelty.novelty, mapFrequency: novelty.mapFrequency, mapTeamShare: novelty.mapTeamShare };
      current.uses += uses;
      current.novelty = Math.max(current.novelty, novelty.novelty);
      rareShells.set(key, current);
    }
  }

  const commonShellReuseShare = commonShellUses / totalUses;
  const rareShellShare = rareShellUses / totalUses;
  const uniquenessScore = weightedNovelty / totalUses;
  const distanceToMeta = uniquenessScore;
  const compStability = numberValue(team.composition_stability_score);
  const reliability = numberValue(team.sample_reliability_score);
  const offMetaStructureScore = uniquenessScore * Math.max(0.15, compStability) * Math.max(0.2, rareShellShare);
  const representativeRareShells = [...rareShells.values()]
    .sort((a, b) => numberValue(b.uses) - numberValue(a.uses) || numberValue(b.novelty) - numberValue(a.novelty))
    .slice(0, 3);

  if (reliability < 0.45) {
    return {
      distanceToMeta,
      uniquenessScore,
      commonShellReuseShare,
      rareShellShare,
      offMetaStructureScore,
      representativeRareShells,
      label: "Weak signal",
      variant: "risk",
      interpretation: "The team shows unusual shells, but the sample is not reliable enough to call it a tactical identity.",
      implication: "Keep it as a watchlist signal, not as a structured off-meta read.",
    };
  }

  if (
    uniquenessScore >= ANALYTIC_RULES.offMetaMinDistance &&
    rareShellShare >= 0.35 &&
    compStability >= ANALYTIC_RULES.offMetaMinCompStability
  ) {
    return {
      distanceToMeta,
      uniquenessScore,
      commonShellReuseShare,
      rareShellShare,
      offMetaStructureScore,
      representativeRareShells,
      label: "Structured novelty",
      variant: "risk",
      interpretation: "This team repeatedly uses rare map-aware composition shells that few other teams adopt.",
      implication: "Study it as a potential anti-meta or innovation profile, not as proof of superior performance.",
    };
  }

  if (commonShellReuseShare >= 0.55 && compStability >= 0.35) {
    return {
      distanceToMeta,
      uniquenessScore,
      commonShellReuseShare,
      rareShellShare,
      offMetaStructureScore,
      representativeRareShells,
      label: "Meta shell follower",
      variant: "good",
      interpretation: "The team repeatedly uses composition shells that are already common on their maps.",
      implication: "Use it as a baseline for comparing more innovative teams.",
    };
  }

  if (uniquenessScore >= ANALYTIC_RULES.offMetaMinDistance) {
    return {
      distanceToMeta,
      uniquenessScore,
      commonShellReuseShare,
      rareShellShare,
      offMetaStructureScore,
      representativeRareShells,
      label: "Unstable novelty",
      variant: "warn",
      interpretation: "The team uses rare shells, but the repetition is not strong enough to call it a structured identity.",
      implication: "Treat it as experimentation until composition reuse becomes clearer.",
    };
  }

  return {
    distanceToMeta,
    uniquenessScore,
    commonShellReuseShare,
    rareShellShare,
    offMetaStructureScore,
    representativeRareShells,
    label: "Contextual adaptation",
    variant: "neutral",
    interpretation: "The team mixes common and uncommon shells without forming a clear novelty profile.",
    implication: "Read choices by map and opponent context rather than as one fixed anti-meta style.",
  };
}

function teamIdentityProfile(team) {
  const comp = numberValue(team.composition_stability_score);
  const mapIdentity = numberValue(team.map_identity_score);
  const mapPool = numberValue(team.map_pool_visibility_score);
  const reliability = numberValue(team.sample_reliability_score);

  if (reliability < 0.45) {
    return {
      label: "Weak signal",
      variant: "risk",
      short: "Insufficient evidence",
      interpretation: "The sample is too thin to infer a stable tactical identity.",
      implication: "Keep the team visible, but avoid ranking it as a reference profile.",
    };
  }

  if (comp >= ANALYTIC_RULES.strongIdentityMinCompStability && mapIdentity >= ANALYTIC_RULES.strongIdentityMinMapIdentity) {
    return {
      label: "Preparation identity",
      variant: "good",
      short: "Stable and readable",
      interpretation: "The team repeats enough composition structure and map identity to be treated as preparation-driven.",
      implication: "Best candidate for scouting: compare its repeated shells against the global meta baseline.",
    };
  }

  if (comp >= ANALYTIC_RULES.strongIdentityMinCompStability) {
    return {
      label: "Composition loyalist",
      variant: "good",
      short: "Stable drafts",
      interpretation: "The team reuses compositions, but without a strong enough map-specific identity signal.",
      implication: "Analyze repeated agent shells first, then verify whether map context explains the reuse.",
    };
  }

  if (mapIdentity >= ANALYTIC_RULES.strongIdentityMinMapIdentity) {
    return {
      label: "Map identity team",
      variant: "warn",
      short: "Map-shaped profile",
      interpretation: "The team has visible map preferences or map-specific structures, without one rigid global composition style.",
      implication: "Start by map pool and local adaptations before comparing global composition reuse.",
    };
  }

  if (mapPool >= ANALYTIC_RULES.flexibleMinMapPool && comp <= ANALYTIC_RULES.flexibleMaxCompStability) {
    return {
      label: "Adaptive profile",
      variant: "neutral",
      short: "Flexible by context",
      interpretation: "The team covers a broad map pool and avoids heavy composition repetition.",
      implication: "Do not force one identity; read patterns through matchup and map context.",
    };
  }

  return {
    label: "Mixed profile",
    variant: "neutral",
    short: "Partially readable",
    interpretation: "The team shows some structure, but not enough to classify it as a clear identity or a fully adaptive profile.",
    implication: "Use it as a secondary comparison point rather than a primary tactical reference.",
  };
}

function TeamProfilePill({ profile }) {
  const variant = profile.variant === "good" ? "good" : profile.variant === "warn" ? "warn" : profile.variant === "risk" ? "risk" : "neutral";
  return <Badge variant={variant}>{profile.label}</Badge>;
}

function TeamIdentitySummaryCard({ label, value, helper, variant = "neutral" }) {
  return (
    <article className={`team-summary-card team-summary-card--${variant}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{helper}</p>
    </article>
  );
}

function TeamMatrix({ teams, selectedTeam, onSelectTeam }) {
  const reliableTeams = teams.filter((team) => numberValue(team.sample_reliability_score) >= 0.45);
  const selectedProfile = reliableTeams.find((team) => team.team === selectedTeam);

  return (
    <div className="team-matrix-card">
      <div className="team-matrix-head">
        <div>
          <h3>Identity map</h3>
          <p>X = map identity, Y = composition stability. Strong identities sit in the upper-right zone.</p>
        </div>
        <RuleNote>Readable identity = comp stability ≥ 60% and map identity ≥ 30%.</RuleNote>
      </div>
      <div className="matrix-interaction-hint">
        <span>Click any team marker to update the dossier below.</span>
        {selectedProfile && <strong>Selected: {formatValue(selectedProfile.team)}</strong>}
      </div>
      <div className="team-matrix">
        <div className="matrix-threshold matrix-threshold--x" />
        <div className="matrix-threshold matrix-threshold--y" />
        <div className="matrix-zone matrix-zone--top-left">Composition loyalists</div>
        <div className="matrix-zone matrix-zone--top-right">Preparation identity</div>
        <div className="matrix-zone matrix-zone--bottom-left">Adaptive / mixed</div>
        <div className="matrix-zone matrix-zone--bottom-right">Map identity</div>
        <div className="matrix-axis matrix-axis--x">Map identity →</div>
        <div className="matrix-axis matrix-axis--y">Composition stability →</div>
        {reliableTeams.map((team) => {
          const x = Math.max(4, Math.min(96, numberValue(team.map_identity_score) * 100));
          const y = Math.max(4, Math.min(96, (1 - numberValue(team.composition_stability_score)) * 100));
          const profile = teamIdentityProfile(team);
          const isActive = selectedTeam === team.team;
          return (
            <button
              key={team.team}
              type="button"
              className={`matrix-dot matrix-dot--${profile.variant} ${isActive ? "active" : ""}`}
              style={{ left: `${x}%`, top: `${y}%` }}
              title={`${team.team}: ${profile.label}`}
              aria-label={`Select ${team.team} dossier`}
              onClick={() => onSelectTeam(team.team)}
            >
              {String(team.team ?? "?").slice(0, 3)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MetaDeviationSummaryCard({ label, value, helper, variant = "neutral" }) {
  return (
    <article className={`meta-deviation-summary-card meta-deviation-summary-card--${variant}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{helper}</p>
    </article>
  );
}

function TeamDeviationMatrix({ teams, selectedTeam, onSelectTeam }) {
  const reliableTeams = teams.filter((team) => numberValue(team.sample_reliability_score) >= 0.45);
  const selectedProfile = reliableTeams.find((team) => team.team === selectedTeam);

  return (
    <div className="team-matrix-card team-matrix-card--deviation">
      <div className="team-matrix-head">
        <div>
          <h3>Meta deviation map</h3>
          <p>X = map-aware composition novelty, Y = composition stability. The upper-right zone shows repeated rare shells, not merely a different pick from the most-used comp.</p>
        </div>
        <RuleNote>Structured novelty = novelty ≥ 65%, rare-shell share ≥ 35%, comp stability ≥ 35%.</RuleNote>
      </div>
      <div className="matrix-interaction-hint">
        <span>Click a marker to inspect whether the deviation is structured or only noisy.</span>
        {selectedProfile && <strong>Selected: {formatValue(selectedProfile.team)}</strong>}
      </div>
      <div className="team-matrix team-matrix--deviation">
        <div className="matrix-threshold matrix-threshold--deviation-x" />
        <div className="matrix-threshold matrix-threshold--deviation-y" />
        <div className="matrix-zone matrix-zone--top-left">Stable common-shell users</div>
        <div className="matrix-zone matrix-zone--top-right">Structured novelty</div>
        <div className="matrix-zone matrix-zone--bottom-left">Common / adaptive</div>
        <div className="matrix-zone matrix-zone--bottom-right">Unstable deviation</div>
        <div className="matrix-axis matrix-axis--x">Composition novelty →</div>
        <div className="matrix-axis matrix-axis--y">Composition stability →</div>
        {reliableTeams.map((team) => {
          const deviation = team.metaDeviation;
          const xScore = numberValue(deviation?.distanceToMeta);
          const yScore = 1 - numberValue(team.composition_stability_score);
          const point = jitteredMatrixPoint({
            id: team.team,
            xScore,
            yScore,
            packedRight: xScore >= 0.85,
          });
          const isActive = selectedTeam === team.team;
          return (
            <button
              key={team.team}
              type="button"
              className={`matrix-dot matrix-dot--${deviation?.variant ?? "neutral"} ${isActive ? "active" : ""}`}
              style={{ left: `${point.x}%`, top: `${point.y}%` }}
              title={`${team.team}: ${deviation?.label} · novelty ${formatPercent(deviation?.uniquenessScore)} · stability ${formatPercent(team.composition_stability_score)}`}
              aria-label={`Select ${team.team} meta deviation dossier`}
              onClick={() => onSelectTeam(team.team)}
            >
              {String(team.team ?? "?").slice(0, 3)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TeamMetaDeviationCard({ team, onSelectTeam }) {
  const deviation = team.metaDeviation;

  return (
    <article className={`team-profile-card team-profile-card--${deviation?.variant ?? "neutral"}`}>
      <div className="team-profile-card__header">
        <div>
          <span className="entity-card__kicker">{deviation?.label ?? "Meta deviation"}</span>
          <h3>{formatValue(team.team)}</h3>
        </div>
        <Badge variant={deviation?.variant ?? "neutral"}>{deviation?.label ?? "Deviation"}</Badge>
      </div>
      <div className="stat-grid stat-grid--3">
        <div><span>Composition novelty</span><strong>{formatPercent(deviation?.distanceToMeta)}</strong></div>
        <div><span>Uniqueness</span><strong>{formatPercent(deviation?.uniquenessScore)}</strong></div>
        <div><span>Comp stability</span><strong>{formatPercent(team.composition_stability_score)}</strong></div>
      </div>
      <p><strong>Reading.</strong> {deviation?.interpretation}</p>
      <p><strong>Caution.</strong> This is not a winrate or strength claim; it only measures structural divergence from common shells.</p>
      <button className="text-action" type="button" onClick={() => onSelectTeam(team.team)}>Open team dossier <span aria-hidden="true">↓</span></button>
    </article>
  );
}


function TeamProfileCard({ team, onSelectTeam }) {
  const profile = teamIdentityProfile(team);
  const comp = numberValue(team.composition_stability_score);
  const mapIdentity = numberValue(team.map_identity_score);
  const mapPool = numberValue(team.map_pool_visibility_score);

  return (
    <article className={`team-profile-card team-profile-card--${profile.variant}`}>
      <div className="team-profile-card__header">
        <div>
          <span className="entity-card__kicker">{profile.short}</span>
          <h3>{formatValue(team.team)}</h3>
        </div>
        <TeamProfilePill profile={profile} />
      </div>
      <div className="stat-grid stat-grid--3">
        <div><span>Comp stability</span><strong>{formatPercent(comp)}</strong></div>
        <div><span>Map identity</span><strong>{formatPercent(mapIdentity)}</strong></div>
        <div><span>Map pool</span><strong>{formatPercent(mapPool)}</strong></div>
      </div>
      <p><strong>Reading.</strong> {profile.interpretation}</p>
      <button className="text-action" type="button" onClick={() => onSelectTeam(team.team)}>Open team dossier <span aria-hidden="true">↓</span></button>
    </article>
  );
}

function TeamDossier({ team, maps, compositions }) {
  if (!team) return <div className="empty-state">Select a team to inspect its tactical dossier.</div>;

  const profile = teamIdentityProfile(team);
  const deviation = team.metaDeviation;
  const teamMaps = topBy(maps.filter((row) => row.team === team.team), "map_identity_score", 5);
  const teamComps = topBy(compositions.filter((row) => row.team === team.team), "composition_frequency", 5);

  return (
    <article className="team-dossier">
      <div className="team-dossier__header">
        <div>
          <span className="eyebrow">Selected team dossier</span>
          <h2>{formatValue(team.team)}</h2>
          <p>{profile.interpretation}</p>
        </div>
        <TeamProfilePill profile={profile} />
      </div>

      <div className="team-dossier__metrics">
        <MetricCard label="Composition stability" value={formatPercent(team.composition_stability_score)} helper="Repeated draft structure" />
        <MetricCard label="Map identity" value={formatPercent(team.map_identity_score)} helper="Map-specific readability" />
        <MetricCard label="Map visibility" value={formatPercent(team.map_pool_visibility_score)} helper="Observed map coverage" />
        <MetricCard label="Reliability" value={formatPercent(team.sample_reliability_score)} helper="Sample caution level" />
        <MetricCard label="Composition novelty" value={formatPercent(deviation?.distanceToMeta)} helper="Map-aware rarity of used shells" />
        <MetricCard label="Rare-shell score" value={formatPercent(deviation?.uniquenessScore)} helper="How uncommon its shells are by map" />
      </div>

      <div className="team-dossier__reading">
        <p><strong>Identity implication.</strong> {profile.implication}</p>
        <p><strong>Meta deviation.</strong> {deviation?.interpretation} {deviation?.implication}</p>
        <p><strong>How to use this.</strong> Start from the repeated composition shells, then check whether the same behavior holds by map. Do not infer team strength or win probability from these signals.</p>
      </div>

      <div className="team-evidence-grid">
        <div className="evidence-card">
          <h3>Map evidence</h3>
          {teamMaps.length > 0 ? teamMaps.map((row) => (
            <div className="evidence-row" key={`${row.team}-${row.map}`}>
              <span>{formatValue(row.map)}</span>
              <strong>{formatPercent(row.map_identity_score)}</strong>
              <em>{humanizeLabel(row.identity_label)}</em>
            </div>
          )) : <p className="muted-text">No map-level evidence available.</p>}
        </div>

        <div className="evidence-card">
          <h3>Composition evidence</h3>
          {teamComps.length > 0 ? teamComps.map((row) => (
            <div className="evidence-row evidence-row--stack" key={`${row.team}-${row.map}-${row.agents}`}>
              <span>{formatValue(row.agents)}</span>
              <strong>{formatPercent(row.composition_frequency)}</strong>
              <em>{formatValue(row.map)} · {formatValue(row.times_used)} uses</em>
            </div>
          )) : <p className="muted-text">No composition-level evidence available.</p>}
        </div>
      </div>
    </article>
  );
}

function OverviewPage({ agentGlobalMeta = [], teams = [], maps = [], compositions = [], pairs = [], insights = null }) {
  const globalAgents = agentGlobalMeta.filter((agent) => agent.agent);
  const sortedAgents = [...globalAgents].sort((a, b) => numberValue(b.avg_pick_rate) - numberValue(a.avg_pick_rate));
  const totalPickMass = sortedAgents.reduce((sum, agent) => sum + numberValue(agent.avg_pick_rate), 0);
  const top5PickMass = sortedAgents.slice(0, 5).reduce((sum, agent) => sum + numberValue(agent.avg_pick_rate), 0);
  const metaConcentration = totalPickMass > 0 ? top5PickMass / totalPickMass : 0;
  const relevantAgents = sortedAgents.filter((agent) => numberValue(agent.avg_pick_rate) >= 0.2);
  const entropy = sortedAgents.reduce((sum, agent) => {
    const p = totalPickMass > 0 ? numberValue(agent.avg_pick_rate) / totalPickMass : 0;
    return p > 0 ? sum - p * Math.log(p) : sum;
  }, 0);
  const effectiveAgents = Math.exp(entropy);
  const metaState = metaStateFromMetrics(metaConcentration, relevantAgents.length);

  const coreMeta = sortedAgents
    .filter((agent) => numberValue(agent.avg_pick_rate) >= ANALYTIC_RULES.coreAgentMinPick && numberValue(agent.cross_map_stability_score) >= ANALYTIC_RULES.coreAgentMinStability)
    .slice(0, 3);

  const top3Agents = coreMeta.length > 0 ? coreMeta : sortedAgents.slice(0, 3);

  const specialists = [...globalAgents]
    .filter((agent) => {
      const avgPick = numberValue(agent.avg_pick_rate);
      const maxPick = numberValue(agent.max_pick_rate);
      const dependence = numberValue(agent.max_map_dependence_score);
      const stability = numberValue(agent.cross_map_stability_score);
      const isStrictCore = avgPick >= ANALYTIC_RULES.coreAgentMinPick && stability >= ANALYTIC_RULES.coreAgentMinStability;
      return !isStrictCore && maxPick >= ANALYTIC_RULES.mapSpecialistMinMaxPick && avgPick < ANALYTIC_RULES.mapSpecialistMaxAvgPick && dependence >= ANALYTIC_RULES.mapSpecialistMinDependence;
    })
    .sort((a, b) => numberValue(b.max_map_dependence_score) - numberValue(a.max_map_dependence_score))
    .slice(0, 3);

  const lowPresence = [...agentGlobalMeta]
    .filter((agent) => numberValue(agent.avg_pick_rate) <= ANALYTIC_RULES.fringeMaxPick)
    .sort((a, b) => numberValue(a.avg_pick_rate) - numberValue(b.avg_pick_rate))
    .slice(0, 5);

  const aggregatedComps = aggregateCompositions(compositions);
  const topCompShare = numberValue(aggregatedComps[0]?.global_frequency);
  const top3CompShare = aggregatedComps.slice(0, 3).reduce((sum, comp) => sum + numberValue(comp.global_frequency), 0);
  const top5CompShare = aggregatedComps.slice(0, 5).reduce((sum, comp) => sum + numberValue(comp.global_frequency), 0);
  const compositionState = compositionStateFromShare(topCompShare, top5CompShare);
  const stableComps = aggregatedComps
    .filter((comp) => numberValue(comp.total_uses) >= 2 || numberValue(comp.teams_using_same_comp) >= 3 || comp.composition_stability_label === "standard_meta_comp")
    .slice(0, 3);

  const strongIdentityAll = [...teams]
    .filter((team) => numberValue(team.composition_stability_score) >= ANALYTIC_RULES.strongIdentityMinCompStability && numberValue(team.map_identity_score) >= ANALYTIC_RULES.strongIdentityMinMapIdentity && numberValue(team.sample_reliability_score) >= 0.45)
    .sort((a, b) => numberValue(b.composition_stability_score) - numberValue(a.composition_stability_score));
  const strongIdentityTeams = strongIdentityAll.slice(0, 3);
  const flexibleTeams = [...teams]
    .filter((team) => numberValue(team.map_pool_visibility_score) >= ANALYTIC_RULES.flexibleMinMapPool && numberValue(team.composition_stability_score) <= ANALYTIC_RULES.flexibleMaxCompStability && numberValue(team.sample_reliability_score) >= 0.45)
    .sort((a, b) => numberValue(b.map_pool_visibility_score) - numberValue(a.map_pool_visibility_score))
    .slice(0, 3);
  const weakSignalTeams = [...teams]
    .filter((team) => numberValue(team.sample_reliability_score) < 0.45)
    .sort((a, b) => numberValue(a.sample_reliability_score) - numberValue(b.sample_reliability_score))
    .slice(0, 5);

  return (
    <>
      <Section eyebrow="Tactical overview" title="Executive read" description="Vue volontairement synthétique : elle lit des signaux observables, pas la performance ni le winrate.">
        <KeyTakeaway>
          The meta is <strong>{metaState.label.toLowerCase()}</strong> at agent level and <strong>{compositionState.short.toLowerCase()}</strong> at composition level. The useful reading is not “who is strongest”, but which picks and structures constrain tactical choices.
        </KeyTakeaway>
        <div className="executive-grid">
          <ExecutiveCard eyebrow="Meta state" title={metaState.label} value={formatPercent(metaConcentration)} variant={metaState.tone}>
            <p>{metaState.takeaway}</p>
            <ul><li>Top 5 agent pick mass: <strong>{formatPercent(metaConcentration)}</strong></li><li>Agents above 20% pick: <strong>{relevantAgents.length}</strong></li><li>Effective agents: <strong>{effectiveAgents.toFixed(1)}</strong></li></ul>
            <p className="muted-text">{metaState.implication}</p>
          </ExecutiveCard>
          <ExecutiveCard eyebrow="Core agents" title="Strict structural core" value={`${coreMeta.length} agents`} variant={coreMeta.length > 0 ? "good" : "warn"}>
            <div className="rank-list">{top3Agents.map((agent) => <div key={agent.agent}><span>{formatValue(agent.agent)}</span><strong>{formatPercent(agent.avg_pick_rate)}</strong></div>)}</div>
            <RuleNote>Rule: avg pick ≥ 40% and cross-map stability ≥ 60%.</RuleNote>
          </ExecutiveCard>
          <ExecutiveCard eyebrow="Composition diversity" title={compositionState.short} value={formatPercent(top5CompShare)} variant={compositionState.tone}>
            <p>{compositionState.takeaway}</p>
            <ul><li>Top comp: <strong>{formatPercent(topCompShare)}</strong></li><li>Top 3 comps: <strong>{formatPercent(top3CompShare)}</strong></li><li>Top 5 comps: <strong>{formatPercent(top5CompShare)}</strong></li></ul>
          </ExecutiveCard>
          <ExecutiveCard eyebrow="Team identity" title="Readable structures" value={`${strongIdentityAll.length}/${teams.length || 0}`}>
            <p>{strongIdentityAll.length > 0 ? "Only a minority of teams show repeated structure strong enough to be treated as a tactical identity." : "No team has enough repeated structure to be treated as a clear identity leader."}</p>
            <RuleNote>Rule: comp stability ≥ 60%, map identity ≥ 30%, reliability ≥ 45%.</RuleNote>
          </ExecutiveCard>
        </div>
      </Section>

      <Section eyebrow="Meta structure" title="Agents that shape the game" description="Les agents sont séparés par rôle analytique avec des seuils explicites : cœur global, spécialistes map, puis faibles présences.">
        <InsightBlock title="Core meta agents" interpretation="These agents pass both thresholds: high average pick rate and high cross-map stability. They are not merely popular; they remain structurally visible across contexts." implication="Use them as the first layer of tactical reading before analyzing map-specific or team-specific variants.">
          <div className="entity-grid">{coreMeta.map((agent) => <AgentInsightCard key={agent.agent} agent={agent} />)}</div>
          {coreMeta.length === 0 && <StatusBanner type="info" message="No agent passes the strict core rule. This is a useful signal: the observed meta is not anchored by a stable global core." />}
        </InsightBlock>
        <InsightBlock title="Map-dependent agents" interpretation="These picks have strong local peaks but do not pass the global-core rule. Their role is tactical and contextual, not universal." implication="Analyze them by map first, then by team usage. A global average would understate their real tactical role.">
          <div className="entity-grid">{specialists.map((agent) => <AgentInsightCard key={agent.agent} agent={agent} type="specialist" />)}</div>
          {specialists.length === 0 && <StatusBanner type="info" message="No clear map specialist passes the current thresholds." />}
        </InsightBlock>
        {lowPresence.length > 0 && <div className="low-signal-strip"><strong>Low presence agents</strong><span>{lowPresence.map((agent) => agent.agent).join(", ")} are not part of the observed competitive core. Do not overinterpret stability scores when pick rate is near zero.</span></div>}
      </Section>

      <Section eyebrow="Composition landscape" title="Is the game standardized or diverse?" description="Les compositions sont agrégées globalement par combinaison d’agents pour éviter les longues tables team × map.">
        <div className="concentration-panel"><div><span>Top composition</span><strong>{formatPercent(topCompShare)}</strong></div><div><span>Top 3 compositions</span><strong>{formatPercent(top3CompShare)}</strong></div><div><span>Top 5 compositions</span><strong>{formatPercent(top5CompShare)}</strong></div><p><strong>{compositionState.label}.</strong> {compositionState.takeaway}<br /><em>{compositionState.implication}</em></p></div>
        <div className="entity-grid entity-grid--wide">{stableComps.map((comp) => <CompositionInsightCard key={`${comp.agents}-${comp.total_uses}`} composition={comp} />)}</div>
      </Section>

      <Section eyebrow="Team identity" title="Which teams have a readable tactical identity?" description="Les équipes sont catégorisées par structure observable, pas par niveau compétitif.">
        <InsightBlock title="Strong identity teams" interpretation="These teams meet explicit identity thresholds, so the signal is strong enough to discuss preparation patterns." implication="They are the best candidates for team-specific scouting and tactical comparison.">
          <div className="entity-grid">{strongIdentityTeams.map((team) => <TeamInsightCard key={team.team} team={team} />)}</div>
          {strongIdentityTeams.length === 0 && <StatusBanner type="info" message="No team passes the strict identity rule on this dataset." />}
        </InsightBlock>
        <InsightBlock title="Flexible teams" interpretation="These teams show broader map visibility and lower rigid composition reuse. Flexibility is not weakness; it is a different observable profile." implication="Their identity should be analyzed through adaptation patterns rather than one fixed composition.">
          <div className="entity-grid">{flexibleTeams.map((team) => <TeamInsightCard key={team.team} team={team} mode="flex" />)}</div>
        </InsightBlock>
        {weakSignalTeams.length > 0 && <div className="low-signal-strip low-signal-strip--risk"><strong>Weak signal teams</strong><span>{weakSignalTeams.map((team) => team.team).join(", ")} have limited reliability. Keep them visible, but do not rank them as tactical references.</span></div>}
      </Section>
    </>
  );
}

function AgentsPage({ agents }) {
  const [mapFilter, setMapFilter] = useState("All");
  const maps = useMemo(() => ["All", ...Array.from(new Set(agents.map((x) => x.map))).filter(Boolean).sort()], [agents]);

  const filtered = useMemo(() => {
    const rows = mapFilter === "All" ? agents : agents.filter((x) => x.map === mapFilter);
    return topBy(rows, "meta_presence_score", 30);
  }, [agents, mapFilter]);

  return (
    <Section eyebrow="Agent meta presence" title="Présence méta agents">
      <div className="toolbar">
        <label>
          Map
          <select value={mapFilter} onChange={(e) => setMapFilter(e.target.value)}>
            {maps.map((map) => <option key={map} value={map}>{map}</option>)}
          </select>
        </label>
      </div>

      <DataTable
        rows={filtered}
        columns={[
          { key: "map", label: "Map" },
          { key: "agent", label: "Agent" },
          { key: "pick_rate", label: "Pick rate", render: formatPercent },
          { key: "local_pick_delta", label: "Delta local", render: formatPercent },
          {
            key: "meta_presence_score",
            label: "Meta presence",
            render: (v) => <>{formatPercent(v)}<ScoreBar value={v} /></>,
          },
          { key: "map_dependence_score", label: "Map dependence" },
          { key: "sample_reliability_score", label: "Reliability", render: formatPercent },
          { key: "agent_meta_label", label: "Label" },
        ]}
      />
    </Section>
  );
}

function TeamsPage({ teams, maps, compositions = [] }) {
  const sortedTeams = [...teams].filter((team) => team.team).sort((a, b) => numberValue(b.sample_reliability_score) - numberValue(a.sample_reliability_score));
  const [selectedTeamName, setSelectedTeamName] = useState(sortedTeams[0]?.team ?? "");

  useEffect(() => {
    if (!selectedTeamName && sortedTeams[0]?.team) {
      setSelectedTeamName(sortedTeams[0].team);
    }
  }, [selectedTeamName, sortedTeams]);

  const selectTeamAndOpenDossier = (teamName) => {
    setSelectedTeamName(teamName);
    window.setTimeout(() => {
      document.getElementById("team-dossier")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };


  const aggregatedComps = aggregateCompositions(compositions);

  const enrichedTeams = sortedTeams.map((team) => ({
    ...team,
    identityProfile: teamIdentityProfile(team),
    metaDeviation: computeTeamMetaDeviation(team, compositions, aggregatedComps, sortedTeams.length),
  }));

  const selectedTeam = enrichedTeams.find((team) => team.team === selectedTeamName) ?? enrichedTeams[0];

  const strongIdentityTeams = enrichedTeams
    .filter((team) => team.identityProfile.label === "Preparation identity")
    .sort((a, b) => numberValue(b.composition_stability_score) - numberValue(a.composition_stability_score));

  const mapIdentityTeams = enrichedTeams
    .filter((team) => team.identityProfile.label === "Map identity team")
    .sort((a, b) => numberValue(b.map_identity_score) - numberValue(a.map_identity_score));

  const adaptiveTeams = enrichedTeams
    .filter((team) => team.identityProfile.label === "Adaptive profile")
    .sort((a, b) => numberValue(b.map_pool_visibility_score) - numberValue(a.map_pool_visibility_score));

  const weakSignalTeams = enrichedTeams
    .filter((team) => team.identityProfile.label === "Weak signal")
    .sort((a, b) => numberValue(a.sample_reliability_score) - numberValue(b.sample_reliability_score));

  const offMetaStructuredTeams = enrichedTeams
    .filter((team) => team.metaDeviation?.label === "Structured novelty")
    .sort((a, b) => numberValue(b.metaDeviation?.offMetaStructureScore) - numberValue(a.metaDeviation?.offMetaStructureScore));

  const metaFollowerTeams = enrichedTeams
    .filter((team) => team.metaDeviation?.label === "Meta follower")
    .sort((a, b) => numberValue(a.metaDeviation?.distanceToMeta) - numberValue(b.metaDeviation?.distanceToMeta));

  const unstableDeviationTeams = enrichedTeams
    .filter((team) => team.metaDeviation?.label === "Unstable deviation")
    .sort((a, b) => numberValue(b.metaDeviation?.distanceToMeta) - numberValue(a.metaDeviation?.distanceToMeta));

  const reliableTeams = enrichedTeams.filter((team) => numberValue(team.sample_reliability_score) >= 0.45);
  const averageCompStability = reliableTeams.length
    ? reliableTeams.reduce((sum, team) => sum + numberValue(team.composition_stability_score), 0) / reliableTeams.length
    : 0;

  return (
    <>
      <Section
        eyebrow="Team identity"
        title="Which teams have a readable tactical identity?"
        description="Cette page ne classe pas les équipes par niveau compétitif. Elle mesure la lisibilité de leur structure : répétition des compositions, identité par map, couverture du map pool et fiabilité du signal."
      >
        <KeyTakeaway>
          Only <strong>{strongIdentityTeams.length} teams</strong> pass the strict preparation-identity rule. Most teams are better understood as adaptive, map-shaped, or weak-sample profiles rather than fixed-style teams.
        </KeyTakeaway>

        <div className="team-summary-grid">
          <TeamIdentitySummaryCard
            label="Preparation identities"
            value={`${strongIdentityTeams.length}/${teams.length || 0}`}
            helper="Stable composition reuse + visible map identity."
            variant="good"
          />
          <TeamIdentitySummaryCard
            label="Adaptive profiles"
            value={adaptiveTeams.length}
            helper="Broad map visibility with low rigid composition reuse."
          />
          <TeamIdentitySummaryCard
            label="Avg comp stability"
            value={formatPercent(averageCompStability)}
            helper="Mean among reliable teams only."
            variant="warn"
          />
          <TeamIdentitySummaryCard
            label="Weak signals"
            value={weakSignalTeams.length}
            helper="Teams excluded from strong tactical conclusions."
            variant="risk"
          />
        </div>
      </Section>

      <Section
        eyebrow="Identity matrix"
        title="Stable structure vs map-specific identity"
        description="Le graphe positionne les équipes selon deux dimensions interprétables. Il aide à distinguer une vraie préparation répétée d’une simple flexibilité contextuelle."
      >
        <TeamMatrix teams={enrichedTeams} selectedTeam={selectedTeam?.team} onSelectTeam={setSelectedTeamName} />
      </Section>

      <Section
        eyebrow="Meta deviation"
        title="Who challenges the dominant composition baseline?"
        description="Cette section détecte les équipes qui s'éloignent des compositions les plus communes tout en gardant une structure interne. Ce n'est pas une mesure de performance."
      >
        <KeyTakeaway>
          <strong>{offMetaStructuredTeams.length} teams</strong> currently look structurally off-meta. They use composition shells that are uncommon globally, but repeated enough internally to deserve tactical inspection.
        </KeyTakeaway>

        <div className="meta-deviation-summary-grid">
          <MetaDeviationSummaryCard
            label="Structured novelty"
            value={offMetaStructuredTeams.length}
            helper="High map-aware composition novelty + enough internal stability."
            variant="risk"
          />
          <MetaDeviationSummaryCard
            label="Meta followers"
            value={metaFollowerTeams.length}
            helper="Close to common shells and stable enough to use as benchmarks."
            variant="good"
          />
          <MetaDeviationSummaryCard
            label="Unstable deviations"
            value={unstableDeviationTeams.length}
            helper="Different from the meta, but not repeated enough yet."
            variant="warn"
          />
        </div>

        <TeamDeviationMatrix teams={enrichedTeams} selectedTeam={selectedTeam?.team} onSelectTeam={setSelectedTeamName} />

        <InsightBlock
          title="Structured novelty candidates"
          interpretation="These teams are not simply flexible. Their compositions differ from dominant shells while still showing enough repetition to be inspected as an alternative structure."
          implication="Use them to study tactical divergence and anti-meta tendencies, without claiming that the approach wins more often."
        >
          <div className="entity-grid">
            {offMetaStructuredTeams.slice(0, 3).map((team) => <TeamMetaDeviationCard key={team.team} team={team} onSelectTeam={selectTeamAndOpenDossier} />)}
          </div>
          {offMetaStructuredTeams.length === 0 && <StatusBanner type="info" message="No team passes the strict structured off-meta thresholds. This is also useful: current deviations are either weak, unstable, or not unique enough." />}
        </InsightBlock>
      </Section>

      <Section
        id="team-dossier"
        eyebrow="Dossier"
        title="Team-level evidence"
        description="Select a team from the matrix or profile cards. This section updates immediately and justifies the selected tactical profile."
      >
        <div className="toolbar toolbar--dossier">
          <label>
            Team
            <select value={selectedTeam?.team ?? ""} onChange={(event) => setSelectedTeamName(event.target.value)}>
              {sortedTeams.map((team) => <option key={team.team} value={team.team}>{team.team}</option>)}
            </select>
          </label>
          <span className="toolbar-note">The dossier is evidence, not a ranking of team strength.</span>
        </div>
        <TeamDossier team={selectedTeam} maps={maps} compositions={compositions} />
      </Section>

      <Section
        eyebrow="Team groups"
        title="Readable tactical profiles"
        description="Les groupes ci-dessous servent à comparer des comportements observables, pas à prédire la performance."
      >
        <div className="team-groups">
          <InsightBlock
            title="Preparation identity teams"
            interpretation="These teams combine repeated composition structure with enough map identity to support a real scouting read."
            implication="Use them as reference cases when explaining team-specific preparation patterns."
          >
            <div className="entity-grid">
              {strongIdentityTeams.slice(0, 3).map((team) => <TeamProfileCard key={team.team} team={team} onSelectTeam={selectTeamAndOpenDossier} />)}
            </div>
            {strongIdentityTeams.length === 0 && <StatusBanner type="info" message="No team passes the strict preparation-identity thresholds." />}
          </InsightBlock>

          <InsightBlock
            title="Map identity teams"
            interpretation="These teams are not globally rigid, but their structure becomes more readable once map context is introduced."
            implication="Analyze their map pool before judging composition reuse at global level."
          >
            <div className="entity-grid">
              {mapIdentityTeams.slice(0, 3).map((team) => <TeamProfileCard key={team.team} team={team} onSelectTeam={selectTeamAndOpenDossier} />)}
            </div>
            {mapIdentityTeams.length === 0 && <StatusBanner type="info" message="No map-identity team passes the current thresholds." />}
          </InsightBlock>

          <InsightBlock
            title="Adaptive teams"
            interpretation="These teams have broad visibility and lower composition repetition, which indicates contextual adaptation rather than one fixed identity."
            implication="Compare their choices map by map; a global average can hide how they adapt."
          >
            <div className="entity-grid">
              {adaptiveTeams.slice(0, 3).map((team) => <TeamProfileCard key={team.team} team={team} onSelectTeam={selectTeamAndOpenDossier} />)}
            </div>
            {adaptiveTeams.length === 0 && <StatusBanner type="info" message="No adaptive team passes the current thresholds." />}
          </InsightBlock>
        </div>
      </Section>
    </>
  );
}

function CompositionsPage({ compositions, pairs }) {
  return (
    <>
      <Section title="Patterns de composition">
        <DataTable
          rows={topBy(compositions, "composition_frequency", 40)}
          columns={[
            { key: "team", label: "Team" },
            { key: "map", label: "Map" },
            { key: "agents", label: "Agents" },
            { key: "times_used", label: "Uses" },
            { key: "composition_frequency", label: "Frequency", render: formatPercent },
            { key: "composition_uniqueness_score", label: "Uniqueness", render: formatPercent },
            { key: "composition_stability_label", label: "Label" },
          ]}
        />
      </Section>

      <Section title="Agent pair patterns">
        <DataTable
          rows={topBy(pairs, "synergy_lift", 40)}
          columns={[
            { key: "map", label: "Map" },
            { key: "agent_a", label: "Agent A" },
            { key: "agent_b", label: "Agent B" },
            { key: "synergy_lift", label: "Lift" },
            { key: "pair_pick_rate", label: "Pair pick rate", render: formatPercent },
            { key: "sample_reliability_score", label: "Reliability", render: formatPercent },
            { key: "pair_pattern_label", label: "Label" },
          ]}
        />
      </Section>
    </>
  );
}

function InsightsPage({ insights }) {
  return (
    <>
      <Section title="Insights">
        <div className="insight-grid">
          {insights?.top_insights?.map((insight, index) => (
            <article className="insight-card" key={index}>
              <div className="insight-meta">
                <Badge>{insight.type}</Badge>
                <Badge variant={insight.confidence === "high" ? "good" : insight.confidence === "medium" ? "warn" : "risk"}>
                  {insight.confidence}
                </Badge>
              </div>
              <h3>{insight.title}</h3>
              <p><strong>Entity:</strong> {formatValue(insight.entity)}</p>
              <p><strong>Metric:</strong> {formatValue(insight.metric)}</p>
              <p><strong>Value:</strong> {formatValue(insight.value)}</p>
              {insight.warning && <p className="warning">{insight.warning}</p>}
            </article>
          )) ?? <div className="empty-state">Aucun insight disponible.</div>}
        </div>
      </Section>

      <Section title="Methodology notes">
        <ul className="methodology-list">
          {(insights?.methodology_notes ?? []).map((note, index) => (
            <li key={index}>{note}</li>
          ))}
        </ul>
      </Section>
    </>
  );
}

function MiniBarChart({ rows, labelKey, valueKey, title, formatter = formatPercent, limit = 10 }) {
  const data = topBy(rows, valueKey, limit);
  const max = Math.max(...data.map((row) => numberValue(row[valueKey])), 1);

  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <div className="bar-chart">
        {data.map((row, index) => {
          const value = numberValue(row[valueKey]);
          return (
            <div className="bar-row" key={`${row[labelKey]}-${index}`}>
              <span className="bar-label">{formatValue(row[labelKey])}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(value / max) * 100}%` }} />
              </div>
              <strong>{formatter(value)}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LabelDistribution({ rows, labelKey, title }) {
  const counts = Object.entries(
    rows.reduce((acc, row) => {
      const label = row[labelKey] ?? "unknown";
      acc[label] = (acc[label] ?? 0) + 1;
      return acc;
    }, {})
  )
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <div className="label-distribution">
        {counts.map((item) => (
          <div className="label-row" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function normalizeRateValue(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (n > 1 && n <= 100) return n / 100;
  if (n >= 0 && n <= 1) return n;
  return null;
}

function structuralExplorationScore(team) {
  const novelty = numberValue(team.metaDeviation?.uniquenessScore);
  const stability = numberValue(team.composition_stability_score);
  const reliability = numberValue(team.sample_reliability_score);
  const rareShare = numberValue(team.metaDeviation?.rareShellShare);
  return Math.max(0, Math.min(1, 0.35 * novelty + 0.3 * stability + 0.2 * reliability + 0.15 * rareShare));
}

function structuralExplorationProfile(team) {
  const novelty = numberValue(team.metaDeviation?.uniquenessScore);
  const stability = numberValue(team.composition_stability_score);
  const score = structuralExplorationScore(team);
  if (novelty >= 0.65 && stability >= 0.35) return { label: "High-priority novelty case", variant: "risk", interpretation: "This team combines rare map-aware shells with enough repetition to justify manual review.", caution: "This is not performance. It only identifies a structurally interesting tactical case.", score };
  if (novelty >= 0.65) return { label: "Novel but unstable", variant: "warn", interpretation: "This team uses uncommon shells, but the pattern is not repeated enough yet.", caution: "Treat it as experimentation or map-context noise until more repetition appears.", score };
  if (stability >= 0.45) return { label: "Stable common structure", variant: "good", interpretation: "This team shows repeated structure, but mostly within common map-aware shells.", caution: "Useful as a baseline, not as an innovation case.", score };
  return { label: "Low-priority structure", variant: "neutral", interpretation: "The structural signals are not strong enough to prioritize this team for tactical review.", caution: "Use the Team Identity page before drawing conclusions.", score };
}

function performanceSignalForTeam(team, performanceRows = []) {
  const perfRow = performanceRows.find((row) => row.team === team.team) ?? {};
  const merged = { ...team, ...perfRow };
  const directKeys = ["winrate", "win_rate", "team_winrate", "observed_winrate", "match_win_rate", "map_win_rate", "series_win_rate"];
  for (const key of directKeys) {
    const value = normalizeRateValue(merged[key]);
    if (value !== null) {
      return { winrate: value, source: key, matches: numberValue(merged.matches_played ?? merged.matches ?? merged.total_matches ?? merged.maps_played ?? merged.maps_covered) };
    }
  }
  const wins = numberValue(merged.wins ?? merged.matches_won ?? merged.maps_won ?? merged.series_won);
  const losses = numberValue(merged.losses ?? merged.matches_lost ?? merged.maps_lost ?? merged.series_lost);
  const total = numberValue(merged.matches_played ?? merged.matches ?? merged.total_matches ?? wins + losses);
  if (wins > 0 && total > 0 && wins <= total) return { winrate: wins / total, source: "wins / matches", matches: total };
  return null;
}

function performanceProfile(team) {
  const perf = team.performanceSignal;
  const deviation = team.metaDeviation;
  if (!perf) return { label: "Performance unavailable", variant: "neutral", interpretation: "No reliable winrate field is available in the current data contract for this team.", caution: "Do not infer performance from structural metrics such as stability, identity, or meta deviation." };
  const highWinrate = perf.winrate >= 0.6;
  const lowWinrate = perf.winrate <= 0.4;
  const highDeviation = numberValue(deviation?.distanceToMeta) >= ANALYTIC_RULES.offMetaMinDistance;
  const stable = numberValue(team.composition_stability_score) >= ANALYTIC_RULES.offMetaMinCompStability;
  if (highWinrate && highDeviation && stable) return { label: "High winrate + structured deviation", variant: "risk", interpretation: "This team combines high observed winrate with rare map-aware composition shells.", caution: "This is a correlation screen only. The winrate may reflect team strength, opponents, map context, or event selection." };
  if (highWinrate && !highDeviation) return { label: "High winrate + meta-close", variant: "good", interpretation: "This team performs strongly while staying relatively close to common composition shells.", caution: "The signal describes context, not the causal effect of those compositions." };
  if (lowWinrate && highDeviation) return { label: "Low winrate + deviation", variant: "warn", interpretation: "This team deviates from the meta, but the observed outcome context is weak.", caution: "Treat this as exploration or noise unless repeated in a larger, controlled sample." };
  return { label: "Neutral performance context", variant: "neutral", interpretation: "The performance signal does not create a strong contextual contrast with the structural profile.", caution: "Use the structural pages first; use winrate only as supporting context." };
}

function PerformanceWarning() {
  return <div className="performance-warning"><strong>Methodological guardrail.</strong> Performance metrics are shown for context only. They do not imply that an agent, composition, or meta deviation causes the outcome.</div>;
}

function PerformanceSummaryCard({ label, value, helper, variant = "neutral" }) {
  return <article className={`performance-summary-card performance-summary-card--${variant}`}><span>{label}</span><strong>{value}</strong><p>{helper}</p></article>;
}

function PerformanceMatrix({ teams, selectedTeam, onSelectTeam, mode = "performance" }) {
  const hasPerformance = mode === "performance";
  const rows = hasPerformance ? teams.filter((team) => team.performanceSignal) : teams.filter((team) => numberValue(team.sample_reliability_score) >= 0.45);
  const selectedProfile = rows.find((team) => team.team === selectedTeam);
  if (rows.length === 0) {
    return <div className="performance-empty-card"><h3>No reliable team rows found</h3><p>The page needs team-level structure rows to build an exploration view.</p></div>;
  }
  return (
    <div className="team-matrix-card team-matrix-card--performance">
      <div className="team-matrix-head"><div><h3>{hasPerformance ? "Structure vs performance context" : "Structural exploration map"}</h3><p>{hasPerformance ? "X = map-aware composition novelty, Y = observed winrate. This is a correlation screen, not a causal model." : "X = map-aware composition novelty, Y = structural exploration score. This replaces missing winrate with an explicit non-performance proxy."}</p></div><RuleNote>{hasPerformance ? "High context zone = winrate ≥ 60%. Novelty zone = novelty ≥ 65%." : "Exploration score = novelty, stability, reliability and rare-shell share. It is not a winrate proxy."}</RuleNote></div>
      <div className="matrix-interaction-hint"><span>Click a marker to inspect the team profile. Exact values remain available in the cards.</span>{selectedProfile && <strong>Selected: {formatValue(selectedProfile.team)}</strong>}</div>
      <div className="team-matrix team-matrix--performance">
        <div className="matrix-threshold matrix-threshold--performance-x" />
        <div className="matrix-threshold matrix-threshold--performance-y" />
        <div className="matrix-zone matrix-zone--top-left">{hasPerformance ? "Common high context" : "Stable common cases"}</div>
        <div className="matrix-zone matrix-zone--top-right">{hasPerformance ? "Novel high context" : "Priority novelty cases"}</div>
        <div className="matrix-zone matrix-zone--bottom-left">{hasPerformance ? "Common low context" : "Low-priority common"}</div>
        <div className="matrix-zone matrix-zone--bottom-right">{hasPerformance ? "Novel low context" : "Novel but weak"}</div>
        <div className="matrix-axis matrix-axis--x">Composition novelty →</div>
        <div className="matrix-axis matrix-axis--y">{hasPerformance ? "Observed winrate →" : "Exploration priority →"}</div>
        {rows.map((team) => {
          const xScore = numberValue(team.metaDeviation?.uniquenessScore);
          const yMetric = hasPerformance ? numberValue(team.performanceSignal?.winrate) : structuralExplorationScore(team);
          const yScore = 1 - yMetric;
          const point = jitteredMatrixPoint({ id: `${hasPerformance ? "perf" : "explore"}-${team.team}`, xScore, yScore, packedRight: xScore >= 0.85 });
          const profile = hasPerformance ? performanceProfile(team) : structuralExplorationProfile(team);
          const isActive = selectedTeam === team.team;
          return <button key={team.team} type="button" className={`matrix-dot matrix-dot--${profile.variant} ${isActive ? "active" : ""}`} style={{ left: `${point.x}%`, top: `${point.y}%` }} title={`${team.team}: ${hasPerformance ? formatPercent(team.performanceSignal.winrate) + " winrate" : formatPercent(structuralExplorationScore(team)) + " exploration score"} · ${formatPercent(team.metaDeviation?.uniquenessScore)} novelty`} aria-label={`Select ${team.team} ${hasPerformance ? "performance" : "exploration"} context`} onClick={() => onSelectTeam(team.team)}>{String(team.team ?? "?").slice(0, 3)}</button>;
        })}
      </div>
    </div>
  );
}

function PerformanceTeamCard({ team, onSelectTeam, mode = "performance" }) {
  const hasPerformance = mode === "performance" && team.performanceSignal;
  const profile = hasPerformance ? performanceProfile(team) : structuralExplorationProfile(team);
  return (
    <article className={`team-profile-card team-profile-card--${profile.variant}`}>
      <div className="team-profile-card__header"><div><span className="entity-card__kicker">{profile.label}</span><h3>{formatValue(team.team)}</h3></div><Badge variant={profile.variant}>{hasPerformance ? formatPercent(team.performanceSignal.winrate) : formatPercent(structuralExplorationScore(team))}</Badge></div>
      <div className="stat-grid stat-grid--3"><div><span>{hasPerformance ? "Winrate" : "Exploration"}</span><strong>{hasPerformance ? formatPercent(team.performanceSignal.winrate) : formatPercent(structuralExplorationScore(team))}</strong></div><div><span>Novelty</span><strong>{formatPercent(team.metaDeviation?.uniquenessScore)}</strong></div><div><span>Stability</span><strong>{formatPercent(team.composition_stability_score)}</strong></div></div>
      <p><strong>Reading.</strong> {profile.interpretation}</p><p><strong>Caution.</strong> {profile.caution}</p>
      <button className="text-action" type="button" onClick={() => onSelectTeam(team.team)}>Inspect context <span aria-hidden="true">↓</span></button>
    </article>
  );
}

function PerformanceContextPage({ teams = [], compositions = [], performance = [] }) {
  const aggregatedComps = useMemo(() => aggregateCompositions(compositions), [compositions]);
  const enrichedTeams = useMemo(() => [...teams].sort((a, b) => String(a.team ?? "").localeCompare(String(b.team ?? ""))).map((team) => ({ ...team, metaDeviation: computeTeamMetaDeviation(team, compositions, aggregatedComps, teams.length), performanceSignal: performanceSignalForTeam(team, performance) })), [teams, compositions, aggregatedComps, performance]);
  const performanceTeams = enrichedTeams.filter((team) => team.performanceSignal);
  const hasPerformance = performanceTeams.length > 0;
  const explorationTeams = [...enrichedTeams]
    .filter((team) => numberValue(team.sample_reliability_score) >= 0.45)
    .sort((a, b) => structuralExplorationScore(b) - structuralExplorationScore(a));
  const [selectedTeamName, setSelectedTeamName] = useState((hasPerformance ? performanceTeams[0]?.team : explorationTeams[0]?.team) ?? enrichedTeams[0]?.team ?? "");
  useEffect(() => {
    const fallback = (hasPerformance ? performanceTeams[0]?.team : explorationTeams[0]?.team) ?? enrichedTeams[0]?.team;
    if (!selectedTeamName && fallback) setSelectedTeamName(fallback);
  }, [selectedTeamName, hasPerformance, performanceTeams, explorationTeams, enrichedTeams]);
  const selectedTeam = enrichedTeams.find((team) => team.team === selectedTeamName) ?? enrichedTeams[0];
  const avgWinrate = performanceTeams.length ? performanceTeams.reduce((sum, team) => sum + numberValue(team.performanceSignal?.winrate), 0) / performanceTeams.length : null;
  const highContextTeams = performanceTeams.filter((team) => numberValue(team.performanceSignal?.winrate) >= 0.6);
  const offMetaHighContextTeams = performanceTeams.filter((team) => numberValue(team.performanceSignal?.winrate) >= 0.6 && numberValue(team.metaDeviation?.uniquenessScore) >= ANALYTIC_RULES.offMetaMinDistance && numberValue(team.composition_stability_score) >= ANALYTIC_RULES.offMetaMinCompStability);
  const priorityExplorationTeams = explorationTeams.filter((team) => numberValue(team.metaDeviation?.uniquenessScore) >= ANALYTIC_RULES.offMetaMinDistance || structuralExplorationScore(team) >= 0.55);
  const selectTeamAndOpen = (teamName) => { setSelectedTeamName(teamName); window.requestAnimationFrame(() => document.getElementById("performance-dossier")?.scrollIntoView({ behavior: "smooth", block: "start" })); };
  const selectedStructuralProfile = selectedTeam ? structuralExplorationProfile(selectedTeam) : null;
  const selectedPerformanceProfile = selectedTeam ? performanceProfile(selectedTeam) : null;
  const selectedProfile = hasPerformance ? selectedPerformanceProfile : selectedStructuralProfile;
  return (
    <>
      <Section eyebrow={hasPerformance ? "Performance context" : "Exploration context"} title={hasPerformance ? "Structure vs outcome context" : "Structural exploration without outcome data"} description={hasPerformance ? "Cette page ajoute le winrate uniquement comme contexte. Elle ne transforme pas les compositions ou la déviation méta en prédiction de performance." : "Aucun winrate fiable n'est exposé. La page reste utile en priorisant les équipes à inspecter via novelty, stabilité et fiabilité — sans prétendre mesurer la performance."}>
        {hasPerformance ? <PerformanceWarning /> : <div className="performance-warning performance-warning--neutral"><strong>Exploration mode.</strong> No safe winrate field is available, so this page shows structural cases worth reviewing. This is not a performance estimate.</div>}
        <KeyTakeaway>{hasPerformance ? <>Performance is available for <strong>{performanceTeams.length} teams</strong>. Read it after structure: first identity, then composition novelty, then outcome context.</> : <>No safe winrate field is available. The page now falls back to <strong>structural exploration</strong>: rare map-aware shells + repetition + reliability.</>}</KeyTakeaway>
        <div className="performance-summary-grid"><PerformanceSummaryCard label={hasPerformance ? "Teams with performance context" : "Teams available for exploration"} value={`${hasPerformance ? performanceTeams.length : explorationTeams.length}/${teams.length || 0}`} helper={hasPerformance ? "Teams exposing winrate or wins/matches fields." : "Reliable teams scored through structural signals only."} variant="good" /><PerformanceSummaryCard label={hasPerformance ? "Average observed winrate" : "Average exploration score"} value={hasPerformance ? (avgWinrate === null ? "—" : formatPercent(avgWinrate)) : formatPercent(explorationTeams.reduce((sum, team) => sum + structuralExplorationScore(team), 0) / Math.max(1, explorationTeams.length))} helper={hasPerformance ? "Shown only when explicit outcome data exists." : "Novelty + stability + reliability + rare-shell share."} /><PerformanceSummaryCard label={hasPerformance ? "High-context teams" : "Priority review cases"} value={hasPerformance ? highContextTeams.length : priorityExplorationTeams.length} helper={hasPerformance ? "Observed winrate ≥ 60%, not a causal strength claim." : "Teams whose structure deserves manual analysis."} variant="warn" /><PerformanceSummaryCard label={hasPerformance ? "Novelty + high context" : "Structured novelty cases"} value={hasPerformance ? offMetaHighContextTeams.length : explorationTeams.filter((team) => team.metaDeviation?.label === "Structured novelty").length} helper={hasPerformance ? "Rare shells combined with high observed winrate." : "Rare shells repeated enough to form a readable pattern."} variant="risk" /></div>
      </Section>
      <Section eyebrow={hasPerformance ? "Structure × performance" : "Structure × exploration"} title={hasPerformance ? "Do rare composition structures appear in high-outcome contexts?" : "Which teams deserve tactical review first?"} description={hasPerformance ? "Le graphe croise novelty compositionnelle et winrate observé. Il sert à repérer des cas à investiguer, pas à expliquer les résultats." : "Le graphe croise novelty compositionnelle et score d'exploration structurel. Il sert à prioriser l'analyse humaine."}><PerformanceMatrix teams={enrichedTeams} selectedTeam={selectedTeam?.team} onSelectTeam={selectTeamAndOpen} mode={hasPerformance ? "performance" : "exploration"} /></Section>
      <Section id="performance-dossier" eyebrow={hasPerformance ? "Performance dossier" : "Exploration dossier"} title="Selected team context" description={hasPerformance ? "Ce dossier réunit outcome context et structure. L'interprétation reste volontairement prudente." : "Ce dossier réunit novelty, stabilité et fiabilité pour expliquer pourquoi une équipe mérite inspection."}>
        <div className="toolbar toolbar--dossier"><label>Team<select value={selectedTeam?.team ?? ""} onChange={(event) => setSelectedTeamName(event.target.value)}>{enrichedTeams.map((team) => <option key={team.team} value={team.team}>{team.team}</option>)}</select></label><span className="toolbar-note">{hasPerformance ? "No causal interpretation is made from this page." : "Structural exploration only: no outcome claim."}</span></div>
        {selectedTeam && <article className="team-dossier performance-dossier-card"><div className="team-dossier__header"><div><span className="eyebrow">{hasPerformance ? "Selected performance context" : "Selected exploration context"}</span><h2>{formatValue(selectedTeam.team)}</h2><p>{selectedProfile?.interpretation}</p></div><Badge variant={selectedProfile?.variant}>{selectedProfile?.label}</Badge></div><div className="team-dossier__metrics"><MetricCard label={hasPerformance ? "Observed winrate" : "Exploration score"} value={hasPerformance && selectedTeam.performanceSignal ? formatPercent(selectedTeam.performanceSignal.winrate) : formatPercent(structuralExplorationScore(selectedTeam))} helper={hasPerformance && selectedTeam.performanceSignal ? `Source: ${selectedTeam.performanceSignal.source}` : "Not performance"} /><MetricCard label="Composition novelty" value={formatPercent(selectedTeam.metaDeviation?.uniquenessScore)} helper="Map-aware shell rarity" /><MetricCard label="Composition stability" value={formatPercent(selectedTeam.composition_stability_score)} helper="Internal repetition" /><MetricCard label="Rare-shell share" value={formatPercent(selectedTeam.metaDeviation?.rareShellShare)} helper="Share of uncommon map-aware shells" /></div><div className="dossier-note-grid"><p><strong>Reading.</strong> {selectedProfile?.interpretation}</p><p><strong>Caution.</strong> {selectedProfile?.caution}</p></div>{selectedTeam.metaDeviation?.representativeRareShells?.length > 0 && <div className="rare-shell-list"><h3>Representative rare shells</h3>{selectedTeam.metaDeviation.representativeRareShells.map((shell) => <div key={`${shell.map}-${shell.agents}`} className="rare-shell-row"><strong>{shell.agents}</strong><span>{shell.map} · {shell.uses} use(s) · novelty {formatPercent(shell.novelty)}</span></div>)}</div>}</article>}
      </Section>
      <Section eyebrow="Teams to inspect" title={hasPerformance ? "High-context structural cases" : "Priority structural cases"} description={hasPerformance ? "Ces cartes ne listent pas les meilleures équipes. Elles listent les cas où outcome context et structure créent une piste d'analyse." : "Ces cartes ne listent pas les meilleures équipes. Elles listent les cas structurellement intéressants à inspecter en premier."}>
        <div className="entity-grid">{(hasPerformance ? (offMetaHighContextTeams.length ? offMetaHighContextTeams : highContextTeams) : priorityExplorationTeams).slice(0, 3).map((team) => <PerformanceTeamCard key={team.team} team={team} onSelectTeam={selectTeamAndOpen} mode={hasPerformance ? "performance" : "exploration"} />)}</div>
        {!hasPerformance && priorityExplorationTeams.length === 0 && <StatusBanner type="info" message="No strong structural exploration case was detected with the current thresholds." />}
      </Section>
    </>
  );
}

function ModelingPage({ agents, teams, maps, compositions, pairs }) {
  const globalAgents = agents.filter((row) => row.map === "All Maps");
  const agentRows = globalAgents.length ? globalAgents : agents;

  return (
    <>
      <Section
        eyebrow="Modeling outputs"
        title="Modélisations analytiques"
        description="Vue opérationnelle des modèles générés : scores, distributions, signaux forts, signaux faibles et limites méthodologiques."
      >
        <div className="modeling-grid">
          <MiniBarChart
            rows={agentRows}
            labelKey="agent"
            valueKey="meta_presence_score"
            title="Top agents — meta presence score"
          />

          <MiniBarChart
            rows={teams}
            labelKey="team"
            valueKey="tactical_profile_score"
            title="Top teams — tactical profile score"
          />

          <MiniBarChart
            rows={maps}
            labelKey="team"
            valueKey="map_identity_score"
            title="Top team map identities"
          />

          <MiniBarChart
            rows={pairs}
            labelKey="agent_a"
            valueKey="synergy_lift"
            title="Top agent pairs — synergy lift"
            formatter={formatValue}
          />
        </div>
      </Section>

      <Section
        eyebrow="Model diagnostics"
        title="Distribution des labels"
        description="Ces graphiques montrent comment les modèles classent les signaux : méta globale, spécialistes map, profils stables, signaux faibles, etc."
      >
        <div className="modeling-grid">
          <LabelDistribution
            rows={agents}
            labelKey="agent_meta_label"
            title="Agent meta labels"
          />

          <LabelDistribution
            rows={teams}
            labelKey="tactical_profile_label"
            title="Team tactical labels"
          />

          <LabelDistribution
            rows={maps}
            labelKey="identity_label"
            title="Map identity labels"
          />

          <LabelDistribution
            rows={pairs}
            labelKey="pair_pattern_label"
            title="Agent pair labels"
          />
        </div>
      </Section>

      <Section
        eyebrow="Model tables"
        title="Tables de modélisation"
        description="Sorties principales du pipeline de modélisation v2."
      >
        <div className="two-col">
          <DataTable
            rows={topBy(agentRows, "meta_presence_score", 12)}
            columns={[
              { key: "agent", label: "Agent" },
              { key: "map", label: "Map" },
              { key: "meta_presence_score", label: "Presence", render: formatPercent },
              { key: "map_dependence_score", label: "Map dep." },
              { key: "sample_reliability_score", label: "Reliability", render: formatPercent },
              { key: "agent_meta_label", label: "Label" },
            ]}
          />

          <DataTable
            rows={topBy(teams, "tactical_profile_score", 12)}
            columns={[
              { key: "team", label: "Team" },
              { key: "tactical_profile_score", label: "Score", render: formatPercent },
              { key: "composition_stability_score", label: "Stability", render: formatPercent },
              { key: "agent_core_score", label: "Core", render: formatPercent },
              { key: "tactical_profile_label", label: "Label" },
            ]}
          />
        </div>
      </Section>
    </>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [agents, setAgents] = useState([]);
  const [agentGlobalMeta, setAgentGlobalMeta] = useState([]);
  const [teams, setTeams] = useState([]);
  const [maps, setMaps] = useState([]);
  const [comps, setComps] = useState([]);
  const [pairs, setPairs] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const responses = await Promise.all([
          fetch(`${API_BASE}/tables/agent-global-meta`),
          fetch(`${API_BASE}/tables/agent-meta-presence`),
          fetch(`${API_BASE}/tables/team-tactical-profiles`),
          fetch(`${API_BASE}/tables/team-map-identity`),
          fetch(`${API_BASE}/tables/composition-patterns`),
          fetch(`${API_BASE}/tables/agent-pair-patterns`),
          Promise.resolve({ ok: true, url: "local:team-performance-context", json: async () => ({ rows: [] }) }),
          fetch(`${API_BASE}/insights`),
        ]);

        const failed = responses.find((response) => !response.ok);
        if (failed) throw new Error(`HTTP ${failed.status} on ${failed.url}`);

        const [
  agentGlobalMetaPayload,
  agentsPayload,
  teamsPayload,
  mapsPayload,
  compsPayload,
  pairsPayload,
  performancePayload,
  insightsPayload,
] = await Promise.all(responses.map((response) => response.json()));

        setAgents(asRows(agentsPayload));
        setAgentGlobalMeta(asRows(agentGlobalMetaPayload));
        setTeams(asRows(teamsPayload));
        setMaps(asRows(mapsPayload));
        setComps(asRows(compsPayload));
        setPairs(asRows(pairsPayload));
        setPerformance(asRows(performancePayload));
        setInsights(insightsPayload && typeof insightsPayload === "object" ? insightsPayload : null);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "agents", label: "Agents" },
    { id: "teams", label: "Teams" },
    { id: "performance", label: "Performance" },
    { id: "compositions", label: "Compositions" },
    { id: "insights", label: "Insights" },
    { id: "modeling", label: "Modélisation" },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">V</span>
          <div>
            <strong>VLR Analytics Pro</strong>
            <small>Modeling Layer v2</small>
          </div>
        </div>

        <nav className="nav-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "active" : ""}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <header className="hero">
          <p className="eyebrow">Valorant / VLR tactical analytics</p>
          <h1>Presence, stability and tactical readability dashboard</h1>
          <p>
            Analyse déterministe des agents, compositions, équipes et maps. Les scores mesurent des signaux observables,
            pas la force compétitive ni une probabilité de victoire.
          </p>
        </header>

        {loading && <StatusBanner type="loading" message="Loading dashboard data..." />}
        {error && <StatusBanner type="error" message={`API connection problem: ${error}`} />}

        {!loading && !error && (
          <>
            {activeTab === "overview" && (
            <OverviewPage
  agentGlobalMeta={agentGlobalMeta}
  teams={teams}
  maps={maps}
  compositions={comps}
  pairs={pairs}
  insights={insights}
/>
            )}
            {activeTab === "agents" && <AgentsPage agents={agents} />}
            {activeTab === "teams" && <TeamsPage teams={teams} maps={maps} compositions={comps} />}
            {activeTab === "performance" && <PerformanceContextPage teams={teams} compositions={comps} performance={performance} />}
            {activeTab === "compositions" && <CompositionsPage compositions={comps} pairs={pairs} />}
            {activeTab === "insights" && <InsightsPage insights={insights} />}
            {activeTab === "modeling" && (
  <ModelingPage
    agents={agents}
    teams={teams}
    maps={maps}
    compositions={comps}
    pairs={pairs}
  />
)}
          </>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);