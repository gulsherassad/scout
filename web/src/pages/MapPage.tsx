import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { MapPoint, MapResponse } from "../api";
import { ErrorState, Loading } from "../components/Status";
import { ROLES, role, roleClass, roleCss } from "../lib/format";
import { useApi } from "../lib/useApi";

const W = 1000;
const H = 640;
const PAD = 24;

/** All attackers on the first two principal components of their style profiles. */
export function MapPage() {
  const { data, error, loading, reload } = useApi<MapResponse>("/map");
  const [hover, setHover] = useState<MapPoint | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const navigate = useNavigate();

  const scale = useMemo(() => {
    if (!data) return null;
    const xs = data.players.map((p) => p.x);
    const ys = data.players.map((p) => p.y);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    return {
      x: (v: number) => PAD + ((v - x0) / (x1 - x0 || 1)) * (W - 2 * PAD),
      y: (v: number) => H - PAD - ((v - y0) / (y1 - y0 || 1)) * (H - 2 * PAD),
    };
  }, [data]);

  if (error) return <div className="page"><ErrorState message={error} onRetry={reload} /></div>;
  if (loading || !data || !scale) return <div className="page"><Loading label="Drawing the map" /></div>;

  const toggle = (r: string) => {
    const next = new Set(hidden);
    if (next.has(r)) next.delete(r);
    else next.add(r);
    setHidden(next);
  };
  // Active players drawn last so they sit on top of faded inactive ones
  const points = [...data.players].sort((a, b) => Number(a.active) - Number(b.active));
  const [v1, v2] = data.explained_variance.map((v) => Math.round(v * 100));

  return (
    <div className="page">
      <header className="map-header">
        <h1>Style map</h1>
        <p className="muted">
          Every attacker in the pool, placed so that similar styles sit close together (the two main directions of variation
          in the profiles: {v1}% and {v2}% of it). Faded points have no league appearance this season. Click a player to open
          their profile.
        </p>
        <div className="legend" role="group" aria-label="Show or hide roles">
          {ROLES.map((r) => (
            <button key={r} type="button" className={hidden.has(r) ? "legend-item off" : "legend-item"} aria-pressed={!hidden.has(r)} onClick={() => toggle(r)}>
              <span className={`role-dot ${roleCss(r)}`} />
              {r}
            </button>
          ))}
        </div>
      </header>
      <div className="map-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="map" role="img" aria-label="Scatter plot of attackers by style">
          <line x1={W / 2} y1={PAD} x2={W / 2} y2={H - PAD} className="map-axis" />
          <line x1={PAD} y1={H / 2} x2={W - PAD} y2={H / 2} className="map-axis" />
          {points
            .filter((p) => !hidden.has(role(p.position)))
            .map((p) => (
              <circle
                key={p.id}
                cx={scale.x(p.x)}
                cy={scale.y(p.y)}
                r={hover?.id === p.id ? 9 : 5.5}
                className={`map-point ${roleClass(p.position)}${p.active === false ? " faded" : ""}`}
                tabIndex={0}
                role="link"
                aria-label={`${p.name}, ${p.team}`}
                onMouseEnter={() => setHover(p)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(p)}
                onBlur={() => setHover(null)}
                onClick={() => navigate(`/player/${p.id}`)}
                onKeyDown={(e) => e.key === "Enter" && navigate(`/player/${p.id}`)}
              />
            ))}
        </svg>
        {hover && (
          <div className="map-tip" style={{ left: `${(scale.x(hover.x) / W) * 100}%`, top: `${(scale.y(hover.y) / H) * 100}%` }}>
            <strong>{hover.name}</strong>
            <span>
              {hover.team} · {hover.position}
              {hover.active === false && " · inactive"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
