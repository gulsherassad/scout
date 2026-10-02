# Split-half self-retrieval: random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 5

Generated 2026-10-02 by `python -m scout.evaluate --shrinkage-k 5`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 5.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 0.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.038 ± 0.008 | 0.127 ± 0.011 | 0.199 ± 0.014 | 0.095 ± 0.008 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.015 ± 0.004 | 0.065 ± 0.012 | 0.112 ± 0.014 | 0.053 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.099 ± 0.032 |
| 20–39 | 208 | 0.131 ± 0.018 |
| 40+ | 231 | 0.285 ± 0.021 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.191 ± 0.023 |
| AML | 54 | 0.152 ± 0.036 |
| AMR | 44 | 0.220 ± 0.043 |
| FW | 207 | 0.215 ± 0.016 |
| FWL | 20 | 0.205 ± 0.079 |
| FWR | 20 | 0.195 ± 0.069 |
| ML | 16 | 0.128 ± 0.074 |
| MR | 18 | 0.225 ± 0.075 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 400.4 | 160 / 485 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 391.3 | 336 / 468 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 352.8 | 117 / 472 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 349.8 | 50 / 485 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 333.2 | 86 / 448 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 333.0 | 167 / 441 |
| Amin Sarr | Verona | FW | 19 | 1046 | 327.6 | 169 / 426 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 322.0 | 172 / 438 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 307.6 | 24 / 473 |
| Tijjani Noslin | Lazio | FW | 34 | 1113 | 292.4 | 90 / 464 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 341.0 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 400.4 |
| Benedict Hollerbach | 397.3 | 391.3 |
| Santiago Hidalgo | 351.7 | 352.8 |
| Amin Sarr | 349.4 | 327.6 |
| Lovro Majer | 345.2 | 349.8 |
| Amine Adli | 326.0 | 333.0 |
| Danny Namaso | 314.2 | 333.2 |
| Maximilian Beier | 312.0 | 322.0 |
| Arnaud Kalimuendo Muinga | 299.2 | 307.6 |
| Tijjani Noslin | 295.4 | 292.4 |
