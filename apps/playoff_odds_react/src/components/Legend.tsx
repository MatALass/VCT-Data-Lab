const items = [
  ["tone-lock", "Lock"],
  ["tone-veryLikely", "Very likely"],
  ["tone-favourable", "Favourable"],
  ["tone-bubble", "Bubble"],
  ["tone-outsider", "Outsider"],
  ["tone-nearlyOut", "Nearly out"],
] as const;

export function Legend() {
  return (
    <div className="legend-row">
      {items.map(([tone, label]) => (
        <div className="legend-item" key={tone}>
          <span className={`legend-swatch ${tone}`} />
          {label}
        </div>
      ))}
    </div>
  );
}
