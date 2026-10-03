import type { Feature } from "../api";

const GROUPS: { title: string; match: (f: string) => boolean }[] = [
  { title: "Output and involvement", match: (f) => !f.startsWith("last_action_") && !f.startsWith("shot_type_") },
  { title: "How shots are created", match: (f) => f.startsWith("last_action_") },
  { title: "Body part", match: (f) => f.startsWith("shot_type_") },
];

function formatRaw(f: Feature): string {
  if (f.value === null) return "—";
  if (f.feature.startsWith("last_action_") || f.feature.startsWith("shot_type_") || f.feature === "buildup_share_of_chain") {
    return `${Math.round(f.value * 100)}%`;
  }
  return f.value.toFixed(2);
}

/** Each style feature as a percentile against all attackers in the pool. */
export function PercentileBars({ features }: { features: Feature[] }) {
  return (
    <div className="percentiles">
      {GROUPS.map((g) => {
        const rows = features.filter((f) => g.match(f.feature));
        if (!rows.length) return null;
        return (
          <section key={g.title}>
            <h3>{g.title}</h3>
            <ul>
              {rows.map((f) => (
                <li key={f.feature}>
                  <span className="pct-label">{f.label.replace(/^share of /, "")}</span>
                  <span className="pct-bar" aria-hidden="true">
                    <span style={{ width: `${f.percentile ?? 0}%` }} className={(f.percentile ?? 0) >= 80 ? "hi" : ""} />
                    <i style={{ left: "50%" }} />
                  </span>
                  <span className="num pct-value" title={`raw value ${formatRaw(f)}`}>
                    {f.percentile === null ? "—" : Math.round(f.percentile)}
                  </span>
                  <span className="pct-raw muted">{formatRaw(f)}</span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      <p className="muted small">Percentile among all attackers in the pool; the tick marks the median. Shares are of the player's shots (no penalties, own goals or direct free kicks).</p>
    </div>
  );
}
