"""Tests for dedupe_match(), clean() and validate() on small hand-built data shaped like Understat's raw JSON."""
import pandas as pd

from scout.parse import clean, dedupe_match, validate

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


def raw_match(rosters_h, shots_h):
    return {"rosters": {"h": rosters_h, "a": {}}, "shots": {"h": shots_h, "a": []}}


def roster_entry(roster_id, player_id, roster_out="0"):
    return {"id": roster_id, "player_id": player_id, "roster_in": "0", "roster_out": roster_out}


def test_clean_match_unchanged_by_dedupe():
    m = raw_match({"50": roster_entry("50", "7"), "51": roster_entry("51", "8")},
                  [shot("1", "7"), shot("2", "8")])
    assert dedupe_match(m, "100") == m


def test_doubled_match_deduped():
    # Match 29482: Understat sent every roster entry and shot twice, under new ids
    m = raw_match({"50": roster_entry("50", "7"), "51": roster_entry("51", "7"),
                   "52": roster_entry("52", "8"), "53": roster_entry("53", "8")},
                  [shot("1", "7"), shot("2", "7"), shot("3", "8"), shot("4", "8")])
    out = dedupe_match(m, "100")
    assert list(out["rosters"]["h"]) == ["50", "52"]
    assert [s["id"] for s in out["shots"]["h"]] == ["1", "3"]


def test_duplicate_roster_differing_in_roster_out_deduped():
    m = raw_match({"50": roster_entry("50", "7", roster_out="60"),
                   "51": roster_entry("51", "7", roster_out="61")}, [])
    assert list(dedupe_match(m, "100")["rosters"]["h"]) == ["50"]


def test_distinct_shots_by_same_player_kept():
    m = raw_match({"50": roster_entry("50", "7")}, [shot("1", "7", X="0.9"), shot("2", "7", X="0.8")])
    assert len(dedupe_match(m, "100")["shots"]["h"]) == 2
