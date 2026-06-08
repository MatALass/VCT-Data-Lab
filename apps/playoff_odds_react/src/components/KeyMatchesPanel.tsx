import type { KeyMatchItem } from "../lib/types";
import { smartPct } from "../lib/format";

interface Props {
  matches: KeyMatchItem[];
}

export function KeyMatchesPanel({ matches }: Props) {
  return (
    <section className="side-panel">
      <div className="panel-head">
        <div>
          <div className="panel-kicker">Leverage board</div>
          <h3>Key matches</h3>
        </div>
        <div className="panel-meta">Top swing spots</div>
      </div>

      <div className="side-list">
        {matches.length ? (
          matches.map((item) => (
            <article className="key-match-card" key={`${item.group}-${item.match}`}>
              <div className="key-match-top">
                <span className="key-match-group">{item.group}</span>
                <span className="key-match-impact">Impact {smartPct(item.importance)}</span>
              </div>
              <div className="key-match-title">{item.match}</div>
              <div className="key-match-headline">{item.headline}</div>
              <div className="key-match-bar" aria-hidden="true">
                <div className="key-match-fill" style={{ width: `${item.importance * 100}%` }} />
              </div>
            </article>
          ))
        ) : (
          <div className="side-empty">No leverage matches are available in the current dataset.</div>
        )}
      </div>
    </section>
  );
}
