# Split-half self-retrieval: random split, cosine similarity, no shrinkage, shot-location zones from NMF with 10 components (fitted on half A)

Generated 2026-10-02 by `python -m scout.evaluate --zones 10`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, no shrinkage, shot-location zones from NMF with 10 components (fitted on half A).
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 6.8 per split on average, out of 33524.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| all features | 0.056 ± 0.008 | 0.178 ± 0.014 | 0.258 ± 0.013 | 0.127 ± 0.008 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.016 ± 0.004 | 0.068 ± 0.013 | 0.112 ± 0.013 | 0.054 ± 0.006 |
| zones only | 0.019 ± 0.005 | 0.072 ± 0.011 | 0.123 ± 0.012 | 0.059 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.114 ± 0.034 |
| 20–39 | 208 | 0.189 ± 0.028 |
| 40+ | 231 | 0.355 ± 0.013 |

## Recall@10 by primary position (all features)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.250 ± 0.022 |
| AML | 54 | 0.277 ± 0.044 |
| AMR | 44 | 0.293 ± 0.051 |
| FW | 207 | 0.244 ± 0.020 |
| FWL | 20 | 0.292 ± 0.059 |
| FWR | 20 | 0.227 ± 0.068 |
| ML | 16 | 0.194 ± 0.111 |
| MR | 18 | 0.392 ± 0.093 |

## Hardest players to re-identify (all features)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 397.0 | 96 / 487 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 385.8 | 310 / 477 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 380.3 | 180 / 466 |
| Amin Sarr | Verona | FW | 19 | 1046 | 377.6 | 208 / 470 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 340.4 | 128 / 468 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 339.8 | 196 / 461 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 320.6 | 145 / 437 |
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 279.2 | 99 / 445 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 277.5 | 12 / 479 |
| Roberto Navarro | Athletic Club | AML | 21 | 1246 | 273.2 | 4 / 471 |

## Paired comparison with the baseline (all features)
Recall@10 here minus the baseline's, on the same 20 splits.

| group | players | recall@10 change | splits better / worse |
|---|---|---|---|
| all | 493 | +0.053 | 20 / 0 |
| <20 shots | 54 | +0.032 | 13 / 3 |
| 20–39 shots | 208 | +0.053 | 20 / 0 |
| 40+ shots | 231 | +0.059 | 20 / 0 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 333.3 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 279.2 |
| Benedict Hollerbach | 397.3 | 385.8 |
| Santiago Hidalgo | 351.7 | 340.4 |
| Amin Sarr | 349.4 | 377.6 |
| Lovro Majer | 345.2 | 397.0 |
| Amine Adli | 326.0 | 380.3 |
| Danny Namaso | 314.2 | 339.8 |
| Maximilian Beier | 312.0 | 320.6 |
| Arnaud Kalimuendo Muinga | 299.2 | 277.5 |
| Tijjani Noslin | 295.4 | 235.2 |
