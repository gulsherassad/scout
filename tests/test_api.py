"""Tests for the HTTP API on a small synthetic dataset (no real data, no network)."""
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from scout.api import create_app
from scout.features import KEYS, build_profiles

from test_features import app as appearance, shot

N_PLAYERS = 14


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data = tmp_path_factory.mktemp("processed")
    rng = np.random.default_rng(0)
    apps, shots = [], []
    for p in range(1, N_PLAYERS + 1):
        for m in range(10):
            apps.append(appearance(m, player_id=p, xA=rng.uniform(0, 0.4), key_passes=int(rng.integers(0, 4)),
                                   xGChain=rng.uniform(0.1, 0.8), xGBuildup=rng.uniform(0, 0.3)))
            for _ in range(int(rng.integers(1, 4))):
                shots.append(shot(m, player_id=p, xG=rng.uniform(0.02, 0.4), X=rng.uniform(0.8, 0.97),
                                  Y=rng.uniform(0.1, 0.9), shotType=rng.choice(["Head", "LeftFoot", "RightFoot"]),
                                  lastAction=rng.choice(["Pass", "Cross", "TakeOn"])))
    profiles = build_profiles(pd.DataFrame(shots), pd.DataFrame(apps), zones=3)
    profiles["window_start"] = pd.Timestamp("2026-01-01")
    profiles["window_end"] = pd.Timestamp("2026-09-20")
    profiles["active"] = profiles["player_id"] != 2               # player 2 is inactive
    profiles.to_parquet(data / "profiles_recent.parquet", index=False)
    pd.DataFrame({
        "understat_player_id": range(1, N_PLAYERS + 1),
        "age_at_snapshot": [19.5 + p for p in range(N_PLAYERS)],  # player p is 18 + p years old
        "market_value_eur": [5e6 * p for p in range(1, N_PLAYERS + 1)],
        "contract_expiration_date": pd.to_datetime(["2027-06-30", "2029-06-30"] * (N_PLAYERS // 2)),
        "current_club_at_snapshot": "Home FC", "value_date": pd.Timestamp("2026-06-01"),
        "valuations_as_of": pd.Timestamp("2026-06-12"),
    }).to_parquet(data / "market.parquet", index=False)
    (data / "zones_recent.json").write_text(json.dumps(
        [{"column": f"zone_{i}", "label": f"shots from zone {i}"} for i in (1, 2, 3)]))
    log = data / "experiments.md"
    log.write_text("| date | commit | flags | description | recall@1 | recall@5 | recall@10 | MRR |\n"
                   "|---|---|---|---|---|---|---|---|\n"
                   "| 2026-10-02 | abc | *(none)* | season | 0.1 | 0.2 | 0.258 ± 0.011 | 0.1 |\n"
                   "| 2026-10-02 | def | `--mode recent` | recent | 0.1 | 0.2 | 0.249 ± 0.018 | 0.1 |\n")
    with TestClient(create_app(data, log)) as c:
        yield c


def test_meta(client):
    m = client.get("/meta").json()
    assert m == {"data_window_end": "2026-09-20", "market_snapshot": "2026-06-12", "pool_size": N_PLAYERS,
                 "window_minutes": 2000, "recall_at_10": 0.249}


def test_search(client):
    assert client.get("/players", params={"q": "P3"}).json() == [
        {"id": 3, "name": "P3", "team": "Home FC", "position": "FW"}]
    assert {r["id"] for r in client.get("/players", params={"q": "p1"}).json()} == {1}   # exact name wins
    assert client.get("/players", params={"q": "zzzz"}).json() == []
    assert client.get("/players", params={"q": ""}).status_code == 422


def test_player_profile(client):
    p = client.get("/players/3").json()
    assert p["id"] == 3 and p["active"] is True and p["window_end"] == "2026-09-20"
    assert p["market"]["age"] == 21 and p["market"]["club_at_snapshot"] == "Home FC"
    assert 0 <= p["distinctiveness"] <= 100
    assert all(0 < f["percentile"] <= 100 for f in p["features"])
    assert not any(f["feature"].startswith("zone_") for f in p["features"])
    assert [z["label"] for z in p["zones"]] == ["shots from zone 1", "shots from zone 2", "shots from zone 3"]
    assert sum(z["weight"] for z in p["zones"]) == pytest.approx(1)
    labels = {f["feature"]: f["label"] for f in p["features"]}
    assert labels["shot_type_left_foot"] == "share of shots with the left foot"


def test_unknown_player_is_404(client):
    assert client.get("/players/999").status_code == 404
    assert client.get("/players/999/similar").status_code == 404


def test_similar_ranking_limit_and_inactive(client):
    s = client.get("/players/3/similar", params={"limit": 5}).json()
    sims = [r["similarity"] for r in s["results"]]
    assert len(sims) == 5 and sims == sorted(sims, reverse=True)
    ids = {r["id"] for r in s["results"]}
    assert 3 not in ids and s["inactive_excluded"] == 1
    everyone = client.get("/players/3/similar", params={"limit": 100}).json()["results"]
    assert 2 not in {r["id"] for r in everyone} and len(everyone) == N_PLAYERS - 2
    with_inactive = client.get("/players/3/similar", params={"limit": 100, "include_inactive": True}).json()
    assert 2 in {r["id"] for r in with_inactive["results"]} and with_inactive["inactive_excluded"] == 0


def test_similar_filters(client):
    s = client.get("/players/3/similar", params={"max_age": 24, "max_value": 30, "contract_before": 2028,
                                                  "limit": 100}).json()
    assert s["results"] and all(r["age"] <= 24 and r["market_value_m"] <= 30 and r["contract_end"] < "2028"
                                for r in s["results"])
    assert s["removed_by_filters"] == s["candidates"] - len(s["results"])


def test_explanation_contributions(client):
    for r in client.get("/players/3/similar", params={"limit": 100}).json()["results"]:
        e = r["explanation"]
        assert e["total"] == pytest.approx(r["similarity"], abs=1e-3)   # contributions sum to the cosine
        top = [t["contribution"] for t in e["top"]]
        assert len(top) == 3 and top == sorted(top, reverse=True)
        assert e["against"]["contribution"] <= min(top)
        assert all(t["label"] for t in e["top"])


def test_map(client):
    m = client.get("/map").json()
    assert len(m["players"]) == N_PLAYERS and len(m["explained_variance"]) == 2
    assert all(np.isfinite([p["x"], p["y"]]).all() for p in m["players"])
    assert {p["id"] for p in m["players"] if p["active"] is False} == {2}


def test_cors_for_local_frontend(client):
    r = client.get("/meta", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in client.get("/meta", headers={"Origin": "http://evil.example"}).headers
