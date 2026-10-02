"""Tests for build_profiles() on small hand-built frames shaped like the processed parquet files."""
import numpy as np
import pandas as pd
import pytest

from scout.features import (ZONE_Y_EDGES, active_players, build_profiles, fit_shot_zones, recent_window, shot_grids,
                            transform_shot_zones)

LOW = {"min_starts": 1, "min_minutes": 0}  # thresholds off, for tests about the maths


def app(match_id, player_id=7, minutes=90, position="FW", xA=0.0, key_passes=0,
        xGChain=0.0, xGBuildup=0.0, team="Home FC"):
    return {"match_id": match_id, "player_id": player_id, "player": f"P{player_id}",
            "team": team, "league": "EPL", "season": 2025, "minutes": minutes,
            "position": position, "started": position != "Sub", "xA": xA,
            "key_passes": key_passes, "xGChain": xGChain, "xGBuildup": xGBuildup}


def shot(match_id, player_id=7, xG=0.1, situation="OpenPlay", result="MissedShots",
         shotType="RightFoot", lastAction="Pass", X=0.9, Y=0.5):
    return {"match_id": match_id, "player_id": player_id, "season": 2025, "xG": xG,
            "situation": situation, "result": result, "is_own_goal": result == "OwnGoal",
            "shotType": shotType, "lastAction": lastAction, "X": X, "Y": Y}


def build(shots, apps, **kw):
    """Profiles without shot zones unless asked: tiny pools can't fit the default NMF."""
    kw.setdefault("zones", 0)
    return build_profiles(pd.DataFrame(shots), pd.DataFrame(apps), **kw).set_index("player_id")


def test_per90_maths():
    apps = [app(1, minutes=90, xA=0.3, key_passes=2, xGChain=0.8, xGBuildup=0.2),
            app(2, minutes=45, xA=0.0, key_passes=1, xGChain=0.4, xGBuildup=0.4)]
    shots = [shot(1, xG=0.2), shot(1, xG=0.1), shot(2, xG=0.3)]
    p = build(shots, apps, **LOW).loc[7]
    assert p["minutes"] == 135
    assert p["npxg_per90"] == pytest.approx(0.6 / 135 * 90)
    assert p["shots_per90"] == pytest.approx(3 / 135 * 90)
    assert p["xa_per90"] == pytest.approx(0.3 / 135 * 90)
    assert p["key_passes_per90"] == pytest.approx(3 / 135 * 90)
    assert p["npxg_per_shot"] == pytest.approx(0.2)
    assert p["buildup_share_of_chain"] == pytest.approx(0.6 / 1.2)


def test_penalties_and_own_goals_excluded_from_style():
    shots = [shot(1, xG=0.2, shotType="LeftFoot"),
             shot(1, xG=0.76, situation="Penalty", result="Goal"),
             shot(1, xG=0.05, situation="DirectFreekick"),
             shot(1, xG=0.0, result="OwnGoal", shotType="Head")]
    p = build(shots, [app(1)], **LOW).loc[7]
    assert p["shots"] == 1
    assert p["npxg_per_shot"] == pytest.approx(0.2)
    assert p["shot_type_left_foot"] == 1.0
    assert p["shot_type_head"] == 0.0
    # npxG drops penalties (and own goals) but keeps direct free kicks
    assert p["npxg_per90"] == pytest.approx(0.25)


def test_subset_of_matches_uses_only_those_matches():
    shots = [shot(1, xG=0.2), shot(2, xG=0.5), shot(2, xG=0.5)]
    all_apps = [app(1, xA=0.1), app(2, xA=0.9)]
    p = build(shots, all_apps[:1], **LOW).loc[7]
    assert p["minutes"] == 90
    assert p["shots"] == 1
    assert p["npxg_per90"] == pytest.approx(0.2)
    assert p["xa_per90"] == pytest.approx(0.1)


def test_players_under_thresholds_excluded():
    apps = ([app(m, player_id=1) for m in range(10)]                         # qualifies
            + [app(m, player_id=2, minutes=250) for m in range(4)]           # 4 starts
            + [app(m, player_id=3, minutes=89) for m in range(10)]           # 890 minutes
            + [app(m, player_id=4) for m in range(5)]                        # 5 starts...
            + [app(m, player_id=4, position="Sub") for m in range(5, 10)]    # ...900 minutes
            + [app(m, player_id=5, position="DC") for m in range(10)])       # not attacking
    p = build([shot(0, player_id=1)], apps)
    assert sorted(p.index) == [1, 4]


def test_primary_position_ignores_sub_minutes():
    apps = ([app(m, position="FW", minutes=60) for m in range(5)]
            + [app(m, position="Sub", minutes=90) for m in range(5, 15)]
            + [app(m, position="DMC", minutes=50) for m in range(15, 20)])
    assert build([shot(0)], apps, **LOW).loc[7, "primary_position"] == "FW"


def shrink_case():
    shots = [shot(1, shotType="Head", lastAction="Cross"), shot(1, shotType="LeftFoot")]
    return shots, [app(1)]


def test_shrinkage_k0_changes_nothing():
    shots, apps = shrink_case()
    raw = build(shots, apps, **LOW)
    pd.testing.assert_frame_equal(build(shots, apps, **LOW, shrinkage_k=0), raw)
    assert raw.loc[7, "shot_type_head"] == 0.5


def test_shrinkage_pulls_shares_towards_prior():
    shots, apps = shrink_case()
    prior = {"shot_type": pd.Series({"head": 0.2, "left_foot": 0.3, "right_foot": 0.5, "other": 0.0}),
             "last_action": pd.Series({"Cross": 0.1, "Pass": 0.6, "Other": 0.1, "Missing": 0.2})}
    k10 = build(shots, apps, **LOW, shrinkage_k=10, priors=prior).loc[7]
    assert k10["shot_type_head"] == pytest.approx((1 + 10 * 0.2) / (2 + 10))
    assert k10.filter(like="shot_type_").sum() == pytest.approx(1)
    huge = build(shots, apps, **LOW, shrinkage_k=1e9, priors=prior).loc[7]
    for cat, share in prior["shot_type"].items():
        assert huge[f"shot_type_{cat}"] == pytest.approx(share, abs=1e-6)


def test_shrinkage_gives_prior_to_player_without_style_shots():
    shots = [shot(1, situation="Penalty", shotType="Head")]
    prior = {"shot_type": pd.Series({"head": 0.2, "left_foot": 0.3, "right_foot": 0.5, "other": 0.0}),
             "last_action": pd.Series({"Pass": 0.8, "Other": 0.1, "Missing": 0.1})}
    p = build(shots, [app(1)], **LOW, shrinkage_k=5, priors=prior).loc[7]
    assert p["shot_type_right_foot"] == pytest.approx(0.5)
    assert pd.isna(build(shots, [app(1)], **LOW).loc[7, "shot_type_head"])  # k = 0: undefined


def zone_shots(rng, player_id, y_range, n=20):
    """n open-play shots at random spots in the box, with Y (0 = attacker's right) in y_range."""
    return [shot(m, player_id=player_id, X=rng.uniform(0.85, 0.97), Y=rng.uniform(*y_range))
            for m in range(n)]


def test_shot_grid_sums_to_one_per_player():
    rng = np.random.default_rng(0)
    shots = pd.DataFrame(zone_shots(rng, 1, (0.2, 0.8), n=30) + zone_shots(rng, 2, (0.4, 0.6), n=3)
                         + [shot(0, player_id=2, situation="Penalty", X=0.885, Y=0.5),
                            shot(0, player_id=3, X=0.30, Y=0.5)])  # far out: clipped into first row
    grids = shot_grids(shots)
    assert sorted(grids.index.get_level_values("player_id")) == [1, 2, 3]
    assert np.allclose(grids.sum(axis=1), 1)
    assert (grids.to_numpy() >= 0).all()


def test_right_sided_player_loads_on_right_sided_components():
    rng = np.random.default_rng(1)
    shots = pd.DataFrame([s for p in range(10) for s in zone_shots(rng, p, (0.05, 0.3))]       # right
                         + [s for p in range(10, 20) for s in zone_shots(rng, p, (0.7, 0.95))]  # left
                         + zone_shots(rng, 99, (0.1, 0.25)))
    grids = shot_grids(shots)
    model = fit_shot_zones(grids.drop(index=99, level="player_id"), k=2)
    y_mid = (ZONE_Y_EDGES[:-1] + ZONE_Y_EDGES[1:]) / 2
    comps = model.components_.reshape(2, 10, 20)
    centre_y = (comps.sum(axis=1) * y_mid).sum(axis=1) / comps.sum(axis=(1, 2))
    weights = transform_shot_zones(model, grids).xs(99, level="player_id").iloc[0].to_numpy()
    assert weights.sum() == pytest.approx(1)
    assert weights[centre_y < 34].sum() > 0.9      # Y < 34 m is the attacker's right half


def test_zone_weights_nan_without_style_shots():
    rng = np.random.default_rng(2)
    shots = pd.DataFrame([s for p in range(6) for s in zone_shots(rng, p, (0.1, 0.9))])
    grids = shot_grids(shots)
    w = transform_shot_zones(fit_shot_zones(grids, k=2), grids.reindex([*grids.index, (42, 2025)]))
    assert w.iloc[-1].isna().all() and not w.iloc[:-1].isna().any().any()


def test_build_profiles_adds_zone_weights():
    rng = np.random.default_rng(3)
    shots = [s for p in range(8) for s in zone_shots(rng, p, (0.1, 0.9))]
    apps = [app(m, player_id=p) for p in range(8) for m in range(20)]
    p = build(shots, apps, **LOW, zones=3)
    assert list(p.filter(like="zone_").columns) == ["zone_1", "zone_2", "zone_3"]
    assert np.allclose(p.filter(like="zone_").sum(axis=1), 1)


def dated_app(match_id, date, season, minutes=90, player_id=7):
    return {**app(match_id, player_id=player_id, minutes=minutes),
            "date": pd.Timestamp(date), "season": season}


def test_recent_window_stops_at_window_minutes_newest_first():
    apps = pd.DataFrame([dated_app(m, f"2026-09-{m + 1:02d}", 2026) for m in range(25)])  # 25 x 90 min
    w = recent_window(apps, window_minutes=2000)
    assert len(w) == 23                                  # 22 x 90 = 1980 < 2000; the 23rd reaches it
    assert w["date"].min() == pd.Timestamp("2026-09-03")  # the two oldest are left out
    assert w["minutes"].sum() == 2070


def test_recent_window_crosses_season_boundary():
    apps = pd.DataFrame([dated_app(m, f"2026-0{8 + m // 10}-{m % 10 + 10}", 2026) for m in range(10)]   # 900 min
                        + [dated_app(100 + m, f"2026-05-{m + 1:02d}", 2025) for m in range(20)])      # older season
    w = recent_window(apps, window_minutes=2000)
    assert w["minutes"].sum() == 2070                    # 10 new + 13 newest of the old season
    old = w[w["match_id"] >= 100]
    assert len(old) == 13 and old["date"].min() == pd.Timestamp("2026-05-08")
    assert set(w["season"]) == {2026}                    # one profile, labelled by its newest season


def test_recent_window_keeps_everything_under_the_limit_and_per_player():
    apps = pd.DataFrame([dated_app(m, f"2026-09-{m + 1:02d}", 2026, player_id=1) for m in range(5)]
                        + [dated_app(m, f"2026-09-{m + 1:02d}", 2026, player_id=2) for m in range(30)])
    w = recent_window(apps, window_minutes=2000)
    assert (w["player_id"] == 1).sum() == 5
    assert (w["player_id"] == 2).sum() == 23


def test_active_players_need_an_appearance_in_the_latest_season():
    apps = pd.DataFrame([dated_app(1, "2026-09-01", 2026, player_id=1),
                         dated_app(2, "2026-05-01", 2025, player_id=1),
                         dated_app(3, "2026-05-01", 2025, player_id=2)])
    assert active_players(apps).to_dict() == {1: True, 2: False}
