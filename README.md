# scout

A football scouting engine that finds statistically similar attacking players across Europe's top 5 leagues, using current-season data from [Understat](https://understat.com). A weekly-updating pipeline downloads new matches, turns them into clean shot and appearance tables, and validates them before anything downstream uses them.

**Status:** early development. Ingestion and parsing are done.

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m scout.ingest --season 2025   # download match data to data/raw/
python -m scout.parse                  # build data/processed/*.parquet and validate
pytest
```

## Known data issues

- **Own goals appear as shot rows.** Understat lists an own goal in the shots data (result `OwnGoal`, xG 0), credited to the player who scored it, but counts it under the roster's `own_goals`, not `shots`. These rows are kept and flagged with `is_own_goal`; filter them out for shot-based analysis.
- **Match 29482 (Real Oviedo vs Villarreal, La Liga 2025/26) is duplicated upstream.** Understat sends every roster entry and shot twice, which also doubles its own xG for the match. `scout.parse` removes the duplicates and prints a note when it does.
- **Cached matches are never re-fetched.** `scout.ingest` downloads each finished match once, so any later correction Understat makes to that match is not picked up. To refresh a match, delete its file in `data/raw/matches/` and run ingest again.

## Data

All match data comes from [understat.com](https://understat.com). Credit for the data goes to Understat. It is not included in or redistributed by this repository: `data/` is gitignored, and each user fetches it themselves with `scout.ingest`. It is fetched for non-commercial personal use only.
