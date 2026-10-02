"""Turn cached raw JSON into two clean tables: shots and appearances.

Reads only from data/raw (no network), so it can be re-run any time.
"""
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")

SHOT_NUM = ["X", "Y", "xG", "minute"]
APP_NUM = ["minutes", "goals", "own_goals", "shots", "xG", "xA", "assists",
           "key_passes", "xGChain", "xGBuildup", "yellow_card", "red_card"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def parse_league_season(league_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flatten every cached match of one league-season into shot rows and appearance rows."""
    league, season = league_file.stem.rsplit("_", 1)
    fixtures = [f for f in load_json(league_file)["dates"] if f["isResult"]]

    shot_rows, app_rows = [], []
    for f in fixtures:
        path = RAW / "matches" / f"{f['id']}.json"
        if not path.exists():
            continue  # not downloaded yet; the next ingest run will fetch it
        m = load_json(path)
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

    apps = apps.rename(columns={"id": "roster_id", "time": "minutes"})
    apps[APP_NUM] = apps[APP_NUM].apply(pd.to_numeric)
    apps["started"] = apps["position"] != "Sub"

    for df in (shots, apps):
        df["date"] = pd.to_datetime(df["date"])
    return shots, apps


def validate(shots: pd.DataFrame, apps: pd.DataFrame) -> list[str]:
    """Return a list of problems. Empty list = data passed every check."""
    problems = []

    # Each row must be unique
    if shots["shot_id"].duplicated().any():
        problems.append(f"{shots['shot_id'].duplicated().sum()} duplicate shot_id")
    if apps.duplicated(["match_id", "player_id"]).any():
        problems.append(f"{apps.duplicated(['match_id', 'player_id']).sum()} duplicate (match_id, player_id)")

    # Values must be in sensible ranges
    for col in ("X", "Y", "xG"):
        bad = ~shots[col].between(0, 1)
        if bad.any():
            problems.append(f"{bad.sum()} shots with {col} outside [0, 1]")
    if (apps["minutes"] < 0).any() or (apps["minutes"] > 130).any():
        problems.append("appearances with impossible minutes")

    # Every shot must belong to a player who played in that match
    keys = apps.set_index(["match_id", "player_id"]).index
    orphan = ~shots.set_index(["match_id", "player_id"]).index.isin(keys)
    if orphan.any():
        problems.append(f"{orphan.sum()} shots with no matching appearance")

    # The roster's shot count should match the number of rows in the shots table
    counted = shots.groupby(["match_id", "player_id"]).size()
    reported = apps.set_index(["match_id", "player_id"])["shots"]
    diff = reported.sub(counted, fill_value=0)
    if (diff != 0).any():
        problems.append(f"{(diff != 0).sum()} appearances where roster shot count != shots table")

    return problems


def main() -> None:
    league_files = sorted((RAW / "league").glob("*.json"))
    parts = [parse_league_season(f) for f in league_files]
    shots = pd.concat([p[0] for p in parts], ignore_index=True)
    apps = pd.concat([p[1] for p in parts], ignore_index=True)
    shots, apps = clean(shots, apps)

    problems = validate(shots, apps)
    for p in problems:
        print("CHECK FAILED:", p)

    OUT.mkdir(parents=True, exist_ok=True)
    shots.to_parquet(OUT / "shots.parquet", index=False)
    apps.to_parquet(OUT / "appearances.parquet", index=False)
    print(f"shots: {len(shots):,} rows | appearances: {len(apps):,} rows | "
          f"{len(problems)} checks failed")


if __name__ == "__main__":
    main()