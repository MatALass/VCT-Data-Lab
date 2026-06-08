import { smartPct } from "../lib/format";

interface Props {
  positions: Record<string, number>;
  qualificationSlots: number;
}

function intensityClass(value: number): string {
  const pctValue = value * 100;
  if (value === 0) return "zero";
  if (pctValue >= 50) return "strong";
  if (pctValue >= 10) return "medium";
  if (pctValue >= 1) return "weak";
  return "trace";
}

export function PositionMini({ positions, qualificationSlots }: Props) {
  const ordered = Object.entries(positions).sort(([a], [b]) => Number(a.slice(1)) - Number(b.slice(1)));

  return (
    <div className="position-profile">
      <div className="mini-chart" aria-hidden="true">
        {ordered.map(([label, value], idx) => {
          const qualified = idx + 1 <= qualificationSlots;
          return (
            <div className="mini-col" key={label}>
              <div
                className={`mini-bar ${qualified ? "qualified" : "non-qualified"} ${intensityClass(value)}`}
                style={{ height: `${Math.max(value > 0 ? 10 : 6, value * 100)}%` }}
                title={`${label}: ${smartPct(value)}`}
              />
            </div>
          );
        })}
      </div>

      <div className="position-breakdown">
        {ordered.map(([label, value], idx) => {
          const qualified = idx + 1 <= qualificationSlots;
          return (
            <div
              key={`detail-${label}`}
              className={`position-pill ${qualified ? "qualified" : "non-qualified"} ${intensityClass(value)}`}
              title={`${label}: ${smartPct(value)}`}
            >
              <span>{label}</span>
              <strong>{smartPct(value)}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}
