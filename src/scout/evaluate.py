"""Evaluate how well profiles identify a player's style, by split-half self-retrieval.

Each pool player's appearances are split at random into halves A and B. A profile built
from B should be more similar to the same player's A profile than to anyone else's.
"""
import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from scout.features import (KEYS, PROCESSED, ZONES, build_profiles, fit_shot_zones,
                            last_action_categories, shot_grids, shots_in, style_priors,
                            transform_shot_zones)

REPORT = Path("reports/eval_baseline.md")
EXPERIMENT_REPORTS = Path("reports/experiments")
SPLITS = ("random", "stratified")
METRICS = ("cosine", "euclidean")
DEFAULTS = {"split": "random", "metric": "cosine", "shrinkage_k": 0, "zones": ZONES}
FULL = "all features"
SEEDS = range(20)
KS = (1, 5, 10)
SHOT_BUCKETS = {"<20": (0, 19), "20–39": (20, 39), "40+": (40, np.inf)}  # full-season style shots
RATES = ["npxg_per90", "shots_per90", "xa_per90", "key_passes_per90", "xgchain_per90",
         "xgbuildup_per90", "npxg_per_shot", "buildup_share_of_chain"]
N_WORST = 10


def feature_sets(columns: list[str]) -> dict[str, list[str]]:
    style = [c for c in columns if c.startswith(("last_action_", "shot_type_"))]
    zones = [c for c in columns if c.startswith("zone_")]
    sets = {FULL: RATES + style + zones, "rates only": RATES, "style only": style}
    if zones:
        sets["zones only"] = zones
    sets["npxG per 90 only"] = ["npxg_per90"]
    return sets


def split_halves(apps: pd.DataFrame, seed: int, split: str = "random") -> pd.Series:
    """True = half A, False = half B. Each player-season's appearances are shuffled and
    split in two; A gets the smaller half when the count is odd. "stratified" halves
    starts and sub appearances separately, so both halves get a similar mix."""
    order = apps.sort_values(KEYS + ["match_id"]).index
    r = pd.Series(np.random.default_rng(seed).random(len(apps)), index=order).reindex(apps.index)
    groups = [apps[k] for k in KEYS] + ([apps["started"]] if split == "stratified" else [])
    grouped = r.groupby(groups)
    return grouped.rank(method="first") <= grouped.transform("size") // 2


def half_profiles(shots, apps, pool, seed, last_actions, split="random", shrinkage_k=0,
                  priors=None, zones=0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Profiles of pool players built on halves A and B, both indexed like `pool`.
    Shot zones come from an NMF fitted on the A-half grids only, then applied to both."""
    in_a = split_halves(apps, seed, split)
    halves = (apps[in_a], apps[~in_a])
    out = []
    for half in halves:
        p = build_profiles(shots, half, last_actions=last_actions,
                           min_starts=0, min_minutes=0, positions=None,
                           shrinkage_k=shrinkage_k, priors=priors, zones=0)
        out.append(p.set_index(KEYS).reindex(pool.index))
    if zones:
        grids = [shot_grids(shots_in(shots, half)).reindex(pool.index) for half in halves]
        model = fit_shot_zones(grids[0], zones)
        out = [p.join(transform_shot_zones(model, g)) for p, g in zip(out, grids)]
    return out[0], out[1]


def standardise(a: pd.DataFrame, b: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, int]:
    """Impute NaNs with A's column mean, then z-score both with A's mean and std."""
    mean = a.mean()
    n_imputed = int(a.isna().sum().sum() + b.isna().sum().sum())
    a, b = a.fillna(mean), b.fillna(mean)
    std = a.std(ddof=0).replace(0, 1)  # a constant column carries no information
    return ((a - mean) / std).to_numpy(), ((b - mean) / std).to_numpy(), n_imputed


def similarity(zb: np.ndarray, za: np.ndarray, metric: str = "cosine") -> np.ndarray:
    """S[i, j] = similarity of B profile i to A profile j: cosine, or minus the Euclidean
    distance. A single feature always uses distance (cosine can only be +1 or -1)."""
    if metric == "euclidean" or za.shape[1] == 1:
        return -np.sqrt(((zb[:, None, :] - za[None, :, :]) ** 2).sum(axis=2))
    na = za / np.maximum(np.linalg.norm(za, axis=1, keepdims=True), 1e-12)
    nb = zb / np.maximum(np.linalg.norm(zb, axis=1, keepdims=True), 1e-12)
    return nb @ na.T


def own_ranks(zb: np.ndarray, za: np.ndarray, metric: str = "cosine") -> np.ndarray:
    """Rank of each player's own A profile among all A profiles (1 = best). Ties count
    against the player, so a profile that can't tell players apart never scores well."""
    s = similarity(zb, za, metric)
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


def evaluate(shots, apps, pool, seeds=SEEDS, split="random", metric="cosine",
             shrinkage_k=0, zones=ZONES) -> tuple[pd.DataFrame, list[tuple[int, int]]]:
    """Ranks for every (seed, feature set, player), and per seed the (imputed, total) values
    of the full feature set. Feature sets come from the half profiles, never from the
    full-season columns in `pool`. Shrinkage priors come from all players' shots, so they
    are the same for both halves."""
    last_actions = last_action_categories(shots)
    priors = style_priors(shots, last_actions) if shrinkage_k else None
    apps = apps.merge(pool.reset_index()[KEYS], on=KEYS)
    rows, imputed = [], []
    for seed in seeds:
        a, b = half_profiles(shots, apps, pool, seed, last_actions, split, shrinkage_k, priors, zones)
        for name, cols in feature_sets(a.columns.tolist()).items():
            za, zb, n = standardise(a[cols], b[cols])
            if name == FULL:
                imputed.append((n, 2 * za.size))
            rows.append(pd.DataFrame({"seed": seed, "feature_set": name,
                                      "rank": own_ranks(zb, za, metric)}, index=pool.index))
    return pd.concat(rows).reset_index(), imputed


def fmt_table(df: pd.DataFrame) -> str:
    """Markdown table without needing the tabulate package."""
    cols = [df.index.name or ""] + df.columns.tolist()
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(map(str, [i, *r])) + " |" for i, r in zip(df.index, df.values)]
    return "\n".join(lines)


def rates_style(ranks: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """Ranks for the full feature set, with each player's pool columns and shot bucket."""
    full = ranks[ranks["feature_set"] == FULL].join(pool, on=KEYS)
    full["hit@10"] = full["rank"] <= 10
    full["shot_bucket"] = pd.cut(full["shots"], [-1, 19, 39, np.inf], labels=list(SHOT_BUCKETS))
    return full


def mean_ranks(ranks: pd.DataFrame) -> pd.Series:
    """Each player's mean rank across splits, full feature set."""
    return ranks[ranks["feature_set"] == FULL].groupby(KEYS)["rank"].mean()


def log_row(ranks: pd.DataFrame, pool: pd.DataFrame) -> dict[str, str]:
    """The experiment-log metrics for the full feature set: mean ± std across splits."""
    full = rates_style(ranks, pool)
    per_seed = full.groupby("seed")["rank"].apply(lambda r: pd.Series(metrics(r.to_numpy()))).unstack()
    per_seed["recall@10 (<20 shots)"] = full[full["shot_bucket"] == "<20"].groupby("seed")["hit@10"].mean()
    return {c: f"{per_seed[c].mean():.3f} ± {per_seed[c].std():.3f}" for c in per_seed}


def paired(ranks: pd.DataFrame, base: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """Recall@10 change from the baseline split by split (same seeds), overall and by shot
    bucket: mean change, and on how many splits it was better / worse."""
    def per_seed(r):
        f = rates_style(r, pool)
        cols = {"all": f.groupby("seed")["hit@10"].mean()}
        cols |= {f"{b} shots": f[f["shot_bucket"] == b].groupby("seed")["hit@10"].mean()
                 for b in SHOT_BUCKETS}
        return pd.DataFrame(cols)
    d = per_seed(ranks) - per_seed(base)
    buckets = pd.cut(pool["shots"], [-1, 19, 39, np.inf], labels=list(SHOT_BUCKETS)).value_counts()
    out = pd.DataFrame({
        "players": [len(pool)] + [int(buckets[b]) for b in SHOT_BUCKETS],
        "recall@10 change": [f"{v:+.3f}" for v in d.mean()],
        "splits better / worse": [f"{(d[c] > 0).sum()} / {(d[c] < 0).sum()}" for c in d],
    }, index=d.columns)
    out.index.name = "group"
    return out


def describe(config: dict) -> str:
    split = "random" if config["split"] == "random" else "stratified (starts and sub appearances halved separately)"
    k, z = config["shrinkage_k"], config["zones"]
    return (f"{split} split, {config['metric']} similarity, "
            + (f"shot-style shares shrunk towards pool-wide shares with k = {k:g}" if k else "no shrinkage")
            + (f", shot-location zones from NMF with {z} components (fitted on half A)" if z else ", no shot zones"))


def summarise(ranks: pd.DataFrame, pool: pd.DataFrame, imputed: list[tuple[int, int]],
              config: dict = DEFAULTS, base: pd.DataFrame | None = None) -> str:
    """Markdown report. `base`: baseline ranks on the same seeds, for the paired comparison
    and to track the baseline's hardest players."""
    n = len(pool)
    per_seed = (ranks.groupby(["feature_set", "seed"])["rank"]
                .apply(lambda r: pd.Series(metrics(r.to_numpy()))).unstack())
    agg = per_seed.groupby("feature_set").agg(["mean", "std"])
    order = list(dict.fromkeys(ranks["feature_set"]))
    main = pd.DataFrame({m: [f"{agg.loc[s, (m, 'mean')]:.3f} ± {agg.loc[s, (m, 'std')]:.3f}"
                             for s in order] for m in baseline(n)}, index=order)
    main.loc["random guess"] = [f"{v:.3f}" for v in baseline(n).values()]
    main.index.name = "features"

    full = rates_style(ranks, pool)

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

    comparison = ""
    if base is not None:
        reference = mean_ranks(base).nlargest(N_WORST)
        now = mean_ranks(ranks).loc[reference.index]
        t = pd.DataFrame({"player": pool.loc[reference.index, "player"].values,
                          "baseline mean rank": reference.round(1).values,
                          "mean rank here": now.round(1).values}).set_index("player")
        comparison = f"""
## Paired comparison with the baseline (all features)
Recall@10 here minus the baseline's, on the same {len(set(ranks["seed"]))} splits.

{fmt_table(paired(ranks, base, pool))}

## Baseline's hardest players under this configuration
Average of the mean ranks: {reference.mean():.1f} in the baseline, {now.mean():.1f} here.

{fmt_table(t)}
"""

    title = "baseline" if config == DEFAULTS else describe(config)
    n_imputed, n_values = np.mean([i for i, _ in imputed]), imputed[0][1]
    return f"""# Split-half self-retrieval: {title}

Generated {date.today()} by `python -m scout.evaluate{cli_args(config)}`.

## Setup
- **Population:** {n} player-seasons from `profiles.parquet` ({", ".join(f"{k} {v}" for k, v in pool["league"].value_counts().items())}).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all {n} A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** {describe(config)}.
- **Splits:** {len(set(ranks["seed"]))} (seeds {min(ranks["seed"])}–{max(ranks["seed"])}); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): {n_imputed:.1f} per split on average, out of {n_values}.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
{fmt_table(main)}

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is {10 / n:.3f} in every bucket.

{breakdown("shot_bucket")}

## Recall@10 by primary position (all features)
{breakdown("primary_position")}

## Hardest players to re-identify (all features)
The {N_WORST} players with the worst mean rank across splits (out of {n}).

{fmt_table(worst)}
{comparison}"""


def cli_args(config: dict) -> str:
    flags = {"split": "--split", "metric": "--metric", "shrinkage_k": "--shrinkage-k", "zones": "--zones"}
    return "".join(f" {flags[k]} {v:g}" if isinstance(v, (int, float)) else f" {flags[k]} {v}"
                   for k, v in config.items() if v != DEFAULTS[k])


def report_path(config: dict) -> Path:
    if config == DEFAULTS:
        return REPORT
    name = f"eval_{config['split']}_{config['metric']}_k{config['shrinkage_k']:g}"
    if config["zones"] != DEFAULTS["zones"]:
        name += f"_zones{config['zones']}"
    return EXPERIMENT_REPORTS / f"{name}.md"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--split", choices=SPLITS, default=DEFAULTS["split"])
    p.add_argument("--metric", choices=METRICS, default=DEFAULTS["metric"])
    p.add_argument("--shrinkage-k", type=float, default=DEFAULTS["shrinkage_k"],
                   help="pseudo-shots at pool-wide shares added to each player's shot-style shares")
    p.add_argument("--zones", type=int, default=DEFAULTS["zones"],
                   help="NMF components for shot-location zones (0 = none)")
    args = p.parse_args()
    config = {"split": args.split, "metric": args.metric, "shrinkage_k": args.shrinkage_k,
              "zones": args.zones}

    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    pool = pd.read_parquet(PROCESSED / "profiles.parquet").set_index(KEYS)
    ranks, imputed = evaluate(shots, apps, pool, **config)
    base = None if config == DEFAULTS else evaluate(shots, apps, pool)[0]

    report = summarise(ranks, pool, imputed, config, base)
    path = report_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report)
    print(report.split("## Recall@10 by primary")[0])
    if base is not None:
        print(report[report.index("## Paired comparison"):report.index("## Baseline's hardest")])
        print(report[report.index("Average of the mean ranks"):].split("\n")[0])
    row = log_row(ranks, pool)
    print("log row: " + " | ".join(f"{k} {v}" for k, v in row.items()))
    print(f"full report: {path}")


if __name__ == "__main__":
    main()
