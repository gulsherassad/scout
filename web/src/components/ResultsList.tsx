import { Link } from "react-router-dom";
import type { SimilarResult } from "../api";
import { formatExplanation, formatValue, roleClass } from "../lib/format";

/** Ranked similar players: style similarity next to output level (npxG per 90). */
export function ResultsList({ results }: { results: SimilarResult[] }) {
  if (results.length === 0) {
    return <p className="empty">No players meet these filters. Loosen them to see more.</p>;
  }
  return (
    <ol className="results">
      <li className="results-head" aria-hidden="true">
        <span>#</span>
        <span>Player</span>
        <span>Pos</span>
        <span>Similarity</span>
        <span title="Non-penalty expected goals per 90: output level, which similarity ignores">npxG/90</span>
      </li>
      {results.map((r, i) => {
        const why = formatExplanation(r.explanation, r.name);
        return (
          <li key={r.id} className={r.active === false ? "result inactive" : "result"}>
            <span className="rank num">{i + 1}</span>
            <div className="result-main">
              <Link to={`/player/${r.id}`} className="result-name">
                {r.name}
              </Link>
              <span className="result-team">
                {r.team} · {r.age ?? "—"} y · {formatValue(r.market_value_m)}
                {r.active === false && <span className="badge badge-inactive">Inactive</span>}
              </span>
              <p className="why">
                <span className="why-shared">{why.shared}.</span> <span className="why-diff">{why.difference}.</span>
              </p>
            </div>
            <span className="pos">
              <span className={`role-dot ${roleClass(r.position)}`} aria-hidden="true" />
              {r.position}
            </span>
            <span className="sim">
              <span className="sim-bar" aria-hidden="true">
                <span style={{ width: `${Math.max(0, r.similarity) * 100}%` }} />
              </span>
              <span className="num">{r.similarity.toFixed(2)}</span>
            </span>
            <span className="num npxg">{r.npxg_per90 === null ? "—" : r.npxg_per90.toFixed(2)}</span>
          </li>
        );
      })}
    </ol>
  );
}
