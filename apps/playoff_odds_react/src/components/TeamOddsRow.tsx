import type { TeamViewModel } from "../lib/types";
import { decimal } from "../lib/format";
import { ProbabilityBar } from "./ProbabilityBar";
import { StatusBadge } from "./StatusBadge";
import { PositionDistributionMini } from "./PositionDistributionMini";

interface TeamOddsRowProps {
  index: number;
  team: TeamViewModel;
  qualificationSlots: number;
}

export function TeamOddsRow({ index, team, qualificationSlots }: TeamOddsRowProps) {
  return (
    <div className="team-row">
      <div className="seed-cell">{index + 1}</div>
      <div className="team-cell">
        <div className="team-name">{team.team}</div>
        <div className="team-sub">Best {team.bestRankSeen} · Worst {team.worstRankSeen}</div>
      </div>
      <div className="prob-cell">
        <ProbabilityBar value={team.qualifyProb} tone={team.tone} />
      </div>
      <div className="status-cell">
        <StatusBadge label={team.status} tone={team.tone} />
      </div>
      <div className="exp-cell">{decimal(team.expectedRankDerived)}</div>
      <div className="dist-cell">
        <PositionDistributionMini positions={team.positions} qualificationSlots={qualificationSlots} />
      </div>
    </div>
  );
}
