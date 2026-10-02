"""Find the players whose full-season style profile is most similar to a given player's.

    python -m scout.similar "Mbappe"              # recent form: newest league minutes
    python -m scout.similar "Mbappe" --season 2025  # one season
"""
import argparse
import difflib
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

from scout.evaluate import FULL, feature_sets, similarity, standardise
from scout.features import KEYS, PROCESSED, WINDOW_MINUTES

TOP_N = 10
LOW_DISTINCTIVENESS = 20  # percentile; below this, matches are much less reliable (see experiments.md)
FUZZY_CUTOFF = 0.8


def normalise(name: str) -> str:
    """Lowercase, strip accents, and treat hyphens and punctuation as spaces."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain.lower()).split())


def find_players(query: str, names: pd.Series) -> list:
    """Index labels of `names` matching `query`.

    An exact match on the full name wins. Otherwise every word of the query must appear in
    the name; if nothing does, fall back to close spellings of the full name or any word.
    """
    q = normalise(query)
    norm = names.map(normalise)
    exact = norm[norm == q]
    if len(exact):
        return list(exact.index)
    words = q.split()
    hits = norm[norm.map(lambda n: all(w in n for w in words))]
    if len(hits):
        return list(hits.index)
    fuzzy = norm.map(lambda n: max(difflib.SequenceMatcher(None, q, part).ratio()
                                   for part in [n, *n.split()]))
    return list(fuzzy[fuzzy >= FUZZY_CUTOFF].sort_values(ascending=False).index)


def similar_players(pool: pd.DataFrame, key) -> tuple[pd.DataFrame, float]:
    """All other players ranked by similarity to `key` (most similar first), and the
    player's distinctiveness percentile."""
    cols = feature_sets(pool.columns.tolist())[FULL]
    z, _, _ = standardise(pool[cols], pool[cols])
    i = pool.index.get_loc(key)
    sims = pd.Series(similarity(z[i:i + 1], z)[0], index=pool.index).drop(key)
    ranked = pool.loc[sims.sort_values(ascending=False).index].assign(similarity=sims)
    dist = np.linalg.norm(z, axis=1)
    percentile = 100 * (np.delete(dist, i) < dist[i]).mean()
    return ranked, percentile


def with_market(profiles: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    """Add age (whole years at snapshot), market value (EUR m) and contract end."""
    m = market.set_index("understat_player_id")[["age_at_snapshot", "market_value_eur", "contract_expiration_date"]]
    out = profiles.join(m, on="player_id")
    out["age"] = np.floor(out["age_at_snapshot"]).astype("Int64")
    out["value_m"] = out["market_value_eur"] / 1e6
    out["contract_end"] = pd.to_datetime(out["contract_expiration_date"])
    return out


def apply_filters(ranked: pd.DataFrame, max_age: int | None = None, max_value: float | None = None,
                  contract_before: int | None = None) -> tuple[pd.DataFrame, int]:
    """Keep players meeting every given criterion, in their similarity order, and count
    how many were removed. A player missing a field that is filtered on is removed."""
    keep = pd.Series(True, index=ranked.index)
    if max_age is not None:
        keep &= ranked["age"].le(max_age).fillna(False).astype(bool)
    if max_value is not None:
        keep &= ranked["value_m"].le(max_value).fillna(False).astype(bool)
    if contract_before is not None:
        keep &= ranked["contract_end"].dt.year.lt(contract_before).fillna(False).astype(bool)
    return ranked[keep], int((~keep).sum())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("name", help='player name, e.g. "Mbappe" (accents optional)')
    p.add_argument("--season", type=int,
                   help="use one season's profiles (e.g. 2025 = 2025/26) instead of recent form")
    p.add_argument("--max-age", type=int, help="maximum age in whole years at the market snapshot")
    p.add_argument("--max-value", type=float, help="maximum market value, EUR millions")
    p.add_argument("--contract-before", type=int,
                   help="contract ends before this year (e.g. 2028: ends in 2027 or earlier)")
    args = p.parse_args()

    market = pd.read_parquet(PROCESSED / "market.parquet")
    if args.season is None:
        profiles = pd.read_parquet(PROCESSED / "profiles_recent.parquet")
    else:
        profiles = pd.read_parquet(PROCESSED / "profiles.parquet")
        profiles = profiles[profiles["season"] == args.season]
        if profiles.empty:
            sys.exit(f"No season profiles for {args.season}.")
    pool = with_market(profiles.set_index(KEYS), market)
    matches = find_players(args.name, pool["player"])
    if not matches:
        sys.exit(f'No player in the pool matches "{args.name}".')
    if len(matches) > 1:
        print(f'"{args.name}" matches {len(matches)} players; please be more specific:')
        for key in matches:
            r = pool.loc[key]
            print(f"  {r['player']} ({r['teams']}, {r['primary_position']})")
        sys.exit(1)

    key = matches[0]
    me = pool.loc[key]
    ranked, percentile = similar_players(pool, key)
    kept, removed = apply_filters(ranked, args.max_age, args.max_value, args.contract_before)
    print(f"{me['player']} | {me['teams']} | {me['league']} | {me['primary_position']} | "
          f"{me['minutes']} min | {me['shots']} shots | npxG/90 {me['npxg_per90']:.2f}")
    if args.season is None:
        print(f"Profile: recent form, league matches {me['window_start']:%Y-%m-%d} to {me['window_end']:%Y-%m-%d} "
              f"(newest {WINDOW_MINUTES} minutes; each player's window below).")
    else:
        print(f"Profile: season {args.season}/{(args.season + 1) % 100:02d}.")
    print(f"Distinctiveness: more distinctive than {percentile:.0f}% of attackers in the pool.")
    if percentile < LOW_DISTINCTIVENESS:
        print("Note: this profile is close to the pool average, so the list below is less reliable.")
    criteria = [f"age <= {args.max_age}" if args.max_age is not None else None,
                f"value <= EUR {args.max_value:g}m" if args.max_value is not None else None,
                f"contract ends before {args.contract_before}" if args.contract_before is not None else None]
    criteria = [c for c in criteria if c]
    if criteria:
        print(f"Filters ({', '.join(criteria)}) removed {removed} of {len(ranked)} players; "
              f"{len(kept)} remain.")

    top = kept.head(TOP_N).reset_index(drop=True)
    top.index = range(1, len(top) + 1)
    print(f"\nTop {len(top)} most similar" + (" meeting the filters:" if criteria else ":"))
    out = pd.DataFrame({
        "player": top["player"], "teams": top["teams"], "league": top["league"],
        "position": top["primary_position"], "minutes": top["minutes"], "age": top["age"],
        "value €m": top["value_m"].round(1), "contract": top["contract_end"].dt.strftime("%Y-%m").fillna("–"),
        "npxG/90": top["npxg_per90"].round(2), "similarity": top["similarity"].round(3),
    })
    if args.season is None:
        out.insert(5, "window", top["window_start"].dt.strftime("%y-%m") + "–" + top["window_end"].dt.strftime("%y-%m"))
    print(out.to_string() if len(out) else "  no players meet the filters")
    as_of = pd.to_datetime(market["valuations_as_of"]).max().date()
    print(f"\nMarket data: Transfermarkt snapshot as of {as_of} (transfermarkt-datasets, CC0).")


if __name__ == "__main__":
    main()
