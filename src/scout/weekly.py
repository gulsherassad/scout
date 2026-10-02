"""Weekly pipeline run (GitHub Actions): ingest, parse, features, market, evaluate.

Writes data/processed/run_status.json in every case, and exits non-zero if parse
validation fails or recall@10 falls more than QUALITY_MARGIN below the logged baseline.

    python -m scout.weekly
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd

from scout.evaluate import evaluate, rates_style
from scout.features import KEYS, PROCESSED, recent_window

SEASONS = (2025, 2026)
# Recent-mode baseline from reports/experiments.md (row "--mode recent", commit 5823926)
BASELINE_RECALL_AT_10 = 0.249
QUALITY_MARGIN = 0.05
STATUS = PROCESSED / "run_status.json"


def run(*args: str) -> subprocess.CompletedProcess:
    """Run a `python -m scout...` step, echoing its output as it would appear in a terminal."""
    print(f"\n$ python -m {' '.join(args)}", flush=True)
    p = subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True)
    print(p.stdout + p.stderr, end="", flush=True)
    return p


def fetched_counts(output: str) -> tuple[int, int]:
    """(matches fetched, failed) from ingest's final 'done: N fetched, M failed' line."""
    m = re.search(r"done: (\d+) fetched, (\d+) failed", output)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def recent_recall_at_10() -> tuple[float, int]:
    """Mean recall@10 of all features on the recent pool, over the standard splits."""
    shots = pd.read_parquet(PROCESSED / "shots.parquet")
    apps = recent_window(pd.read_parquet(PROCESSED / "appearances.parquet"))
    pool = pd.read_parquet(PROCESSED / "profiles_recent.parquet").set_index(KEYS)
    ranks, _ = evaluate(shots, apps, pool)
    return float(rates_style(ranks, pool).groupby("seed")["hit@10"].mean().mean()), len(pool)


def quality_ok(recall: float, baseline: float = BASELINE_RECALL_AT_10, margin: float = QUALITY_MARGIN) -> bool:
    return recall >= baseline - margin


def git_sha() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def write_status(status: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=1))
    print(f"\n{STATUS}:\n{json.dumps(status, indent=1)}")


def main() -> None:
    status = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_sha": git_sha(),
              "matches_fetched": 0, "fetch_failures": 0, "checks_passed": None,
              "recall_at_10": None, "baseline_recall_at_10": BASELINE_RECALL_AT_10,
              "quality_ok": None, "pool_size": None, "failed_step": None}

    for season in SEASONS:
        p = run("scout.ingest", "--season", str(season))
        fetched, failed = fetched_counts(p.stdout)
        status["matches_fetched"] += fetched
        status["fetch_failures"] += failed
        if p.returncode and not failed:  # crashed (e.g. league page unreachable), not just missed matches
            status["fetch_failures"] += 1
        if p.returncode:
            # Missed matches are fetched next week; flag in the log but keep going
            print(f"::warning::ingest {season}: {failed} match(es) failed after retries")

    p = run("scout.parse")
    status["checks_passed"] = p.returncode == 0
    if p.returncode:
        status["failed_step"] = "parse"
        write_status(status)
        print("::error::parse validation failed; no processed data was written")
        sys.exit(1)

    for step in (("scout.features",), ("scout.features", "--mode", "recent"), ("scout.market",)):
        p = run(*step)
        if p.returncode:
            status["failed_step"] = " ".join(step)
            write_status(status)
            sys.exit(p.returncode)

    recall, n = recent_recall_at_10()
    status |= {"recall_at_10": round(recall, 3), "pool_size": n, "quality_ok": quality_ok(recall)}
    write_status(status)
    if not status["quality_ok"]:
        print(f"::error::quality alarm: recall@10 {recall:.3f} is more than {QUALITY_MARGIN} below the "
              f"baseline {BASELINE_RECALL_AT_10}")
        sys.exit(1)


if __name__ == "__main__":
    main()
