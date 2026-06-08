interface Props {
  insights: string[];
}

export function InsightsPanel({ insights }: Props) {
  return (
    <section className="side-panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Narrative engine</div>
          <h3>Auto insights</h3>
        </div>
        <div className="panel-meta">Simulation reads</div>
      </div>
      {insights.length ? (
        <ul className="insights-list">
          {insights.map((item, idx) => (
            <li key={`${idx}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <div className="side-empty">No generated insights were found in the dataset.</div>
      )}
    </section>
  );
}
