# Split-half self-retrieval: random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 10

Generated 2026-10-02 by `python -m scout.evaluate --shrinkage-k 10`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 10.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 0.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.037 ± 0.006 | 0.124 ± 0.010 | 0.197 ± 0.015 | 0.093 ± 0.007 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.015 ± 0.004 | 0.064 ± 0.012 | 0.112 ± 0.014 | 0.052 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.116 ± 0.037 |
| 20–39 | 208 | 0.131 ± 0.020 |
| 40+ | 231 | 0.276 ± 0.022 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.191 ± 0.024 |
| AML | 54 | 0.153 ± 0.036 |
| AMR | 44 | 0.220 ± 0.042 |
| FW | 207 | 0.210 ± 0.019 |
| FWL | 20 | 0.210 ± 0.077 |
| FWR | 20 | 0.198 ± 0.072 |
| ML | 16 | 0.125 ± 0.079 |
| MR | 18 | 0.208 ± 0.065 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 400.0 | 169 / 486 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 385.2 | 322 / 464 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 355.5 | 124 / 473 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 353.0 | 49 / 486 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 341.0 | 87 / 456 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 336.8 | 168 / 448 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 325.9 | 164 / 438 |
| Amin Sarr | Verona | FW | 19 | 1046 | 310.8 | 153 / 412 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 310.0 | 23 / 474 |
| Tom Louchet | Nice | AML | 21 | 1344 | 298.8 | 66 / 453 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 341.0 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 400.0 |
| Benedict Hollerbach | 397.3 | 385.2 |
| Santiago Hidalgo | 351.7 | 355.5 |
| Amin Sarr | 349.4 | 310.8 |
| Lovro Majer | 345.2 | 353.0 |
| Amine Adli | 326.0 | 336.8 |
| Danny Namaso | 314.2 | 341.0 |
| Maximilian Beier | 312.0 | 325.9 |
| Arnaud Kalimuendo Muinga | 299.2 | 310.0 |
| Tijjani Noslin | 295.4 | 291.8 |
