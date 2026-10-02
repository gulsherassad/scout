"""Tests for clean() and validate() on small hand-built frames shaped like Understat's raw data."""
import pandas as pd

from scout.parse import clean, validate

MATCH = {"match_id": "100", "date": "2025-08-16 15:00:00"}


def shot(shot_id, player_id, result="MissedShots", X="0.9", team="Home FC"):
    return {"id": shot_id, "player_id": player_id, "player": f"P{player_id}", "team": team,
            "result": result, "X": X, "Y": "0.5", "xG": "0.1", "minute": "10",
            "lastAction": "None", **MATCH}


def app(roster_id, player_id, shots="0", own_goals="0", team="Home FC"):
    nums = {"goals": "0", "xG": "0", "xA": "0", "assists": "0", "key_passes": "0",
            "xGChain": "0", "xGBuildup": "0", "yellow_card": "0", "red_card": "0"}
    return {**nums, "id": roster_id, "player_id": player_id, "player": f"P{player_id}",
            "team": team, "team_id": "1", "time": "90", "position": "FW",
            "shots": shots, "own_goals": own_goals, **MATCH}


def run(shot_rows, app_rows):
    shots, apps = clean(pd.DataFrame(shot_rows), pd.DataFrame(app_rows))
    return shots, apps, validate(shots, apps)


def test_clean_data_passes():
    shots, apps, problems = run([shot("1", "7"), shot("2", "7"), shot("3", "8")],
                                [app("50", "7", shots="2"), app("51", "8", shots="1")])
    assert problems == []
    for col in ("shot_id", "match_id", "player_id"):
        assert shots[col].dtype == "int64"
    for col in ("roster_id", "match_id", "player_id", "team_id"):
        assert apps[col].dtype == "int64"


def test_own_goal_not_counted_as_shot():
    # Understat: one real shot plus one own goal in the shots list; roster says shots=1, own_goals=1
    shots, _, problems = run([shot("1", "7"), shot("2", "7", result="OwnGoal", X="0.04")],
                             [app("50", "7", shots="1", own_goals="1")])
    assert problems == []
    assert shots.set_index("shot_id")["is_own_goal"].to_dict() == {1: False, 2: True}


def test_genuine_shot_count_mismatch_caught():
    _, _, problems = run([shot("1", "7")], [app("50", "7", shots="2")])
    assert len(problems) == 1
    assert "roster shots != non-own-goal rows" in problems[0]
    assert "P7" in problems[0]


def test_duplicate_appearance_caught():
    _, _, problems = run([shot("1", "7")], [app("50", "7", shots="1"), app("51", "7", shots="1")])
    assert any("duplicate (match_id, player_id)" in p for p in problems)


def test_x_out_of_range_caught():
    _, _, problems = run([shot("1", "7", X="1.4")], [app("50", "7", shots="1")])
    assert len(problems) == 1
    assert "X outside [0, 1]" in problems[0]
