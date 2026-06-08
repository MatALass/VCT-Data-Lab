import { smartPct } from "../lib/format";

interface PositionDistributionMiniProps {
  positions: Record<string, number>;
  qualificationSlots: number;
}

export function PositionDistributionMini({ positions, qualificationSlots }: PositionDistributionMiniProps) {
  const ordered = Object.entries(positions).sort(([a], [b]) => Number(a.replace("P", "")) - Number(b.replace("P", "")));

  return (
    <div className="position-profile">
      <div className="mini-chart" aria-hidden="true">
        {ordered.map(([label, value], index) => {
          const qualified = index + 1 <= qualificationSlots;
          const level = value >= 0.5 ? "strong" : value >= 0.1 ? "medium" : value > 0 ? "weak" : "zero";
          return (
            <div className="mini-col" key={label}>
              <div
                className={`mini-bar ${qualified ? "qualified" : "non-qualified"} ${level}`}
                style={{ height: `${Math.max(6, value * 100)}%` }}
                title={`${label}: ${smartPct(value)}`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
