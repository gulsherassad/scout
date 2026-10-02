# Split-half self-retrieval: random split, euclidean similarity, no shrinkage

Generated 2026-10-02 by `python -m scout.evaluate --metric euclidean`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, euclidean similarity, no shrinkage.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 4.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.041 ± 0.008 | 0.130 ± 0.012 | 0.201 ± 0.014 | 0.098 ± 0.008 |
| rates only | 0.022 ± 0.006 | 0.078 ± 0.011 | 0.130 ± 0.010 | 0.063 ± 0.006 |
| style only | 0.018 ± 0.005 | 0.071 ± 0.012 | 0.118 ± 0.013 | 0.057 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.054 ± 0.033 |
| 20–39 | 208 | 0.107 ± 0.020 |
| 40+ | 231 | 0.319 ± 0.025 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.203 ± 0.028 |
| AML | 54 | 0.185 ± 0.055 |
| AMR | 44 | 0.211 ± 0.050 |
| FW | 207 | 0.207 ± 0.019 |
| FWL | 20 | 0.183 ± 0.063 |
| FWR | 20 | 0.180 ± 0.083 |
| ML | 16 | 0.144 ± 0.064 |
| MR | 18 | 0.233 ± 0.069 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Khalis Merah | Lyon | AMC | 6 | 1187 | 468.3 | 394 / 493 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 452.4 | 379 / 493 |
| Antonio Sánchez | Mallorca | AMR | 6 | 1016 | 402.0 | 43 / 493 |
| Evann Guessand | Aston Villa, Crystal Palace | AMR | 11 | 920 | 398.3 | 121 / 493 |
| Henrik Meister | Pisa | FW | 20 | 1494 | 363.8 | 67 / 491 |
| Adam Karabec | Lyon | AMR | 9 | 922 | 343.8 | 78 / 493 |
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 342.2 | 44 / 489 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 341.5 | 160 / 471 |
| Mathias Honsak | FC Heidenheim | ML | 31 | 1263 | 339.6 | 18 / 476 |
| André Almeida | Valencia | AMC | 7 | 1007 | 334.8 | 35 / 487 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 241.6 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 342.2 |
| Benedict Hollerbach | 397.3 | 452.4 |
| Santiago Hidalgo | 351.7 | 216.6 |
| Amin Sarr | 349.4 | 312.2 |
| Lovro Majer | 345.2 | 172.4 |
| Amine Adli | 326.0 | 341.5 |
| Danny Namaso | 314.2 | 71.5 |
| Maximilian Beier | 312.0 | 146.8 |
| Arnaud Kalimuendo Muinga | 299.2 | 188.4 |
| Tijjani Noslin | 295.4 | 172.0 |
