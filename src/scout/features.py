"""Build player style profiles: one row per player-season of attacking players.

Everything is computed from the rows passed in, never from season totals, so
build_profiles() works on any subset of matches (e.g. half a season, for validation).
"""
from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")

# Player pool. FWL/FWR are Understat's labels for the two strikers in a front two.
ATTACKING_POSITIONS = {"FW", "FWL", "FWR", "AMC", "AML", "AMR", "ML", "MR"}
MIN_STARTS = 5
MIN_MINUTES = 900

# Shots used for style features
STYLE_EXCLUDED_SITUATIONS = {"Penalty", "DirectFreekick"}
RARE_LAST_ACTION_SHARE = 0.02  # lastAction values below this share of shots become "Other"
SHOT_TYPES = {"Head": "head", "LeftFoot": "left_foot", "RightFoot": "right_foot"}  # rest -> "other"

KEYS = ["player_id", "season"]
APP_SUMS = {"xA": "xa", "key_passes": "key_passes", "xGChain": "xgchain", "xGBuildup": "xgbuildup"}


def style_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """Shots that say something about a player's style: no own goals, penalties or direct free kicks."""
    return shots[~shots["is_own_goal"] & ~shots["situation"].isin(STYLE_EXCLUDED_SITUATIONS)]


def last_action_categories(shots: pd.DataFrame) -> list[str]:
    """lastAction values that make up at least RARE_LAST_ACTION_SHARE of style shots."""
    share = style_shots(shots)["lastAction"].value_counts(normalize=True, dropna=False)
    return sorted(k for k, v in share.items() if pd.notna(k) and v >= RARE_LAST_ACTION_SHARE)


def snake(name: str) -> str:
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in name).lstrip("_")


def primary_positions(apps: pd.DataFrame) -> pd.DataFrame:
    """Position with the most minutes in starts; ties go to more starts, then alphabetical."""
    starts = (apps[apps["started"]].groupby(KEYS + ["position"])
              .agg(pos_minutes=("minutes", "sum"), pos_starts=("minutes", "size")).reset_index())
    starts = starts.sort_values(KEYS + ["pos_minutes", "pos_starts", "position"],
                                ascending=[True, True, False, False, True])
    return starts.drop_duplicates(KEYS).set_index(KEYS)[["position"]].rename(
        columns={"position": "primary_position"})


def by_minutes(apps: pd.DataFrame, col: str) -> pd.Series:
    """Values of `col` per player-season, most minutes first, joined with ", "."""
    m = apps.groupby(KEYS + [col])["minutes"].sum().reset_index()
    m = m.sort_values(KEYS + ["minutes", col], ascending=[True, True, False, True])
    return m.groupby(KEYS)[col].agg(", ".join)


def style_categories(shots: pd.DataFrame, last_actions: list[str]) -> dict[str, pd.Series]:
    """Each style shot's lastAction and shotType category, indexed by player-season."""
    style = style_shots(shots)
    idx = style.set_index(KEYS).index
    last_action = style["lastAction"].where(style["lastAction"].isin(last_actions), "Other")
    last_action = last_action.where(style["lastAction"].notna(), "Missing")
    shot_type = style["shotType"].map(SHOT_TYPES).fillna("other")
    return {"last_action": pd.Series(last_action.values, index=idx),
            "shot_type": pd.Series(shot_type.values, index=idx)}


def category_columns(last_actions: list[str]) -> dict[str, list[str]]:
    return {"last_action": last_actions + ["Other", "Missing"],
            "shot_type": list(SHOT_TYPES.values()) + ["other"]}


def style_priors(shots: pd.DataFrame, last_actions: list[str]) -> dict[str, pd.Series]:
    """Share of each style category across all players' style shots."""
    cats, cols = style_categories(shots, last_actions), category_columns(last_actions)
    return {name: cats[name].value_counts(normalize=True).reindex(cols[name], fill_value=0)
            for name in cats}


def shares(cats: pd.Series, index: pd.Index, columns: list[str], prefix: str,
           k: float = 0, prior: pd.Series | None = None) -> pd.DataFrame:
    """Per player-season share of shots in each category, shrunk towards `prior`:
    (count + k * prior) / (n_shots + k). With k = 0 these are raw shares, NaN without shots."""
    counts = pd.crosstab([cats.index.get_level_values(key) for key in KEYS], cats.values,
                         rownames=KEYS).reindex(index=index, columns=columns, fill_value=0)
    if k:
        counts = counts + k * prior[columns]
    out = counts.div(counts.sum(axis=1), axis=0)
    out.columns = [f"{prefix}_{snake(c)}" for c in columns]
    return out


def build_profiles(shots: pd.DataFrame, apps: pd.DataFrame, *,
                   last_actions: list[str] | None = None,
                   min_starts: int = MIN_STARTS, min_minutes: int = MIN_MINUTES,
                   positions: set[str] | None = ATTACKING_POSITIONS,
                   shrinkage_k: float = 0,
                   priors: dict[str, pd.Series] | None = None) -> pd.DataFrame:
    """One row per player-season in the pool, built only from the appearances in `apps`.

    Shots are restricted to (match_id, player_id) pairs in `apps`, so passing a subset of
    appearances is enough to build profiles on a subset of matches.
    `last_actions` fixes the lastAction categories; by default they come from `shots`.
    Pass the full-data categories when comparing profiles built on different subsets,
    so both have the same columns. `positions=None` turns off the primary-position filter.
    `shrinkage_k` > 0 shrinks shot-style shares towards `priors` (see style_priors();
    by default computed from `shots`), adding k pseudo-shots at the pool-wide shares.
    """
    shots = shots.merge(apps[["match_id", "player_id"]].drop_duplicates(), on=["match_id", "player_id"])
    if last_actions is None:
        last_actions = last_action_categories(shots)

    g = apps.groupby(KEYS)
    p = pd.DataFrame({
        "player": g["player"].first(),
        "teams": by_minutes(apps, "team"),
        "league": by_minutes(apps, "league").str.split(", ").str[0],  # league with most minutes
        "minutes": g["minutes"].sum(),
        "starts": g["started"].sum(),
    }).join(primary_positions(apps))

    style = style_shots(shots)
    p["shots"] = style.groupby(KEYS).size().reindex(p.index, fill_value=0)

    # a) per-90 rates. npxG keeps direct free kicks: it is non-penalty xG, not a style filter.
    per90 = p["minutes"] / 90
    npxg = shots[~shots["is_own_goal"] & (shots["situation"] != "Penalty")].groupby(KEYS)["xG"].sum()
    p["npxg_per90"] = npxg.reindex(p.index, fill_value=0) / per90
    p["shots_per90"] = p["shots"] / per90
    for col, name in APP_SUMS.items():
        p[f"{name}_per90"] = g[col].sum() / per90

    # b) ratios; NaN where the denominator is 0
    style_xg = style.groupby(KEYS)["xG"].sum().reindex(p.index, fill_value=0)
    p["npxg_per_shot"] = (style_xg / p["shots"]).where(p["shots"] > 0)
    chain, buildup = g["xGChain"].sum(), g["xGBuildup"].sum()
    p["buildup_share_of_chain"] = (buildup / chain).where(chain > 0)

    # c) shot-style shares, optionally shrunk towards the pool-wide share
    # (with k = 0, NaN for players with no style shots)
    if shrinkage_k and priors is None:
        priors = style_priors(shots, last_actions)
    cats, cols = style_categories(shots, last_actions), category_columns(last_actions)
    for name in cats:
        p = p.join(shares(cats[name], p.index, cols[name], name,
                          shrinkage_k, priors[name] if shrinkage_k else None))

    pool = (p["starts"] >= min_starts) & (p["minutes"] >= min_minutes)
    if positions is not None:
        pool &= p["primary_position"].isin(positions)
    return p[pool].reset_index().sort_values(["league", "teams", "player"], ignore_index=True)


def report(profiles: pd.DataFrame, apps: pd.DataFrame) -> None:
    pd.set_option("display.width", 200)
    print(f"\n{len(profiles)} player-seasons in pool\n")
    print(profiles["league"].value_counts().to_string(), "\n")
    print(profiles["primary_position"].value_counts().to_string(), "\n")
    print("Top 10 by npxG per 90:")
    print(profiles.nlargest(10, "npxg_per90")[
        ["player", "teams", "league", "primary_position", "minutes", "npxg_per90", "shots_per90"]
    ].round(3).to_string(index=False), "\n")

    # Every start position, to spot wing-backs (who would also start at DL/DR/DML/DMR)
    starts = apps[apps["started"]].groupby(KEYS)["position"].agg(
        lambda s: ", ".join(f"{k} {v}" for k, v in s.value_counts().items())).rename("start_positions")
    wide = profiles[profiles["primary_position"].isin({"ML", "MR"})]
    print(f"15 random ML/MR players (of {len(wide)}):")
    print(wide.sample(min(15, len(wide)), random_state=0).join(starts, on=KEYS)[
        ["player", "teams", "league", "primary_position", "minutes", "start_positions"]
    ].to_string(index=False))


def main() -> None:
    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    profiles = build_profiles(shots, apps)
    profiles.to_parquet(PROCESSED / "profiles.parquet", index=False)
    print(f"wrote {PROCESSED / 'profiles.parquet'}: {len(profiles)} rows, {profiles.shape[1]} columns")
    report(profiles, apps)


if __name__ == "__main__":
    main()
