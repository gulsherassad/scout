// Pure formatting helpers (unit-tested in format.test.ts).
import type { Explanation, Reason } from "../api";

export type Filters = {
  maxAge?: number;
  maxValue?: number;
  contractBefore?: number;
  includeInactive: boolean;
  limit?: number;
};

export const EMPTY_FILTERS: Filters = { includeInactive: false };

const QUERY_KEYS: Record<Exclude<keyof Filters, "includeInactive">, string> = {
  maxAge: "max_age",
  maxValue: "max_value",
  contractBefore: "contract_before",
  limit: "limit",
};

/** Query string for /players/{id}/similar ("" when no filter is set). Empty, non-finite
 * or negative numbers are left out; include_inactive is sent only when true. */
export function buildSimilarQuery(filters: Filters): string {
  const params = new URLSearchParams();
  for (const [key, name] of Object.entries(QUERY_KEYS) as [keyof typeof QUERY_KEYS, string][]) {
    const value = filters[key];
    if (value !== undefined && Number.isFinite(value) && value >= 0) params.set(name, String(value));
  }
  if (filters.includeInactive) params.set("include_inactive", "true");
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** Inverse of buildSimilarQuery, for filters kept in the page URL. */
export function parseFilters(params: URLSearchParams): Filters {
  const num = (name: string) => {
    const raw = params.get(name);
    if (raw === null || raw.trim() === "") return undefined;
    const value = Number(raw);
    return Number.isFinite(value) && value >= 0 ? value : undefined;
  };
  return {
    maxAge: num("max_age"),
    maxValue: num("max_value"),
    contractBefore: num("contract_before"),
    limit: num("limit"),
    includeInactive: params.get("include_inactive") === "true",
  };
}

/** "share of shots with the left foot" stays as is; direction is added in front. */
function trait(reason: Reason): string {
  return `${reason.z_player > 0 ? "high" : "low"} ${reason.label}`;
}

/** Plain-language "why similar?" text from an explanation.
 * shared: the top contributions where both players sit on the same side of the average.
 * difference: the most negative contribution, saying which player is higher. */
export function formatExplanation(explanation: Explanation, otherName: string): { shared: string; difference: string } {
  const shared = explanation.top.filter((r) => r.contribution > 0).map(trait);
  const against = explanation.against;
  const difference =
    against.contribution < 0
      ? `${against.label}: ${otherName} ${against.z_other > against.z_player ? "higher" : "lower"}`
      : "no clear difference";
  return {
    shared: shared.length ? `Both: ${shared.join(", ")}` : "No strongly shared traits",
    difference: `Main difference: ${difference}`,
  };
}

export function formatValue(millions: number | null | undefined): string {
  if (millions === null || millions === undefined) return "—";
  return millions >= 10 ? `€${Math.round(millions)}m` : `€${millions.toFixed(1)}m`;
}

/** "2027-06-30" -> "Jun 2027". */
export function formatMonth(date: string | null | undefined): string {
  if (!date) return "—";
  const d = new Date(`${date}T00:00:00Z`);
  return d.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "—";
  const d = new Date(`${date}T00:00:00Z`);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** Understat position codes grouped into roles, for colour and legends. */
export type Role = "Striker" | "Attacking midfielder" | "Winger" | "Wide midfielder" | "Other";

export function role(position: string): Role {
  if (["FW", "FWL", "FWR"].includes(position)) return "Striker";
  if (position === "AMC") return "Attacking midfielder";
  if (["AML", "AMR"].includes(position)) return "Winger";
  if (["ML", "MR"].includes(position)) return "Wide midfielder";
  return "Other";
}

export const ROLES: Role[] = ["Striker", "Attacking midfielder", "Winger", "Wide midfielder"];

/** CSS class carrying a role's colour, e.g. "role-attacking-midfielder". */
export function roleCss(r: Role): string {
  return `role-${r.toLowerCase().replace(/\s+/g, "-")}`;
}

export function roleClass(position: string): string {
  return roleCss(role(position));
}
