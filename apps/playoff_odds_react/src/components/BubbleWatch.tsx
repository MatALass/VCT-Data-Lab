import type { TeamViewModel } from "../lib/types";
import { pct, decimal } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

interface Props {
  teams: TeamViewModel[];
}

export function BubbleWatch({ teams }: Props) {
  return (
    <section className="side-panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Pressure zone</div>
          <h3>Bubble watch</h3>
        </div>
        <div className="panel-meta">Cutline stress</div>
      </div>

      <div className="bubble-list">
        {teams.length ? (
          teams.map((team) => (
            <article className="bubble-card" key={`${team.group}-${team.team}`}>
              <div className="bubble-top">
                <div>
                  <div className="bubble-team">{team.team}</div>
                  <div className="bubble-group">{team.group}</div>
                </div>
                <StatusBadge label={team.status} tone={team.tone} />
              </div>
              <div className="bubble-prob">{pct(team.qualifyProb)}</div>
              <div className="bubble-meta">
                Expected rank {decimal(team.expectedRankDerived)} · Best {team.bestRankSeen} · Worst {team.worstRankSeen}
              </div>
            </article>
          ))
        ) : (
          <div className="side-empty">No true bubble teams are currently detected around the qualification line.</div>
        )}
      </div>
    </section>
  );
}
