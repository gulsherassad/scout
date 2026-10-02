"""Download Understat data and cache the raw JSON on disk.

Finished matches never change, so each one is fetched exactly once.
Re-running only downloads matches played since the last run.
"""
import argparse
import json
import time
from pathlib import Path

import requests

BASE = "https://understat.com"
HEADERS = {"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0"}
RAW = Path("data/raw")
LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
DELAY_S = 1.5  # pause between requests
RETRY_WAITS_S = (2, 4, 8)  # after a failed request, wait this long and retry; then give up

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_json(path: str, session: requests.Session = SESSION, sleep=time.sleep) -> dict:
    """GET a JSON endpoint, retrying failed requests (network errors, HTTP errors, bad JSON)
    with exponential backoff. Raises the last error once the retries are used up."""
    for attempt, wait in enumerate((*RETRY_WAITS_S, None)):
        try:
            r = session.get(f"{BASE}/{path}", timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if wait is None:
                raise
            print(f"  retry {attempt + 1}/{len(RETRY_WAITS_S)} for {path} in {wait}s: {e}")
            sleep(wait)


def save_json(data: dict, dest: Path) -> None:
    """Write to a temp file, then rename: an interrupted run never leaves a half-written file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(dest)


def match_path(match_id: str) -> Path:
    return RAW / "matches" / f"{match_id}.json"


def ingest_league(league: str, season: int) -> dict:
    # League data changes every week, so always refetch it.
    data = fetch_json(f"getLeagueData/{league}/{season}")
    save_json(data, RAW / "league" / f"{league}_{season}.json")

    finished = [f["id"] for f in data["dates"] if f["isResult"]]
    todo = [mid for mid in finished if not match_path(mid).exists()]
    print(f"{league} {season}: {len(finished)} finished, {len(todo)} to fetch")

    failed = []
    for i, mid in enumerate(todo, 1):
        try:
            save_json(fetch_json(f"getMatchData/{mid}"), match_path(mid))
        except (requests.RequestException, ValueError) as e:
            failed.append(mid)
            print(f"  failed {mid}: {e}")
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}")
        time.sleep(DELAY_S)

    return {"league": league, "season": season, "finished": len(finished),
            "fetched": len(todo) - len(failed), "failed": failed}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, required=True, help="start year, e.g. 2025 = 2025/26")
    p.add_argument("--leagues", nargs="+", default=LEAGUES)
    args = p.parse_args()

    results = [ingest_league(lg, args.season) for lg in args.leagues]
    failed = [m for r in results for m in r["failed"]]
    print(f"done: {sum(r['fetched'] for r in results)} fetched, {len(failed)} failed")
    if failed:
        raise SystemExit(1)  # non-zero exit so a scheduler notices


if __name__ == "__main__":
    main()