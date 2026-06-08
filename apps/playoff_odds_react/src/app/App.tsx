import { useMemo, useState } from "react";
import rawDataset from "../../../../data/playoff_odds/vct-emea-2026.json";
import { BubbleWatch } from "../components/BubbleWatch";
import { GroupPanel } from "../components/GroupPanel";
import { InsightsPanel } from "../components/InsightsPanel";
import { KeyMatchesPanel } from "../components/KeyMatchesPanel";
import { Legend } from "../components/Legend";
import { MetricCard } from "../components/MetricCard";
import { ScenarioDrawer } from "../components/ScenarioDrawer";
import { SectionTitle } from "../components/SectionTitle";
import { SideList } from "../components/SideList";
import { pct } from "../lib/format";
import type { Dataset, TeamViewModel } from "../lib/types";
import { bubbleTeams, closestToFifty, contestedTeamsCount, cutoffGap, locks, nearlyOut } from "../lib/transforms";

const dataset = rawDataset as Dataset;

function renderTieBreakers(notes?: Dataset["notes"]) {
  const tieBreakers = notes?.officialTieBreakers ?? notes?.tiebreakApproximation ?? [];
  return tieBreakers.length ? tieBreakers.join(" → ") : "Not available in dataset notes";
}

export default function App() {
  const [selectedTeam, setSelectedTeam] = useState<TeamViewModel | null>(null);

  const bubble = useMemo(() => bubbleTeams(dataset), []);
  const locked = useMemo(() => locks(dataset), []);
  const out = useMemo(() => nearlyOut(dataset), []);
  const closest = useMemo(() => closestToFifty(dataset), []);
  const cutoff = useMemo(() => cutoffGap(dataset), []);
  const contestedCount = useMemo(() => contestedTeamsCount(dataset), []);
  const tieBreakerText = renderTieBreakers(dataset.notes);

  return (
    <div className="app-shell">
      <main className="page">
        <header className="hero">
          <div className="hero-copy">
            <div className="eyebrow">Playoff analytics</div>
            <h1>
              {dataset.league} <span>{dataset.season}</span>
            </h1>
            <p>
              Qualification odds, pressure around the cutline, and scenario extremes in a cleaner dashboard built for fast reading.
            </p>
            <Legend />
            <div className="hero-footnote">
              Select any team row to inspect best and worst observed simulation outcomes.
            </div>
          </div>

          <div className="hero-metrics">
            <MetricCard
              label="Simulation sample"
              value={dataset.notes?.sampleSize ? dataset.notes.sampleSize.toLocaleString() : "N/A"}
              hint="Main Monte Carlo batch powering qualification probabilities."
            />
            <MetricCard
              label="Conditional sample"
              value={dataset.notes?.conditionalSampleSize ? dataset.notes.conditionalSampleSize.toLocaleString() : "N/A"}
              hint="Used to estimate match leverage and swing scenarios."
            />
            <MetricCard
              label="Contested teams"
              value={String(contestedCount)}
              hint="Teams currently sitting between 25% and 75% odds."
            />
            <MetricCard
              label="Closest to 50%"
              value={closest ? `${closest.team} · ${pct(closest.qualifyProb)}` : "N/A"}
              hint="Most balanced qualification case in the current snapshot."
            />
          </div>
        </header>

        <section className="info-strip">
          <div className="info-pill">
            <div className="eyebrow">Format</div>
            <strong>Top {dataset.qualificationSlots} qualify</strong>
          </div>
          <div className="info-pill">
            <div className="eyebrow">Tightest cutline</div>
            <strong>
              {cutoff ? `${cutoff.group} · ${cutoff.fourthTeam} vs ${cutoff.fifthTeam}` : "No cutline found"}
            </strong>
          </div>
          <div className="info-pill">
            <div className="eyebrow">What-if mode</div>
            <strong>{dataset.notes?.whatIfMode ?? "Not specified"}</strong>
          </div>
          <div className="info-pill">
            <div className="eyebrow">Model</div>
            <strong>{dataset.notes?.modelType ?? "Standings + rules"}</strong>
          </div>
        </section>

        <section className="layout">
          <section className="main-col">
            <SectionTitle
              eyebrow="Qualification board"
              title="Odds by group"
              description="Compare each group with a lighter, more focused view of confidence, rank pressure, and finish distribution."
            />
            <div className="stack">
              {dataset.groups.map((group) => (
                <GroupPanel key={group.name} dataset={dataset} groupName={group.name} onSelectTeam={setSelectedTeam} />
              ))}
            </div>
          </section>

          <aside className="side-col">
            <KeyMatchesPanel matches={dataset.keyMatches ?? []} />
            <InsightsPanel insights={dataset.insights ?? []} />
            <SideList
              title="Locks"
              subtitle="Teams essentially secured in the current simulation landscape."
              items={locked.map((team) => ({ label: `${team.team} · ${team.group}`, value: pct(team.qualifyProb) }))}
            />
            <SideList
              title="Nearly out"
              subtitle="Long-shot teams with very little room for error from here."
              items={out.map((team) => ({ label: `${team.team} · ${team.group}`, value: pct(team.qualifyProb) }))}
            />
            <BubbleWatch teams={bubble} />
            <section className="side-panel">
              <div className="panel-head">
                <div>
                  <div className="panel-kicker">Method layer</div>
                  <h3>Model notes</h3>
                </div>
                <div className="panel-meta">Pipeline-backed</div>
              </div>
              <ul className="note-list">
                <li>JSON payload is generated by the Python simulation pipeline, not by hardcoded frontend transforms.</li>
                <li>Tie-break chain: {tieBreakerText}</li>
                <li>Scenario drawer exposes best and worst observed cases from the simulation sample.</li>
                <li>Key-match leverage comes from conditional simulation, not static heuristics.</li>
                <li>Console what-if editing updates the source config and regenerates the dataset.</li>
              </ul>
            </section>
          </aside>
        </section>
      </main>

      <ScenarioDrawer team={selectedTeam} onClose={() => setSelectedTeam(null)} />
    </div>
  );
}
