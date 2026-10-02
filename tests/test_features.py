"""Tests for build_profiles() on small hand-built frames shaped like the processed parquet files."""
import pandas as pd
import pytest

from scout.features import build_profiles

LOW = {"min_starts": 1, "min_minutes": 0}  # thresholds off, for tests about the maths


def app(match_id, player_id=7, minutes=90, position="FW", xA=0.0, key_passes=0,
        xGChain=0.0, xGBuildup=0.0, team="Home FC"):
    return {"match_id": match_id, "player_id": player_id, "player": f"P{player_id}",
            "team": team, "league": "EPL", "season": 2025, "minutes": minutes,
            "position": position, "started": position != "Sub", "xA": xA,
            "key_passes": key_passes, "xGChain": xGChain, "xGBuildup": xGBuildup}


def shot(match_id, player_id=7, xG=0.1, situation="OpenPlay", result="MissedShots",
         shotType="RightFoot", lastAction="Pass"):
    return {"match_id": match_id, "player_id": player_id, "season": 2025, "xG": xG,
            "situation": situation, "result": result, "is_own_goal": result == "OwnGoal",
            "shotType": shotType, "lastAction": lastAction}


def build(shots, apps, **kw):
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
