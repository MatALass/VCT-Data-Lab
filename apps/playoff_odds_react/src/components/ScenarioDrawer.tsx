import { useMemo } from "react";
import type { FinalStandingRow, MatchResult, ScenarioCase, TeamViewModel } from "../lib/types";

interface Props {
  team: TeamViewModel | null;
  onClose: () => void;
}

function renderRecordBits(record?: ScenarioCase["finalRecord"]) {
  if (!record) return [];
  const bits: Array<[string, string | number]> = [];
  if (record.wins !== undefined && record.losses !== undefined) bits.push(["Record", `${record.wins}-${record.losses}`]);
  if (record.mapDiff !== undefined) bits.push(["Map diff", record.mapDiff]);
  if (record.roundDiff !== undefined) bits.push(["Round diff", record.roundDiff]);
  if (record.mapProfile) bits.push(["Map profile", record.mapProfile]);
  if (record.roundProfile) bits.push(["Round profile", record.roundProfile]);
  return bits;
}

function MatchList({ matches }: { matches: MatchResult[] }) {
  if (!matches.length) {
    return <div className="scenario-empty">No match path was bundled for this scenario.</div>;
  }

  return (
    <ul className="scenario-list">
      {matches.map((match, index) => (
        <li key={`${match.group}-${match.match}-${index}`}>
          <span>
            <strong>{match.match}</strong> <span className="scenario-group">{match.group}</span>
          </span>
          <span>{match.result ?? match.winner ?? "Outcome recorded"}</span>
        </li>
      ))}
    </ul>
  );
}

function StandingsTable({ rows }: { rows: FinalStandingRow[] }) {
  if (!rows.length) {
    return <div className="scenario-empty">No final standing table is attached to this scenario.</div>;
  }

  return (
    <div className="scenario-table">
      {rows.map((row) => {
        const meta = [
          row.wins !== undefined && row.losses !== undefined ? `${row.wins}-${row.losses}` : null,
          row.mapDiff !== undefined ? `MD ${row.mapDiff}` : null,
          row.roundDiff !== undefined ? `RD ${row.roundDiff}` : null,
        ]
          .filter(Boolean)
          .join(" · ");

        return (
          <div className="scenario-standing-row" key={`${row.rank}-${row.team}`}>
            <div className="scenario-standing-rank">{row.rank}</div>
            <div>
              <strong>{row.team}</strong>
              {meta ? <div className="scenario-standing-meta">{meta}</div> : null}
            </div>
            {row.qualifyProb !== undefined ? <div>{(row.qualifyProb * 100).toFixed(1)}%</div> : null}
          </div>
        );
      })}
    </div>
  );
}

function ScenarioSection({ title, scenario, kind }: { title: string; scenario?: ScenarioCase | null; kind: "best" | "worst" }) {
  if (!scenario) {
    return (
      <section className={`scenario-section ${kind}`}>
        <div className="scenario-kicker">{kind === "best" ? "Upside case" : "Danger case"}</div>
        <div className="scenario-title">{title}</div>
        <div className="scenario-empty">This dataset does not include an observed {kind} case for the selected team.</div>
      </section>
    );
  }

  const recordBits = renderRecordBits(scenario.finalRecord);

  return (
    <section className={`scenario-section ${kind}`}>
      <div className="scenario-kicker">{kind === "best" ? "Upside case" : "Danger case"}</div>
      <div className="scenario-title">{title}</div>
      <div className="scenario-rank">Final rank #{scenario.finalRank}</div>
      {scenario.note ? <p className="scenario-note">{scenario.note}</p> : null}

      <div className="scenario-grid">
        <div className="scenario-subpanel">
          <h4>Path summary</h4>
          {recordBits.length ? (
            <ul className="scenario-list">
              {recordBits.map(([label, value]) => (
                <li key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <div className="scenario-empty">No final record bundle is attached to this scenario.</div>
          )}
        </div>

        <div className="scenario-subpanel">
          <h4>Forced results</h4>
          <MatchList matches={scenario.matchResults ?? []} />
        </div>
      </div>

      <div className="scenario-subpanel" style={{ marginTop: 16 }}>
        <h4>Final standings</h4>
        <StandingsTable rows={scenario.finalStandings ?? []} />
      </div>
    </section>
  );
}

export function ScenarioDrawer({ team, onClose }: Props) {
  const open = Boolean(team);

  const title = useMemo(() => {
    if (!team) return "";
    return `${team.team} · ${team.group}`;
  }, [team]);

  return (
    <div className={`scenario-overlay ${open ? "open" : ""}`} onClick={onClose}>
      <aside className={`scenario-drawer ${open ? "open" : ""}`} onClick={(e) => e.stopPropagation()}>
        <div className="scenario-topbar">
          <div>
            <div className="eyebrow">Scenario explorer</div>
            <h2>{title}</h2>
          </div>
          <button type="button" className="scenario-close" onClick={onClose}>
            Close
          </button>
        </div>

        {team ? (
          <div className="scenario-content">
            <ScenarioSection title="Best observed case" scenario={team.scenarioExtremes?.bestCase} kind="best" />
            <ScenarioSection title="Worst observed case" scenario={team.scenarioExtremes?.worstCase} kind="worst" />
          </div>
        ) : null}
      </aside>
    </div>
  );
}
