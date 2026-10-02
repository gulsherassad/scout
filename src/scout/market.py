"""Join Transfermarkt market data (transfermarkt-datasets, CC0) to the player pool.

The project stopped updating in July 2026, so this is a fixed snapshot. Tables are
downloaded once into data/raw/transfermarkt/ and never re-fetched.

    python -m scout.market
"""
import difflib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.optimize import linear_sum_assignment

from scout.features import KEYS, PROCESSED

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
RAW = Path("data/raw/transfermarkt")
TABLES = ["players", "player_valuations", "clubs", "appearances", "competitions", "games"]
CLUB_MAP = Path("data_mappings/clubs.csv")
SAMPLE = Path("reports/match_sample.md")

SEASON = 2025  # both sources label 2025/26 as 2025
LEAGUES = {"EPL": "GB1", "La_liga": "ES1", "Bundesliga": "L1", "Serie_A": "IT1", "Ligue_1": "FR1"}

CLUB_LOW_CONFIDENCE = 0.75   # club matches below this score are printed for checking
MIN_NAME_SCORE = 0.75        # player matches below this are left unmatched
GOALS_TOLERANCE = 2          # verification: flag if goals differ by more than this
MINUTES_TOLERANCE = 0.20     # ... or minutes by more than this share of Understat's
N_SAMPLE = 50

# Words that say what kind of club it is rather than which club
CLUB_STOPWORDS = {"fc", "cf", "ac", "as", "sc", "afc", "ssc", "ss", "us", "ud", "cd", "rc", "rcd",
                  "sd", "ca", "vfb", "vfl", "tsg", "fsv", "sv", "bv", "ssv", "osc", "ogc", "aj",
                  "acf", "de", "club", "football", "futbol", "calcio", "associazione", "sportiva",
                  "1", "1846", "1899", "1900", "1901", "1904", "1907", "1909", "1910", "1913", "1919"}


# ---------- download ----------

def download() -> None:
    """Fetch any missing table once (temp file, then rename) and record the snapshot."""
    RAW.mkdir(parents=True, exist_ok=True)
    meta_path = RAW / "snapshot.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"files": {}}
    for name in TABLES:
        dest = RAW / f"{name}.csv.gz"
        if dest.exists():
            if name not in meta["files"]:  # cached by hand: record which version it is
                h = requests.head(f"{BASE}/{name}.csv.gz", timeout=30)
                meta["files"][name] = {"last_modified": h.headers.get("Last-Modified"), "downloaded_at": None}
            continue
        r = requests.get(f"{BASE}/{name}.csv.gz", timeout=120)
        r.raise_for_status()
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(r.content)
        tmp.replace(dest)
        meta["files"][name] = {"last_modified": r.headers.get("Last-Modified"),
                               "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print(f"downloaded {name}")
    meta_path.write_text(json.dumps(meta, indent=1))


def read(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(RAW / f"{name}.csv.gz", **kw)


# ---------- name matching ----------

# Letters that Unicode decomposition can't reduce to an ASCII base letter
SPECIAL_LETTERS = str.maketrans({"ı": "i", "İ": "I", "ø": "o", "Ø": "O", "ł": "l", "Ł": "L",
                                 "đ": "d", "Đ": "D", "ß": "ss", "æ": "ae", "Æ": "AE", "œ": "oe"})


def normalise(name: str, stopwords: set[str] = frozenset()) -> list[str]:
    """Lowercase ASCII tokens: accents stripped, hyphens and punctuation split words."""
    plain = unicodedata.normalize("NFKD", str(name).translate(SPECIAL_LETTERS))
    plain = plain.encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z0-9]+", plain) if t and t not in stopwords]


def token_match(a: str, b: str) -> float:
    """How well two single tokens match: initials match any word with that letter,
    a word contained in the other counts as a match ("lyon" / "lyonnais")."""
    if len(a) == 1 or len(b) == 1:
        return 1.0 if a[0] == b[0] else 0.0
    if min(len(a), len(b)) >= 4 and (a in b or b in a):
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def name_score(a: str, b: str, stopwords: set[str] = frozenset()) -> float:
    """Similarity in [0, 1], independent of word order. Every word of the shorter name
    is matched to its best word in the longer one (so extra middle or second surnames
    don't count against), blended with a whole-string comparison to break ties."""
    ta, tb = normalise(a, stopwords), normalise(b, stopwords)
    if not ta or not tb:
        return 0.0
    short, long_ = sorted((ta, tb), key=len)
    tokens = np.mean([max(token_match(s, l) for l in long_) for s in short])
    whole = difflib.SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return float(0.8 * tokens + 0.2 * whole)


def best_candidate(name: str, candidates: pd.Series) -> tuple[object, float]:
    """Index label and score of the best-matching candidate name (None, 0 if none)."""
    if candidates.empty:
        return None, 0.0
    scores = candidates.map(lambda c: name_score(name, c))
    return scores.idxmax(), float(scores.max())


# ---------- clubs ----------

def tm_league_clubs(games: pd.DataFrame, clubs: pd.DataFrame) -> pd.DataFrame:
    """Clubs that played SEASON league games, with every name variant Transfermarkt uses."""
    g = games[games["competition_id"].isin(LEAGUES.values()) & (games["season"] == SEASON)]
    names = pd.concat([g[["competition_id", "home_club_id", "home_club_name"]].set_axis(["competition_id", "club_id", "name"], axis=1),
                       g[["competition_id", "away_club_id", "away_club_name"]].set_axis(["competition_id", "club_id", "name"], axis=1)])
    out = names.groupby(["competition_id", "club_id"])["name"].agg(lambda s: sorted(set(s.dropna()))).reset_index()
    extra = clubs.set_index("club_id")
    out["variants"] = [n + [extra.at[c, "name"], extra.at[c, "club_code"].replace("-", " ")] if c in extra.index else n
                       for c, n in zip(out["club_id"], out["name"])]
    out["name"] = out["name"].str[0]
    return out


def map_clubs(teams: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    """One-to-one mapping of Understat teams to Transfermarkt clubs within each league,
    maximising the total name score (Hungarian assignment)."""
    rows = []
    for league, comp in LEAGUES.items():
        ours = teams.loc[teams["league"] == league, "team"].sort_values().tolist()
        theirs = tm[tm["competition_id"] == comp].reset_index(drop=True)
        score = np.array([[max(name_score(t, v, CLUB_STOPWORDS) for v in variants)
                           for variants in theirs["variants"]] for t in ours])
        r, c = linear_sum_assignment(-score)
        for i, j in zip(r, c):
            runner_up = np.delete(score[i], j).max() if score.shape[1] > 1 else 0.0
            rows.append({"league": league, "understat_team": ours[i],
                         "transfermarkt_club_id": int(theirs.at[j, "club_id"]),
                         "transfermarkt_club": theirs.at[j, "name"],
                         "score": round(float(score[i, j]), 3), "runner_up_score": round(float(runner_up), 3)})
    return pd.DataFrame(rows)


# ---------- players ----------

def tm_league_appearances(appearances: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Transfermarkt appearances in SEASON games of our 5 leagues."""
    g = games.loc[games["competition_id"].isin(LEAGUES.values()) & (games["season"] == SEASON), ["game_id"]]
    return appearances.merge(g, on="game_id")


def match_players(pool: pd.DataFrame, club_map: pd.DataFrame, tm_apps: pd.DataFrame,
                  tm_players: pd.DataFrame) -> pd.DataFrame:
    """Best Transfermarkt candidate for each pool player, among players who appeared in
    league games for the club(s) mapped from the player's Understat team(s)."""
    club_ids = club_map.set_index("understat_team")["transfermarkt_club_id"]
    by_club = tm_apps.groupby("player_club_id")["player_id"].unique()
    names = tm_players.set_index("player_id")["name"]
    rows = []
    for (pid, season), r in pool.iterrows():
        clubs = [club_ids[t] for t in r["teams"].split(", ") if t in club_ids]
        ids = pd.unique(np.concatenate([by_club.get(c, np.array([], dtype=int)) for c in clubs] or [[]]))
        best, score = best_candidate(r["player"], names.reindex(ids).dropna())
        rows.append({"understat_player_id": pid, "season": season, "player": r["player"],
                     "teams": r["teams"], "candidates": len(ids), "best_candidate": names.get(best),
                     "best_candidate_id": best, "match_score": round(score, 3)})
    out = pd.DataFrame(rows)
    ok = out["match_score"] >= MIN_NAME_SCORE
    out["transfermarkt_player_id"] = out["best_candidate_id"].where(ok).astype("Int64")
    out["transfermarkt_name"] = out["best_candidate"].where(ok)
    return out.drop(columns="best_candidate_id")


def verify(matches: pd.DataFrame, understat_apps: pd.DataFrame, tm_apps: pd.DataFrame) -> pd.DataFrame:
    """Add both sides' league goals and minutes and flag pairs that disagree."""
    us = understat_apps.groupby("player_id")[["goals", "minutes"]].sum().add_prefix("understat_")
    tm = (tm_apps.groupby("player_id")[["goals", "minutes_played"]].sum()
          .rename(columns={"goals": "tm_goals", "minutes_played": "tm_minutes"}))
    out = matches.join(us, on="understat_player_id").join(tm, on="transfermarkt_player_id")
    goals_off = (out["understat_goals"] - out["tm_goals"]).abs() > GOALS_TOLERANCE
    minutes_off = (out["understat_minutes"] - out["tm_minutes"]).abs() > MINUTES_TOLERANCE * out["understat_minutes"]
    out["flag_reason"] = np.select([goals_off & minutes_off, goals_off, minutes_off],
                                   ["goals and minutes", "goals", "minutes"], default="")
    out["verification_flag"] = out["flag_reason"] != ""
    out.loc[out["transfermarkt_player_id"].isna(), ["verification_flag", "flag_reason"]] = [False, "unmatched"]
    return out


def market_columns(matched: pd.DataFrame, tm_players: pd.DataFrame, valuations: pd.DataFrame,
                   snapshot: pd.Timestamp) -> pd.DataFrame:
    """Market fields for each matched player: latest valuation and snapshot details."""
    latest = (valuations.assign(date=pd.to_datetime(valuations["date"])).sort_values("date")
              .groupby("player_id").last()[["market_value_in_eur", "date"]]
              .rename(columns={"market_value_in_eur": "market_value_eur", "date": "value_date"}))
    p = tm_players.set_index("player_id")[["date_of_birth", "position", "sub_position", "foot",
                                           "contract_expiration_date", "current_club_name"]]
    out = matched.join(p, on="transfermarkt_player_id").join(latest, on="transfermarkt_player_id")
    for col in ("date_of_birth", "contract_expiration_date"):
        out[col] = pd.to_datetime(out[col])
    out["age_at_snapshot"] = ((snapshot - out["date_of_birth"]).dt.days / 365.25).round(1)
    out["snapshot_date"] = snapshot
    return out.rename(columns={"current_club_name": "current_club_at_snapshot"})


def write_sample(v: pd.DataFrame, path: Path = SAMPLE, n: int = N_SAMPLE) -> None:
    """Random matched pairs, names, clubs, goals and minutes only, for checking by hand."""
    s = v[v["transfermarkt_player_id"].notna()].sample(n, random_state=0).sort_values("player")
    lines = ["# Player match sample", "",
             f"{n} random matched pairs (seed 0) for checking by hand. Goals and minutes are "
             f"{SEASON}/{(SEASON + 1) % 100:02d} league totals from each source.", "",
             "| Understat name | Transfermarkt name | club (Understat) | match score | goals U / TM | minutes U / TM | flag |",
             "|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        lines.append(f"| {r['player']} | {r['transfermarkt_name']} | {r['teams']} | {r['match_score']:.2f} | "
                     f"{r['understat_goals']} / {r['tm_goals']:.0f} | {r['understat_minutes']} / {r['tm_minutes']:.0f} | "
                     f"{r['flag_reason']} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    download()
    games, clubs = read("games"), read("clubs")
    tm_players, valuations = read("players"), read("player_valuations")
    tm_apps = tm_league_appearances(read("appearances"), games)
    snapshot = pd.to_datetime(games["date"]).max()
    meta = json.loads((RAW / "snapshot.json").read_text())
    meta |= {"snapshot_date": str(snapshot.date()), "latest_valuation": str(valuations["date"].max())}
    (RAW / "snapshot.json").write_text(json.dumps(meta, indent=1))
    print(f"Transfermarkt snapshot: games to {snapshot.date()}, valuations to {valuations['date'].max()}")

    apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    apps = apps[apps["season"] == SEASON]
    pool = pd.read_parquet(PROCESSED / "profiles.parquet").set_index(KEYS)

    club_map = map_clubs(apps[["league", "team"]].drop_duplicates(), tm_league_clubs(games, clubs))
    CLUB_MAP.parent.mkdir(exist_ok=True)
    club_map.to_csv(CLUB_MAP, index=False)
    low = club_map[club_map["score"] < CLUB_LOW_CONFIDENCE]
    print(f"\nclubs: {len(club_map)} mapped -> {CLUB_MAP}; {len(low)} low-confidence (score < {CLUB_LOW_CONFIDENCE}):")
    print(low.to_string(index=False) if len(low) else "  none")

    v = verify(match_players(pool, club_map, tm_apps, tm_players), apps, tm_apps)
    market = market_columns(v, tm_players, valuations, snapshot)
    market.to_parquet(PROCESSED / "market.parquet", index=False)

    matched = v["transfermarkt_player_id"].notna()
    flagged = v[v["verification_flag"]]
    print(f"\nplayers: {matched.sum()} of {len(v)} matched ({matched.mean():.1%}); "
          f"{len(flagged)} flagged by verification ({len(flagged) / matched.sum():.1%} of matched)")
    pd.set_option("display.width", 220)
    cols = ["player", "teams", "transfermarkt_name", "match_score", "understat_goals", "tm_goals",
            "understat_minutes", "tm_minutes"]
    print(f"\nUnmatched ({(~matched).sum()}): best candidate scored below {MIN_NAME_SCORE}")
    um = v[~matched]
    print(um[["player", "teams", "candidates", "best_candidate", "match_score"]].to_string(index=False)
          if len(um) else "  none")
    print(f"\nFlagged ({len(flagged)}):")
    print(flagged[cols + ["flag_reason"]].to_string(index=False) if len(flagged) else "  none")

    write_sample(v)
    print(f"\nwrote {PROCESSED / 'market.parquet'} ({len(market)} rows) and {SAMPLE}")


if __name__ == "__main__":
    main()
