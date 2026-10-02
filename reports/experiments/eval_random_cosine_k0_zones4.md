# Split-half self-retrieval: random split, cosine similarity, no shrinkage, shot-location zones from NMF with 4 components (fitted on half A)

Generated 2026-10-02 by `python -m scout.evaluate --zones 4`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, no shrinkage, shot-location zones from NMF with 4 components (fitted on half A).
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 5.2 per split on average, out of 27608.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| all features | 0.056 ± 0.006 | 0.170 ± 0.011 | 0.252 ± 0.014 | 0.123 ± 0.006 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.016 ± 0.004 | 0.068 ± 0.013 | 0.112 ± 0.013 | 0.054 ± 0.006 |
| zones only | 0.013 ± 0.005 | 0.054 ± 0.011 | 0.097 ± 0.015 | 0.048 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.116 ± 0.037 |
| 20–39 | 208 | 0.175 ± 0.021 |
| 40+ | 231 | 0.352 ± 0.021 |

## Recall@10 by primary position (all features)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.237 ± 0.025 |
| AML | 54 | 0.256 ± 0.052 |
| AMR | 44 | 0.276 ± 0.058 |
| FW | 207 | 0.248 ± 0.020 |
| FWL | 20 | 0.275 ± 0.077 |
| FWR | 20 | 0.240 ± 0.070 |
| ML | 16 | 0.181 ± 0.095 |
| MR | 18 | 0.367 ± 0.085 |

## Hardest players to re-identify (all features)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 394.8 | 309 / 475 |
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 387.7 | 121 / 481 |
| Amin Sarr | Verona | FW | 19 | 1046 | 369.4 | 214 / 457 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 361.4 | 151 / 472 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 352.4 | 40 / 485 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 336.8 | 157 / 476 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 329.6 | 176 / 458 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 328.6 | 121 / 455 |
| Che Adams | Torino | FW | 53 | 1899 | 292.7 | 104 / 453 |
| Patrick Wimmer | Wolfsburg | AML | 24 | 1678 | 285.5 | 43 / 473 |

## Paired comparison with the baseline (all features)
Recall@10 here minus the baseline's, on the same 20 splits.

| group | players | recall@10 change | splits better / worse |
|---|---|---|---|
| all | 493 | +0.047 | 20 / 0 |
| <20 shots | 54 | +0.034 | 17 / 1 |
| 20–39 shots | 208 | +0.039 | 19 / 0 |
| 40+ shots | 231 | +0.056 | 20 / 0 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 335.3 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 387.7 |
| Benedict Hollerbach | 397.3 | 394.8 |
| Santiago Hidalgo | 351.7 | 361.4 |
| Amin Sarr | 349.4 | 369.4 |
| Lovro Majer | 345.2 | 352.4 |
| Amine Adli | 326.0 | 336.8 |
| Danny Namaso | 314.2 | 328.6 |
| Maximilian Beier | 312.0 | 329.6 |
| Arnaud Kalimuendo Muinga | 299.2 | 284.8 |
| Tijjani Noslin | 295.4 | 208.0 |
