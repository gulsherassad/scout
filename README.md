# scout

Find attacking players with a similar style across Europe's top 5 leagues, from current-season [Understat](https://understat.com) data.

![Shot-location zones learned by NMF: six heatmaps on a half pitch](reports/figures/shot_zones_k6.png)

*The six shot-location zones learned from all attackers' shots; each player's profile includes how their shots split across them.*

**Status:** early development. Ingestion, parsing, features, evaluation and similarity search work; the pipeline is not yet scheduled.

## Example

```
$ python -m scout.similar "Saka"
                 player                teams      league position  minutes  similarity
1          Nicolas Pepe           Villarreal     La_liga       MR     2407       0.871
2       Ousmane Dembélé  Paris Saint Germain     Ligue_1       FW     1050       0.865
3          Lamine Yamal            Barcelona     La_liga      AMR     2291       0.864
4         Mohamed Salah            Liverpool         EPL      AMR     2163       0.850
5       Florian Thauvin                 Lens     Ligue_1      AMC     2510       0.849
6                Antony           Real Betis     La_liga      AMR     2495       0.845
7         Michael Olise        Bayern Munich  Bundesliga      AMR     2308       0.809
8       Mason Greenwood            Marseille     Ligue_1      AMR     2503       0.806
9   Francisco Conceição             Juventus     Serie_A      AMC     2124       0.796
10         Paulo Dybala                 Roma     Serie_A      AMC     1360       0.719
```

## How it works

**Data:** 2025/26 season, EPL, La Liga, Bundesliga, Serie A and Ligue 1: 1,752 matches and about 44k shots.

**Pipeline:**
1. `scout.ingest` downloads league and match data from Understat and caches it.
2. `scout.parse` builds shot and appearance tables and runs validation checks. If any check fails, nothing is written.
3. `scout.features` builds one profile per player-season for attackers with at least 5 starts and 900 minutes (493 players).
4. `scout.evaluate` measures how well the profiles identify players (see below).

**Features** (z-scored, compared by cosine similarity):
- **Per-90 rates:** non-penalty xG, shots, xA, key passes, xGChain and xGBuildup, plus npxG per shot and xGBuildup's share of xGChain.
- **Chance-creation style shares:** how a player's shots split by the action before the shot (pass, cross, take-on, rebound, …) and by body part.
- **Shot zones:** a smoothed heatmap of each player's shot locations, reduced to weights on six zones with non-negative matrix factorisation (NMF), following Decroos et al., "Player Vectors". Flanks are not mirrored, because the side a player shoots from is part of their style.

Shot-based features leave out own goals, penalties and direct free kicks.

## Evaluation

There are no labels for "similar players", so the benchmark tests self-retrieval instead. Each player's matches are split at random into two halves, and a profile is built from each half. A good profile should rank a player's own other half among the most similar of all 493.

Results over 20 random splits (mean ± std):

| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| rates + style shares | 0.042 ± 0.008 | 0.132 ± 0.011 | 0.205 ± 0.015 | 0.099 ± 0.007 |
| **all features (+ shot zones)** | **0.059 ± 0.009** | **0.178 ± 0.012** | **0.258 ± 0.011** | **0.128 ± 0.008** |

- **Shot zones** improve recall@10 on all 20 splits when compared split by split on the same splits.
- **The number of zones** (k = 6) was tuned on this same benchmark, so that result is slightly optimistic.
- **Full log:** [reports/experiments.md](reports/experiments.md) has every experiment, including the rejected ones (stratified splits, Euclidean distance, shrinking style shares).

## Limitations

- **Attackers only.** Understat has shots and chance creation but no defensive events, so defenders and midfielders can't be profiled fairly.
- **Style, not level.** Cosine similarity compares the shape of a profile, not its size, so a player who does the same things at a lower output can still be a close match.
- **Average-looking players are hard to match.** Profiles close to the pool average are mostly noise. `scout.similar` shows a distinctiveness percentile and warns when a player is in the bottom 20%.
- **Data issues.** Understat has a few quirks, handled at parse time: see [Known data issues](#known-data-issues).

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

python -m scout.ingest --season 2025   # download match data to data/raw/
python -m scout.parse                  # build data/processed/*.parquet and validate
python -m scout.features               # build data/processed/profiles.parquet
python -m scout.evaluate               # write reports/eval_baseline.md
python -m scout.similar "Saka"         # 10 most similar players
pytest
```

## Known data issues

- **Own goals appear as shot rows.** Understat lists an own goal in the shots data (result `OwnGoal`, xG 0), credited to the player who scored it, but counts it under the roster's `own_goals`, not `shots`. These rows are kept and flagged with `is_own_goal`; filter them out for shot-based analysis.
- **Match 29482 (Real Oviedo vs Villarreal, La Liga 2025/26) is duplicated upstream.** Understat sends every roster entry and shot twice, which also doubles its own xG for the match. `scout.parse` removes the duplicates and prints a note when it does.
- **Cached matches are never re-fetched.** `scout.ingest` downloads each finished match once, so any later correction Understat makes to that match is not picked up. To refresh a match, delete its file in `data/raw/matches/` and run ingest again.

## Data

All match data comes from [understat.com](https://understat.com). Credit for the data goes to Understat. It is not included in or redistributed by this repository: `data/` is gitignored, and each user fetches it themselves with `scout.ingest`. It is fetched for non-commercial personal use only.
