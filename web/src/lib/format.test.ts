import { describe, expect, it } from "vitest";
import type { Explanation, Reason } from "../api";
import { buildSimilarQuery, formatExplanation, parseFilters } from "./format";

const reason = (label: string, contribution: number, z_player: number, z_other: number): Reason => ({
  feature: label.replace(/\s+/g, "_"),
  label,
  contribution,
  z_player,
  z_other,
});

describe("formatExplanation", () => {
  const explanation: Explanation = {
    top: [
      reason("share of shots from the right of the box", 0.17, 2.1, 1.8),
      reason("key passes per 90", 0.12, 1.4, 1.5),
      reason("share of shots with the head", 0.05, -1.2, -0.9),
    ],
    against: reason("share of shots after a take-on (dribble)", -0.03, -0.4, 1.1),
    total: 0.81,
  };

  it("lists shared traits with their direction", () => {
    expect(formatExplanation(explanation, "Lamine Yamal").shared).toBe(
      "Both: high share of shots from the right of the box, high key passes per 90, low share of shots with the head",
    );
  });

  it("names the main difference and who is higher", () => {
    expect(formatExplanation(explanation, "Lamine Yamal").difference).toBe(
      "Main difference: share of shots after a take-on (dribble): Lamine Yamal higher",
    );
    const lower = { ...explanation, against: reason("shots per 90", -0.02, 1.5, -0.3) };
    expect(formatExplanation(lower, "X").difference).toBe("Main difference: shots per 90: X lower");
  });

  it("leaves out traits that don't add to the similarity", () => {
    const weak = { ...explanation, top: [reason("shots per 90", 0.1, 1, 1), reason("xA", 0, 0, 2)] };
    expect(formatExplanation(weak, "X").shared).toBe("Both: high shots per 90");
    const none = { ...explanation, top: [reason("xA", -0.01, 1, -1)] };
    expect(formatExplanation(none, "X").shared).toBe("No strongly shared traits");
  });

  it("says when there is no clear difference", () => {
    const close = { ...explanation, against: reason("shots per 90", 0.001, 0.1, 0.1) };
    expect(formatExplanation(close, "X").difference).toBe("Main difference: no clear difference");
  });
});

describe("buildSimilarQuery", () => {
  it("is empty without filters", () => {
    expect(buildSimilarQuery({ includeInactive: false })).toBe("");
  });

  it("maps every filter to the API's parameter names", () => {
    expect(buildSimilarQuery({ maxAge: 24, maxValue: 40, contractBefore: 2028, includeInactive: true, limit: 10 })).toBe(
      "?max_age=24&max_value=40&contract_before=2028&limit=10&include_inactive=true",
    );
  });

  it("drops unset, non-numeric and negative values", () => {
    expect(buildSimilarQuery({ maxAge: Number.NaN, maxValue: -5, contractBefore: undefined, includeInactive: false })).toBe("");
    expect(buildSimilarQuery({ maxValue: 2.5, includeInactive: false })).toBe("?max_value=2.5");
  });

  it("keeps zero, a valid limit", () => {
    expect(buildSimilarQuery({ maxValue: 0, includeInactive: false })).toBe("?max_value=0");
  });

  it("round-trips through parseFilters", () => {
    const filters = { maxAge: 23, maxValue: 15.5, contractBefore: 2027, includeInactive: true, limit: undefined };
    expect(parseFilters(new URLSearchParams(buildSimilarQuery(filters)))).toEqual(filters);
    expect(parseFilters(new URLSearchParams("max_age=abc&include_inactive=yes"))).toEqual({
      maxAge: undefined, maxValue: undefined, contractBefore: undefined, limit: undefined, includeInactive: false,
    });
  });
});
