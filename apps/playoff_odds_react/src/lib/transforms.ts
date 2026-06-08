import type { Dataset, TeamData, TeamViewModel } from "./types";

export function expectedRank(positions: Record<string, number>): number {
  return Object.entries(positions).reduce((acc, [key, value]) => {
    const rank = Number(key.replace("P", ""));
    return acc + rank * value;
  }, 0);
}

function orderedPositions(positions: Record<string, number>): Array<[string, number]> {
  return Object.entries(positions).sort(([a], [b]) => Number(a.replace("P", "")) - Number(b.replace("P", "")));
}

export function derivedBestRank(positions: Record<string, number>, threshold = 1e-9): number {
  const found = orderedPositions(positions).find(([, value]) => value > threshold);
  return found ? Number(found[0].replace("P", "")) : 0;
}

export function derivedWorstRank(positions: Record<string, number>, threshold = 1e-9): number {
  const found = [...orderedPositions(positions)].reverse().find(([, value]) => value > threshold);
  return found ? Number(found[0].replace("P", "")) : 0;
}

export function tone(prob: number): TeamViewModel["tone"] {
  if (prob >= 0.99) return "lock";
  if (prob >= 0.8) return "veryLikely";
  if (prob >= 0.6) return "favourable";
  if (prob >= 0.4) return "bubble";
  if (prob >= 0.1) return "outsider";
  return "nearlyOut";
}

export function toneLabel(prob: number): string {
  const t = tone(prob);
  switch (t) {
    case "lock": return "Lock";
    case "veryLikely": return "Very likely";
    case "favourable": return "Favourable";
    case "bubble": return "Bubble";
    case "outsider": return "Outsider";
    case "nearlyOut": return "Nearly out";
  }
}

export function teamVM(team: TeamData, group: string): TeamViewModel {
  return {
    ...team,
    group,
    bestRankSeen: derivedBestRank(team.positions),
    worstRankSeen: derivedWorstRank(team.positions),
    expectedRankDerived: team.expectedRank ?? expectedRank(team.positions),
    status: toneLabel(team.qualifyProb),
    tone: tone(team.qualifyProb),
  };
}

export function allTeams(dataset: Dataset): TeamViewModel[] {
  return dataset.groups.flatMap((group) => group.teams.map((team) => teamVM(team, group.name)));
}

export function bubbleTeams(dataset: Dataset): TeamViewModel[] {
  return allTeams(dataset)
    .filter((team) => team.qualifyProb >= 0.25 && team.qualifyProb <= 0.75)
    .sort((a, b) => Math.abs(a.qualifyProb - 0.5) - Math.abs(b.qualifyProb - 0.5));
}

export function locks(dataset: Dataset): TeamViewModel[] {
  return allTeams(dataset).filter((team) => team.qualifyProb >= 0.99).sort((a, b) => b.qualifyProb - a.qualifyProb);
}

export function nearlyOut(dataset: Dataset): TeamViewModel[] {
  return allTeams(dataset).filter((team) => team.qualifyProb <= 0.1).sort((a, b) => a.qualifyProb - b.qualifyProb);
}

export function sortedGroupTeams(dataset: Dataset, groupName: string): TeamViewModel[] {
  const group = dataset.groups.find((g) => g.name === groupName);
  if (!group) return [];
  return group.teams
    .map((team) => teamVM(team, group.name))
    .sort((a, b) => {
      if (b.qualifyProb !== a.qualifyProb) return b.qualifyProb - a.qualifyProb;
      return a.expectedRankDerived - b.expectedRankDerived;
    });
}

export function cutoffGap(dataset: Dataset): { group: string; gap: number; fourthTeam: string; fifthTeam: string } | null {
  const candidates = dataset.groups
    .map((group) => {
      const teams = sortedGroupTeams(dataset, group.name);
      const slots = dataset.qualificationSlots;
      const fourth = teams[slots - 1];
      const fifth = teams[slots];
      if (!fourth || !fifth) return null;
      return {
        group: group.name,
        gap: fourth.qualifyProb - fifth.qualifyProb,
        fourthTeam: fourth.team,
        fifthTeam: fifth.team,
      };
    })
    .filter(Boolean) as Array<{ group: string; gap: number; fourthTeam: string; fifthTeam: string }>;

  if (candidates.length === 0) return null;
  return candidates.sort((a, b) => a.gap - b.gap)[0];
}

export function closestToFifty(dataset: Dataset): TeamViewModel | null {
  const teams = allTeams(dataset);
  if (teams.length === 0) return null;
  return [...teams].sort((a, b) => Math.abs(a.qualifyProb - 0.5) - Math.abs(b.qualifyProb - 0.5))[0];
}

export function contestedTeamsCount(dataset: Dataset): number {
  return allTeams(dataset).filter((team) => team.qualifyProb >= 0.25 && team.qualifyProb <= 0.75).length;
}
