# Split-half self-retrieval: random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 40

Generated 2026-10-02 by `python -m scout.evaluate --shrinkage-k 40`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 40.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 0.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.035 ± 0.008 | 0.120 ± 0.009 | 0.195 ± 0.013 | 0.091 ± 0.008 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.015 ± 0.004 | 0.064 ± 0.012 | 0.111 ± 0.012 | 0.052 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.143 ± 0.050 |
| 20–39 | 208 | 0.133 ± 0.022 |
| 40+ | 231 | 0.264 ± 0.023 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.197 ± 0.022 |
| AML | 54 | 0.152 ± 0.029 |
| AMR | 44 | 0.217 ± 0.042 |
| FW | 207 | 0.201 ± 0.021 |
| FWL | 20 | 0.235 ± 0.084 |
| FWR | 20 | 0.198 ± 0.066 |
| ML | 16 | 0.131 ± 0.078 |
| MR | 18 | 0.206 ± 0.065 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 395.8 | 179 / 486 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 367.1 | 295 / 457 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 361.7 | 144 / 475 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 359.6 | 43 / 485 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 356.0 | 97 / 469 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 337.8 | 149 / 467 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 334.3 | 155 / 442 |
| Tom Louchet | Nice | AML | 21 | 1344 | 318.1 | 92 / 455 |
| Adam Daghim | Wolfsburg | AMR | 27 | 1328 | 315.8 | 144 / 444 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 314.2 | 24 / 473 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 338.3 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 395.8 |
| Benedict Hollerbach | 397.3 | 367.1 |
| Santiago Hidalgo | 351.7 | 361.7 |
| Amin Sarr | 349.4 | 264.6 |
| Lovro Majer | 345.2 | 359.6 |
| Amine Adli | 326.0 | 337.8 |
| Danny Namaso | 314.2 | 356.0 |
| Maximilian Beier | 312.0 | 334.3 |
| Arnaud Kalimuendo Muinga | 299.2 | 314.2 |
| Tijjani Noslin | 295.4 | 292.2 |
