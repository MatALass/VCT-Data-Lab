import type { TeamViewModel } from "../lib/types";
import { pct } from "../lib/format";

interface Props {
  value: number;
  tone: TeamViewModel["tone"];
}

export function ProbabilityBar({ value, tone }: Props) {
  return (
    <div className="prob-block" aria-label={`Qualification probability ${pct(value)}`}>
      <div className="prob-topline">
        <span className="prob-label">Qualification odds</span>
        <strong className="prob-value">{pct(value)}</strong>
      </div>
      <div className="prob-rail" aria-hidden="true">
        <div className={`prob-fill tone-${tone}`} style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}
