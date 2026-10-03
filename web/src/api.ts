// Typed client for the FastAPI backend (src/scout/api.py).

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type PlayerSummary = {
  id: number;
  name: string;
  team: string;
  league: string;
  position: string;
  minutes: number | null;
  active: boolean | null;
  window_start: string | null;
  window_end: string | null;
  age: number | null;
  market_value_m: number | null;
  contract_end: string | null;
};

export type SearchHit = Pick<PlayerSummary, "id" | "name" | "team" | "position">;

export type Reason = {
  feature: string;
  label: string;
  contribution: number;
  z_player: number; // standard deviations from the pool average
  z_other: number;
};

export type Explanation = { top: Reason[]; against: Reason; total: number };

export type SimilarResult = PlayerSummary & {
  similarity: number;
  npxg_per90: number | null;
  explanation: Explanation;
};

export type SimilarResponse = {
  player: PlayerSummary;
  distinctiveness: number;
  low_reliability: boolean;
  candidates: number;
  inactive_excluded: number;
  removed_by_filters: number;
  results: SimilarResult[];
};

export type Feature = { feature: string; label: string; value: number | null; percentile: number | null };
export type ZoneWeight = { feature: string; label: string; weight: number | null };

export type PlayerProfile = PlayerSummary & {
  market: {
    age: number | null;
    value_m: number | null;
    contract_end: string | null;
    value_date: string | null;
    club_at_snapshot: string | null;
  };
  distinctiveness: number;
  low_reliability: boolean;
  features: Feature[];
  zones: ZoneWeight[];
};

export type ZonesResponse = {
  pitch: { length: number; width: number };
  x_edges: number[]; // metres from own goal line, along the pitch
  y_edges: number[]; // metres from the attacker's right touchline
  zones: { column: string; label: string; grid: number[][] }[]; // grid[x][y]
};

export type MapPoint = Pick<PlayerSummary, "id" | "name" | "team" | "position" | "active"> & { x: number; y: number };
export type MapResponse = { explained_variance: number[]; players: MapPoint[] };

export type Meta = {
  data_window_end: string | null;
  market_snapshot: string | null;
  pool_size: number;
  window_minutes: number;
  recall_at_10: number | null;
};

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(`Can't reach the scout API at ${API_URL}. Is it running?`);
  }
  if (!res.ok) {
    const detail = await res.json().then((b) => b?.detail, () => undefined);
    throw new ApiError(typeof detail === "string" ? detail : `Request failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}
