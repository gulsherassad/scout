# Split-half self-retrieval: baseline

Generated 2026-10-02 by `python -m scout.evaluate`.

## Setup
- **Population:** 493 player-seasons from `profiles.parquet` (EPL 116, La_liga 109, Serie_A 93, Ligue_1 88, Bundesliga 87).
- **Method:** each player's appearances are split at random into halves A and B. Profiles built on B are matched against all 493 A profiles by cosine similarity on z-scored features (fitted on A); we record where the player's own A profile ranks.
- **Splits:** 20 (seeds 0–19); metrics are mean ± std across splits.
- **Imputed values** (NaN replaced by A's mean, all features): 4.2 per split on average, out of 23664.
- The single-feature baseline uses minus the absolute difference instead of cosine, which is always ±1 in one dimension. Ties count against the player.

## Retrieval metrics
| features | recall@1 | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| rates + style | 0.042 ± 0.008 | 0.132 ± 0.011 | 0.205 ± 0.015 | 0.099 ± 0.007 |
| rates only | 0.020 ± 0.005 | 0.073 ± 0.010 | 0.124 ± 0.011 | 0.061 ± 0.005 |
| style only | 0.016 ± 0.004 | 0.068 ± 0.013 | 0.112 ± 0.013 | 0.054 ± 0.006 |
| npxG per 90 only | 0.004 ± 0.004 | 0.020 ± 0.005 | 0.043 ± 0.007 | 0.024 ± 0.004 |
| random guess | 0.002 | 0.010 | 0.020 | 0.014 |

## Recall@10 by full-season shot count (rates + style)
Shots exclude own goals, penalties and direct free kicks. Random guess is 0.020 in every bucket.

| shot_bucket | players | recall@10 |
|---|---|---|
| <20 | 54 | 0.081 ± 0.028 |
| 20–39 | 208 | 0.136 ± 0.022 |
| 40+ | 231 | 0.296 ± 0.022 |

## Recall@10 by primary position (rates + style)
| primary_position | players | recall@10 |
|---|---|---|
| AMC | 114 | 0.192 ± 0.027 |
| AML | 54 | 0.162 ± 0.044 |
| AMR | 44 | 0.227 ± 0.044 |
| FW | 207 | 0.222 ± 0.020 |
| FWL | 20 | 0.205 ± 0.074 |
| FWR | 20 | 0.205 ± 0.076 |
| ML | 16 | 0.128 ± 0.052 |
| MR | 18 | 0.228 ± 0.076 |

## Hardest players to re-identify (rates + style)
The 10 players with the worst mean rank across splits (out of 493).

| player | teams | position | shots | minutes | mean rank | best / worst rank |
|---|---|---|---|---|---|---|
| Shuto Machino | Borussia M.Gladbach | FW | 25 | 1046 | 401.4 | 150 / 484 |
| Benedict Hollerbach | Mainz 05 | FW | 22 | 903 | 397.3 | 325 / 467 |
| Santiago Hidalgo | Toulouse | AMC | 34 | 1387 | 351.7 | 90 / 471 |
| Amin Sarr | Verona | FW | 19 | 1046 | 349.4 | 176 / 445 |
| Lovro Majer | Wolfsburg | AMC | 25 | 1390 | 345.2 | 55 / 486 |
| Amine Adli | Bournemouth | AML | 19 | 1036 | 326.0 | 160 / 435 |
| Danny Namaso | Auxerre | ML | 59 | 2544 | 314.2 | 83 / 451 |
| Maximilian Beier | Borussia Dortmund | AMC | 49 | 2069 | 312.0 | 172 / 450 |
| Arnaud Kalimuendo Muinga | Eintracht Frankfurt, Nottingham Forest | FW | 34 | 1506 | 299.2 | 34 / 475 |
| Tijjani Noslin | Lazio | FW | 34 | 1113 | 295.4 | 90 / 466 |
