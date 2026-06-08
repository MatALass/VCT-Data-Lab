import type { TeamViewModel } from "../lib/types";

interface Props {
  label: string;
  tone: TeamViewModel["tone"];
}

export function StatusBadge({ label, tone }: Props) {
  return (
    <span className={`status-badge tone-${tone}`}>
      <span className="status-badge-dot" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
