interface Props {
  label: string;
  value: string;
  hint?: string;
}

export function MetricCard({ label, value, hint }: Props) {
  return (
    <article className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {hint ? <div className="metric-hint">{hint}</div> : null}
    </article>
  );
}
