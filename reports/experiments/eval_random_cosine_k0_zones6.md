# Split-half self-retrieval: random split, cosine similarity, no shrinkage, shot-location zones from NMF with 6 components (fitted on half A)

Generated 2026-10-02 by `python -m scout.evaluate --zones 6`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, no shrinkage, shot-location zones from NMF with 6 components (fitted on half A).
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 5.8 per split on average, out of 29580.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| all features | 0.059 ± 0.009 | 0.178 ± 0.012 | 0.258 ± 0.011 | 0.128 ± 0.008 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.016 ± 0.004 | 0.068 ± 0.013 | 0.112 ± 0.013 | 0.054 ± 0.006 |
| zones only | 0.016 ± 0.005 | 0.065 ± 0.008 | 0.118 ± 0.012 | 0.055 ± 0.004 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.118 ± 0.033 |
| 20–39 | 208 | 0.182 ± 0.019 |
| 40+ | 231 | 0.360 ± 0.017 |

## Recall@10 by primary position (all features)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.246 ± 0.023 |
| AML | 54 | 0.271 ± 0.046 |
| AMR | 44 | 0.284 ± 0.052 |
| FW | 207 | 0.248 ± 0.017 |
| FWL | 20 | 0.292 ± 0.059 |
| FWR | 20 | 0.245 ± 0.072 |
| ML | 16 | 0.206 ± 0.106 |
| MR | 18 | 0.375 ± 0.092 |

## Hardest players to re-identify (all features)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 397.8 | 345 / 483 |
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 390.0 | 165 / 484 |
| Amin Sarr | Verona | FW | 19 | 1046 | 373.3 | 250 / 454 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 369.0 | 134 / 487 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 358.8 | 144 / 482 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 353.2 | 85 / 460 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 350.6 | 126 / 472 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 329.4 | 158 / 462 |
| Patrick Wimmer | Wolfsburg | AML | 24 | 1678 | 294.5 | 38 / 476 |
| Roberto Navarro | Athletic Club | AML | 21 | 1246 | 278.6 | 7 / 465 |

## Paired comparison with the baseline (all features)
Recall@10 here minus the baseline's, on the same 20 splits.

| group | players | recall@10 change | splits better / worse |
|---|---|---|---|
| all | 493 | +0.053 | 20 / 0 |
| <20 shots | 54 | +0.036 | 16 / 1 |
| 20–39 shots | 208 | +0.046 | 20 / 0 |
| 40+ shots | 231 | +0.064 | 20 / 0 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 342.2 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 390.0 |
| Benedict Hollerbach | 397.3 | 397.8 |
| Santiago Hidalgo | 351.7 | 353.2 |
| Amin Sarr | 349.4 | 373.3 |
| Lovro Majer | 345.2 | 369.0 |
| Amine Adli | 326.0 | 358.8 |
| Danny Namaso | 314.2 | 350.6 |
| Maximilian Beier | 312.0 | 329.4 |
| Arnaud Kalimuendo Muinga | 299.2 | 266.6 |
| Tijjani Noslin | 295.4 | 233.5 |
