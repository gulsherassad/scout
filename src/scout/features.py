"""Build player style profiles: one row per player-season of attacking players.

Everything is computed from the rows passed in, never from season totals, so
build_profiles() works on any subset of matches (e.g. half a season, for validation).
"""
from pathlib import Path

import argparse
import json

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import NMF

PROCESSED = Path("data/processed")

# Player pool. FWL/FWR are Understat's labels for the two strikers in a front two.
ATTACKING_POSITIONS = {"FW", "FWL", "FWR", "AMC", "AML", "AMR", "ML", "MR"}
MIN_STARTS = 5
MIN_MINUTES = 900

# Recent mode: each player's newest league appearances, across seasons, up to this many minutes
WINDOW_MINUTES = 2000

# Shots used for style features
STYLE_EXCLUDED_SITUATIONS = {"Penalty", "DirectFreekick"}
RARE_LAST_ACTION_SHARE = 0.02  # lastAction values below this share of shots become "Other"
SHOT_TYPES = {"Head": "head", "LeftFoot": "left_foot", "RightFoot": "right_foot"}  # rest -> "other"

# Shot-location zones (Decroos et al., "Player Vectors"). Understat X/Y are fractions of the
# pitch: X runs towards the attacked goal, Y = 0 is the attacker's right touchline.
PITCH_LENGTH, PITCH_WIDTH = 105, 68
ZONE_X_EDGES = np.linspace(70, 105, 11)  # 3.5 m cells; shots from further out go in the first row
ZONE_Y_EDGES = np.linspace(0, 68, 21)    # 3.4 m cells, full width, not mirrored
ZONE_SMOOTHING = 1.0                     # Gaussian sigma, in cells
ZONES = 6                                # NMF components in default profiles (experiments.md); 0 = none

KEYS = ["player_id", "season"]
APP_SUMS = {"xA": "xa", "key_passes": "key_passes", "xGChain": "xgchain", "xGBuildup": "xgbuildup"}


def style_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """Shots that say something about a player's style: no own goals, penalties or direct free kicks."""
    return shots[~shots["is_own_goal"] & ~shots["situation"].isin(STYLE_EXCLUDED_SITUATIONS)]


def shots_in(shots: pd.DataFrame, apps: pd.DataFrame) -> pd.DataFrame:
    """Shots taken in the appearances in `apps`, labelled with the appearances' season
    (which recent mode sets to the window's season)."""
    keys = apps[["match_id", "player_id", "season"]].drop_duplicates()
    return shots.drop(columns="season").merge(keys, on=["match_id", "player_id"])


def recent_window(apps: pd.DataFrame, window_minutes: int = WINDOW_MINUTES) -> pd.DataFrame:
    """Each player's most recent appearances, newest first across seasons, up to and
    including the one that reaches `window_minutes`. Every row's season is set to the
    season of the player's newest appearance, so the window is one player-season."""
    a = apps.sort_values(["player_id", "date", "match_id"], ascending=[True, False, False])
    before = a.groupby("player_id")["minutes"].cumsum() - a["minutes"]
    window = a[before < window_minutes].copy()
    window["season"] = window.groupby("player_id")["season"].transform("max")
    return window


def active_players(apps: pd.DataFrame) -> pd.Series:
    """True for players with at least one league appearance in the latest season in `apps`."""
    current = apps["season"].max()
    return apps.groupby("player_id")["season"].max().eq(current).rename("active")


def window_dates(window: pd.DataFrame) -> pd.DataFrame:
    """First and last appearance date of each player's window."""
    return window.groupby(KEYS)["date"].agg(window_start="min", window_end="max")


def shot_grids(shots: pd.DataFrame) -> pd.DataFrame:
    """Per player-season, a smoothed histogram of style-shot locations over the attacking
    area, flattened to one column per cell and normalised to sum to 1 (shape, not volume).
    Players without style shots are left out."""
    nx, ny = len(ZONE_X_EDGES) - 1, len(ZONE_Y_EDGES) - 1
    s = style_shots(shots)
    if s.empty:
        return pd.DataFrame(columns=range(nx * ny), index=pd.MultiIndex.from_tuples([], names=KEYS))
    x = (s["X"] * PITCH_LENGTH).clip(ZONE_X_EDGES[0], ZONE_X_EDGES[-1] - 1e-9)
    y = (s["Y"] * PITCH_WIDTH).clip(ZONE_Y_EDGES[0], ZONE_Y_EDGES[-1] - 1e-9)
    cell = (np.digitize(x, ZONE_X_EDGES) - 1) * ny + (np.digitize(y, ZONE_Y_EDGES) - 1)
    counts = pd.crosstab([s[k] for k in KEYS], cell).reindex(columns=range(nx * ny), fill_value=0)
    grid = gaussian_filter(counts.to_numpy(float).reshape(-1, nx, ny),
                           sigma=(0, ZONE_SMOOTHING, ZONE_SMOOTHING), mode="constant")
    grid /= grid.sum(axis=(1, 2), keepdims=True)
    return pd.DataFrame(grid.reshape(len(grid), -1), index=counts.index)


def fit_shot_zones(grids: pd.DataFrame, k: int) -> NMF:
    """NMF with k components on the player x grid-cell matrix."""
    return NMF(n_components=k, init="nndsvda", max_iter=2000, random_state=0).fit(
        grids.dropna().to_numpy())


def transform_shot_zones(model: NMF, grids: pd.DataFrame) -> pd.DataFrame:
    """Each player's component weights, normalised to sum to 1 (NaN without style shots)."""
    w = model.transform(grids.fillna(0).to_numpy())
    total = w.sum(axis=1, keepdims=True)
    w = np.divide(w, total, out=np.full_like(w, np.nan), where=total > 0)
    return pd.DataFrame(w, index=grids.index, columns=[f"zone_{i + 1}" for i in range(w.shape[1])])


def zone_model(shots: pd.DataFrame, apps: pd.DataFrame, profiles: pd.DataFrame, k: int = ZONES) -> NMF:
    """The NMF behind `profiles`' zone weights: the same fit as build_profiles(zones=k)."""
    keys = profiles.set_index(KEYS).index
    grids = shot_grids(shots_in(shots, apps.merge(profiles[KEYS], on=KEYS))).reindex(keys)
    return fit_shot_zones(grids, k)


def zone_centre(component: np.ndarray) -> tuple[float, float]:
    """A component's centre of mass: metres from the goal line, and metres to the
    attacker's right of the centre line (negative = left)."""
    nx, ny = len(ZONE_X_EDGES) - 1, len(ZONE_Y_EDGES) - 1
    w = component.reshape(nx, ny) / component.sum()
    x_mid = (ZONE_X_EDGES[:-1] + ZONE_X_EDGES[1:]) / 2
    y_mid = (ZONE_Y_EDGES[:-1] + ZONE_Y_EDGES[1:]) / 2
    return PITCH_LENGTH - (w.sum(axis=1) * x_mid).sum(), PITCH_WIDTH / 2 - (w.sum(axis=0) * y_mid).sum()


def describe_zone(component: np.ndarray) -> str:
    """Plain-language label, e.g. "shots from the right of the box"."""
    depth, lateral = zone_centre(component)
    side = "" if abs(lateral) < 4 else ("right" if lateral > 0 else "left")
    if depth < 9:
        where = "close range" + (f", {side} side" if side else "")
    elif depth < 15:
        where = f"the {side or 'centre'} of the box"
    elif depth < 20:
        where = "the edge of the box" + (f", {side}" if side else "")
    else:
        where = "outside the box" + (f", {side}" if side else "")
    return f"shots from {where}"


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
                   priors: dict[str, pd.Series] | None = None,
                   zones: int = ZONES) -> pd.DataFrame:
    """One row per player-season in the pool, built only from the appearances in `apps`.

    Shots are restricted to (match_id, player_id) pairs in `apps`, so passing a subset of
    appearances is enough to build profiles on a subset of matches.
    `last_actions` fixes the lastAction categories; by default they come from `shots`.
    Pass the full-data categories when comparing profiles built on different subsets,
    so both have the same columns. `positions=None` turns off the primary-position filter.
    `shrinkage_k` > 0 shrinks shot-style shares towards `priors` (see style_priors();
    by default computed from `shots`), adding k pseudo-shots at the pool-wide shares.
    `zones` > 0 adds shot-location zone weights from an NMF with that many components,
    fitted on the shot grids of the players in the returned pool.
    """
    shots = shots_in(shots, apps)
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
    p = p[pool]
    if zones:
        grids = shot_grids(shots).reindex(p.index)
        p = p.join(transform_shot_zones(fit_shot_zones(grids, zones), grids))
    return p.reset_index().sort_values(["league", "teams", "player"], ignore_index=True)


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
    p = argparse.ArgumentParser(description="Build player style profiles.")
    p.add_argument("--mode", choices=("season", "recent"), default="season",
                   help=f"one profile per player-season, or per player from their newest "
                        f"{WINDOW_MINUTES} league minutes across seasons")
    args = p.parse_args()

    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    if args.mode == "recent":
        active = active_players(apps)
        apps = recent_window(apps)
        path = PROCESSED / "profiles_recent.parquet"
    else:
        path = PROCESSED / "profiles.parquet"
    profiles = build_profiles(shots, apps)
    if args.mode == "recent":
        profiles = profiles.join(window_dates(apps), on=KEYS).join(active, on="player_id")
        print(f"active (a league appearance in {apps['season'].max()}/{(apps['season'].max() + 1) % 100:02d}): "
              f"{profiles['active'].sum()} of {len(profiles)}")
    profiles.to_parquet(path, index=False)
    print(f"wrote {path}: {len(profiles)} rows, {profiles.shape[1]} columns")
    if ZONES:
        model = zone_model(shots, apps, profiles)
        nx, ny = len(ZONE_X_EDGES) - 1, len(ZONE_Y_EDGES) - 1
        zones = [{"column": f"zone_{i + 1}", "label": describe_zone(c),
                  "grid": (c / c.sum()).reshape(nx, ny).round(6).tolist()}  # [x row][y col], sums to 1
                 for i, c in enumerate(model.components_)]
        zone_path = path.with_name(path.stem.replace("profiles", "zones") + ".json")
        zone_path.write_text(json.dumps({
            "pitch": {"length": PITCH_LENGTH, "width": PITCH_WIDTH},
            "x_edges": ZONE_X_EDGES.tolist(), "y_edges": ZONE_Y_EDGES.tolist(),
            "y_zero_side": "attacker's right", "zones": zones}))
        print(f"wrote {zone_path}: " + "; ".join(f"{z['column']} = {z['label']}" for z in zones))
    if args.mode == "recent":
        print(f"window end: {profiles['window_end'].min().date()} to {profiles['window_end'].max().date()}; "
              f"window start: {profiles['window_start'].min().date()} to {profiles['window_start'].max().date()}")
    report(profiles, apps)


if __name__ == "__main__":
    main()
