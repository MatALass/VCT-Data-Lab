import type { Dataset, TeamViewModel } from "../lib/types";
import { sortedGroupTeams } from "../lib/transforms";
import { TeamRow } from "./TeamRow";

interface Props {
  dataset: Dataset;
  groupName: string;
  onSelectTeam: (team: TeamViewModel) => void;
}

export function GroupPanel({ dataset, groupName, onSelectTeam }: Props) {
  const teams = sortedGroupTeams(dataset, groupName);

  return (
    <section className="group-panel" data-group-mark={groupName.charAt(0)}>
      <div className="group-head">
        <div>
          <div className="group-kicker">Group</div>
          <h3>{groupName}</h3>
        </div>
        <div className="group-note">
          <span className="legend-dot qualified" /> Top {dataset.qualificationSlots} advance
        </div>
      </div>

      <div className="group-table-head">
        <span>Seed</span>
        <span>Team</span>
        <span>Qualification</span>
        <span>Status</span>
        <span>Exp. rank</span>
        <span>Finish distribution</span>
      </div>

      <div className="group-body">
        {teams.map((team, index) => (
          <TeamRow
            key={team.team}
            team={team}
            index={index}
            qualificationSlots={dataset.qualificationSlots}
            onClick={() => onSelectTeam(team)}
          />
        ))}
      </div>
    </section>
  );
}
