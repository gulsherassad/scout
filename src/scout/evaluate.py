"""Evaluate how well profiles identify a player's style, by split-half self-retrieval.

Each pool player's appearances are split at random into halves A and B. A profile built
from B should be more similar to the same player's A profile than to anyone else's.
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from scout.features import KEYS, PROCESSED, build_profiles, last_action_categories

REPORT = Path("reports/eval_baseline.md")
SEEDS = range(20)
KS = (1, 5, 10)
SHOT_BUCKETS = {"<20": (0, 19), "20–39": (20, 39), "40+": (40, np.inf)}  # full-season style shots
RATES = ["npxg_per90", "shots_per90", "xa_per90", "key_passes_per90", "xgchain_per90",
         "xgbuildup_per90", "npxg_per_shot", "buildup_share_of_chain"]
N_WORST = 10


def feature_sets(columns: list[str]) -> dict[str, list[str]]:
    style = [c for c in columns if c.startswith(("last_action_", "shot_type_"))]
    return {"rates + style": RATES + style, "rates only": RATES, "style only": style,
            "npxG per 90 only": ["npxg_per90"]}


def split_halves(apps: pd.DataFrame, seed: int) -> pd.Series:
    """True = half A, False = half B. Each player-season's appearances are shuffled and
    split in two; A gets the smaller half when the count is odd."""
    order = apps.sort_values(KEYS + ["match_id"]).index
    r = pd.Series(np.random.default_rng(seed).random(len(apps)), index=order).reindex(apps.index)
    grouped = r.groupby([apps[k] for k in KEYS])
    return grouped.rank(method="first") <= grouped.transform("size") // 2


def half_profiles(shots, apps, pool, seed, last_actions) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Profiles of pool players built on halves A and B, both indexed like `pool`."""
    in_a = split_halves(apps, seed)
    out = []
    for half in (apps[in_a], apps[~in_a]):
        p = build_profiles(shots, half, last_actions=last_actions,
                           min_starts=0, min_minutes=0, positions=None)
        out.append(p.set_index(KEYS).reindex(pool.index))
    return out[0], out[1]


def standardise(a: pd.DataFrame, b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, int]:
    """Impute NaNs with A's column mean, then z-score both with A's mean and std."""
    mean = a.mean()
    n_imputed = int(a.isna().sum().sum() + b.isna().sum().sum())
    a, b = a.fillna(mean), b.fillna(mean)
    std = a.std(ddof=0).replace(0, 1)  # a constant column carries no information
    return ((a - mean) / std).to_numpy(), ((b - mean) / std).to_numpy(), n_imputed


def similarity(zb: np.ndarray, za: np.ndarray) -> np.ndarray:
    """S[i, j] = similarity of B profile i to A profile j: cosine, or minus the absolute
    difference for a single feature (where cosine can only be +1 or -1)."""
    if za.shape[1] == 1:
        return -np.abs(zb - za.T)
    na = za / np.maximum(np.linalg.norm(za, axis=1, keepdims=True), 1e-12)
    nb = zb / np.maximum(np.linalg.norm(zb, axis=1, keepdims=True), 1e-12)
    return nb @ na.T


def own_ranks(zb: np.ndarray, za: np.ndarray) -> np.ndarray:
    """Rank of each player's own A profile among all A profiles (1 = best). Ties count
    against the player, so a profile that can't tell players apart never scores well."""
    s = similarity(zb, za)
    return (s >= np.diag(s)[:, None]).sum(axis=1)


def metrics(ranks: np.ndarray) -> dict[str, float]:
    m = {f"recall@{k}": float(np.mean(ranks <= k)) for k in KS}
    m["MRR"] = float(np.mean(1 / ranks))
    return m


def baseline(n: int) -> dict[str, float]:
    """Expected metrics when the own profile lands at a uniformly random rank."""
    m = {f"recall@{k}": k / n for k in KS}
    m["MRR"] = float(np.mean(1 / np.arange(1, n + 1)))
    return m


def evaluate(shots, apps, pool, seeds=SEEDS) -> tuple[pd.DataFrame, list[int]]:
    """Ranks for every (seed, feature set, player), and NaNs imputed per seed (all features)."""
    last_actions = last_action_categories(shots)
    apps = apps.merge(pool.reset_index()[KEYS], on=KEYS)
    sets = feature_sets(pool.columns.tolist())
    rows, imputed = [], []
    for seed in seeds:
        a, b = half_profiles(shots, apps, pool, seed, last_actions)
        for name, cols in sets.items():
            za, zb, n = standardise(a[cols], b[cols])
            if name == "rates + style":
                imputed.append(n)
            rows.append(pd.DataFrame({"seed": seed, "feature_set": name,
                                      "rank": own_ranks(zb, za)}, index=pool.index))
    return pd.concat(rows).reset_index(), imputed


def fmt_table(df: pd.DataFrame) -> str:
    """Markdown table without needing the tabulate package."""
    cols = [df.index.name or ""] + df.columns.tolist()
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(map(str, [i, *r])) + " |" for i, r in zip(df.index, df.values)]
    return "\n".join(lines)


def summarise(ranks: pd.DataFrame, pool: pd.DataFrame, imputed: list[int]) -> str:
    n = len(pool)
    per_seed = (ranks.groupby(["feature_set", "seed"])["rank"]
                .apply(lambda r: pd.Series(metrics(r.to_numpy()))).unstack())
    agg = per_seed.groupby("feature_set").agg(["mean", "std"])
    order = list(feature_sets(pool.columns.tolist()))
    main = pd.DataFrame({m: [f"{agg.loc[s, (m, 'mean')]:.3f} ± {agg.loc[s, (m, 'std')]:.3f}"
                             for s in order] for m in baseline(n)}, index=order)
    main.loc["random guess"] = [f"{v:.3f}" for v in baseline(n).values()]
    main.index.name = "features"

    full = ranks[ranks["feature_set"] == "rates + style"].join(pool, on=KEYS)
    full["hit@10"] = full["rank"] <= 10
    full["shot_bucket"] = pd.cut(full["shots"], [-1, 19, 39, np.inf], labels=list(SHOT_BUCKETS))

    def breakdown(col):
        per_seed = full.groupby([col, "seed"], observed=True)["hit@10"].mean().unstack()
        players = full.groupby(col, observed=True)[KEYS].apply(lambda d: len(d.drop_duplicates()))
        out = pd.DataFrame({"players": players,
                            "recall@10": [f"{m:.3f} ± {s:.3f}" for m, s in
                                          zip(per_seed.mean(axis=1), per_seed.std(axis=1))]})
        out.index.name = col
        return fmt_table(out)

    worst = (full.groupby(KEYS)["rank"].agg(["mean", "min", "max"]).join(pool)
             .nlargest(N_WORST, "mean").reset_index())
    worst = pd.DataFrame({
        "player": worst["player"], "teams": worst["teams"], "position": worst["primary_position"],
        "shots": worst["shots"], "minutes": worst["minutes"],
        "mean rank": worst["mean"].round(1), "best / worst rank": worst["min"].astype(str) + " / " + worst["max"].astype(str),
    }).set_index("player")

    return f"""# Split-half self-retrieval: baseline

Generated {date.today()} by `python -m scout.evaluate`.

## Setup
- **Population:** {n} player-seasons from `profiles.parquet` ({", ".join(f"{k} {v}" for k, v in pool["league"].value_counts().items())}).
- **Method:** each player's appearances are split at random into halves A and B. Profiles built on B are matched against all {n} A profiles by cosine similarity on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Splits:** {len(set(ranks["seed"]))} (seeds {min(ranks["seed"])}–{max(ranks["seed"])}); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): {np.mean(imputed):.1f} per split on average, out of {2 * n * len(feature_sets(pool.columns.tolist())["rates + style"])}.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
{fmt_table(main)}

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is {10 / n:.3f} in every bucket.

{breakdown("shot_bucket")}

## Recall@10 by primary position (rates + style)
{breakdown("primary_position")}

## Hardest players to re-identify (rates + style)
The {N_WORST} players with the worst mean rank across splits (out of {n}).

{fmt_table(worst)}
"""


def main() -> None:
    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    pool = pd.read_parquet(PROCESSED / "profiles.parquet").set_index(KEYS)
    ranks, imputed = evaluate(shots, apps, pool)
    report = summarise(ranks, pool, imputed)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report)
    print(report.split("## Recall@10 by primary")[0])
    print(f"full report: {REPORT}")


if __name__ == "__main__":
    main()
