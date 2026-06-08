interface Props {
  title: string;
  subtitle: string;
  items: Array<{ label: string; value: string }>;
}

export function SideList({ title, subtitle, items }: Props) {
  return (
    <section className="side-panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Standings pulse</div>
          <h3>{title}</h3>
        </div>
        <div className="panel-meta">{items.length} teams</div>
      </div>

      {items.length ? (
        <div className="side-list">
          {items.map((item) => (
            <article className="side-row" key={`${item.label}-${item.value}`}>
              <div className="side-row-top">
                <span className="side-row-label">{item.label}</span>
                <strong>{item.value}</strong>
              </div>
              <div className="side-row-sub">{subtitle}</div>
            </article>
          ))}
        </div>
      ) : (
        <div className="side-empty">No teams match this bucket in the current simulation snapshot.</div>
      )}
    </section>
  );
}
