"""Find the players whose full-season style profile is most similar to a given player's.

    python -m scout.similar "Mbappe"
"""
import argparse
import difflib
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

from scout.evaluate import feature_sets, similarity, standardise
from scout.features import KEYS, PROCESSED

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
    """The TOP_N most similar players to `key`, and the player's distinctiveness percentile."""
    cols = feature_sets(pool.columns.tolist())["rates + style"]
    z, _, _ = standardise(pool[cols], pool[cols])
    i = pool.index.get_loc(key)
    sims = pd.Series(similarity(z[i:i + 1], z)[0], index=pool.index).drop(key)
    top = pool.loc[sims.nlargest(TOP_N).index].assign(similarity=sims.nlargest(TOP_N))
    dist = np.linalg.norm(z, axis=1)
    percentile = 100 * (np.delete(dist, i) < dist[i]).mean()
    return top, percentile


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("name", help='player name, e.g. "Mbappe" (accents optional)')
    args = p.parse_args()

    pool = pd.read_parquet(PROCESSED / "profiles.parquet").set_index(KEYS)
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
    top, percentile = similar_players(pool, key)
    print(f"{me['player']} | {me['teams']} | {me['league']} | {me['primary_position']} | "
          f"{me['minutes']} min | {me['shots']} shots | season {key[1]}")
    print(f"Distinctiveness: more distinctive than {percentile:.0f}% of attackers in the pool.")
    if percentile < LOW_DISTINCTIVENESS:
        print("Note: this profile is close to the pool average, so the list below is less reliable.")
    print(f"\nTop {TOP_N} most similar:")
    out = top.reset_index()[["player", "teams", "league", "primary_position", "minutes", "similarity"]]
    out["similarity"] = out["similarity"].round(3)
    out.index = range(1, len(out) + 1)
    print(out.rename(columns={"primary_position": "position"}).to_string())


if __name__ == "__main__":
    main()
