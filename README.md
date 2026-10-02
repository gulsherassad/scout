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

## Data

All match data comes from [understat.com](https://understat.com). Credit for the data goes to Understat. It is not included in or redistributed by this repository: `data/` is gitignored, and each user fetches it themselves with `scout.ingest`. It is fetched for non-commercial personal use only.
