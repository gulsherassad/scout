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
PLAYER_OVERRIDES = Path("data_mappings/player_overrides.csv")  # hand-checked pairs names can't match
SAMPLE = Path("reports/match_sample.md")
SAMPLE_IDS = Path("data_mappings/sample_ids.csv")  # pins the hand-checked sample
POOLS = [PROCESSED / "profiles.parquet", PROCESSED / "profiles_recent.parquet"]

SEASON = 2025  # both sources label 2025/26 as 2025
LEAGUES = {"EPL": "GB1", "La_liga": "ES1", "Bundesliga": "L1", "Serie_A": "IT1", "Ligue_1": "FR1"}
# The snapshot has no second divisions: clubs promoted for 2026/27 are found through each
# country's domestic cup and through clubs.csv's (snapshot) league listing.
LEAGUE_CUPS = {"GB1": "FAC", "ES1": "CDR", "L1": "DFB", "IT1": "CIT", "FR1": "FRCH"}

CLUB_LOW_CONFIDENCE = 0.75   # club matches below this score are printed for checking
NEW_CLUB_MIN_SCORE = 0.75    # promoted clubs below this are left unmapped (club not in snapshot)
MIN_NAME_SCORE = 0.75        # player matches below this are left unmatched
GOALS_TOLERANCE = 1          # verification: flag if goals differ by more than this
MINUTES_TOLERANCE = 0.15     # ... or minutes by more than this share of Understat's
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
    """Candidate clubs per league, with every name variant Transfermarkt uses: clubs in
    SEASON league or domestic-cup games, and clubs listed in that league in clubs.csv."""
    league_of = {c: c for c in LEAGUES.values()} | {cup: lg for lg, cup in LEAGUE_CUPS.items()}
    g = games[games["competition_id"].isin(league_of) & (games["season"] == SEASON)]
    g = g.assign(competition_id=g["competition_id"].map(league_of))
    listed = clubs.loc[clubs["domestic_competition_id"].isin(LEAGUES.values()),
                       ["domestic_competition_id", "club_id", "name"]]
    names = pd.concat([g[["competition_id", "home_club_id", "home_club_name"]].set_axis(["competition_id", "club_id", "name"], axis=1),
                       g[["competition_id", "away_club_id", "away_club_name"]].set_axis(["competition_id", "club_id", "name"], axis=1),
                       listed.set_axis(["competition_id", "club_id", "name"], axis=1)])
    out = names.groupby(["competition_id", "club_id"])["name"].agg(lambda s: sorted(set(s.dropna()))).reset_index()
    lg = games[games["competition_id"].isin(LEAGUES.values()) & (games["season"] == SEASON)]
    out["in_league"] = out["club_id"].isin(set(lg["home_club_id"]) | set(lg["away_club_id"]))
    extra = clubs.set_index("club_id")
    out["variants"] = [n + [extra.at[c, "name"], extra.at[c, "club_code"].replace("-", " ")] if c in extra.index else n
                       for c, n in zip(out["club_id"], out["name"])]
    out["name"] = out["name"].str[0]
    out = out[out["variants"].map(len) > 0]  # no usable name: cannot be matched
    out["name"] = out["name"].fillna(out["variants"].str[0])
    return out.reset_index(drop=True)


def assign(ours: list[str], theirs: pd.DataFrame, league: str) -> list[dict]:
    """One-to-one assignment maximising the total name score (Hungarian algorithm)."""
    if not ours or theirs.empty:
        return []
    score = np.array([[max(name_score(t, v, CLUB_STOPWORDS) for v in variants)
                       for variants in theirs["variants"]] for t in ours])
    rows = []
    for i, j in zip(*linear_sum_assignment(-score)):
        runner_up = np.delete(score[i], j).max() if score.shape[1] > 1 else 0.0
        rows.append({"league": league, "understat_team": ours[i],
                     "transfermarkt_club_id": int(theirs.at[j, "club_id"]),
                     "transfermarkt_club": theirs.at[j, "name"],
                     "score": round(float(score[i, j]), 3), "runner_up_score": round(float(runner_up), 3)})
    return rows


def map_clubs(teams: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    """Map Understat teams (league, team, season) to Transfermarkt clubs within each league.
    Teams that played SEASON are assigned among Transfermarkt's SEASON league clubs only;
    teams new since then (promoted) among the remaining candidates (cup and listed clubs),
    so a lower-league cup side can never take an established club's place."""
    first = teams.groupby(["league", "team"])["season"].min().reset_index()
    rows = []
    for league, comp in LEAGUES.items():
        f = first[first["league"] == league]
        clubs = tm[tm["competition_id"] == comp]
        stage1 = assign(sorted(f.loc[f["season"] <= SEASON, "team"]), clubs[clubs["in_league"]].reset_index(drop=True), league)
        used = {r["transfermarkt_club_id"] for r in stage1}
        rest = clubs[~clubs["in_league"] & ~clubs["club_id"].isin(used)].reset_index(drop=True)
        stage2 = assign(sorted(f.loc[f["season"] > SEASON, "team"]), rest, league)
        for r in stage2:  # a club missing from the snapshot must not take a wrong match
            if r["score"] < NEW_CLUB_MIN_SCORE:
                r.update(transfermarkt_club_id=None, transfermarkt_club=None)
        rows += stage1 + stage2
    out = pd.DataFrame(rows)
    out["transfermarkt_club_id"] = out["transfermarkt_club_id"].astype("Int64")
    return out


# ---------- players ----------

def tm_league_appearances(appearances: pd.DataFrame, games: pd.DataFrame,
                          all_competitions: bool = False) -> pd.DataFrame:
    """Transfermarkt appearances in SEASON games of our 5 leagues (or of any competition)."""
    g = games[games["season"] == SEASON]
    if not all_competitions:
        g = g[g["competition_id"].isin(LEAGUES.values())]
    return appearances.merge(g[["game_id"]], on="game_id")


def match_players(pool: pd.DataFrame, club_map: pd.DataFrame, tm_apps: pd.DataFrame,
                  tm_players: pd.DataFrame) -> pd.DataFrame:
    """Best Transfermarkt candidate for each pool player (indexed by Understat player_id),
    among players who played SEASON games for, or were registered at the snapshot with,
    the club(s) mapped from the player's Understat team(s)."""
    club_ids = (club_map.dropna(subset=["transfermarkt_club_id"]).drop_duplicates("understat_team")
                .set_index("understat_team")["transfermarkt_club_id"])
    by_club = pd.concat([tm_apps[["player_club_id", "player_id"]],
                         tm_players[["current_club_id", "player_id"]].set_axis(["player_club_id", "player_id"], axis=1)]
                        ).groupby("player_club_id")["player_id"].unique()
    names = tm_players.set_index("player_id")["name"]
    rows = []
    for pid, r in pool.iterrows():
        clubs = [club_ids[t] for t in r["teams"].split(", ") if t in club_ids]
        ids = pd.unique(np.concatenate([by_club.get(c, np.array([], dtype=int)) for c in clubs] or [[]]))
        best, score = best_candidate(r["player"], names.reindex(ids).dropna())
        rows.append({"understat_player_id": pid, "player": r["player"],
                     "teams": r["teams"], "candidates": len(ids), "best_candidate": names.get(best),
                     "best_candidate_id": best, "match_score": round(score, 3)})
    out = pd.DataFrame(rows)
    ok = out["match_score"] >= MIN_NAME_SCORE
    out["transfermarkt_player_id"] = out["best_candidate_id"].where(ok).astype("Int64")
    out["transfermarkt_name"] = out["best_candidate"].where(ok)
    out["match_method"] = np.where(ok, "name", "")
    return out.drop(columns="best_candidate_id")


def apply_overrides(matches: pd.DataFrame, overrides: pd.DataFrame,
                    tm_players: pd.DataFrame) -> pd.DataFrame:
    """Set hand-checked pairs from the override file. Only matching changes: overridden
    pairs still go through verification like any other. match_score stays the name score."""
    out = matches.copy()
    names = tm_players.set_index("player_id")["name"]
    unknown = set(overrides["transfermarkt_player_id"]) - set(names.index)
    if unknown:
        raise ValueError(f"override Transfermarkt ids not in players table: {sorted(unknown)}")
    o = overrides.set_index("understat_player_id")["transfermarkt_player_id"]
    rows = out["understat_player_id"].isin(o.index)
    tm_ids = out.loc[rows, "understat_player_id"].map(o)
    out.loc[rows, "transfermarkt_player_id"] = tm_ids.astype("Int64")
    out.loc[rows, "transfermarkt_name"] = tm_ids.map(names)
    out.loc[rows, "match_score"] = [round(name_score(a, b), 3)
                                    for a, b in zip(out.loc[rows, "player"], out.loc[rows, "transfermarkt_name"])]
    out.loc[rows, "match_method"] = "override"
    return out


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
    no_stats = out["understat_minutes"].isna() | out["tm_minutes"].isna()
    out.loc[no_stats, ["verification_flag", "flag_reason"]] = [False, f"no {SEASON}/{(SEASON + 1) % 100:02d} league stats to compare"]
    out.loc[out["transfermarkt_player_id"].isna(), ["verification_flag", "flag_reason"]] = [False, "unmatched"]
    return out


def market_columns(matched: pd.DataFrame, tm_players: pd.DataFrame, valuations: pd.DataFrame,
                   snapshot: pd.Timestamp) -> pd.DataFrame:
    """Market fields for each matched player: latest valuation and snapshot details.
    `valuations_as_of` is the newest valuation in the whole snapshot."""
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
    out["valuations_as_of"] = pd.to_datetime(valuations["date"]).max()
    return out.rename(columns={"current_club_name": "current_club_at_snapshot"})


def sample_ids(v: pd.DataFrame, path: Path = SAMPLE_IDS, n: int = N_SAMPLE) -> list[int]:
    """The pinned sample's Understat ids; drawn at random (seed 0) and saved the first time."""
    if path.exists():
        return pd.read_csv(path)["understat_player_id"].tolist()
    ids = v[v["transfermarkt_player_id"].notna()].sample(n, random_state=0)["understat_player_id"].tolist()
    pd.DataFrame({"understat_player_id": ids}).to_csv(path, index=False)
    return ids


def write_sample(v: pd.DataFrame, ids: list[int], path: Path = SAMPLE) -> None:
    """The pinned matched pairs: names, clubs, goals and minutes only, for checking by hand."""
    s = v[v["understat_player_id"].isin(ids)].sort_values("player")
    n = len(s)
    lines = ["# Player match sample", "",
             f"{n} random matched pairs (seed 0, pinned in {SAMPLE_IDS}) for checking by hand. Goals and minutes are "
             f"{SEASON}/{(SEASON + 1) % 100:02d} league totals from each source.", "",
             "| Understat name | Transfermarkt name | club (Understat) | match score | goals U / TM | minutes U / TM | flag |",
             "|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        lines.append(f"| {r['player']} | {r['transfermarkt_name']} | {r['teams']} | {r['match_score']:.2f} | "
                     f"{r['understat_goals']} / {r['tm_goals']:.0f} | {r['understat_minutes']} / {r['tm_minutes']:.0f} | "
                     f"{r['flag_reason']} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def pool_players() -> pd.DataFrame:
    """Every player in any profile pool, indexed by Understat player_id, with their name
    and every team they have a profile for (most minutes first within each pool)."""
    frames = [pd.read_parquet(p)[["player_id", "player", "teams"]] for p in POOLS if p.exists()]
    pool = pd.concat(frames)
    teams = pool.groupby("player_id")["teams"].agg(
        lambda s: ", ".join(dict.fromkeys(t for ts in s for t in ts.split(", "))))
    return pool.groupby("player_id")[["player"]].last().join(teams)


def main() -> None:
    download()
    games, clubs = read("games"), read("clubs")
    tm_players, valuations = read("players"), read("player_valuations")
    all_tm_apps = read("appearances")
    tm_apps = tm_league_appearances(all_tm_apps, games)
    tm_season_apps = tm_league_appearances(all_tm_apps, games, all_competitions=True)
    snapshot = pd.to_datetime(games["date"]).max()
    meta = json.loads((RAW / "snapshot.json").read_text())
    meta |= {"snapshot_date": str(snapshot.date()), "latest_valuation": str(valuations["date"].max())}
    (RAW / "snapshot.json").write_text(json.dumps(meta, indent=1))
    print(f"Transfermarkt snapshot: games to {snapshot.date()}, valuations to {valuations['date'].max()}")

    all_apps = pd.read_parquet(PROCESSED / "appearances.parquet")
    apps = all_apps[all_apps["season"] == SEASON]
    pool = pool_players()

    club_map = map_clubs(all_apps[["league", "team", "season"]].drop_duplicates(), tm_league_clubs(games, clubs))
    CLUB_MAP.parent.mkdir(exist_ok=True)
    club_map.to_csv(CLUB_MAP, index=False)
    unmapped = club_map[club_map["transfermarkt_club_id"].isna()]
    low = club_map[(club_map["score"] < CLUB_LOW_CONFIDENCE) & club_map["transfermarkt_club_id"].notna()]
    print(f"\nclubs: {len(club_map) - len(unmapped)} of {len(club_map)} mapped -> {CLUB_MAP}; "
          f"{len(low)} low-confidence (score < {CLUB_LOW_CONFIDENCE}):")
    print(low.to_string(index=False) if len(low) else "  none")
    print(f"unmapped (promoted, no Transfermarkt club scored >= {NEW_CLUB_MIN_SCORE}): "
          + (", ".join(f"{r.understat_team} ({r.league}, best score {r.score})" for r in unmapped.itertuples()) or "none"))

    matches = apply_overrides(match_players(pool, club_map, tm_season_apps, tm_players),
                              pd.read_csv(PLAYER_OVERRIDES), tm_players)
    v = verify(matches, apps, tm_apps)
    market = market_columns(v, tm_players, valuations, snapshot)
    market.to_parquet(PROCESSED / "market.parquet", index=False)

    matched = v["transfermarkt_player_id"].notna()
    flagged = v[v["verification_flag"]]
    n_override = (v["match_method"] == "override").sum()
    print(f"\nplayers: {matched.sum()} of {len(v)} matched ({matched.mean():.1%}; {n_override} from "
          f"{PLAYER_OVERRIDES}); {len(flagged)} flagged by verification "
          f"(goals off by > {GOALS_TOLERANCE} or minutes by > {MINUTES_TOLERANCE:.0%})")
    new = ~v["understat_player_id"].isin(apps["player_id"])
    print(f"players with no {SEASON}/{(SEASON + 1) % 100:02d} Understat appearances (new to our leagues): "
          f"{new.sum()}, of whom {(new & matched).sum()} matched (unverified: no shared season to compare) "
          f"and {(new & ~matched).sum()} unmatched")
    pd.set_option("display.width", 220)
    cols = ["player", "teams", "transfermarkt_name", "match_method", "match_score", "understat_goals", "tm_goals",
            "understat_minutes", "tm_minutes"]
    print(f"\nUnmatched ({(~matched).sum()}): best candidate scored below {MIN_NAME_SCORE}")
    um = v[~matched]
    print(um[["player", "teams", "candidates", "best_candidate", "match_score"]].to_string(index=False)
          if len(um) else "  none")
    print(f"\nFlagged ({len(flagged)}):")
    print(flagged[cols + ["flag_reason"]].to_string(index=False) if len(flagged) else "  none")
    print(f"\nNew to our leagues and matched (no stats to verify; check by hand if it matters):")
    print(v[new & matched][["player", "teams", "transfermarkt_name", "match_score"]].to_string(index=False)
          if (new & matched).any() else "  none")

    # The hand-checked sample shows each player's 2025/26 club(s), so it stays the same as more seasons arrive
    season_teams = pd.read_parquet(POOLS[0]).drop_duplicates("player_id").set_index("player_id")["teams"]
    write_sample(v.assign(teams=v["understat_player_id"].map(season_teams).fillna(v["teams"])), sample_ids(v))
    print(f"\nwrote {PROCESSED / 'market.parquet'} ({len(market)} rows) and {SAMPLE}")


if __name__ == "__main__":
    main()
