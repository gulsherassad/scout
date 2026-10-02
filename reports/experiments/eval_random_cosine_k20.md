# Split-half self-retrieval: random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 20

Generated 2026-10-02 by `python -m scout.evaluate --shrinkage-k 20`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split into halves A and B. Profiles built on B are matched against all 493 A profiles on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Configuration:** random split, cosine similarity, shot-style shares shrunk towards pool-wide shares with k = 20.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 0.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.035 ± 0.007 | 0.123 ± 0.009 | 0.196 ± 0.014 | 0.092 ± 0.007 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.015 ± 0.004 | 0.063 ± 0.012 | 0.111 ± 0.013 | 0.052 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.123 ± 0.042 |
| 20–39 | 208 | 0.133 ± 0.022 |
| 40+ | 231 | 0.271 ± 0.024 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.193 ± 0.024 |
| AML | 54 | 0.151 ± 0.028 |
| AMR | 44 | 0.220 ± 0.040 |
| FW | 207 | 0.206 ± 0.020 |
| FWL | 20 | 0.225 ± 0.085 |
| FWR | 20 | 0.193 ± 0.063 |
| ML | 16 | 0.125 ± 0.081 |
| MR | 18 | 0.217 ± 0.062 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 398.9 | 174 / 488 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 376.4 | 310 / 459 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 359.4 | 130 / 475 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 356.0 | 44 / 486 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 348.4 | 91 / 460 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 337.9 | 161 / 458 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 329.8 | 158 / 438 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 313.0 | 21 / 475 |
| Tom Louchet | Nice | AML | 21 | 1344 | 307.9 | 78 / 455 |
| Adam Daghim | Wolfsburg | AMR | 27 | 1328 | 303.6 | 122 / 428 |

## Baseline's hardest players under this configuration
Average of the mean ranks: 339.2 in the baseline, 339.9 here.

| player | baseline mean rank | mean rank here |
|---|---|---|
| Shuto Machino | 401.4 | 398.9 |
| Benedict Hollerbach | 397.3 | 376.4 |
| Santiago Hidalgo | 351.7 | 359.4 |
| Amin Sarr | 349.4 | 288.0 |
| Lovro Majer | 345.2 | 356.0 |
| Amine Adli | 326.0 | 337.9 |
| Danny Namaso | 314.2 | 348.4 |
| Maximilian Beier | 312.0 | 329.8 |
| Arnaud Kalimuendo Muinga | 299.2 | 313.0 |
| Tijjani Noslin | 295.4 | 291.2 |
