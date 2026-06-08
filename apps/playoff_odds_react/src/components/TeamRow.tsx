import type { TeamViewModel } from "../lib/types";
import { decimal } from "../lib/format";
import { ProbabilityBar } from "./ProbabilityBar";
import { StatusBadge } from "./StatusBadge";
import { PositionMini } from "./PositionMini";

interface Props {
  team: TeamViewModel;
  index: number;
  qualificationSlots: number;
  onClick: () => void;
}

export function TeamRow({ team, index, qualificationSlots, onClick }: Props) {
  const volatility = team.worstRankSeen - team.bestRankSeen;

  return (
    <button className="team-row team-row-button" onClick={onClick} type="button">
      <div className="seed-cell">{index + 1}</div>
      <div className="team-cell">
        <div className="team-name">{team.team}</div>
        <div className="team-sub">
          Best {team.bestRankSeen} · Worst {team.worstRankSeen} · Volatility {volatility}
        </div>
      </div>
      <div className="prob-cell">
        <ProbabilityBar value={team.qualifyProb} tone={team.tone} />
      </div>
      <div className="status-cell">
        <StatusBadge label={team.status} tone={team.tone} />
      </div>
      <div className="exp-cell">{decimal(team.expectedRankDerived)}</div>
      <div className="dist-cell">
        <PositionMini positions={team.positions} qualificationSlots={qualificationSlots} />
      </div>
    </button>
  );
}
