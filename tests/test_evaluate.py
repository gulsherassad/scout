"""Tests for split-half self-retrieval on small hand-built data."""
import numpy as np
import pandas as pd
import pytest

import scout.evaluate as ev
from scout.evaluate import baseline, evaluate, metrics, own_ranks, split_halves, summarise
from scout.features import KEYS, build_profiles, last_action_categories, shot_grids, shots_in

from test_features import app, shot


def season_apps(n_players=12, n_matches=10):
    return pd.DataFrame([app(m, player_id=p, xA=0.05 * p, xGChain=0.1 * p, xGBuildup=0.02 * p)
                         for p in range(1, n_players + 1) for m in range(n_matches)])


def test_split_puts_every_appearance_in_exactly_one_half():
    apps = season_apps(n_players=3, n_matches=7)
    in_a = split_halves(apps, seed=0)
    assert in_a.index.equals(apps.index) and in_a.dtype == bool
    per_player = in_a.groupby(apps["player_id"]).agg(["sum", "size"])
    assert (per_player["sum"] == 3).all() and (per_player["size"] == 7).all()
    assert not split_halves(apps, seed=0).ne(in_a).any()      # same seed, same split
    assert split_halves(apps, seed=1).ne(in_a).any()          # different seed, different split
    shuffled = apps.sample(frac=1, random_state=5)            # input order doesn't matter
    assert split_halves(shuffled, seed=0).reindex(apps.index).equals(in_a)


def test_identical_halves_rank_first():
    z = np.random.default_rng(0).normal(size=(30, 8))
    assert (own_ranks(z, z) == 1).all()
    assert (own_ranks(z[:, :1], z[:, :1]) == 1).all()        # single-feature path


def test_ties_count_against_player():
    za = np.array([[1.0, 0.0], [2.0, 0.0]])                   # same direction: cosine ties
    assert own_ranks(za, za).tolist() == [2, 2]


def test_metrics_on_tiny_example():
    m = metrics(np.array([1, 2, 6, 11]))
    assert m["recall@1"] == 0.25
    assert m["recall@5"] == 0.5
    assert m["recall@10"] == 0.75
    assert m["MRR"] == pytest.approx((1 + 1 / 2 + 1 / 6 + 1 / 11) / 4)
    b = baseline(4)
    assert b["recall@1"] == 0.25 and b["recall@10"] == 2.5
    assert b["MRR"] == pytest.approx((1 + 1 / 2 + 1 / 3 + 1 / 4) / 4)


def test_end_to_end_on_synthetic_data():
    apps = season_apps()
    rng = np.random.default_rng(0)
    shots = pd.DataFrame([shot(m, player_id=p, xG=0.02 * p,
                               shotType=["Head", "LeftFoot", "RightFoot"][p % 3],
                               lastAction=["Pass", "Cross", None][p % 3])
                          for p in range(1, 13) for m in range(10) for _ in range(rng.integers(0, 3))])
    pool = build_profiles(shots, apps, zones=0).set_index(KEYS)
    ranks, imputed = evaluate(shots, apps, pool, seeds=range(2), zones=0)
    assert len(ranks) == 2 * 4 * len(pool)                    # seeds x feature sets x players
    assert ranks["rank"].between(1, len(pool)).all()
    report = summarise(ranks, pool, imputed)
    assert "## Retrieval metrics" in report and "random guess" in report


def test_stratified_split_halves_starts_and_subs_separately():
    apps = pd.concat([season_apps(n_players=2, n_matches=6),
                      pd.DataFrame([app(m, player_id=p, position="Sub", minutes=20)
                                    for p in (1, 2) for m in range(6, 10)])], ignore_index=True)
    in_a = split_halves(apps, seed=3, split="stratified")
    per = in_a.groupby([apps["player_id"], apps["started"]]).sum()
    assert (per.xs(True, level="started") == 3).all()        # 6 starts -> 3 in A
    assert (per.xs(False, level="started") == 2).all()       # 4 subs -> 2 in A


def test_euclidean_identical_halves_rank_first():
    z = np.random.default_rng(1).normal(size=(30, 8))
    assert (own_ranks(z, z, metric="euclidean") == 1).all()
    za = np.array([[1.0, 0.0], [2.0, 0.0]])                   # cosine ties, distance doesn't
    assert own_ranks(za, za, metric="euclidean").tolist() == [1, 1]


def test_zone_nmf_fitted_on_half_a_only(monkeypatch):
    apps = season_apps(n_players=8, n_matches=10)
    rng = np.random.default_rng(0)
    shots = pd.DataFrame([shot(m, player_id=p, X=rng.uniform(0.8, 0.97), Y=rng.uniform(0.1, 0.9))
                          for p in range(1, 9) for m in range(10) for _ in range(2)])
    pool = build_profiles(shots, apps, zones=0).set_index(KEYS)
    fitted = []
    real_fit = ev.fit_shot_zones
    monkeypatch.setattr(ev, "fit_shot_zones", lambda g, k: fitted.append(g) or real_fit(g, k))

    a, b = ev.half_profiles(shots, apps, pool, seed=4, last_actions=last_action_categories(shots), zones=3)
    in_a = split_halves(apps, seed=4)
    expected = shot_grids(shots_in(shots, apps[in_a])).reindex(pool.index)
    assert len(fitted) == 1
    pd.testing.assert_frame_equal(fitted[0], expected)
    assert not fitted[0].equals(shot_grids(shots_in(shots, apps[~in_a])).reindex(pool.index))
    assert [c for c in a.columns if c.startswith("zone_")] == ["zone_1", "zone_2", "zone_3"]
    assert np.allclose(b.filter(like="zone_").sum(axis=1), 1)
