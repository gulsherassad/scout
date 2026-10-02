"""Turn cached raw JSON into two clean tables: shots and appearances.

Reads only from data/raw (no network), so it can be re-run any time.
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")

SHOT_NUM = ["X", "Y", "xG", "minute"]
APP_NUM = ["minutes", "goals", "own_goals", "shots", "xG", "xA", "assists",
           "key_passes", "xGChain", "xGBuildup", "yellow_card", "red_card"]
SHOT_IDS = ["shot_id", "match_id", "player_id"]
APP_IDS = ["roster_id", "match_id", "player_id", "team_id"]
MAX_ROWS_SHOWN = 10


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def dedupe_match(m: dict, match_id: str) -> dict:
    """Drop entries Understat sent twice within a side (seen in match 29482).

    A player appears at most once per side, so roster entries are deduped by player_id
    (copies can differ in roster_in/roster_out, which point at other roster ids).
    Shots are duplicates when every field except id matches.
    """
    rosters, shots, dropped_r, dropped_s = {}, {}, 0, 0
    for side in ("h", "a"):
        seen_players, kept = set(), {}
        for key, r in m["rosters"][side].items():
            if r["player_id"] in seen_players:
                dropped_r += 1
            else:
                seen_players.add(r["player_id"])
                kept[key] = r
        rosters[side] = kept

        seen_shots, kept = set(), []
        for s in m["shots"][side]:
            content = tuple(sorted((k, str(v)) for k, v in s.items() if k != "id"))
            if content in seen_shots:
                dropped_s += 1
            else:
                seen_shots.add(content)
                kept.append(s)
        shots[side] = kept

    if dropped_r or dropped_s:
        print(f"match {match_id}: dropped {dropped_r} duplicate roster entries, "
              f"{dropped_s} duplicate shots (Understat sent them twice)")
    return {**m, "rosters": rosters, "shots": shots}


def parse_league_season(league_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flatten every cached match of one league-season into shot rows and appearance rows."""
    league, season = league_file.stem.rsplit("_", 1)
    fixtures = [f for f in load_json(league_file)["dates"] if f["isResult"]]

    shot_rows, app_rows = [], []
    for f in fixtures:
        path = RAW / "matches" / f"{f['id']}.json"
        if not path.exists():
            continue  # not downloaded yet; the next ingest run will fetch it
        m = dedupe_match(load_json(path), f["id"])
        meta = {"match_id": f["id"], "league": league, "season": int(season),
                "date": f["datetime"]}
        teams = {"h": f["h"]["title"], "a": f["a"]["title"]}

        for side in ("h", "a"):
            for s in m["shots"][side]:
                shot_rows.append({**s, **meta, "team": teams[side]})
            for r in m["rosters"][side].values():
                app_rows.append({**r, **meta, "team": teams[side]})

    return pd.DataFrame(shot_rows), pd.DataFrame(app_rows)


def clean(shots: pd.DataFrame, apps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fix types and names. Understat sends every value as a string."""
    shots = shots.rename(columns={"id": "shot_id"})
    shots[SHOT_NUM] = shots[SHOT_NUM].apply(pd.to_numeric)
    shots["lastAction"] = shots["lastAction"].replace("None", pd.NA)
    shots["is_own_goal"] = shots["result"] == "OwnGoal"
    shots[SHOT_IDS] = shots[SHOT_IDS].astype("int64")

    apps = apps.rename(columns={"id": "roster_id", "time": "minutes"})
    apps[APP_NUM] = apps[APP_NUM].apply(pd.to_numeric)
    apps["started"] = apps["position"] != "Sub"
    apps[APP_IDS] = apps[APP_IDS].astype("int64")

    for df in (shots, apps):
        df["date"] = pd.to_datetime(df["date"])
    return shots, apps


def problem(msg: str, rows: pd.DataFrame, cols: list[str]) -> str:
    """Describe a failed check: the count, then the first few offending rows."""
    table = rows[cols].head(MAX_ROWS_SHOWN).to_string(index=False)
    more = f"\n  ... and {len(rows) - MAX_ROWS_SHOWN} more" if len(rows) > MAX_ROWS_SHOWN else ""
    return f"{len(rows)} {msg}\n  " + table.replace("\n", "\n  ") + more


def count_mismatches(apps: pd.DataFrame, shots: pd.DataFrame, roster_col: str) -> pd.DataFrame:
    """Appearances whose roster `roster_col` differs from their number of rows in `shots`."""
    keys = ["match_id", "player_id"]
    counted = shots.groupby(keys).size().rename("shots_table").reset_index()
    df = apps[keys + ["player", "team", roster_col]].merge(counted, on=keys, how="left")
    df["shots_table"] = df["shots_table"].fillna(0).astype(int)
    return df[df[roster_col] != df["shots_table"]].rename(columns={roster_col: "roster"})


def validate(shots: pd.DataFrame, apps: pd.DataFrame) -> list[str]:
    """Return a list of problems. Empty list = data passed every check."""
    problems = []
    keys = ["match_id", "player_id"]

    # Each row must be unique
    dup = shots["shot_id"].duplicated(keep=False)
    if dup.any():
        problems.append(problem("shots with duplicate shot_id", shots[dup],
                                ["shot_id", "match_id", "player", "team", "minute"]))
    dup = apps.duplicated(keys, keep=False)
    if dup.any():
        problems.append(problem("appearances with duplicate (match_id, player_id)", apps[dup],
                                ["match_id", "player_id", "player", "team"]))

    # Values must be in sensible ranges
    for col in ("X", "Y", "xG"):
        bad = ~shots[col].between(0, 1)
        if bad.any():
            problems.append(problem(f"shots with {col} outside [0, 1]", shots[bad],
                                    ["match_id", "player", "team", col]))
    bad = ~apps["minutes"].between(0, 130)
    if bad.any():
        problems.append(problem("appearances with impossible minutes", apps[bad],
                                ["match_id", "player", "team", "minutes"]))

    # Every shot must belong to a player who played in that match
    orphan = ~shots.set_index(keys).index.isin(apps.set_index(keys).index)
    if orphan.any():
        problems.append(problem("shots with no matching appearance", shots[orphan],
                                ["match_id", "player_id", "player", "team"]))

    # Understat lists own goals as rows in the shots data (result "OwnGoal", xG 0,
    # credited to the player who put it in their own net) but the roster counts them
    # under `own_goals`, not `shots`. So each kind is reconciled separately.
    bad = count_mismatches(apps, shots[~shots["is_own_goal"]], "shots")
    if len(bad):
        problems.append(problem("appearances where roster shots != non-own-goal rows in shots table",
                                bad, ["match_id", "player", "team", "roster", "shots_table"]))
    bad = count_mismatches(apps, shots[shots["is_own_goal"]], "own_goals")
    if len(bad):
        problems.append(problem("appearances where roster own_goals != own-goal rows in shots table",
                                bad, ["match_id", "player", "team", "roster", "shots_table"]))

    return problems


def main() -> None:
    league_files = sorted((RAW / "league").glob("*.json"))
    parts = [parse_league_season(f) for f in league_files]
    shots = pd.concat([p[0] for p in parts], ignore_index=True)
    apps = pd.concat([p[1] for p in parts], ignore_index=True)
    shots, apps = clean(shots, apps)

    problems = validate(shots, apps)
    if problems:
        for p in problems:
            print("CHECK FAILED:", p)
        # Downstream steps must never read data that failed validation
        print(f"{len(problems)} checks failed; parquet files not written")
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    shots.to_parquet(OUT / "shots.parquet", index=False)
    apps.to_parquet(OUT / "appearances.parquet", index=False)
    print(f"shots: {len(shots):,} rows | appearances: {len(apps):,} rows | all checks passed")


if __name__ == "__main__":
    main()