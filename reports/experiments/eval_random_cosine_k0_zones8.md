# Split-half self-retrieval: random split, cosine similarity, no shrinkage, shot-location zones from NMF with 8 components (fitted on half A)

Generated 2026-10-02 by `python -m scout.evaluate --zones 8`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, no shrinkage, shot-location zones from NMF with 8 components (fitted on half A).
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 6.2 per split on average, out of 31552.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| all features | 0.058 ± 0.010 | 0.175 ± 0.012 | 0.258 ± 0.014 | 0.127 ± 0.009 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.016 ± 0.004 | 0.068 ± 0.013 | 0.112 ± 0.013 | 0.054 ± 0.006 |
| zones only | 0.018 ± 0.005 | 0.071 ± 0.011 | 0.119 ± 0.014 | 0.058 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (all features)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.123 ± 0.039 |
| 20–39 | 208 | 0.185 ± 0.025 |
| 40+ | 231 | 0.354 ± 0.018 |

## Recall@10 by primary position (all features)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.251 ± 0.022 |
| AML | 54 | 0.264 ± 0.048 |
| AMR | 44 | 0.294 ± 0.052 |
| FW | 207 | 0.244 ± 0.018 |
| FWL | 20 | 0.285 ± 0.067 |
| FWR | 20 | 0.222 ± 0.062 |
| ML | 16 | 0.216 ± 0.096 |
| MR | 18 | 0.389 ± 0.100 |

## Hardest players to re-identify (all features)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 392.2 | 121 / 489 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 389.6 | 319 / 470 |
| Amin Sarr | Verona | FW | 19 | 1046 | 386.4 | 238 / 456 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 380.4 | 144 / 476 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 343.6 | 180 / 464 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 341.0 | 104 / 477 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 322.6 | 145 / 443 |
| Roberto Navarro | Athletic Club | AML | 21 | 1246 | 294.7 | 10 / 461 |
| Morgan Gibbs-White | Nottingham Forest | AMC | 77 | 3142 | 287.0 | 48 / 423 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 273.4 | 17 / 479 |

## Paired comparison with the baseline (all features)
Recall@10 here minus the baseline's, on the same 20 splits.

| group | players | recall@10 change | splits better / worse |
|---|---|---|---|
| all | 493 | +0.053 | 20 / 0 |
| <20 shots | 54 | +0.042 | 14 / 1 |
| 20–39 shots | 208 | +0.049 | 20 / 0 |
| 40+ shots | 231 | +0.058 | 20 / 0 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 335.2 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 273.2 |
| Benedict Hollerbach | 397.3 | 389.6 |
| Santiago Hidalgo | 351.7 | 341.0 |
| Amin Sarr | 349.4 | 386.4 |
| Lovro Majer | 345.2 | 392.2 |
| Amine Adli | 326.0 | 380.4 |
| Danny Namaso | 314.2 | 343.6 |
| Maximilian Beier | 312.0 | 322.6 |
| Arnaud Kalimuendo Muinga | 299.2 | 273.4 |
| Tijjani Noslin | 295.4 | 250.0 |
