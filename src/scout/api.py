"""HTTP API for the scouting engine: search, profiles, similar players, a style map.

Uses the recent-form profiles and the same ranking as `python -m scout.similar`.
Data is loaded once at startup from SCOUT_DATA (default data/processed).

    uvicorn scout.api:app --reload
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from scout.features import PROCESSED, WINDOW_MINUTES
from scout.similar import Pool, find_players

EXPERIMENT_LOG = Path("reports/experiments.md")
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # local frontend (Vite)
N_TOP_REASONS = 3

LABELS = {
    "npxg_per90": "non-penalty xG per 90",
    "shots_per90": "shots per 90",
    "xa_per90": "expected assists (xA) per 90",
    "key_passes_per90": "key passes per 90",
    "xgchain_per90": "involvement in attacks that end in a shot (xGChain per 90)",
    "xgbuildup_per90": "involvement in build-up play (xGBuildup per 90)",
    "npxg_per_shot": "average shot quality (npxG per shot)",
    "buildup_share_of_chain": "share of attacking involvement that is build-up",
    "shot_type_head": "share of shots with the head",
    "shot_type_left_foot": "share of shots with the left foot",
    "shot_type_right_foot": "share of shots with the right foot",
    "shot_type_other": "share of shots with another body part",
}
LAST_ACTIONS = {
    "pass": "a pass", "cross": "a cross", "take_on": "a take-on (dribble)", "rebound": "a rebound",
    "aerial": "an aerial duel", "chipped": "a chipped ball", "ball_recovery": "winning the ball back",
    "ball_touch": "a first touch", "head_pass": "a headed pass", "throughball": "a through ball",
    "other": "another action", "missing": "an unrecorded action",
}


def feature_label(column: str, zone_labels: dict[str, str]) -> str:
    """Plain-language name of a profile column."""
    if column in zone_labels:
        return f"share of {zone_labels[column]}"
    if column.startswith("last_action_"):
        action = column.removeprefix("last_action_")
        return f"share of shots after {LAST_ACTIONS.get(action, action.replace('_', ' '))}"
    return LABELS.get(column, column.replace("_", " "))


def logged_recall_at_10(path: Path) -> float | None:
    """recall@10 (mean) of the newest experiment-log row for recent-form profiles."""
    if not path.exists():
        return None
    header, value = None, None
    for line in path.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "recall@10" in cells and header is None:
            header = cells
        elif header and len(cells) == len(header) and "--mode recent" in line:
            value = float(cells[header.index("recall@10")].split("±")[0])
    return value


def clean(value):
    """JSON-friendly: NaN/NA to None, numpy scalars to Python, dates to ISO strings."""
    if value is None or (not isinstance(value, (str, bytes)) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


class Scout:
    """Everything the endpoints need, computed once."""

    def __init__(self, data_dir: Path, log_path: Path):
        profiles = pd.read_parquet(data_dir / "profiles_recent.parquet")
        self.market = pd.read_parquet(data_dir / "market.parquet").set_index("understat_player_id")
        self.pool = Pool(profiles, self.market.reset_index())
        self.key = {key[0]: key for key in self.pool.df.index}  # player_id -> pool key (one row each)
        zones_path = data_dir / "zones_recent.json"
        zones = json.loads(zones_path.read_text()) if zones_path.exists() else []
        self.zone_labels = {z["column"]: z["label"] for z in zones}
        self.zone_columns = [c for c in self.pool.features if c.startswith("zone_")]
        self.style_columns = [c for c in self.pool.features if c not in self.zone_columns]
        self.percentiles = self.pool.df[self.style_columns].rank(pct=True) * 100
        self.map = self._map()
        df = self.pool.df
        self.meta = {
            "data_window_end": clean(pd.to_datetime(df["window_end"]).max()) if "window_end" in df else None,
            "market_snapshot": clean(pd.to_datetime(self.market["valuations_as_of"]).max())
            if "valuations_as_of" in self.market else None,
            "pool_size": len(df),
            "window_minutes": WINDOW_MINUTES,
            "recall_at_10": logged_recall_at_10(log_path),
        }

    def _map(self) -> pd.DataFrame:
        """First two principal components of the z-scored profiles."""
        z = self.pool.z - self.pool.z.mean(axis=0)
        u, s, _ = np.linalg.svd(z, full_matrices=False)
        coords = u[:, :2] * s[:2]
        self.map_variance = (s[:2] ** 2 / (s ** 2).sum()).round(3).tolist()
        return pd.DataFrame(coords, index=self.pool.df.index, columns=["x", "y"])

    def lookup(self, player_id: int):
        if player_id not in self.key:
            raise HTTPException(status_code=404, detail=f"no player {player_id} in the pool")
        return self.key[player_id]

    def summary(self, key) -> dict:
        r = self.pool.df.loc[key]
        return {"id": int(key[0]), "name": r["player"], "team": r["teams"], "league": r["league"],
                "position": r["primary_position"], "minutes": clean(r["minutes"]),
                "active": clean(r.get("active")), "window_start": clean(r.get("window_start")),
                "window_end": clean(r.get("window_end")), "age": clean(r["age"]),
                "market_value_m": clean(r["value_m"]), "contract_end": clean(r["contract_end"])}

    def explanation(self, key, other) -> dict:
        c = self.pool.contributions(key, other)
        item = lambda f: {"feature": f, "label": feature_label(f, self.zone_labels),  # noqa: E731
                          "contribution": round(float(c[f]), 4)}
        worst = c.idxmin()
        return {"top": [item(f) for f in c.nlargest(N_TOP_REASONS).index],
                "against": item(worst), "total": round(float(c.sum()), 4)}


def create_app(data_dir: Path = PROCESSED, log_path: Path = EXPERIMENT_LOG) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.scout = Scout(Path(data_dir), Path(log_path))
        yield

    app = FastAPI(title="scout", description=__doc__.splitlines()[0], lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET"], allow_headers=["*"])

    def state(request: Request) -> Scout:
        return request.app.state.scout

    @app.get("/players")
    def search_players(request: Request, q: str = Query(..., min_length=1, description="player name")):
        s = state(request)
        keys = find_players(q, s.pool.df["player"])
        return [{k: s.summary(key)[k] for k in ("id", "name", "team", "position")} for key in keys]

    @app.get("/players/{player_id}")
    def player(request: Request, player_id: int):
        s = state(request)
        key = s.lookup(player_id)
        _, distinctiveness = s.pool.ranked(key)
        m = s.market.loc[player_id] if player_id in s.market.index else pd.Series(dtype=object)
        df = s.pool.df
        return {
            **s.summary(key),
            "market": {"age": clean(df.at[key, "age"]), "value_m": clean(df.at[key, "value_m"]),
                       "contract_end": clean(df.at[key, "contract_end"]),
                       "value_date": clean(m.get("value_date")),
                       "club_at_snapshot": clean(m.get("current_club_at_snapshot"))},
            "distinctiveness": round(distinctiveness, 1),
            "features": [{"feature": f, "label": feature_label(f, s.zone_labels),
                          "value": clean(df.at[key, f]), "percentile": clean(round(s.percentiles.at[key, f], 1))}
                         for f in s.style_columns],
            "zones": [{"feature": f, "label": s.zone_labels.get(f, f), "weight": clean(round(df.at[key, f], 4))}
                      for f in s.zone_columns],
        }

    @app.get("/players/{player_id}/similar")
    def similar(request: Request, player_id: int, max_age: int | None = None, max_value: float | None = None,
                contract_before: int | None = None, include_inactive: bool = False,
                limit: int = Query(10, ge=1, le=100)):
        s = state(request)
        key = s.lookup(player_id)
        found = s.pool.search(key, max_age, max_value, contract_before, include_inactive)
        results = found["results"].head(limit)
        return {
            "player": s.summary(key),
            "distinctiveness": round(found["distinctiveness"], 1),
            "candidates": found["candidates"], "inactive_excluded": found["inactive_excluded"],
            "removed_by_filters": found["removed_by_filters"],
            "results": [{**s.summary(other), "similarity": round(float(results.at[other, "similarity"]), 4),
                         "npxg_per90": clean(results.at[other, "npxg_per90"]),
                         "explanation": s.explanation(key, other)} for other in results.index],
        }

    @app.get("/map")
    def style_map(request: Request):
        s = state(request)
        df = s.pool.df
        return {"explained_variance": s.map_variance,
                "players": [{"id": int(key[0]), "name": df.at[key, "player"], "team": df.at[key, "teams"],
                             "position": df.at[key, "primary_position"], "active": clean(df.at[key, "active"])
                             if "active" in df else None,
                             "x": round(float(s.map.at[key, "x"]), 4), "y": round(float(s.map.at[key, "y"]), 4)}
                            for key in df.index]}

    @app.get("/meta")
    def meta(request: Request):
        return state(request).meta

    return app


app = create_app(Path(os.environ.get("SCOUT_DATA", PROCESSED)))
