# Split-half self-retrieval: recent mode (each player's newest 2000 league minutes across seasons), random split, cosine similarity, no shrinkage, shot-location zones from NMF with 6 components (fitted on half A)

Generated 2026-10-02 by `python -m scout.evaluate --mode recent`.

## Setup
- **Population:** 522 player-seasons from `profiles_recent.parquet` (EPL 123, La_liga 119, Serie_A 99, Bundesliga 91, Ligue_1 90).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 522 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** recent mode (each player's newest 2000 league minutes across seasons), random split, cosine similarity, no shrinkage, shot-location zones from NMF with 6 components (fitted on half A).
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 3.5 per split on average, out of 31320.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| all features | 0.058 ± 0.009 | 0.166 ± 0.013 | 0.249 ± 0.018 | 0.125 ± 0.009 |
| rates only | 0.016 ± 0.005 | 0.064 ± 0.014 | 0.114 ± 0.015 | 0.054 ± 0.007 |
| style only | 0.017 ± 0.004 | 0.064 ± 0.008 | 0.111 ± 0.011 | 0.055 ± 0.005 |
| zones only | 0.013 ± 0.004 | 0.062 ± 0.012 | 0.111 ± 0.014 | 0.051 ± 0.006 |
| npxG per 90 only | 0.005 ± 0.003 | 0.023 ± 0.007 | 0.044 ± 0.011 | 0.025 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.019 | 0.013 |

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.019 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 51 | 0.118 ± 0.045 |
| 20–39 | 216 | 0.197 ± 0.031 |
| 40+ | 255 | 0.320 ± 0.024 |

## Recall@10 by primary position (all features)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 121 | 0.244 ± 0.025 |
| AML | 57 | 0.248 ± 0.052 |
| AMR | 53 | 0.279 ± 0.045 |
| FW | 219 | 0.248 ± 0.021 |
| FWL | 20 | 0.193 ± 0.086 |
| FWR | 21 | 0.243 ± 0.098 |
| ML | 15 | 0.223 ± 0.090 |
| MR | 16 | 0.306 ± 0.103 |

## Hardest players to re-identify (all features)
The 10 players with the worst mean rank across splits (out of 522).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 412.8 | 135 / 519 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 384.9 | 212 / 491 |
| Benedict Hollerbach | Mainz 05 | FW | 24 | 916 | 382.1 | 294 / 491 |
| Amin Sarr | Verona | FW | 19 | 1046 | 368.2 | 126 / 501 |
| Shuto Machino | Borussia M.Gladbach | FW | 29 | 1090 | 330.7 | 130 / 478 |
| Patrick Wimmer | Wolfsburg, Hoffenheim | AML | 33 | 1884 | 320.0 | 79 / 482 |
| Mateo Joseph | Mallorca | FW | 33 | 1707 | 306.4 | 118 / 467 |
| Iliman Ndiaye | Everton, Manchester City | AML | 34 | 2010 | 302.4 | 99 / 430 |
| Yuito Suzuki | Freiburg | AMC | 46 | 1973 | 299.4 | 38 / 487 |
| Patrick Cutrone | Parma Calcio 1913, Monza | FW | 29 | 1099 | 292.2 | 44 / 453 |
