import type { ZoneWeight, ZonesResponse } from "../api";

/** The attacking half seen from behind the attacker: goal at the top, their right on the right.
 * Each grid cell is shaded by Σ (player's weight on zone k) × (zone k's share of shots in the cell),
 * i.e. the player's shot map as the NMF zones describe it. */
export function ShotZonesPitch({ zones, weights }: { zones: ZonesResponse; weights: ZoneWeight[] }) {
  const { length, width } = zones.pitch;
  const half = length / 2;
  const w = new Map(weights.map((z) => [z.feature, z.weight ?? 0]));
  const nx = zones.x_edges.length - 1;
  const ny = zones.y_edges.length - 1;

  const heat: number[][] = Array.from({ length: nx }, (_, ix) =>
    Array.from({ length: ny }, (_, iy) => zones.zones.reduce((sum, z) => sum + (w.get(z.column) ?? 0) * z.grid[ix][iy], 0)),
  );
  const peak = Math.max(...heat.flat(), 1e-9);

  // Screen coordinates in metres: sx from the attacker's left touchline, sy from the goal line
  const sx = (y: number) => width - y;
  const sy = (x: number) => length - x;
  const box = { w: 40.32, d: 16.5 };
  const six = { w: 18.32, d: 5.5 };
  const arcDx = Math.sqrt(9.15 ** 2 - (box.d - 11) ** 2);

  return (
    <figure className="pitch-figure">
      <svg viewBox={`-2 -3 ${width + 4} ${half + 5}`} className="pitch" role="img" aria-label="Shot map by zone on the attacking half">
        <rect x={0} y={0} width={width} height={half} className="pitch-grass" />
        {heat.map((row, ix) =>
          row.map((v, iy) => (
            <rect
              key={`${ix}-${iy}`}
              x={sx(zones.y_edges[iy + 1])}
              y={sy(zones.x_edges[ix + 1])}
              width={zones.y_edges[iy + 1] - zones.y_edges[iy]}
              height={zones.x_edges[ix + 1] - zones.x_edges[ix]}
              className="heat"
              style={{ opacity: Math.pow(v / peak, 0.8) }}
            />
          )),
        )}
        <g className="pitch-lines">
          <rect x={0} y={0} width={width} height={half} />
          <rect x={(width - box.w) / 2} y={0} width={box.w} height={box.d} />
          <rect x={(width - six.w) / 2} y={0} width={six.w} height={six.d} />
          <rect x={(width - 7.32) / 2} y={-1.5} width={7.32} height={1.5} />
          <path d={`M ${width / 2 - arcDx} ${box.d} A 9.15 9.15 0 0 0 ${width / 2 + arcDx} ${box.d}`} />
          <path d={`M ${width / 2 - 9.15} ${half} A 9.15 9.15 0 0 1 ${width / 2 + 9.15} ${half}`} />
          <circle cx={width / 2} cy={11} r={0.35} className="spot" />
        </g>
        <text x={1} y={half - 1.2} className="pitch-label">
          left
        </text>
        <text x={width - 1} y={half - 1.2} className="pitch-label" textAnchor="end">
          right
        </text>
      </svg>
      <figcaption>
        <ul className="zone-list">
          {[...weights]
            .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))
            .map((z) => (
              <li key={z.feature}>
                <span className="zone-label">{z.label}</span>
                <span className="zone-bar" aria-hidden="true">
                  <span style={{ width: `${(z.weight ?? 0) * 100}%` }} />
                </span>
                <span className="num">{z.weight === null ? "—" : `${Math.round(z.weight * 100)}%`}</span>
              </li>
            ))}
        </ul>
      </figcaption>
    </figure>
  );
}
